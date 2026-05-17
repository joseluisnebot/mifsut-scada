import asyncio
import os
import sys
import logging
import time
import yaml
import paho.mqtt.client as mqtt

sys.path.insert(0, "/app")
from base_driver import BaseDriver

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger("driver.snmp")

MOCK = os.getenv("MOCK_DEVICES", "true").lower() == "true"
MQTT_HOST = os.getenv("MQTT_HOST", "mosquitto")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
DEVICES_PATH = os.getenv("SNMP_DEVICES_PATH", "/app/devices/snmp")
TEMPLATES_PATH = "/app/templates/snmp"


class SnmpDriver(BaseDriver):
    def __init__(self, device_config, template, mqtt_client):
        super().__init__(device_config, template, mqtt_client)
        self._engine = None
        self._community = None
        self._version = None
        self._host = None
        self._port = 161

    async def connect(self) -> bool:
        if MOCK:
            logger.info(f"[{self.device_id}] MOCK connect OK")
            return True
        try:
            from pysnmp.hlapi.asyncio import SnmpEngine
            self._engine = SnmpEngine()
            self._host = self.config["connection"]["host"]
            self._port = int(self.config["connection"].get("port", 161))
            self._community = self.template.get("community", "public")
            version_map = {"v1": 0, "v2c": 1}
            self._version = version_map.get(self.template.get("version", "v2c"), 1)
            logger.info(f"[{self.device_id}] SNMP connect OK → {self._host}:{self._port}")
            return True
        except Exception as e:
            logger.error(f"[{self.device_id}] connect error: {e}")
            return False

    async def disconnect(self): ...

    async def read_tag(self, tag: dict) -> dict:
        if MOCK:
            return await self.mock_value(tag)
        try:
            from pysnmp.hlapi.asyncio import (
                getCmd, CommunityData, UdpTransportTarget,
                ContextData, ObjectType, ObjectIdentity
            )
            error_indication, error_status, _, var_binds = await getCmd(
                self._engine,
                CommunityData(self._community, mpModel=self._version),
                UdpTransportTarget((self._host, self._port), timeout=2, retries=1),
                ContextData(),
                ObjectType(ObjectIdentity(tag["oid"]))
            )
            if error_indication:
                logger.warning(f"[{self.device_id}] {tag['id']}: {error_indication}")
                return None
            if error_status:
                logger.warning(f"[{self.device_id}] {tag['id']}: {error_status.prettyPrint()}")
                return None
            raw = var_binds[0][1].prettyPrint()
            try:
                value = float(raw) * tag.get("scale", 1)
            except ValueError:
                value = raw
            return {
                "value": value,
                "unit": tag.get("unit", ""),
                "ts": int(time.time() * 1000),
                "quality": "good",
                "protocol": self.protocol,
            }
        except Exception as e:
            logger.error(f"[{self.device_id}] read_tag {tag['id']} error: {e}")
            return None

    async def write_tag(self, tag: dict, value) -> bool:
        logger.warning(f"[{self.device_id}] SNMP write not implemented")
        return False


def load_devices():
    devices = []
    if not os.path.isdir(DEVICES_PATH):
        return devices
    for fname in os.listdir(DEVICES_PATH):
        if fname.endswith((".yaml", ".yml")):
            with open(os.path.join(DEVICES_PATH, fname)) as f:
                devices.append(yaml.safe_load(f))
    return devices


def load_template(name: str) -> dict:
    for ext in (".yaml", ".yml"):
        path = os.path.join(TEMPLATES_PATH, f"{name}{ext}")
        if os.path.exists(path):
            with open(path) as f:
                return yaml.safe_load(f)
    raise FileNotFoundError(name)


def get_template_mtime(name: str) -> float:
    for ext in (".yaml", ".yml"):
        path = os.path.join(TEMPLATES_PATH, f"{name}{ext}")
        if os.path.exists(path):
            return os.path.getmtime(path)
    return 0.0


async def main():
    try:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id="driver-snmp")
    except AttributeError:
        client = mqtt.Client(client_id="driver-snmp")
    client.connect(MQTT_HOST, MQTT_PORT, 60)
    client.loop_start()

    running: dict[str, asyncio.Task] = {}
    template_mtimes: dict[str, float] = {}

    while True:
        devices = load_devices()
        current_ids = set()
        for dev in devices:
            did = dev.get("device_id")
            if not did:
                continue
            current_ids.add(did)
            tpl_name = dev.get("template", "generic-snmp")
            mtime = get_template_mtime(tpl_name)

            template_changed = did in template_mtimes and template_mtimes[did] != mtime
            if template_changed and did in running:
                running[did].cancel()
                del running[did]
                logger.info(f"[{did}] template modificado, reiniciando...")

            if did not in running or running[did].done():
                try:
                    template = load_template(tpl_name)
                except FileNotFoundError:
                    logger.warning(f"Template no encontrado para {did}, ignorando")
                    continue
                template_mtimes[did] = mtime
                logger.info(f"Iniciando driver para {did}")
                running[did] = asyncio.create_task(SnmpDriver(dev, template, client).poll_loop())

        # cancelar tareas de dispositivos eliminados
        for did in list(running):
            if did not in current_ids:
                running[did].cancel()
                del running[did]
                logger.info(f"Driver detenido para {did}")

        await asyncio.sleep(30)


if __name__ == "__main__":
    asyncio.run(main())

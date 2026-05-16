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

    async def connect(self) -> bool:
        if MOCK:
            logger.info(f"[{self.device_id}] MOCK connect OK")
            return True
        return True

    async def disconnect(self): ...

    async def read_tag(self, tag: dict) -> dict:
        if MOCK:
            return await self.mock_value(tag)
        try:
            from pysnmp.hlapi.asyncio import (
                getCmd, SnmpEngine, CommunityData, UdpTransportTarget,
                ContextData, ObjectType, ObjectIdentity
            )
            host = self.config["connection"]["host"]
            community = self.template.get("community", "public")
            version_map = {"v1": 0, "v2c": 1}
            version = version_map.get(self.template.get("version", "v2c"), 1)

            error_indication, error_status, error_index, var_binds = await getCmd(
                SnmpEngine(),
                CommunityData(community, mpModel=version),
                UdpTransportTarget((host, 161)),
                ContextData(),
                ObjectType(ObjectIdentity(tag["oid"]))
            )
            if error_indication or error_status:
                return None
            value = var_binds[0][1].prettyPrint()
            try:
                value = float(value)
            except ValueError:
                pass
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


async def main():
    try:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id="driver-snmp")
    except AttributeError:
        client = mqtt.Client(client_id="driver-snmp")
    client.connect(MQTT_HOST, MQTT_PORT, 60)
    client.loop_start()

    devices = load_devices()
    if not devices:
        devices = [{
            "device_id": "switch-snmp-demo",
            "template": "generic-snmp",
            "connection": {"host": "192.168.1.1"},
            "poll_interval_ms": 5000,
        }]

    tasks = []
    for dev in devices:
        try:
            template = load_template(dev.get("template", "generic-snmp"))
        except FileNotFoundError:
            continue
        tasks.append(asyncio.create_task(SnmpDriver(dev, template, client).poll_loop()))

    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())

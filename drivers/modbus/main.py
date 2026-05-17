import asyncio
import os
import sys
import logging
import yaml
import paho.mqtt.client as mqtt

sys.path.insert(0, "/app")
from base_driver import BaseDriver

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger("driver.modbus")

MOCK = os.getenv("MOCK_DEVICES", "true").lower() == "true"
MQTT_HOST = os.getenv("MQTT_HOST", "mosquitto")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
DEVICES_PATH = os.getenv("MODBUS_DEVICES_PATH", "/app/devices/modbus")
TEMPLATES_PATH = "/app/templates/modbus"


class ModbusDriver(BaseDriver):
    def __init__(self, device_config, template, mqtt_client):
        super().__init__(device_config, template, mqtt_client)
        self.client = None

    async def connect(self) -> bool:
        if MOCK:
            logger.info(f"[{self.device_id}] MOCK connect OK")
            return True
        try:
            from pymodbus.client import AsyncModbusTcpClient
            host = self.config["connection"]["host"]
            port = self.config["connection"].get("port", 502)
            self.client = AsyncModbusTcpClient(host, port=port)
            await self.client.connect()
            return self.client.connected
        except Exception as e:
            logger.error(f"[{self.device_id}] connect error: {e}")
            return False

    async def disconnect(self):
        if self.client:
            self.client.close()

    async def read_tag(self, tag: dict) -> dict:
        if MOCK:
            return await self.mock_value(tag)
        try:
            from pymodbus.client import AsyncModbusTcpClient
            unit_id = self.config["connection"].get("unit_id", 1)
            address = tag["address"] - 40001
            result = await self.client.read_holding_registers(address, 2, slave=unit_id)
            if result.isError():
                return None
            raw = result.registers[0]
            scale = tag.get("scale", 1)
            value = raw * scale
            import time
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
        if MOCK:
            logger.info(f"[{self.device_id}] MOCK write {tag['id']} = {value}")
            return True
        try:
            unit_id = self.config["connection"].get("unit_id", 1)
            address = tag["address"] - 40001
            scale = tag.get("scale", 1)
            raw = int(value / scale)
            result = await self.client.write_register(address, raw, slave=unit_id)
            return not result.isError()
        except Exception as e:
            logger.error(f"[{self.device_id}] write_tag error: {e}")
            return False


def load_devices():
    devices = []
    if not os.path.isdir(DEVICES_PATH):
        return devices
    for fname in os.listdir(DEVICES_PATH):
        if fname.endswith(".yaml") or fname.endswith(".yml"):
            with open(os.path.join(DEVICES_PATH, fname)) as f:
                devices.append(yaml.safe_load(f))
    return devices


def load_template(template_name: str) -> dict:
    path = os.path.join(TEMPLATES_PATH, f"{template_name}.yaml")
    if not os.path.exists(path):
        path = os.path.join(TEMPLATES_PATH, f"{template_name}.yml")
    with open(path) as f:
        return yaml.safe_load(f)


def get_template_mtime(template_name: str) -> float:
    for ext in (".yaml", ".yml"):
        path = os.path.join(TEMPLATES_PATH, f"{template_name}{ext}")
        if os.path.exists(path):
            return os.path.getmtime(path)
    return 0.0


async def main():
    try:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id="driver-modbus")
    except AttributeError:
        client = mqtt.Client(client_id="driver-modbus")
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
            tpl_name = dev.get("template", "generic-modbus")
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
                    logger.error(f"Template {tpl_name} not found, skipping {did}")
                    continue
                template_mtimes[did] = mtime
                logger.info(f"Iniciando driver para {did}")
                running[did] = asyncio.create_task(ModbusDriver(dev, template, client).poll_loop())

        for did in list(running):
            if did not in current_ids:
                running[did].cancel()
                del running[did]
                logger.info(f"Driver detenido para {did}")

        await asyncio.sleep(30)


if __name__ == "__main__":
    asyncio.run(main())

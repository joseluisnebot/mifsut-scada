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
logger = logging.getLogger("driver.dnp3")

MOCK = os.getenv("MOCK_DEVICES", "true").lower() == "true"
MQTT_HOST = os.getenv("MQTT_HOST", "mosquitto")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
DEVICES_PATH = os.getenv("DNP3_DEVICES_PATH", "/app/devices/dnp3")
TEMPLATES_PATH = "/app/templates/dnp3"


class Dnp3Driver(BaseDriver):
    def __init__(self, device_config, template, mqtt_client):
        super().__init__(device_config, template, mqtt_client)

    async def connect(self) -> bool:
        if MOCK:
            logger.info(f"[{self.device_id}] MOCK connect OK")
            return True
        try:
            logger.warning(f"[{self.device_id}] Real DNP3 requires pydnp3 native build")
            return False
        except Exception as e:
            logger.error(f"[{self.device_id}] connect error: {e}")
            return False

    async def disconnect(self): ...

    async def read_tag(self, tag: dict) -> dict:
        if MOCK:
            return await self.mock_value(tag)
        return None

    async def write_tag(self, tag: dict, value) -> bool:
        if MOCK:
            logger.info(f"[{self.device_id}] MOCK write {tag['id']} = {value}")
            return True
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
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id="driver-dnp3")
    except AttributeError:
        client = mqtt.Client(client_id="driver-dnp3")
    client.connect(MQTT_HOST, MQTT_PORT, 60)
    client.loop_start()

    devices = load_devices()
    if not devices:
        devices = [{
            "device_id": "rtu-dnp3-demo",
            "template": "generic-dnp3",
            "connection": {"host": "192.168.1.40", "port": 20000},
            "poll_interval_ms": 2000,
        }]

    tasks = []
    for dev in devices:
        try:
            template = load_template(dev.get("template", "generic-dnp3"))
        except FileNotFoundError:
            continue
        tasks.append(asyncio.create_task(Dnp3Driver(dev, template, client).poll_loop()))

    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())

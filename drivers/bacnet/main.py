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
logger = logging.getLogger("driver.bacnet")

MOCK = os.getenv("MOCK_DEVICES", "true").lower() == "true"
MQTT_HOST = os.getenv("MQTT_HOST", "mosquitto")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
DEVICES_PATH = os.getenv("BACNET_DEVICES_PATH", "/app/devices/bacnet")
TEMPLATES_PATH = "/app/templates/bacnet"


class BacnetDriver(BaseDriver):
    def __init__(self, device_config, template, mqtt_client):
        super().__init__(device_config, template, mqtt_client)
        self.app = None

    async def connect(self) -> bool:
        if MOCK:
            logger.info(f"[{self.device_id}] MOCK connect OK")
            return True
        try:
            import BAC0
            ip = self.config["connection"].get("host")
            self.app = BAC0.connect()
            return True
        except Exception as e:
            logger.error(f"[{self.device_id}] connect error: {e}")
            return False

    async def disconnect(self):
        if self.app:
            try:
                self.app.disconnect()
            except Exception:
                pass

    async def read_tag(self, tag: dict) -> dict:
        if MOCK:
            return await self.mock_value(tag)
        try:
            host = self.config["connection"]["host"]
            obj_type = tag["object_type"]
            obj_instance = tag["object_instance"]
            prop = tag.get("property", "presentValue")
            point = f"{host} {obj_type} {obj_instance} {prop}"
            value = self.app.read(point)
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
            host = self.config["connection"]["host"]
            obj_type = tag["object_type"]
            obj_instance = tag["object_instance"]
            prop = tag.get("property", "presentValue")
            point = f"{host} {obj_type} {obj_instance} {prop}"
            self.app.write(f"{point} {value}")
            return True
        except Exception as e:
            logger.error(f"[{self.device_id}] write_tag error: {e}")
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
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id="driver-bacnet")
    except AttributeError:
        client = mqtt.Client(client_id="driver-bacnet")
    client.connect(MQTT_HOST, MQTT_PORT, 60)
    client.loop_start()

    devices = load_devices()
    if not devices:
        devices = [{
            "device_id": "hvac-bacnet-demo",
            "template": "generic-bacnet",
            "connection": {"host": "192.168.1.30"},
            "poll_interval_ms": 2000,
        }]

    tasks = []
    for dev in devices:
        try:
            template = load_template(dev.get("template", "generic-bacnet"))
        except FileNotFoundError:
            continue
        tasks.append(asyncio.create_task(BacnetDriver(dev, template, client).poll_loop()))

    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())

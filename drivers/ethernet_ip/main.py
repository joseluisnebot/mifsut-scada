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
logger = logging.getLogger("driver.ethernet_ip")

MOCK = os.getenv("MOCK_DEVICES", "true").lower() == "true"
MQTT_HOST = os.getenv("MQTT_HOST", "mosquitto")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
DEVICES_PATH = os.getenv("ETHERNET_IP_DEVICES_PATH", "/app/devices/ethernet_ip")
TEMPLATES_PATH = "/app/templates/ethernet_ip"


class EthernetIpDriver(BaseDriver):
    def __init__(self, device_config, template, mqtt_client):
        super().__init__(device_config, template, mqtt_client)
        self.plc = None

    async def connect(self) -> bool:
        if MOCK:
            logger.info(f"[{self.device_id}] MOCK connect OK")
            return True
        try:
            from pycomm3 import LogixDriver
            host = self.config["connection"]["host"]
            self.plc = LogixDriver(host)
            self.plc.open()
            return True
        except Exception as e:
            logger.error(f"[{self.device_id}] connect error: {e}")
            return False

    async def disconnect(self):
        if self.plc:
            try:
                self.plc.close()
            except Exception:
                pass

    async def read_tag(self, tag: dict) -> dict:
        if MOCK:
            return await self.mock_value(tag)
        try:
            result = self.plc.read(tag["tag_name"])
            return {
                "value": result.value,
                "unit": tag.get("unit", ""),
                "ts": int(time.time() * 1000),
                "quality": "good" if result.error is None else "bad",
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
            result = self.plc.write((tag["tag_name"], value))
            return result.error is None
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
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id="driver-ethernet-ip")
    except AttributeError:
        client = mqtt.Client(client_id="driver-ethernet-ip")
    client.connect(MQTT_HOST, MQTT_PORT, 60)
    client.loop_start()

    devices = load_devices()
    if not devices:
        devices = [{
            "device_id": "compactlogix-demo",
            "template": "allen-bradley-compactlogix",
            "connection": {"host": "192.168.1.50"},
            "poll_interval_ms": 1000,
        }]

    tasks = []
    for dev in devices:
        try:
            template = load_template(dev.get("template", "allen-bradley-compactlogix"))
        except FileNotFoundError:
            continue
        tasks.append(asyncio.create_task(EthernetIpDriver(dev, template, client).poll_loop()))

    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())

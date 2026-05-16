import asyncio
import os
import sys
import logging
import yaml
import paho.mqtt.client as mqtt

sys.path.insert(0, "/app")
from base_driver import BaseDriver

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger("driver.opcua")

MOCK = os.getenv("MOCK_DEVICES", "true").lower() == "true"
MQTT_HOST = os.getenv("MQTT_HOST", "mosquitto")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
DEVICES_PATH = os.getenv("OPCUA_DEVICES_PATH", "/app/devices/opcua")
TEMPLATES_PATH = "/app/templates/opcua"


class OpcuaDriver(BaseDriver):
    def __init__(self, device_config, template, mqtt_client):
        super().__init__(device_config, template, mqtt_client)
        self.opc_client = None

    async def connect(self) -> bool:
        if MOCK:
            logger.info(f"[{self.device_id}] MOCK connect OK")
            return True
        try:
            from asyncua import Client
            url = self.config["connection"].get("url", "opc.tcp://localhost:4840")
            self.opc_client = Client(url=url)
            await self.opc_client.connect()
            return True
        except Exception as e:
            logger.error(f"[{self.device_id}] connect error: {e}")
            return False

    async def disconnect(self):
        if self.opc_client:
            await self.opc_client.disconnect()

    async def read_tag(self, tag: dict) -> dict:
        if MOCK:
            return await self.mock_value(tag)
        try:
            import time
            node = self.opc_client.get_node(tag["node_id"])
            value = await node.read_value()
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
            from asyncua import ua
            node = self.opc_client.get_node(tag["node_id"])
            await node.write_value(ua.DataValue(ua.Variant(value)))
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
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id="driver-opcua")
    except AttributeError:
        client = mqtt.Client(client_id="driver-opcua")
    client.connect(MQTT_HOST, MQTT_PORT, 60)
    client.loop_start()

    devices = load_devices()
    if not devices:
        devices = [{
            "device_id": "plc-siemens-demo",
            "template": "siemens-s7-1500",
            "connection": {"url": "opc.tcp://192.168.1.20:4840"},
            "poll_interval_ms": 1000,
        }]

    tasks = []
    for dev in devices:
        try:
            template = load_template(dev.get("template", "generic-opcua"))
        except FileNotFoundError:
            continue
        tasks.append(asyncio.create_task(OpcuaDriver(dev, template, client).poll_loop()))

    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())

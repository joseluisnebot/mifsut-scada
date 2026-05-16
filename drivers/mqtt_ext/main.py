import asyncio
import os
import sys
import json
import logging
import time
import yaml
import paho.mqtt.client as mqtt

sys.path.insert(0, "/app")
from base_driver import BaseDriver

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger("driver.mqtt_ext")

MOCK = os.getenv("MOCK_DEVICES", "true").lower() == "true"
MQTT_HOST = os.getenv("MQTT_HOST", "mosquitto")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
DEVICES_PATH = os.getenv("MQTT_EXT_DEVICES_PATH", "/app/devices/mqtt_ext")
TEMPLATES_PATH = "/app/templates/mqtt_ext"


class MqttExtDriver(BaseDriver):
    def __init__(self, device_config, template, mqtt_client):
        super().__init__(device_config, template, mqtt_client)
        self._values = {}

    async def connect(self) -> bool:
        if MOCK:
            return True
        try:
            host = self.config["connection"].get("host", MQTT_HOST)
            port = self.config["connection"].get("port", MQTT_PORT)
            ext = mqtt.Client(client_id=f"ext-{self.device_id}")

            def on_message(client, userdata, msg):
                try:
                    payload = json.loads(msg.payload)
                    tag_id = msg.topic.split("/")[-1]
                    self._values[tag_id] = payload.get("value", payload)
                except Exception:
                    pass

            ext.on_message = on_message
            ext.connect(host, port, 60)
            for tag in self.template.get("tags", []):
                topic = tag["subscribe_topic"].replace("{device_id}", self.device_id)
                ext.subscribe(topic)
            ext.loop_start()
            return True
        except Exception as e:
            logger.error(f"[{self.device_id}] connect error: {e}")
            return False

    async def disconnect(self): ...

    async def read_tag(self, tag: dict) -> dict:
        if MOCK:
            return await self.mock_value(tag)
        value = self._values.get(tag["id"])
        if value is None:
            return None
        return {
            "value": value,
            "unit": tag.get("unit", ""),
            "ts": int(time.time() * 1000),
            "quality": "good",
            "protocol": self.protocol,
        }

    async def write_tag(self, tag: dict, value) -> bool:
        topic = tag.get("publish_topic", "").replace("{device_id}", self.device_id)
        if topic:
            self.mqtt.publish(topic, json.dumps({"value": value}))
        return True


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
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id="driver-mqtt-ext")
    except AttributeError:
        client = mqtt.Client(client_id="driver-mqtt-ext")
    client.connect(MQTT_HOST, MQTT_PORT, 60)
    client.loop_start()

    devices = load_devices()
    if not devices:
        devices = [{
            "device_id": "iot-sensor-demo",
            "template": "generic-mqtt-device",
            "connection": {},
            "poll_interval_ms": 2000,
        }]

    tasks = []
    for dev in devices:
        try:
            template = load_template(dev.get("template", "generic-mqtt-device"))
        except FileNotFoundError:
            continue
        tasks.append(asyncio.create_task(MqttExtDriver(dev, template, client).poll_loop()))

    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())

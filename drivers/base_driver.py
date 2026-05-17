import asyncio
import json
import random
import time
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class BaseDriver(ABC):
    def __init__(self, device_config: dict, template: dict, mqtt_client):
        self.device_id = device_config["device_id"]
        self.config = device_config
        self.template = template
        self.mqtt = mqtt_client
        self.connected = False
        self.poll_interval = device_config.get("poll_interval_ms", 1000) / 1000.0
        self.protocol = template.get("protocol", "unknown")

    @abstractmethod
    async def connect(self) -> bool: ...

    @abstractmethod
    async def disconnect(self): ...

    @abstractmethod
    async def read_tag(self, tag: dict) -> dict: ...

    @abstractmethod
    async def write_tag(self, tag: dict, value) -> bool: ...

    async def poll_loop(self):
        await self._publish_status(online=False)
        last_heartbeat = 0.0
        while True:
            if not self.connected:
                self.connected = await self.connect()
                if not self.connected:
                    await self._publish_status(online=False, error="Connection failed")
                    await asyncio.sleep(5)
                    continue
                await self._publish_status(online=True)
                last_heartbeat = time.time()

            try:
                for tag in self.template.get("tags", []):
                    result = await self.read_tag(tag)
                    if result:
                        topic = f"scada/{self.device_id}/{tag['id']}"
                        self.mqtt.publish(topic, json.dumps(result))
                        logger.debug(f"{topic} → {result['value']}")
            except Exception as e:
                logger.error(f"[{self.device_id}] poll error: {e}")
                self.connected = False
                await self._publish_status(online=False, error=str(e))

            # heartbeat cada 30s para que el core sepa que sigue vivo
            if self.connected and time.time() - last_heartbeat >= 30:
                await self._publish_status(online=True)
                last_heartbeat = time.time()

            await asyncio.sleep(self.poll_interval)

    async def _publish_status(self, online: bool, error=None):
        payload = {
            "online": online,
            "ts": int(time.time() * 1000),
            "protocol": self.protocol,
            "error": error,
        }
        self.mqtt.publish(
            f"scada/{self.device_id}/_status",
            json.dumps(payload),
            retain=True,
        )

    async def mock_value(self, tag: dict) -> dict:
        unit = tag.get("unit", "")
        tag_type = tag.get("type", "float")

        ranges = {
            "°C": (15.0, 85.0),
            "Hz": (45.0, 55.0),
            "A": (0.0, 100.0),
            "V": (200.0, 250.0),
            "rpm": (0, 3000),
            "bar": (0.0, 10.0),
            "m/min": (0.0, 50.0),
            "%": (0.0, 100.0),
        }

        low, high = ranges.get(unit, (0.0, 100.0))

        if tag_type == "bool":
            value = random.random() > 0.1
        elif tag_type in ("int", "int16", "int32"):
            value = random.randint(int(low), int(high))
        else:
            value = round(random.uniform(low, high), 2)

        return {
            "value": value,
            "unit": unit,
            "ts": int(time.time() * 1000),
            "quality": "good",
            "protocol": self.protocol,
        }

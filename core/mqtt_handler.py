import json
import logging
import os
import asyncio
from datetime import datetime, timezone

import paho.mqtt.client as mqtt
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

logger = logging.getLogger(__name__)

INFLUX_URL = os.getenv("INFLUX_URL", "http://influxdb:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "mytoken")
INFLUX_ORG = os.getenv("INFLUX_ORG", "scada")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "signals")

_latest: dict = {}
_ws_clients: set = set()
_loop: asyncio.AbstractEventLoop = None

influx_client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
write_api = influx_client.write_api(write_options=SYNCHRONOUS)


def get_latest() -> dict:
    return _latest


def clear_device(device_id: str):
    keys = [k for k in _latest if k.split("/")[0] == device_id]
    for k in keys:
        del _latest[k]


def register_ws(ws):
    _ws_clients.add(ws)


def unregister_ws(ws):
    _ws_clients.discard(ws)


def set_loop(loop: asyncio.AbstractEventLoop):
    global _loop
    _loop = loop


def _on_message(client, userdata, msg):
    try:
        parts = msg.topic.split("/")
        if len(parts) < 3:
            return
        device_id = parts[1]
        tag_id = parts[2]

        if tag_id == "_status":
            key = f"{device_id}/_status"
            payload = json.loads(msg.payload)
            _latest[key] = payload
            _broadcast({"type": "status", "device_id": device_id, "data": payload})
            return

        if tag_id.endswith("/set"):
            return

        payload = json.loads(msg.payload)
        key = f"{device_id}/{tag_id}"
        _latest[key] = payload

        _broadcast({"type": "tag", "device_id": device_id, "tag_id": tag_id, "data": payload})

        try:
            point = (
                Point("tag_value")
                .tag("device_id", device_id)
                .tag("tag_id", tag_id)
                .tag("protocol", payload.get("protocol", "unknown"))
                .field("value", float(payload["value"]) if not isinstance(payload["value"], bool) else int(payload["value"]))
                .field("quality", payload.get("quality", "unknown"))
                .time(payload.get("ts", None), WritePrecision.MS)
            )
            write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=point)
        except Exception as e:
            logger.debug(f"InfluxDB write error: {e}")

    except Exception as e:
        logger.error(f"MQTT message error: {e}")


def _broadcast(data: dict):
    if not _loop or not _ws_clients:
        return
    msg = json.dumps(data)
    dead = set()
    for ws in list(_ws_clients):
        try:
            asyncio.run_coroutine_threadsafe(ws.send_text(msg), _loop)
        except Exception:
            dead.add(ws)
    _ws_clients.difference_update(dead)


def create_mqtt_client(host: str, port: int) -> mqtt.Client:
    try:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id="scada-core")
    except AttributeError:
        client = mqtt.Client(client_id="scada-core")

    def on_connect(c, userdata, flags, rc):
        if rc == 0:
            c.subscribe("scada/#")
            logger.info(f"MQTT conectado y suscrito a scada/#")
        else:
            logger.error(f"MQTT error de conexión rc={rc}")

    def on_disconnect(c, userdata, rc):
        logger.warning(f"MQTT desconectado (rc={rc}), reconectando automáticamente...")

    client.on_message    = _on_message
    client.on_connect    = on_connect
    client.on_disconnect = on_disconnect
    client.reconnect_delay_set(min_delay=1, max_delay=30)
    client.connect(host, port, keepalive=60)
    client.loop_start()
    logger.info(f"MQTT cliente iniciado → {host}:{port}")
    return client

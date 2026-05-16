import json
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import paho.mqtt.client as mqtt

router = APIRouter(prefix="/api/tags", tags=["write"])

_mqtt_client: mqtt.Client = None


def set_mqtt(client: mqtt.Client):
    global _mqtt_client
    _mqtt_client = client


class WritePayload(BaseModel):
    value: float | bool | int | str


@router.post("/{device_id}/{tag_id}/write")
async def write_tag(device_id: str, tag_id: str, payload: WritePayload):
    if _mqtt_client is None:
        raise HTTPException(status_code=503, detail="MQTT not connected")
    topic = f"scada/{device_id}/{tag_id}/set"
    _mqtt_client.publish(topic, json.dumps({"value": payload.value}))
    return {"ok": True, "topic": topic, "value": payload.value}

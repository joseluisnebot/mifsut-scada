import os
import yaml
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

ALARMS_FILE = "/app/devices/alarms.yaml"

router = APIRouter(prefix="/api/alarms", tags=["alarms"])


def _load() -> dict:
    if not os.path.exists(ALARMS_FILE):
        return {}
    with open(ALARMS_FILE) as f:
        return yaml.safe_load(f) or {}


def _save(data: dict):
    os.makedirs(os.path.dirname(ALARMS_FILE), exist_ok=True)
    with open(ALARMS_FILE, "w") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True)


class ThresholdSet(BaseModel):
    device_id: str
    tag_id: str
    min: float | None = None
    max: float | None = None


@router.get("")
async def list_alarms():
    data = _load()
    result = {}
    for device_id, tags in data.items():
        for tag_id, thresholds in tags.items():
            result[f"{device_id}/{tag_id}"] = thresholds
    return result


@router.post("")
async def set_alarm(t: ThresholdSet):
    data = _load()
    if t.device_id not in data:
        data[t.device_id] = {}
    entry = {}
    if t.min is not None:
        entry["min"] = t.min
    if t.max is not None:
        entry["max"] = t.max
    if not entry:
        raise HTTPException(status_code=400, detail="Indica al menos min o max")
    data[t.device_id][t.tag_id] = entry
    _save(data)
    return {"ok": True}


@router.delete("/{device_id}/{tag_id}")
async def delete_alarm(device_id: str, tag_id: str):
    data = _load()
    if device_id not in data or tag_id not in data[device_id]:
        raise HTTPException(status_code=404, detail="Umbral no encontrado")
    del data[device_id][tag_id]
    if not data[device_id]:
        del data[device_id]
    _save(data)
    return {"ok": True}

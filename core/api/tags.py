import os
from fastapi import APIRouter, HTTPException, Query
from core.mqtt_handler import get_latest

INFLUX_URL = os.getenv("INFLUX_URL", "http://influxdb:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "mytoken")
INFLUX_ORG = os.getenv("INFLUX_ORG", "scada")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "signals")

router = APIRouter(prefix="/api/tags", tags=["tags"])


@router.get("")
async def list_tags():
    latest = get_latest()
    result = []
    for key, data in latest.items():
        if key.endswith("/_status"):
            continue
        parts = key.split("/")
        result.append({"device_id": parts[0], "tag_id": parts[1], **data})
    return result


@router.get("/{device_id}/{tag_id}/history")
async def tag_history(
    device_id: str,
    tag_id: str,
    minutes: int = Query(default=60, ge=5, le=10080),
    start: str = Query(default=None),
    end: str = Query(default=None),
):
    from datetime import datetime

    if start and end:
        try:
            dt_start = datetime.fromisoformat(start.replace("Z", "+00:00"))
            dt_end   = datetime.fromisoformat(end.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(status_code=400, detail="Formato de fecha inválido")
        duration_min = (dt_end - dt_start).total_seconds() / 60
        range_clause = f'start: {dt_start.strftime("%Y-%m-%dT%H:%M:%SZ")}, stop: {dt_end.strftime("%Y-%m-%dT%H:%M:%SZ")}'
    else:
        duration_min = minutes
        range_clause = f"start: -{minutes}m"

    if duration_min <= 15:
        window = "10s"
    elif duration_min <= 60:
        window = "30s"
    elif duration_min <= 360:
        window = "2m"
    elif duration_min <= 1440:
        window = "10m"
    elif duration_min <= 10080:
        window = "1h"
    else:
        window = "6h"

    query = f"""
from(bucket: "{INFLUX_BUCKET}")
  |> range({range_clause})
  |> filter(fn: (r) => r["_measurement"] == "tag_value")
  |> filter(fn: (r) => r["device_id"] == "{device_id}")
  |> filter(fn: (r) => r["tag_id"] == "{tag_id}")
  |> filter(fn: (r) => r["_field"] == "value")
  |> aggregateWindow(every: {window}, fn: mean, createEmpty: false)
  |> yield(name: "mean")
"""
    try:
        from influxdb_client import InfluxDBClient
        client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
        tables = client.query_api().query(query)
        points = []
        for table in tables:
            for record in table.records:
                v = record.get_value()
                if v is not None:
                    points.append({
                        "ts": int(record.get_time().timestamp() * 1000),
                        "value": round(float(v), 3),
                    })
        client.close()
        return {"device_id": device_id, "tag_id": tag_id, "points": points}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"InfluxDB error: {e}")


@router.get("/{device_id}/{tag_id}")
async def get_tag(device_id: str, tag_id: str):
    key = f"{device_id}/{tag_id}"
    latest = get_latest()
    if key not in latest:
        raise HTTPException(status_code=404, detail="Tag not found")
    return {"device_id": device_id, "tag_id": tag_id, **latest[key]}

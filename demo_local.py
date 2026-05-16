"""
Demo local sin Docker ni MQTT.
Simula 3 dispositivos y expone la API + WebSocket en http://localhost:8000
"""
import asyncio
import json
import random
import time
import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("demo")

app = FastAPI(title="SCADA Demo Local")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

_latest: dict = {}
_ws_clients: set = set()

DEMO_DEVICES = [
    {
        "device_id": "variador-linea1",
        "protocol": "modbus_tcp",
        "tags": [
            {"id": "frecuencia_salida", "unit": "Hz",  "low": 45.0, "high": 55.0},
            {"id": "corriente_motor",   "unit": "A",   "low": 10.0, "high": 80.0},
            {"id": "tension_dc",        "unit": "V",   "low": 520,  "high": 560},
            {"id": "temperatura_igbt",  "unit": "°C",  "low": 40.0, "high": 75.0},
            {"id": "setpoint_velocidad","unit": "rpm", "low": 1400, "high": 1500, "writable": True},
        ],
    },
    {
        "device_id": "plc-siemens-s7",
        "protocol": "opcua",
        "tags": [
            {"id": "temperatura_zona1", "unit": "°C", "low": 18.0, "high": 25.0},
            {"id": "temperatura_zona2", "unit": "°C", "low": 22.0, "high": 35.0},
            {"id": "setpoint_temp",     "unit": "°C", "low": 20.0, "high": 24.0, "writable": True},
            {"id": "estado_maquina",    "unit": "",   "low": 0,    "high": 3, "type": "int"},
        ],
    },
    {
        "device_id": "iot-sensor-exterior",
        "protocol": "mqtt_ext",
        "tags": [
            {"id": "temperatura",  "unit": "°C", "low": 10.0, "high": 38.0},
            {"id": "humedad",      "unit": "%",  "low": 30.0, "high": 90.0},
            {"id": "bateria",      "unit": "%",  "low": 60.0, "high": 100.0},
        ],
    },
]


def mock_value(tag: dict, protocol: str) -> dict:
    low, high = tag["low"], tag["high"]
    t = tag.get("type", "float")
    if t == "int":
        value = random.randint(int(low), int(high))
    elif t == "bool":
        value = random.random() > 0.1
    else:
        value = round(random.uniform(low, high), 2)
    return {
        "value": value,
        "unit": tag["unit"],
        "ts": int(time.time() * 1000),
        "quality": "good",
        "protocol": protocol,
    }


async def broadcast(data: dict):
    dead = set()
    for ws in list(_ws_clients):
        try:
            await ws.send_json(data)
        except Exception:
            dead.add(ws)
    _ws_clients.difference_update(dead)


async def simulate():
    # Publicar status inicial
    for device in DEMO_DEVICES:
        did = device["device_id"]
        _latest[f"{did}/_status"] = {
            "online": True,
            "ts": int(time.time() * 1000),
            "protocol": device["protocol"],
            "error": None,
        }

    logger.info("Simulacion iniciada con 3 dispositivos mock")

    while True:
        for device in DEMO_DEVICES:
            did = device["device_id"]
            for tag in device["tags"]:
                data = mock_value(tag, device["protocol"])
                key = f"{did}/{tag['id']}"
                _latest[key] = data
                await broadcast({"type": "tag", "device_id": did, "tag_id": tag["id"], "data": data})
                logger.info(f"  {did}/{tag['id']} = {data['value']} {data['unit']}")

        await asyncio.sleep(2)


@app.on_event("startup")
async def startup():
    asyncio.create_task(simulate())


@app.get("/api/tags")
async def list_tags():
    result = []
    for key, data in _latest.items():
        if "_status" in key:
            continue
        did, tid = key.split("/", 1)
        result.append({"device_id": did, "tag_id": tid, **data})
    return result


@app.get("/api/devices")
async def list_devices():
    result = []
    for device in DEMO_DEVICES:
        did = device["device_id"]
        status = _latest.get(f"{did}/_status", {})
        result.append({
            "device_id": did,
            "online": status.get("online", False),
            "protocol": device["protocol"],
            "error": None,
        })
    return result


@app.get("/api/templates")
async def list_templates():
    return {
        "modbus": ["abb-acs880", "schneider-m340", "generic-modbus"],
        "opcua": ["siemens-s7-1500", "generic-opcua"],
        "ethernet_ip": ["allen-bradley-compactlogix"],
        "bacnet": ["generic-bacnet"],
        "dnp3": ["generic-dnp3"],
        "snmp": ["generic-snmp"],
        "mqtt_ext": ["generic-mqtt-device"],
    }


@app.post("/api/tags/{device_id}/{tag_id}/write")
async def write_tag(device_id: str, tag_id: str, payload: dict):
    logger.info(f"WRITE {device_id}/{tag_id} = {payload.get('value')}")
    key = f"{device_id}/{tag_id}"
    if key in _latest:
        _latest[key]["value"] = payload.get("value")
    return {"ok": True}


@app.websocket("/ws/tags")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    _ws_clients.add(ws)
    # Enviar estado actual al conectar
    for key, data in _latest.items():
        if "_status" in key:
            did = key.split("/")[0]
            await ws.send_json({"type": "status", "device_id": did, "data": data})
        else:
            did, tid = key.split("/", 1)
            await ws.send_json({"type": "tag", "device_id": did, "tag_id": tid, "data": data})
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        _ws_clients.discard(ws)


if __name__ == "__main__":
    print("\n" + "="*55)
    print("  SCADA Demo Local")
    print("  API:       http://localhost:8000")
    print("  Docs:      http://localhost:8000/docs")
    print("  WebSocket: ws://localhost:8000/ws/tags")
    print("  3 dispositivos mock actualizandose cada 2s")
    print("="*55 + "\n")
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="warning")

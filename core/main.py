import asyncio
import logging
import os

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine

import core.mqtt_handler as mq
from core.models import Base
from core.api import tags, write, devices, alarms
from core.api.write import set_mqtt

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger("core")

MQTT_HOST = os.getenv("MQTT_HOST", "mosquitto")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
POSTGRES_URL = os.getenv("POSTGRES_URL", "postgresql://scada:scada@postgres:5432/scada")

app = FastAPI(title="SCADA Core API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tags.router)
app.include_router(write.router)
app.include_router(devices.router)
app.include_router(alarms.router)


@app.on_event("startup")
async def startup():
    try:
        engine = create_engine(POSTGRES_URL)
        Base.metadata.create_all(engine)
        logger.info("PostgreSQL tables OK")
    except Exception as e:
        logger.warning(f"PostgreSQL init warning: {e}")

    loop = asyncio.get_event_loop()
    mq.set_loop(loop)
    mqtt_client = mq.create_mqtt_client(MQTT_HOST, MQTT_PORT)
    set_mqtt(mqtt_client)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.websocket("/ws/tags")
async def ws_tags(websocket: WebSocket):
    await websocket.accept()
    mq.register_ws(websocket)
    try:
        latest = mq.get_latest()
        for key, data in latest.items():
            if key.endswith("/_status"):
                parts = key.split("/")
                await websocket.send_json({"type": "status", "device_id": parts[0], "data": data})
            else:
                parts = key.split("/")
                await websocket.send_json({"type": "tag", "device_id": parts[0], "tag_id": parts[1], "data": data})
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        mq.unregister_ws(websocket)

import os
import re
import yaml
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any
from core.mqtt_handler import get_latest

TEMPLATES_PATH = "/app/templates"
DEVICES_PATH = "/app/devices"

router = APIRouter(prefix="/api", tags=["devices"])


class DeviceCreate(BaseModel):
    device_id: str
    template: str
    protocol: str
    connection: dict
    poll_interval_ms: int = 1000


class TagSchema(BaseModel):
    id: str
    type: str = "float32"
    unit: str = ""
    writable: bool = False
    scale: float = 1.0
    # modbus
    address: int | None = None
    # opcua
    node_id: str | None = None
    # bacnet
    object_type: str | None = None
    object_instance: int | None = None
    property: str | None = None
    # ethernet_ip
    tag_name: str | None = None
    # snmp
    oid: str | None = None
    # dnp3
    group: int | None = None
    variation: int | None = None
    index: int | None = None
    # mqtt_ext
    subscribe_topic: str | None = None
    publish_topic: str | None = None


class TemplateCreate(BaseModel):
    protocol: str
    name: str
    manufacturer: str
    model: str
    tags: list[TagSchema]
    # snmp extras
    version: str | None = None
    community: str | None = None


def _safe_name(s: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_\-]", "-", s).lower()


def _tag_to_dict(tag: TagSchema, protocol: str) -> dict:
    base = {"id": tag.id, "type": tag.type, "unit": tag.unit, "writable": tag.writable}
    if protocol == "modbus_tcp" and tag.address is not None:
        base["address"] = tag.address
        base["scale"] = tag.scale
    elif protocol == "opcua" and tag.node_id:
        base["node_id"] = tag.node_id
    elif protocol == "bacnet":
        base.update({"object_type": tag.object_type, "object_instance": tag.object_instance,
                     "property": tag.property or "presentValue"})
    elif protocol == "ethernet_ip" and tag.tag_name:
        base["tag_name"] = tag.tag_name
    elif protocol == "snmp" and tag.oid:
        base["oid"] = tag.oid
    elif protocol == "dnp3":
        base.update({"group": tag.group, "variation": tag.variation, "index": tag.index})
    elif protocol == "mqtt_ext":
        if tag.subscribe_topic:
            base["subscribe_topic"] = tag.subscribe_topic
        if tag.publish_topic:
            base["publish_topic"] = tag.publish_topic
    return base


# ── Devices ──────────────────────────────────────────────────────────────────

@router.get("/devices")
async def list_devices():
    latest = get_latest()
    # También incluir devices de fichero aunque no estén online aún
    file_devices = {}
    for proto in os.listdir(DEVICES_PATH) if os.path.isdir(DEVICES_PATH) else []:
        proto_path = os.path.join(DEVICES_PATH, proto)
        if not os.path.isdir(proto_path):
            continue
        for fname in os.listdir(proto_path):
            if fname.endswith((".yaml", ".yml")):
                with open(os.path.join(proto_path, fname)) as f:
                    dev = yaml.safe_load(f)
                did = dev.get("device_id", fname.replace(".yaml", ""))
                file_devices[did] = {"device_id": did, "protocol": proto,
                                     "template": dev.get("template", ""),
                                     "online": False, "error": None}

    for key in latest:
        device_id = key.split("/")[0]
        status = latest.get(f"{device_id}/_status", {})
        if device_id in file_devices:
            file_devices[device_id]["online"] = status.get("online", False)
            file_devices[device_id]["error"] = status.get("error")
        else:
            file_devices[device_id] = {
                "device_id": device_id,
                "online": status.get("online", False),
                "protocol": status.get("protocol", "unknown"),
                "template": "",
                "error": status.get("error"),
            }

    return list(file_devices.values())


@router.post("/devices")
async def add_device(device: DeviceCreate):
    devices_dir = os.path.join(DEVICES_PATH, device.protocol)
    os.makedirs(devices_dir, exist_ok=True)
    config = {
        "device_id": device.device_id,
        "template": device.template,
        "connection": device.connection,
        "poll_interval_ms": device.poll_interval_ms,
    }
    path = os.path.join(devices_dir, f"{device.device_id}.yaml")
    with open(path, "w") as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
    return {"ok": True, "path": path}


@router.delete("/devices/{device_id}")
async def delete_device(device_id: str):
    deleted = []
    for proto in os.listdir(DEVICES_PATH) if os.path.isdir(DEVICES_PATH) else []:
        proto_path = os.path.join(DEVICES_PATH, proto)
        if not os.path.isdir(proto_path):
            continue
        for fname in os.listdir(proto_path):
            if fname.endswith((".yaml", ".yml")):
                path = os.path.join(proto_path, fname)
                with open(path) as f:
                    dev = yaml.safe_load(f)
                if dev.get("device_id") == device_id:
                    os.remove(path)
                    deleted.append(path)
    if not deleted:
        raise HTTPException(status_code=404, detail="Device file not found")
    return {"ok": True, "deleted": deleted}


@router.get("/devices/{device_id}/status")
async def device_status(device_id: str):
    latest = get_latest()
    status_key = f"{device_id}/_status"
    if status_key not in latest:
        raise HTTPException(status_code=404, detail="Device not found or not connected yet")
    return latest[status_key]


# ── Templates ─────────────────────────────────────────────────────────────────

@router.get("/templates")
async def list_templates():
    result = {}
    if not os.path.isdir(TEMPLATES_PATH):
        return result
    for protocol in os.listdir(TEMPLATES_PATH):
        proto_path = os.path.join(TEMPLATES_PATH, protocol)
        if os.path.isdir(proto_path):
            templates = []
            for fname in sorted(os.listdir(proto_path)):
                if fname.endswith((".yaml", ".yml")):
                    templates.append(fname.replace(".yaml", "").replace(".yml", ""))
            result[protocol] = templates
    return result


@router.get("/templates/{protocol}/{name}")
async def get_template(protocol: str, name: str):
    for ext in (".yaml", ".yml"):
        path = os.path.join(TEMPLATES_PATH, protocol, f"{name}{ext}")
        if os.path.exists(path):
            with open(path) as f:
                return yaml.safe_load(f)
    raise HTTPException(status_code=404, detail="Template not found")


@router.get("/templates/{protocol}")
async def list_protocol_templates(protocol: str):
    proto_path = os.path.join(TEMPLATES_PATH, protocol)
    if not os.path.isdir(proto_path):
        raise HTTPException(status_code=404, detail="Protocol not found")
    templates = []
    for fname in sorted(os.listdir(proto_path)):
        if fname.endswith((".yaml", ".yml")):
            name = fname.replace(".yaml", "").replace(".yml", "")
            with open(os.path.join(proto_path, fname)) as f:
                data = yaml.safe_load(f)
            templates.append({"name": name, **data})
    return templates


@router.post("/templates")
async def create_template(tpl: TemplateCreate):
    proto_path = os.path.join(TEMPLATES_PATH, tpl.protocol)
    os.makedirs(proto_path, exist_ok=True)
    fname = _safe_name(tpl.name)
    path = os.path.join(proto_path, f"{fname}.yaml")

    data: dict = {
        "manufacturer": tpl.manufacturer,
        "model": tpl.model,
        "protocol": tpl.protocol,
    }
    if tpl.version:
        data["version"] = tpl.version
    if tpl.community:
        data["community"] = tpl.community

    data["tags"] = [_tag_to_dict(t, tpl.protocol) for t in tpl.tags]

    with open(path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True)

    return {"ok": True, "name": fname, "path": path}


@router.delete("/templates/{protocol}/{name}")
async def delete_template(protocol: str, name: str):
    for ext in (".yaml", ".yml"):
        path = os.path.join(TEMPLATES_PATH, protocol, f"{name}{ext}")
        if os.path.exists(path):
            os.remove(path)
            return {"ok": True, "deleted": path}
    raise HTTPException(status_code=404, detail="Template not found")

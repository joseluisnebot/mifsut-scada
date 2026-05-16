# SCADA Web — Self-Hosted & Portable

Sistema SCADA web moderno basado en Docker Compose. Soporta Modbus TCP, OPC-UA, EtherNet/IP, BACnet, DNP3, SNMP y MQTT.

## Arranque rápido

```bash
# 1. Copiar variables de entorno
cp .env.example .env

# 2. Levantar stack completo (modo MOCK, sin hardware)
docker-compose up --build

# 3. Abrir dashboard
http://localhost:3000
```

El modo `MOCK_DEVICES=true` genera datos simulados realistas sin necesidad de hardware real.

## Cómo añadir un dispositivo

1. Crea un archivo YAML en `devices/<protocolo>/`:

```yaml
device_id: mi-variador
template: abb-acs880
connection:
  host: 192.168.1.10
  port: 502
  unit_id: 1
poll_interval_ms: 1000
```

2. Reinicia el driver correspondiente:
```bash
docker-compose restart driver-modbus
```

O usa el formulario en `http://localhost:3000/devices`.

## Cómo crear un template nuevo

Crea un archivo YAML en `templates/<protocolo>/`:

```yaml
manufacturer: Mi Fabricante
model: Mi Modelo
protocol: modbus_tcp
tags:
  - id: mi_tag
    address: 40001
    type: float32
    scale: 0.1
    unit: "°C"
    writable: false
```

## Cómo añadir un protocolo nuevo

1. Crea `drivers/<protocolo>/` con `Dockerfile`, `main.py`, `requirements.txt`
2. Hereda `BaseDriver` de `base_driver.py`
3. Implementa `connect()`, `disconnect()`, `read_tag()`, `write_tag()`
4. Añade el servicio en `docker-compose.yml`
5. Crea templates en `templates/<protocolo>/`

El core y el frontend **no cambian**.

## Perfiles Docker Compose

```bash
# Solo Modbus (por defecto)
docker-compose up

# Modbus + OPC-UA + BACnet
docker-compose --profile opcua --profile bacnet up

# Todos los protocolos
docker-compose --profile opcua --profile mqtt-ext --profile bacnet \
               --profile dnp3 --profile ethernet-ip --profile snmp up
```

## Comandos útiles

```bash
# Ver logs de un driver
docker-compose logs -f driver-modbus

# Reiniciar solo el core
docker-compose restart core

# Ver datos en tiempo real via MQTT
docker exec -it $(docker-compose ps -q mosquitto) \
  mosquitto_sub -t "scada/#" -v

# API directa
curl http://localhost:8000/api/tags
curl http://localhost:8000/api/devices
curl http://localhost:8000/api/templates

# Escribir un valor
curl -X POST http://localhost:8000/api/tags/variador-linea1/setpoint_velocidad/write \
  -H "Content-Type: application/json" \
  -d '{"value": 1500}'
```

## Arquitectura

```
Driver (Python) → MQTT (Mosquitto) → Core (FastAPI) → WebSocket → Frontend (Next.js)
                                           ↓
                                      InfluxDB (histórico)
                                      PostgreSQL (config)
```

## Variables de entorno clave

| Variable | Descripción | Default |
|----------|-------------|---------|
| `MOCK_DEVICES` | Simular dispositivos sin hardware | `true` |
| `MQTT_HOST` | Host del broker MQTT | `mosquitto` |
| `INFLUX_TOKEN` | Token de InfluxDB | `mytoken` |
| `POSTGRES_URL` | URL de PostgreSQL | `postgresql://...` |

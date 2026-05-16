# Guía de Instalación — SCADA Web Industrial
**Desarrollado por mifsut.com**

---

## Requisitos previos

| Componente | Versión mínima | Notas |
|---|---|---|
| Linux (Ubuntu/Debian) | 20.04+ | También funciona en Raspberry Pi OS |
| Docker Engine | 20.x+ | Motor de contenedores |
| docker-compose | v2.x | Orquestador |
| RAM | 2 GB mínimo | 4 GB recomendado |
| Disco | 5 GB libres | Para datos históricos |

---

## 1. Instalar Docker

```bash
# Actualizar el sistema
sudo apt update && sudo apt upgrade -y

# Instalar Docker
curl -fsSL https://get.docker.com | sudo sh

# Añadir tu usuario al grupo docker (evita usar sudo cada vez)
sudo usermod -aG docker $USER

# Cerrar sesión y volver a entrar para que el grupo se aplique
# O ejecutar en la misma terminal:
newgrp docker

# Verificar instalación
docker --version
```

---

## 2. Instalar docker-compose

```bash
# Descargar la versión estable
mkdir -p ~/.local/bin
curl -fsSL "https://github.com/docker/compose/releases/download/v2.27.0/docker-compose-linux-x86_64" \
  -o ~/.local/bin/docker-compose
chmod +x ~/.local/bin/docker-compose

# Verificar
~/.local/bin/docker-compose version
```

> Si prefieres instalación global: `sudo mv ~/.local/bin/docker-compose /usr/local/bin/`

---

## 3. Descargar el proyecto

```bash
# Opción A: copiar desde otro equipo (scp)
scp -r usuario@origen:/ruta/scada ~/scada

# Opción B: clonar desde git (si está en repositorio)
git clone https://github.com/tu-usuario/scada.git ~/scada

# Entrar en el directorio
cd ~/scada
```

---

## 4. Configurar variables de entorno

```bash
# Copiar el fichero de ejemplo
cp .env.example .env

# Editar si necesitas cambiar algún valor
nano .env
```

### Variables importantes del `.env`

```bash
# Poner en false cuando tengas hardware real conectado
MOCK_DEVICES=true

# Credenciales de InfluxDB (puedes cambiarlas)
INFLUX_TOKEN=mytoken
INFLUX_ORG=scada
INFLUX_BUCKET=signals

# Credenciales PostgreSQL
POSTGRES_URL=postgresql://scada:scada@postgres:5432/scada

# URL pública del SCADA (cambiar si accedes desde otra máquina)
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
```

> **Producción:** Cambia `INFLUX_TOKEN`, las contraseñas de PostgreSQL y pon la IP real del servidor en `NEXT_PUBLIC_API_URL`.

---

## 5. Primer arranque

```bash
cd ~/scada

# Construir y arrancar todos los servicios (primera vez tarda 5-10 min)
~/.local/bin/docker-compose up --build

# O en segundo plano (recomendado después de la primera vez)
~/.local/bin/docker-compose up --build -d
```

### Verificar que todo está corriendo

```bash
~/.local/bin/docker-compose ps
```

Deberías ver algo así:

```
NAME                    STATUS          PORTS
scada-mosquitto-1       Up              0.0.0.0:1883->1883/tcp
scada-influxdb-1        Up              0.0.0.0:8086->8086/tcp
scada-postgres-1        Up (healthy)    0.0.0.0:5432->5432/tcp
scada-core-1            Up              0.0.0.0:8000->8000/tcp
scada-frontend-1        Up              0.0.0.0:3000->3000/tcp
scada-driver-modbus-1   Up
```

### Abrir el dashboard

```
http://localhost:3000
```

Si accedes desde otra máquina en la misma red:
```
http://IP_DEL_SERVIDOR:3000
```

---

## 6. Arranque automático al encender el equipo

```bash
# Copiar el servicio systemd
sudo cp ~/scada/scada.service /etc/systemd/system/

# Activar
sudo systemctl daemon-reload
sudo systemctl enable scada.service
sudo systemctl start scada.service

# Verificar estado
sudo systemctl status scada.service
```

A partir de este momento el SCADA arranca solo cada vez que se enciende el equipo.

```bash
# Comandos útiles del servicio
sudo systemctl stop scada.service      # parar
sudo systemctl restart scada.service   # reiniciar
sudo systemctl status scada.service    # ver estado
```

---

## 7. Activar protocolos adicionales

Por defecto solo arranca el driver Modbus. Para activar otros:

```bash
# Modbus + OPC-UA
~/.local/bin/docker-compose --profile opcua up -d

# Modbus + OPC-UA + BACnet
~/.local/bin/docker-compose --profile opcua --profile bacnet up -d

# Todos los protocolos
~/.local/bin/docker-compose \
  --profile opcua \
  --profile mqtt-ext \
  --profile bacnet \
  --profile dnp3 \
  --profile ethernet-ip \
  --profile snmp up -d
```

---

## 8. Conectar hardware real

### 1. Editar el `.env`

```bash
MOCK_DEVICES=false
```

### 2. Configurar el dispositivo

Edita (o crea) el fichero en `devices/modbus/mi-dispositivo.yaml`:

```yaml
device_id: variador-linea1
template: delta-ms300
connection:
  host: 192.168.1.10    # IP del dispositivo o del conversor USR-W610
  port: 502
  unit_id: 1
poll_interval_ms: 1000
```

### 3. Reiniciar el driver

```bash
~/.local/bin/docker-compose restart driver-modbus
```

---

## 9. Puertos utilizados

| Puerto | Servicio | Uso |
|---|---|---|
| **3000** | Frontend | Dashboard web |
| **8000** | Core API | REST + WebSocket |
| **1883** | MQTT | Broker Mosquitto |
| **8086** | InfluxDB | Base de datos de series temporales |
| **5432** | PostgreSQL | Base de datos de configuración |
| **9001** | MQTT WebSocket | MQTT sobre WebSocket |

Abre estos puertos en el firewall si accedes desde red externa:

```bash
sudo ufw allow 3000/tcp
sudo ufw allow 8000/tcp
```

---

## 10. Actualizar el sistema

```bash
cd ~/scada

# Parar
~/.local/bin/docker-compose down

# Obtener cambios (si usas git)
git pull

# Reconstruir y arrancar
~/.local/bin/docker-compose up --build -d
```

---

## Solución de problemas

### El dashboard no carga
```bash
# Ver logs del frontend
~/.local/bin/docker-compose logs frontend

# Ver logs del core
~/.local/bin/docker-compose logs core
```

### No aparecen datos en el dashboard
```bash
# Verificar que el driver está publicando en MQTT
docker exec -it scada-mosquitto-1 \
  mosquitto_sub -t "scada/#" -v
```

### Error de permisos en Docker
```bash
sudo usermod -aG docker $USER
newgrp docker
```

### Reiniciar solo un servicio
```bash
~/.local/bin/docker-compose restart core
~/.local/bin/docker-compose restart driver-modbus
~/.local/bin/docker-compose restart frontend
```

### Ver logs en tiempo real
```bash
~/.local/bin/docker-compose logs -f core
~/.local/bin/docker-compose logs -f driver-modbus
```

---

*mifsut.com — SCADA Web Industrial*

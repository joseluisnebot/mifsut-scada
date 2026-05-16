# Guía de Usuario — SCADA Web Industrial
**Desarrollado por mifsut.com**

---

## Acceso al sistema

Abre el navegador y ve a:
```
http://IP_DEL_SERVIDOR:3000
```

El sistema tiene tres secciones accesibles desde la barra de navegación superior:

| Sección | URL | Para qué sirve |
|---|---|---|
| **Dashboard** | `/` | Ver datos en tiempo real y gestionar alarmas |
| **Dispositivos** | `/devices` | Añadir y eliminar dispositivos |
| **Templates** | `/templates` | Crear y gestionar plantillas de dispositivos |

---

## Dashboard

### ¿Qué se ve?

Cada dispositivo aparece como una tarjeta con:

- **Indicador de estado** — punto verde (ONLINE) o rojo (OFFLINE)
- **Una ficha por cada tag** (variable del dispositivo) que muestra:
  - Nombre del tag
  - **Valor actual** en tiempo real (se actualiza automáticamente)
  - **Gráfica en tiempo real** — curva de los últimos valores recibidos
  - Líneas de umbral sobre la gráfica (si has configurado alarmas)
  - Campo de setpoint para enviar valores al dispositivo

### Indicador de conexión WebSocket

En la esquina superior derecha verás:
- 🟢 **En vivo** — datos actualizándose en tiempo real
- 🔴 **disconnected** — reconectando automáticamente

---

## Alarmas

### Configurar un umbral de alarma

1. Localiza el tag que quieres supervisar en el dashboard
2. Haz clic en el icono de **campana** 🔔 (esquina superior derecha del tag)
3. En la ventana que aparece, introduce:
   - **Mínimo** — el sistema genera alarma si el valor cae por debajo de este número
   - **Máximo** — el sistema genera alarma si el valor supera este número
   - Puedes poner solo uno de los dos o ambos
4. Pulsa **Guardar**

### ¿Qué ocurre cuando hay alarma?

- El valor del tag se muestra en **rojo**
- Aparece el texto **ALARMA** parpadeando junto al tag
- La gráfica se dibuja en rojo
- En la cabecera del dashboard aparece el contador de alarmas activas
- Las líneas de umbral son visibles en la gráfica

### Modificar o eliminar un umbral

- Para **modificar**: pulsa la campana naranja 🔔 del tag y cambia los valores
- Para **eliminar**: pulsa la campana, deja los campos vacíos y pulsa **Guardar**, o usa el botón **Quitar**

### Los umbrales persisten

Los umbrales se guardan en el servidor (`devices/alarms.yaml`). No se pierden al reiniciar el sistema ni al cerrar el navegador.

---

## Enviar valores a dispositivos (Setpoints)

Los tags que tienen control (writable) permiten enviar valores directamente al dispositivo:

1. Localiza el tag en el dashboard (por ejemplo `setpoint_frecuencia`)
2. Escribe el valor en el campo de texto junto al botón **Enviar**
3. Pulsa **Enviar**
4. Aparecerá ✓ si el comando se envió correctamente

> **Nota:** En modo simulador (`MOCK_DEVICES=true`) el valor se acepta pero no afecta al hardware real. Con `MOCK_DEVICES=false` el valor se escribe directamente en el dispositivo.

---

## Gestión de dispositivos

### Ver dispositivos

En la página **Dispositivos** (`/devices`) puedes ver todos los dispositivos configurados con su estado (ONLINE/OFFLINE).

### Añadir un dispositivo nuevo

1. Ve a la página **Dispositivos**
2. Pulsa el botón **+ Añadir dispositivo**
3. Rellena el formulario:
   - **ID del dispositivo** — nombre único (sin espacios, usa guiones): `variador-linea1`
   - **Protocolo** — el protocolo de comunicación: `modbus`, `opcua`, etc.
   - **Template** — la plantilla del modelo de dispositivo
   - **Host / IP** — dirección IP del dispositivo o del conversor WiFi
   - **Puerto** — puerto de comunicación (Modbus TCP: 502)
   - **Poll interval** — cada cuántos milisegundos se leen los datos
4. Pulsa **Guardar dispositivo**

El dispositivo quedará guardado y el driver lo detectará al reiniciar.

> **Reiniciar el driver** para que cargue el nuevo dispositivo:
> ```bash
> ~/.local/bin/docker-compose restart driver-modbus
> ```

### Eliminar un dispositivo

En la lista de dispositivos, pulsa el icono de **papelera** 🗑️ junto al dispositivo. Se eliminará el fichero de configuración del servidor.

---

## Gestión de templates

Un **template** define qué variables (tags) tiene un modelo de dispositivo y cómo leerlas.

### Ver templates existentes

En la página **Templates** (`/templates`) están listados todos los templates organizados por protocolo. Haz clic en uno para ver sus tags.

### Crear un template nuevo

Útil cuando tienes un dispositivo de una marca no incluida por defecto.

1. Ve a **Templates** y pulsa **Nuevo template**
2. Rellena:
   - **Protocolo**: `modbus`, `opcua`, `bacnet`, etc.
   - **Nombre**: identificador del template (ej: `siemens-logo-8`)
   - **Fabricante** y **Modelo**
3. Añade los tags con **+ Añadir tag**
4. Para cada tag indica:
   - **ID tag** — nombre de la variable (ej: `temperatura_zona1`)
   - **Dirección / Node ID** — registro del dispositivo (consultar manual)
   - **Tipo** — `float32`, `int16`, `bool`, etc.
   - **Unidad** — `°C`, `Hz`, `A`, `V`, etc.
   - **Scale** — factor de escala (ej: `0.01` si el dispositivo da el valor ×100)
   - **Escribible** — marca si se puede enviar setpoint
5. Pulsa **Guardar template**

### Dirección Modbus — cómo calcularla

El manual del dispositivo indica los registros en formato hexadecimal (ej: `0x2101`).

```
Dirección en el template = 40001 + valor_decimal_del_registro

Ejemplo: 0x2101 (hex) = 8449 (decimal)
→ Dirección template = 40001 + 8449 = 48450
```

### Eliminar un template

En la lista de templates, pulsa el icono de **papelera** 🗑️ junto al template.

> No elimines un template si hay dispositivos usándolo.

---

## Añadir varios dispositivos del mismo modelo

Para añadir múltiples variadores del mismo modelo (ej: varios Delta MS300):

1. Cada dispositivo necesita un **ID único** y su propia **IP** (o `unit_id` diferente si comparten bus RS485)
2. Todos pueden usar el **mismo template** (`delta-ms300`)
3. Añade cada uno desde la página Dispositivos o creando un fichero YAML en `devices/modbus/`

**Ejemplo con USR-W610 (conversor RS485 a WiFi):**
- Un USR-W610 por variador → cada uno tiene IP diferente, `unit_id: 1`
- Un USR-W610 compartido → misma IP, `unit_id` diferente para cada variador (configurado en el variador)

---

## Protocolos soportados

| Protocolo | Perfil Docker | Casos de uso |
|---|---|---|
| **Modbus TCP** | activo por defecto | Variadores, PLCs, sensores |
| **OPC-UA** | `--profile opcua` | PLCs Siemens S7, sistemas modernos |
| **EtherNet/IP** | `--profile ethernet-ip` | PLCs Allen-Bradley |
| **BACnet** | `--profile bacnet` | Sistemas HVAC, climatización |
| **DNP3** | `--profile dnp3` | Subestaciones eléctricas |
| **SNMP** | `--profile snmp` | Switches, routers, UPS |
| **MQTT externo** | `--profile mqtt-ext` | Sensores IoT, ESP32, Arduino |

---

## Ejemplo práctico de conexión: dispositivo industrial con Modbus RTU

El mundo industrial tiene miles de dispositivos distintos — variadores, PLCs, contadores de energía, sensores de temperatura, analizadores de red, etc. Cada fabricante tiene sus propios modelos y parámetros, pero el **procedimiento de integración es siempre el mismo**.

A continuación se muestra un ejemplo completo usando dos dispositivos concretos:
- **Delta VFD2A8MS21ANSAA** como dispositivo industrial (variador de frecuencia)
- **PUSR USR-W610** como conversor de comunicaciones (RS485 → WiFi)

> Este ejemplo vale como referencia para cualquier otra combinación: un PLC Siemens con módulo Ethernet, un analizador de red Carlo Gavazzi con puerto TCP, un sensor Endress+Hauser con Modbus TCP, etc. El procedimiento es idéntico — solo cambian los parámetros específicos de cada aparato.

---

### Concepto general: dos tipos de dispositivos

En la mayoría de instalaciones industriales encontrarás esta distinción:

**Dispositivo de campo** — el aparato que hace el trabajo (variador, PLC, sensor, medidor...). Puede comunicar por:
- RS485 / RS232 con Modbus RTU → necesita un conversor para llegar al SCADA por red
- Ethernet con Modbus TCP, OPC-UA, EtherNet/IP → se conecta directamente al SCADA

**Conversor de comunicaciones** — dispositivo auxiliar que no hace ninguna función de control. Solo traduce el protocolo serie (RS485) a red TCP/IP. Ejemplos: PUSR USR-W610, Moxa NPort, Advantech EKI, Elfin-EE11, etc.

La cadena típica con conversor es:

```
Dispositivo de campo          Conversor            Red           SCADA
──────────────────────────────────────────────────────────────────────
Variador / PLC / Sensor  →  RS485 → TCP/IP  →  WiFi/LAN  →  Dashboard
       (Modbus RTU)           (cualquier          (IP)        (Modbus TCP)
                               marca)
```

Si el dispositivo ya tiene Ethernet integrado, el conversor no es necesario:

```
Dispositivo con Ethernet  →  Red LAN/WiFi  →  SCADA
```

---

### Ejemplo paso a paso

#### Paso 1 — Configurar el dispositivo de campo (Delta MS300)

El variador Delta tiene un teclado y pantalla en el frontal. Se accede al menú de parámetros y se configura el puerto RS485:

| Parámetro | Valor | Descripción |
|---|---|---|
| P09.00 | 1 | Dirección Modbus del variador (unit_id) |
| P09.01 | 9600 | Velocidad RS485 en baudios |
| P09.04 | 3 | Formato: Modbus RTU, 8 bits, sin paridad, 1 stop |
| P00.20 | 3 | Fuente de comando marcha/paro: comunicación |
| P00.21 | 3 | Fuente de referencia de frecuencia: comunicación |

> En otros dispositivos (PLCs, medidores, etc.) busca en su manual los parámetros equivalentes: dirección Modbus, velocidad de comunicación y formato de trama. El concepto es el mismo.

> Si hay varios dispositivos en el mismo bus RS485, cada uno lleva una dirección diferente (1, 2, 3...).

---

#### Paso 2 — Configurar el conversor de comunicaciones (USR-W610)

El USR-W610 tiene su propia interfaz web de administración, completamente independiente del variador.

1. Conéctate a su WiFi de fábrica o por cable Ethernet
2. Abre en el navegador: `http://192.168.0.7` (IP por defecto de fábrica)
3. Configura el **lado serie** (RS485 → hacia el variador):
   - **Baud rate**: 9600 (debe coincidir con el variador)
   - **Data bits**: 8 · **Stop bits**: 1 · **Parity**: None
4. Configura el **lado red** (TCP/IP → hacia el SCADA):
   - **Modo**: TCP Server
   - **Puerto local**: 502
5. Conecta el USR-W610 a tu red WiFi (SSID y contraseña)
6. Anota la IP que obtiene en tu red — esa IP es la que usará el SCADA

> Con otros conversores (Moxa NPort, Elfin, etc.) el proceso es equivalente. Solo cambia la interfaz de configuración. El objetivo es siempre el mismo: que el conversor escuche peticiones Modbus TCP en un puerto y las reenvíe por RS485 al dispositivo.

---

#### Paso 3 — Conexión física RS485

El cable va desde el terminal RS485 del variador hasta el terminal RS485 del conversor:

```
Dispositivo de campo         Conversor RS485→TCP
────────────────────────────────────────────────
Terminal A / D+ / RS485+  ──  Terminal A
Terminal B / D- / RS485-  ──  Terminal B
GND / Shield              ──  GND  (recomendado)
```

> Los nombres de los terminales varían según el fabricante (A/B, D+/D-, +/-). Consulta el manual de cada aparato. Para distancias superiores a 5 metros usar cable trenzado apantallado.

---

#### Paso 4 — Configurar el dispositivo en el SCADA

Desde la página **Dispositivos** de la web, o editando directamente el fichero `devices/modbus/mi-dispositivo.yaml`:

```yaml
device_id: delta-vfd-linea1        # nombre único que aparecerá en el dashboard
template: delta-ms300              # template con los registros del dispositivo
connection:
  host: 192.168.1.XX               # IP del conversor en tu red (NO del variador)
  port: 502                        # puerto configurado en el conversor
  unit_id: 1                       # dirección Modbus del variador (P09.00)
poll_interval_ms: 1000             # lectura cada 1 segundo
```

> La IP es siempre la del **conversor** (o la del dispositivo si tiene Ethernet propio). El variador no tiene IP — solo tiene RS485.

---

### ¿Y si mi dispositivo es de otra marca?

El proceso es idéntico. Solo cambia:

1. **Los parámetros de configuración** del dispositivo — están en el manual de cada marca
2. **El template** — créalo en la página Templates con los registros Modbus que indica el manual

Marcas comunes con Modbus RTU/TCP: ABB, Siemens, Schneider, Danfoss, WEG, Omron, Mitsubishi, Yaskawa, Rockwell, Carlo Gavazzi, Eastron, Finder, Phoenix Contact...

Todas funcionan igual en este SCADA. Solo necesitas el manual de comunicaciones de tu dispositivo para saber qué registros leer.

---

## Datos históricos

El sistema guarda todo el histórico en InfluxDB. Para consultar los datos históricos de un tag haz clic en el icono de gráfica ampliada (disponible en versiones futuras o accediendo directamente a InfluxDB).

**Acceso a InfluxDB:**
```
http://IP_DEL_SERVIDOR:8086
Usuario: admin
Contraseña: adminpassword
```

---

## Preguntas frecuentes

**¿Se pierden los datos si se reinicia el sistema?**
No. Los datos históricos están en InfluxDB (volumen Docker persistente), los templates y dispositivos en ficheros YAML, y los umbrales de alarma en `devices/alarms.yaml`.

**¿Puedo acceder desde fuera de la red local?**
Sí, expón los puertos 3000 y 8000 en tu router (o usa una VPN). Cambia `NEXT_PUBLIC_API_URL` con la IP pública.

**¿Cuántos dispositivos puede gestionar?**
No hay límite fijo. El sistema está diseñado para decenas de dispositivos. Para instalaciones grandes aumenta la RAM del servidor.

**¿Cómo añado un protocolo nuevo?**
Crea una carpeta en `drivers/nuevo_protocolo/` con `Dockerfile`, `main.py` y `requirements.txt`, hereda la clase `BaseDriver`, y añade el servicio en `docker-compose.yml`. El dashboard lo mostrará automáticamente sin ningún cambio más.

**El valor de un tag aparece como "Sin datos"**
- Verifica que el driver está corriendo: `docker-compose logs driver-modbus`
- Comprueba la conexión IP al dispositivo
- Revisa el `unit_id` del dispositivo

---

## Atajos de teclado del navegador

| Atajo | Acción |
|---|---|
| `Ctrl + Shift + R` | Recargar sin caché (útil después de actualizar) |
| `F5` | Recargar normal |

---

*© mifsut.com — SCADA Web Industrial*

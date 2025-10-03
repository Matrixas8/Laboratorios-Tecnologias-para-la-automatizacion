# Sistema de control de temperatura en data center con Raspberry Pico 2W y CircuitPython

<img width="711" height="403" alt="image" src="https://github.com/Matrixas8/Laboratorios-Tecnologias-para-la-automatizacion/blob/main/lab-diagrama_bb.jpg" />

## Escenario: cabina móvil de pintura que usan en un taller.

En las cabinas hay una compuerta que regula la apertura para evacuar vapores, y se cuenta con un sistema de ventilación que evita la acumulación de partículas de pintura.
La compuerta se controla de forma automática a través de un sensor de concentración de vapor, que mide en tiempo real la cantidad presente en el interior de la cabina y envía la señal al sistema para definir el nivel de apertura requerido.
Como la cabina se desplaza por todo el taller, es importante asegurarse de que no quede inclinada por irregularidades del piso. Si esto ocurre, se activa un LED rojo y el relé corta el extractor inmediatamente.


## El LED bicolor indica el estado del sistema:

Verde → Operación normal
Rojo → Emergencia

El relé controla el encendido y apagado del extractor, mientras que el conversor de corriente utiliza señal PWM para ajustar la posición de la compuerta según el valor de presión.
Detalle del funcionamiento del setpoint y control de la compuerta
Modos de operación de la compuerta:


Sensor de presión: un sensor de presión controla el valor de apertura de la compuerta según este valor sea mayor o menor.


# Detalle del funcionamiento del setpoint y control de la compuerta:

### Modos de operación de la compuerta:

La compuerta recibe un valor de apertura proporcional a la concentración de vapor medida.
El sistema traduce la señal del sensor en un porcentaje de apertura deseado de la compuerta.
    Ejemplo: un setpoint del 50% abrirá la compuerta a la mitad de su recorrido.
El estado normal de presión suele ser un 50%, si baja o sube de ese valor la compuerta se abrirá o cerrará para mantener estable el flujo.
Fuera del estado normal se habilita un control manual por setpoint 

### Cambio de estado y prioridades:

Emergencia: siempre tiene máxima prioridad.
Si la cabina detecta inclinación irregular, se enciende el LED rojo y el relé corta inmediatamente el extractor.
En este estado, la compuerta no responde al setpoint ni al sensor de presión hasta que se resuelva la emergencia.

## Control de la compuerta vía PWM:

El valor del sensor de presión será simulado con un joystick para efectos académicos.
El valor de apertura se traduce a un duty cycle del PWM del conversor de corriente.
Por ejemplo:

0% apertura → 0º PWM
100% apertura → 180º PWM

Esto garantiza un control preciso de la posición de la compuerta.

## Indicadores y seguridad:

### LED bicolor:
Verde → Operación normal, sin alerta.
Rojo → Emergencia (cabina inclinada o cualquier fallo crítico).

### Relé del extractor:
Activado → extractor encendido.
Desactivado → corte inmediato en caso de emergencia.


# Red de Microcontroladores con MQTT y Node-RED

## MQTT

MQTT (Message Queuing Telemetry Transport) es un protocolo de mensajería ligero, orientado a eventos, diseñado para dispositivos con recursos limitados y redes inestables. Usa el modelo publicador–suscriptor sobre TCP/IP.

En qué consiste:

- Broker: servidor central que recibe y distribuye mensajes.
- Clientes: publican o se suscriben a "temas" (topics).
- QoS (Quality of Service): mecanismo que ofrece tres niveles distintos (0, 1, 2) para garantizar diferentes grados de entrega de mensajes.
    - El nivel 0 proporciona entrega "fire and forget" sin confirmación
    - El nivel 1 garantiza que el mensaje llegue al menos una vez con confirmación
    - El nivel 2 asegura que el mensaje se entregue exactamente una vez mediante handshake

Cómo funciona:

1. Un cliente se conecta al broker.
2. Publica mensajes en un topic, por ejemplo sensores/temperatura.
3. Otros clientes se suscriben a ese topic y reciben los mensajes en tiempo real.

## Implementación

### Arquitectura

<img width="1052" height="581" alt="image" src="https://github.com/user-attachments/assets/bf514b11-8409-4225-9a2b-69cae70f4bcb" />


- **Sensores (12 microcontroladores Pico 2W)**: Cada uno publica sus datos (temperatura, humedad, movimiento, etc.) en un topic MQTT único:
    - `sensores/[nombre de equipo]/[magnitud que mide]`
    - `sensores/relay/temperatura`
- **Controlador Maestro (1 microcontrolador Pico 2W extra)**: Se suscribe a todos los sensores y centraliza la información en un solo topic (`/mediciones/`).
- **Broker MQTT**: Usamos un broker local, por lo que [instalamos mosquitto](https://mosquitto.org/download/) en nuestra PC. Mosquitto corre automaticamente en el puerto 1883, sin embargo, necesitamos dos brokers para implementar nuestra arquitectura, podemos crear otra instancia del servicio para que corra en el puerto 1884
    - Buscamos la ubicación donde instalamos mosquitto e identificamos el archivo generico de configuraciones mosquitto.conf. Tendremos que abrir este archivo como administrador par moder modificarlo. Hay que hacer una pequeña modificación, colocamos al principio las siguientes lineas:
        
        ```markdown
        listener 1883
        allow_anonymous true
        ```
        
        Luego guardamos, cambiamos su nombre a `mosquitto_a.conf` , lo clonamos y guardamos la copia como `mosquitto_b.conf` . Dentro de este otro archivo colocamos:
        
        ```markdown
        listener 1884
        allow_anonymous true
        ```
        
        Tenemos listo dos archivos de configuraciones para crear dos instancias del broker. 
        
        Para simplificar la ejecución de estas instancias recomiendo crear un archivo `mosquitto_run.bat` :
        
        ```markdown
        @echo off
        cd "C:\Program Files\mosquitto"
        
        start "" mosquitto -c "C:\Program Files\mosquitto\mosquitto_a.conf"
        start "" mosquitto -c "C:\Program Files\mosquitto\mosquitto_b.conf"
        
        exit
        ```
        
        Para verificar que efectivamente estan corriendo estas instancias ejecutamos en consola:
        
        ```markdown
        netstat -ano | findstr "1883 1884”
        ```
        
        Deberias ver que para ambos puertos el estado es “LISTENING”.
        
- **Node-RED (en la PC)**: Se conecta al broker MQTT, escucha el tema (`mediciones/#`) y muestra cada valor en gráficos, indicadores, contadores, etc. según corresponda.
    - Lo instalamos https://nodered.org/docs/getting-started/windows, y ejecutamos el comando `node-red` , luego podremos abrir el servidor donde esta corriendo.
    - Debemos instalar la extensión `@flowfuse/node-red-dashboard` para tener acceso a distintos tipos de graficos.

### Librerías

Vamos a necesitar incorporar librerías que no vienen por defecto. En https://circuitpython.org/libraries se puede descargar un zip con todas las librerías. Luego las copias en la carpeta `/lib` en el microcontrolador.

Las librerías son:

- `/lib/adafruit_minimqtt`: Copiar la carpeta completa.
- `/lib/adafruit_ticks.mpy`: Módulo que necesita minimqtt.
- `/lib/adafruit_connection_manager.mpy`: Módulo que necesita minimqtt.
- `/lib/adafruit_esp32spi_socketpool.mpy`: Módulo para conectarnos a la red.

### Descubrimiento automático de sensores

Cuando un sensor se conecta a la red, además de comenzar a publicar sus datos periódicamente, envía un mensaje de anuncio al tema especial `/descubrir/`.

El mensaje contiene la información mínima necesaria para que el maestro lo identifique, por ejemplo en formato JSON:

```json
{
  "equipo": "relay",
  "magnitudes": ["temperatura", "humedad"]
}

```

El maestro está suscripto al tema `/descubrir/`. Cada vez que se publica en el, lo interpreta como un sensor recientemente conectado y lo agrega a una lista de sensores conocidos. Luego, se suscribe dinámicamente al **tema** de ese sensor para empezar a recibir sus datos en tiempo real.

### Node-red

El maestro centraliza toda la información que recibe y la publica en el tema `/mediciones/#` , a traves del puerto 1884.

Por ejemplo:

- `/mediciones/[equipo]/[magnitud]`
- `/mediciones/relay/temperatura`

> Notece que el maestro no publica en sensores sino en mediciones.
> 

De esta forma, Node-RED solo necesita escuchar `/mediciones/#` para recibir en tiempo real toda la información de la red de sensores.

### Configuración de los microcontroladores

```python
import time
import wifi
import socketpool
import adafruit_minimqtt.adafruit_minimqtt as MQTT

# Configuración de RED
SSID = "Tu wifi"
PASSWORD = "Contraseña de tu wifi"
BROKER = "La IPv4 de la pc donde corre mosquitto. Win: ipconfig o Linux: ip addr"  
NOMBRE_EQUIPO = "relay"
DESCOVERY_TOPIC = "descubrir"
TOPIC = f"sensores/{NOMBRE_EQUIPO}"

print(f"Intentando conectar a {SSID}...")
try:
    wifi.radio.connect(SSID, PASSWORD)
    print(f"Conectado a {SSID}")
    print(f"Dirección IP: {wifi.radio.ipv4_address}")
except Exception as e:
    print(f"Error al conectar a WiFi: {e}")
    while True:
        pass 

# Configuración MQTT 
pool = socketpool.SocketPool(wifi.radio)

def connect(client, userdata, flags, rc):
    print("Conectado al broker MQTT")
    client.publish(DESCOVERY_TOPIC, json.dumps({"equipo":NOMBRE_EQUIPO,"magnitudes": ["temperatura", "humedad"]}))

mqtt_client = MQTT.MQTT(
    broker=BROKER,
    port=1883,
    socket_pool=pool
)

mqtt_client.on_connect = connect
mqtt_client.connect()

# Usamos estas varaibles globales para controlar cada cuanto publicamos
last_pub = 0
PUB_INTERVAL = 5  
def publish():
    global last_pub
    now = time.monotonic()
   
    if now - last_pub >= PUB_INTERVAL:
        try:
            temp_topic = f"{TOPIC}/[una_magnitud]" 
            mqtt_client.publish(temp_topic, str([var_de_una_magnitud]))
            
            hum_topic = f"{TOPIC}/[otra magnitud]" 
            mqtt_client.publish(hum_topic, str([var_de_otra_magnitud]))
            
            last_pub = now
          
        except Exception as e:
            print(f"Error publicando MQTT: {e}")

```

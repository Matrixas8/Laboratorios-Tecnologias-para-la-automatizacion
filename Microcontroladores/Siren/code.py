import board
import digitalio
import analogio
import pwmio
import busio
import time
import wifi
import socketpool
import json
import adafruit_minimqtt.adafruit_minimqtt as MQTT
from adafruit_motor import servo

# Configuración de RED
SSID = "wfrre-Docentes"  # revisa que no tenga doble espacio
PASSWORD = "20$tscFrre.24"
BROKER = "10.13.100.154"
NOMBRE_EQUIPO = "Punteros_Locos"
DISCOVERY_TOPIC = "descubrir"
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
    client.publish(DISCOVERY_TOPIC, "conectado desde Pico")
    client.publish(DISCOVERY_TOPIC, json.dumps({
        "equipo": NOMBRE_EQUIPO,
        "magnitudes": ["inclinacion", "joystick"]
    }))
    mqtt_client.publish("sensores/inclinacion/inclinacion", "Hola desde Pico")


mqtt_client = MQTT.MQTT(
    broker=BROKER,
    port=1883,
    socket_pool=pool
)

mqtt_client.on_connect = connect
mqtt_client.connect()

# --- Sensores ---
joystick = analogio.AnalogIn(board.A0)   # Eje del joystick
inclinacion = digitalio.DigitalInOut(board.GP15)
inclinacion.direction = digitalio.Direction.INPUT
inclinacion.pull = digitalio.Pull.UP

# --- LEDs ---
led_verde = digitalio.DigitalInOut(board.GP14)
led_verde.direction = digitalio.Direction.OUTPUT

led_rojo = digitalio.DigitalInOut(board.GP13)
led_rojo.direction = digitalio.Direction.OUTPUT

# --- Relé ---
rele = digitalio.DigitalInOut(board.GP12)
rele.direction = digitalio.Direction.OUTPUT

# --- Servo compuerta ---
pwm_servo = pwmio.PWMOut(board.GP11, duty_cycle=0, frequency=50)
compuerta = servo.Servo(pwm_servo, min_pulse=600, max_pulse=2400)

# --- Variables ---
modo_emergencia = False
LAST_PUB = 0
PUB_INTERVAL = 5

def leer_joystick():
    valor = (joystick.value / 65535) * 100
    return int(valor)

def aplicar_pwm(porcentaje):
    angulo = int((porcentaje / 100) * 180)
    compuerta.angle = max(0, min(180, angulo))

def publish():
    global LAST_PUB
    now = time.monotonic()
    if now - LAST_PUB >= PUB_INTERVAL:
        try:
            temp_topic = f"{TOPIC}/inclinacion"
            mqtt_client.publish(temp_topic, str(inclinacion.value))
            
            joy_topic = f"{TOPIC}/joystick"
            mqtt_client.publish(joy_topic, str(leer_joystick()))

            print(f"Publicado -> inclinacion: {inclinacion.value}, joystick: {leer_joystick()}")
            LAST_PUB = now
        except Exception as e:
            print(f"Error publicando MQTT: {e}")

while True:
    mqtt_client.loop() 
    publish()          
    time.sleep(0.2)
import board
import digitalio
import analogio
import pwmio
import busio
import time
import wifi
import socketpool
import supervisor
import json
import adafruit_minimqtt.adafruit_minimqtt as MQTT
from adafruit_motor import servo


# Configuración de RED
SSID = "Wifi"  # revisa que no tenga doble espacio
PASSWORD = "contraseña-wifi"
BROKER = "ipv4 del broker"
NOMBRE_EQUIPO = "punteros_locos"
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
        "magnitudes": ["inclinacion", "presion"]
    }))

mqtt_client = MQTT.MQTT(
    broker=BROKER,
    port=1883,
    socket_pool=pool
)
mqtt_client.on_connect = connect
mqtt_client.connect()

# Usamos estas varaibles globales para controlar cada cuanto publicamos
LAST_PUB = 0
PUB_INTERVAL = 1  

def publish():
    global LAST_PUB
    now = time.monotonic()
    if now - LAST_PUB >= PUB_INTERVAL:
        try:
            temp_topic = f"{TOPIC}/inclinacion"
            mqtt_client.publish(temp_topic, str(inclinacion.value).lower())
            
            joy_topic = f"{TOPIC}/presion"
            mqtt_client.publish(joy_topic, str(leer_joystick()))

            print(f"Publicado -> inclinacion: {inclinacion.value}, presion: {leer_joystick()}")
            LAST_PUB = now
        except Exception as e:
            print(f"Error publicando MQTT: {e}")

# --- Sensores ---
sensor_vapor = analogio.AnalogIn(board.A0)   # Simulado con joystick
inclinacion = digitalio.DigitalInOut(board.GP15)
inclinacion.direction = digitalio.Direction.INPUT
inclinacion.pull = digitalio.Pull.UP

# --- LEDs (bicolor) ---
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

# --- UART para setpoint manual ---
uart = busio.UART(board.GP0, board.GP1, baudrate=9600, timeout=0.1)

# --- Variables ---
modo_emergencia = False
setpoint_manual = None   # Valor fijo de apertura ingresado por serial
valor_automatico = 0

def leer_sensor_vapor():
    """Normalizar de 0–65535 a 0–100 (%)"""
    valor = (sensor_vapor.value / 65535) * 100
    return int(valor)

def aplicar_pwm(porcentaje):
    """Convertir porcentaje (0–100) a ángulo (0–180)"""
    angulo = int((porcentaje / 100) * 180)
    angulo = max(0, min(180, angulo))
    compuerta.angle = angulo

while True:
    # --- Chequear emergencia ---
    if not inclinacion.value:  
        modo_emergencia = True
        led_rojo.value = True
        led_verde.value = False
        rele.value = False     # Cortar extractor
        aplicar_pwm(0)         # Cerrar compuerta
        print("🚨 Emergencia detectada: cabina inclinada. Sistema detenido.")
        time.sleep(0.5)
        continue
    else:
        modo_emergencia = False

    # --- Estado normal ---
    led_rojo.value = False
    led_verde.value = True
    rele.value = True   # Encender extractor

    # --- Lectura de sensor automático ---
    valor_automatico = leer_sensor_vapor()

    # --- Lectura de UART (setpoint manual) ---
    data = uart.read()
    if data:
        try:
            valor = int(data.decode().strip())
            if valor == -1:
                setpoint_manual = None  # Reset → volver a automático
                print("📡 Modo automático reactivado por UART")
            else:
                setpoint_manual = valor
                print(f"📡 Setpoint manual recibido por UART: {setpoint_manual}%")
        except:
            print("⚠️ Error leyendo UART")

    # --- Lectura de USB (Thonny) ---
    if supervisor.runtime.serial_bytes_available:
        try:
            entrada_usb = input().strip()
            if entrada_usb != "":
                valor = int(entrada_usb)
                if valor == -1:
                    setpoint_manual = None  # Reset → volver a automático
                    print("💻 Modo automático reactivado por USB")
                else:
                    setpoint_manual = valor
                    print(f"💻 Setpoint manual recibido por USB: {setpoint_manual}%")
        except:
            print("⚠️ Valor inválido en consola USB")

    # --- Control de compuerta ---
    if setpoint_manual is not None:
        aplicar_pwm(setpoint_manual)
        modo = "Manual"
        valor_usado = setpoint_manual
    else:
        aplicar_pwm(valor_automatico)
        modo = "Automático"
        valor_usado = valor_automatico

    # --- Monitoreo serial ---
    print(f"Modo: {modo} | Sensor: {valor_automatico}% | Setpoint Manual: {setpoint_manual} | Aplicado: {valor_usado}%")

    time.sleep(0.1)
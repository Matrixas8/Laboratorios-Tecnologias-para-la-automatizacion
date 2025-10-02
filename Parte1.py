import board
import digitalio
import analogio
import pwmio
import busio
import time
import supervisor
from adafruit_motor import servo

# --- Sensores ---
joystick = analogio.AnalogIn(board.A0)   # Eje del joystick
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

# --- UART para setpoint automático ---
uart = busio.UART(board.GP0, board.GP1, baudrate=9600, timeout=0.1)

# --- Variables ---
modo_emergencia = False
setpoint = 0   # Valor de apertura automático (0-100)

def leer_joystick():
    # Normalizar de 0-65535 a 0-100 (%)
    valor = (joystick.value / 65535) * 100
    return int(valor)

def aplicar_pwm(porcentaje):
    # Convertir porcentaje (0–100) a ángulo (0–180)
    angulo = int((porcentaje / 100) * 180)
    angulo = max(0, min(180, angulo))  # Limitar rango válido
    compuerta.angle = angulo

while True:
    # --- Chequear emergencia ---
    if not inclinacion.value:  # Sensor detecta inclinación
        modo_emergencia = True
        led_rojo.value = True
        led_verde.value = False
        rele.value = False  # Apagar extractor
        aplicar_pwm(0)      # Cerrar compuerta
        print("🚨 Emergencia detectada: cabina inclinada. Sistema detenido.")
        time.sleep(0.5)
        continue
    else:
        modo_emergencia = False

    # --- Estado normal ---
    led_rojo.value = False
    led_verde.value = True
    rele.value = True   # Encender extractor

    # --- Lectura de joystick ---
    valor_manual = leer_joystick()

    # --- Lectura de UART (setpoint automático) ---
    data = uart.read()
    if data:
        try:
            setpoint = int(data.decode().strip())
            print(f"📡 Nuevo setpoint recibido por UART: {setpoint}%")
        except:
            print("⚠️ Error leyendo UART")

    # --- Lectura de entrada USB (desde consola de Thonny) ---
    if supervisor.runtime.serial_bytes_available:
        try:
            entrada_usb = input().strip()
            if entrada_usb != "":
                setpoint = int(entrada_usb)
                print(f"💻 Nuevo setpoint recibido por USB: {setpoint}%")
        except:
            print("⚠️ Valor inválido en consola USB")

    # --- Prioridades ---

    reposo = 50
    margen = 10

    if abs(valor_manual - reposo) > margen:  # Modo manual si se detecta movimiento
        aplicar_pwm(valor_manual)
        modo = "Manual"
        valor_usado = valor_manual
    else:
        aplicar_pwm(setpoint)
        modo = "Automático"
        valor_usado = setpoint

    # --- Monitoreo serial ---
    print(f"Modo: {modo} | Joystick: {valor_manual}% | Setpoint: {setpoint}% | Aplicado: {valor_usado}%")

    time.sleep(0.1)

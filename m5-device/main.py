import M5
import time
import network
from M5 import *

from umqtt.simple import MQTTClient


# =========================
# System
# =========================

DELAY_UPDATE = 0.5


# =========================
# Wi-Fi connection
# =========================

WIFI_SSID = "HAXE_HEADQUARTER_2G"
WIFI_PASSWORD = "Cxtn4Bill95"

def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if not wlan.isconnected():
        print("Connecting to Wi-Fi...")
        wlan.connect(WIFI_SSID,WIFI_PASSWORD)

        while not wlan.isconnected():
            time.sleep(0.5)

    print("Wi-Fi connected")
    print("Device IP address:",wlan.ifconfig()[0])


# =========================
# UI
# =========================


LABELS_SPACING = 80

INITIAL_X = 10
INITIAL_Y = 20

BACKGROUND_COLOR = 0x222222
TITLE_TEXT_COLOR = 0xAAAAAA
VALUE_TEXT_COLOR = 0xFFFFFF

TITLE_FONT = Widgets.FONTS.DejaVu18
VALUE_FONT = Widgets.FONTS.DejaVu24

WIDGET_OFFSET_X = 80
WIDGET_OFFSET_Y = 30

TITLE_TEXT_SIZE = 1.5
VALUE_TEXT_SIZE = 1.2

COLUMNS = 3
ROWS = 2


# =========================
# MQTT
# =========================

MQTT_BROKER = "192.168.31.212"
MQTT_PORT = 1883
MQTT_CLIENT_ID = b"m5stack-01"
MQTT_TOPIC = "pc/data"

def parse_kv(s: str) -> dict:
    if isinstance(s, bytes):
        s = s.decode('utf-8')
    return dict(pair.split(":", 1) for pair in s.split(","))

def on_message(topic, msg):
    if topic == MQTT_TOPIC.encode('utf-8'):
        dict = parse_kv(msg)
        update_values(dict["gpu"], dict["vram"], dict["temp"], dict["cpu"], dict["ram"], dict["temp"])

def connect_mqtt():
    print("Connecting to MQTT broker:",MQTT_BROKER)

    client = MQTTClient(MQTT_CLIENT_ID,MQTT_BROKER,port=MQTT_PORT)
    client.set_callback(on_message)
    client.connect()
    client.subscribe(MQTT_TOPIC)
    print("MQTT connected")

    return client


# =========================
# Setup
# =========================

def setup():
    M5.begin()

    M5.Display.fillScreen(0x000000)
    M5.Display.setCursor(10,10)
    M5.Display.print("Connecting Wi-Fi...")
    connect_wifi()

    M5.Display.fillScreen(0x000000)
    M5.Display.setCursor(10,10)
    M5.Display.print("Connecting MQTT...")

    global mqtt
    mqtt = connect_mqtt()
    M5.Display.fillScreen(0x000000)
    M5.Display.setCursor(10,10)
    M5.Display.print("MQTT CONNECTED")

    Widgets.fillScreen(BACKGROUND_COLOR)

    Widgets.Label(
        "GPU",
        20, 20,
        TITLE_TEXT_SIZE,
        TITLE_TEXT_COLOR,
        BACKGROUND_COLOR,
        TITLE_FONT
    )

    Widgets.Label(
        "VRAM",
        120, 20,
        TITLE_TEXT_SIZE,
        TITLE_TEXT_COLOR,
        BACKGROUND_COLOR,
        TITLE_FONT
    )

    Widgets.Label(
        "TEMP",
        210, 20,
        TITLE_TEXT_SIZE,
        TITLE_TEXT_COLOR,
        BACKGROUND_COLOR,
        TITLE_FONT
    )

    Widgets.Label(
        "CPU",
        20, 100,
        TITLE_TEXT_SIZE,
        TITLE_TEXT_COLOR,
        BACKGROUND_COLOR,
        TITLE_FONT
    )

    Widgets.Label(
        "RAM",
        120, 100,
        TITLE_TEXT_SIZE,
        TITLE_TEXT_COLOR,
        BACKGROUND_COLOR,
        TITLE_FONT
    )

    Widgets.Label(
        "TEMP",
        210, 100,
        TITLE_TEXT_SIZE,
        TITLE_TEXT_COLOR,
        BACKGROUND_COLOR,
        TITLE_FONT
    )

    global labels
    labels = [
        Widgets.Label(
            "0",
            20, 45,
            VALUE_TEXT_SIZE,
            VALUE_TEXT_COLOR,
            BACKGROUND_COLOR,
            VALUE_FONT
        ),

        Widgets.Label(
            "0",
            120, 45,
            VALUE_TEXT_SIZE,
            VALUE_TEXT_COLOR,
            BACKGROUND_COLOR,
            VALUE_FONT
        ),

        Widgets.Label(
            "0",
            210, 45,
            VALUE_TEXT_SIZE,
            VALUE_TEXT_COLOR,
            BACKGROUND_COLOR,
            VALUE_FONT
        ),

        Widgets.Label(
            "0",
            20, 125,
            VALUE_TEXT_SIZE,
            VALUE_TEXT_COLOR,
            BACKGROUND_COLOR,
            VALUE_FONT
        ),

        Widgets.Label(
            "0",
            120, 125,
            VALUE_TEXT_SIZE,
            VALUE_TEXT_COLOR,
            BACKGROUND_COLOR,
            VALUE_FONT
        ),

        Widgets.Label(
            "0",
            210, 125,
            VALUE_TEXT_SIZE,
            VALUE_TEXT_COLOR,
            BACKGROUND_COLOR,
            VALUE_FONT
        )
    ]

def update_values(gpu: str, vram: str, temp1: str, cpu: str, ram: str, temp2: str):
    labels[0].setText(gpu + "%")    # GPU
    labels[1].setText(vram + "%")   # VRAM
    labels[2].setText(temp1 + "°")  # TEMP
    labels[3].setText(cpu + "%")    # CPU
    labels[4].setText(ram + " G")   # RAM
    labels[5].setText(temp2 + "°")  # TEMP

# =========================
# Main loop
# =========================

def loop():
    M5.update()
    mqtt.check_msg()
    time.sleep(DELAY_UPDATE)

# =========================
# Start
# =========================

if __name__ == '__main__':
    try:
        setup()
        while True:
            loop()
    except (Exception, KeyboardInterrupt) as e:
        try:
            from utility import print_error_msg
            print_error_msg(e)
        except ImportError:
            print("please update to latest firmware")

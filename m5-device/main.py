import M5
import time
import network
from M5 import *
import ujson

from umqtt.simple import MQTTClient


# =========================
# Configuration
# =========================

class AppConfig:
    def __init__(self):
        self.wifi_ssid = "empty"
        self.wifi_pass = "empty"
        self.update_rate = 0.5

    def load_from_file(self, filename="./conf.json"):
        try:
            with open(filename, "r") as f:
                data = ujson.load(f)
                self.__dict__.update(data)
        except Exception as e:
            print("Failed to load conf:", e)

# =========================
# Wi-Fi connection
# =========================

WIFI_SSID = "HAXE_HEADQUARTER_2G"
WIFI_PASSWORD = "Cxtn4Bill95"

def connect_wifi(conf: AppConfig):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if not wlan.isconnected():
        print("Connecting to Wi-Fi...")
        wlan.connect(conf.wifi_ssid, conf.wifi_pass)

        while not wlan.isconnected():
            time.sleep(0.5)

    print("Wi-Fi connected")
    print("Device IP address:",wlan.ifconfig()[0])


# =========================
# UI
# =========================


BACKGROUND_COLOR = 0x222222
TITLE_TEXT_COLOR = 0xAAAAAA
VALUE_TEXT_COLOR = 0xFFFFFF

TITLE_FONT = Widgets.FONTS.DejaVu18
VALUE_FONT = Widgets.FONTS.DejaVu24

INITIAL_X = 15
INITIAL_Y = 20

WIDGET_OFFSET_X = 100
WIDGET_OFFSET_Y = 100
VALUE_OFFSET_Y = 35

TITLE_TEXT_SIZE = 1.5
VALUE_TEXT_SIZE = 1.2

MAX_COLUMNS = 3


titles = ["GPU", "VRAM", "TEMP", "CPU", "RAM", "TEMP"]
labels = []

def buildWidgets():
    x_multiplier = 0
    y_multiplier = 0

    for idx, title in enumerate(titles):
        if idx != 0 and idx % MAX_COLUMNS == 0:
            x_multiplier = 0
            y_multiplier += 1

        x = INITIAL_X + x_multiplier * WIDGET_OFFSET_X
        y = INITIAL_Y + y_multiplier * WIDGET_OFFSET_Y

        Widgets.Label(title, x, y, TITLE_TEXT_SIZE, TITLE_TEXT_COLOR, BACKGROUND_COLOR, TITLE_FONT)

        labels.append(
            Widgets.Label("0", x, y + VALUE_OFFSET_Y, VALUE_TEXT_SIZE, VALUE_TEXT_COLOR, BACKGROUND_COLOR, VALUE_FONT))

        x_multiplier += 1


# =========================
# MQTT
# =========================

MQTT_BROKER = "192.168.31.169"
MQTT_PORT = 1883
MQTT_CLIENT_ID = b"m5stack-01"
MQTT_TOPIC = "pc/data"
MQTT_VERSION = 2

def parse_kv(s: str) -> dict:
    if isinstance(s, bytes):
        s = s.decode('utf-8')
    return dict(pair.split(":", 1) for pair in s.split(","))

def on_message(topic, msg):
    if topic == MQTT_TOPIC.encode('utf-8'):
        dict = parse_kv(msg)

        labels[0].setText(dict["gpu"])      # GPU
        labels[1].setText(dict["vram"])     # VRAM
        labels[2].setText(dict["temp_gpu"]) # TEMP GPU
        labels[3].setText(dict["cpu"])      # CPU
        labels[4].setText(dict["ram"])      # RAM
        labels[5].setText(dict["temp_cpu"]) # TEMP CPU

def connect_mqtt(conf: AppConfig):
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
    time.sleep(0.5)

    M5.Display.fillScreen(0x000000)
    M5.Display.setCursor(10,10)
    M5.Display.print("Reading agent-conf.json...")
    global cfg
    cfg = AppConfig()
    cfg.load_from_file()

    M5.Display.fillScreen(0x000000)
    M5.Display.setCursor(10,10)
    M5.Display.print("Connecting Wi-Fi...")
    connect_wifi(cfg)

    M5.Display.fillScreen(0x000000)
    M5.Display.setCursor(10,10)
    M5.Display.print("Connecting MQTT...")

    global mqtt
    mqtt = connect_mqtt(cfg)
    M5.Display.fillScreen(0x000000)
    M5.Display.setCursor(10,10)
    M5.Display.print("MQTT CONNECTED")

    Widgets.fillScreen(BACKGROUND_COLOR)
    buildWidgets()

# =========================
# Main loop
# =========================

DELAY_UPDATE = 0.5

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

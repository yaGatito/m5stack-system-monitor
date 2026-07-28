import M5
import time
import network
import machine
from hardware import sdcard
import os
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
        self.mqtt_broker_host="192.168.31.169"
        self.mqtt_broker_port="1883"
        self.desktop_topic="pc/data"
        self.orangepi5_topic="opi5/data"

    def load_from_file(self, filename):
        try:
            sd = machine.SDCard(
                slot=2,
                sck=machine.Pin(18),
                miso=machine.Pin(19),
                mosi=machine.Pin(23),
                cs=machine.Pin(4),
                freq=1_000_000,
            )

            os.mount(sd, "/sd")
            with open(filename, "r") as f:
                content = f.read()
                data = ujson.loads(content)
                self.wifi_ssid = data.get("wifi_ssid")
                self.wifi_pass = data.get("wifi_pass")
                self.update_rate = data.get("update_rate")
                self.mqtt_broker_host = data.get("mqtt_broker_host")
                self.mqtt_broker_port = data.get("mqtt_broker_port")
                self.desktop_topic = data.get("desktop_topic")
                self.orangepi5_topic = data.get("orangepi5_topic")

        except Exception as e:
            print("Failed to load conf:", e)


# =========================
# Wi-Fi connection
# =========================

def connect_wifi(conf: AppConfig):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if not wlan.isconnected():
        print("Connecting to Wi-Fi...")
        wlan.connect(conf.wifi_ssid, conf.wifi_pass)

        while not wlan.isconnected():
            time.sleep(0.5)

    print("Wi-Fi connected to ",conf.wifi_ssid)
    print("Device IP address:",wlan.ifconfig()[0])


# =========================
# UI
# =========================


HIGHLIGHTED_NAV_TEXT_COLOR = 0xFFFFFF
BACKGROUND_COLOR = 0x222222
NAV_BACKGROUND_COLOR = 0x00AAAA
NAV_TEXT_COLOR = 0x00ffff
TITLE_TEXT_COLOR = 0xAAAAAA
VALUE_TEXT_COLOR = 0xFFFFFF


WIDGETS_INITIAL_X = 10
WIDGETS_INITIAL_Y = 20
NAVBAR_INITIAL_X = 30
NAVBAR_INITIAL_Y = 200

WIDGET_OFFSET_X = 150
WIDGET_OFFSET_Y = 60
VALUE_OFFSET_Y = 35

TITLE_TEXT_SIZE = 1.5
VALUE_TEXT_SIZE = 1.2

MAX_COLUMNS = 2


pcTitles = ["CPU", "RAM", "TEMP", "GPU", "VRAM", "TEMP"]
opi5Titles = ["CPU", "RAM", "TEMP", "DOWN", "SSD", "ZRAM"]
buttons = ["opi5", "tst", "pc"]

# widgets = []
valueLabels = []
navbar  = []

def dehighlight(exceptOne: int):
    for idx, btn in enumerate(buttons):
      if idx != exceptOne:
        navbar[idx].setColor(NAV_TEXT_COLOR)
        navbar[idx].setText(btn)

def highligh(idx: int):
    navbar[idx].setColor(HIGHLIGHTED_NAV_TEXT_COLOR)
    navbar[idx].setText(buttons[idx]+"<")

def button_a_handler(state):
    highligh(0)
    dehighlight(0)
    mqtt.subscribe(cfg.orangepi5_topic)
    mqtt.unsubscribe(cfg.desktop_topic)

def button_b_handler(state):
    highligh(1)
    dehighlight(1)

def button_c_handler(state):
    highligh(2)
    dehighlight(2)
    mqtt.unsubscribe(cfg.orangepi5_topic)
    mqtt.subscribe(cfg.desktop_topic)

def buildWidgets(titles: list[str]):
    x_multiplier = 0
    y_multiplier = 0

    for idx, title in enumerate(titles):
        if idx != 0 and idx % MAX_COLUMNS == 0:
            x_multiplier = 0
            y_multiplier += 1

        x = WIDGETS_INITIAL_X + x_multiplier * WIDGET_OFFSET_X
        y = WIDGETS_INITIAL_Y + y_multiplier * WIDGET_OFFSET_Y

        valueLabels.append(
            Widgets.Label(title, x, y, TITLE_TEXT_SIZE, TITLE_TEXT_COLOR, BACKGROUND_COLOR, Widgets.FONTS.DejaVu18))

        # valueLabels.append(
        #     Widgets.Label("0", x, y + VALUE_OFFSET_Y, VALUE_TEXT_SIZE, VALUE_TEXT_COLOR, BACKGROUND_COLOR, Widgets.FONTS.DejaVu24))

        x_multiplier += 1

    navbar.append(Widgets.Label(buttons[0], 30, 200, TITLE_TEXT_SIZE, NAV_TEXT_COLOR, NAV_BACKGROUND_COLOR, Widgets.FONTS.DejaVu24))
    navbar.append(Widgets.Label(buttons[1], 135, 200, TITLE_TEXT_SIZE, NAV_TEXT_COLOR, NAV_BACKGROUND_COLOR, Widgets.FONTS.DejaVu24))
    navbar.append(Widgets.Label(buttons[2], 233, 200, TITLE_TEXT_SIZE, NAV_TEXT_COLOR, NAV_BACKGROUND_COLOR, Widgets.FONTS.DejaVu24))


# =========================
# MQTT
# =========================

MQTT_CLIENT_ID = b"m5stack-01"
MQTT_PC_TOPIC = "pc/data"
MQTT_OPI_TOPIC = "opi5/data"

def parse_kv(s: str) -> dict:
    if isinstance(s, bytes):
        s = s.decode('utf-8')
    return dict(pair.split(":", 1) for pair in s.split(","))

def on_message(topic, msg):
    if topic == MQTT_PC_TOPIC.encode('utf-8'):
        dict = parse_kv(msg)
        valueLabels[0].setText(pcTitles[0] + ": " + dict["cpu"])      # CPU
        valueLabels[1].setText(pcTitles[1] + ": "  + dict["ram"])      # RAM
        valueLabels[2].setText(pcTitles[2] + ": "  + dict["temp_cpu"]) # TEMP CPU

        valueLabels[3].setText(pcTitles[3] + ": "  + dict["gpu"])      # GPU
        valueLabels[4].setText(pcTitles[4] + ": "  + dict["vram"])     # VRAM
        valueLabels[5].setText(pcTitles[5] + ": "  + dict["temp_gpu"]) # TEMP GPU

    if topic == MQTT_OPI_TOPIC.encode('utf-8'):
        dict = parse_kv(msg)
        valueLabels[0].setText(opi5Titles[0] + ": "  + dict["cpu"])      # CPU
        valueLabels[1].setText(opi5Titles[1] + ": "  + dict["ram"])      # RAM
        valueLabels[2].setText(opi5Titles[2] + ": "  + dict["temp_cpu"]) # TEMP CPU

        valueLabels[3].setText(opi5Titles[3] + ": "  + dict["net_spd"])      # GPU
        valueLabels[4].setText(opi5Titles[4] + ": "  + dict["ssd"])     # VRAM
        valueLabels[5].setText(opi5Titles[5] + ": "  + dict["zram"]) # TEMP GPU

def connect_mqtt(conf: AppConfig):
    print("SSID:", conf.wifi_ssid)

    client = MQTTClient(MQTT_CLIENT_ID, conf.mqtt_broker_host, port=conf.mqtt_broker_port)
    client.set_callback(on_message)
    client.connect()
    client.subscribe(conf.orangepi5_topic)
    print("MQTT connected")

    return client


# =========================
# Setup
# =========================

# slot = 2
# SCK  = GPIO18
# MISO = GPIO19
# MOSI = GPIO23
# CS   = GPIO4
# freq = 1 MHz


def setup():
    M5.begin()
    time.sleep(0.5)

    M5.Display.fillScreen(0x000000)
    M5.Display.setCursor(10,10)
    M5.Display.print("Reading agent-conf.json...")
    global cfg
    cfg = AppConfig()
    cfg.load_from_file("/sd/conf.json")

    print("SSID:", cfg.wifi_ssid)
    print("MQTT host:", cfg.mqtt_broker_host)
    print("MQTT port:", cfg.mqtt_broker_port)

    M5.Display.fillScreen(0x000000)
    M5.Display.setCursor(10,10)
    M5.Display.print("Connecting Wi-Fi...")

    print("before connect wifi")
    connect_wifi(cfg)
    print("after connect wifi")

    M5.Display.fillScreen(0x000000)
    M5.Display.setCursor(10,10)
    M5.Display.print("Connecting MQTT...")

    global mqtt
    mqtt = connect_mqtt(cfg)
    M5.Display.fillScreen(0x000000)
    M5.Display.setCursor(10,10)
    M5.Display.print("MQTT CONNECTED")

    Widgets.fillScreen(BACKGROUND_COLOR)
    current_mode = "opi5"
    buildWidgets(opi5Titles)
    highligh(0)

    BtnA.setCallback(type=BtnA.CB_TYPE.WAS_CLICKED,cb=button_a_handler)
    BtnB.setCallback(type=BtnB.CB_TYPE.WAS_CLICKED,cb=button_b_handler)
    BtnC.setCallback(type=BtnC.CB_TYPE.WAS_CLICKED,cb=button_c_handler)


# =========================
# Main loop
# =========================

def loop():
    M5.update()
    mqtt.check_msg()
    time.sleep(0.1)

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

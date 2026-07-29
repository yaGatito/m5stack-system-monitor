import M5
import time
import network
import machine
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

IDX_HIGHLIGHTED_NAV_TEXT_COLOR = 0
IDX_HIGHLIGHTED_NAV_BACKGROUND_COLOR = 1
IDX_BACKGROUND_COLOR = 2
IDX_NAV_BACKGROUND_COLOR = 3
IDX_NAV_TEXT_COLOR = 4
IDX_TITLE_TEXT_COLOR = 5
IDX_VALUE_TEXT_COLOR = 6

themePointer = 10
previousTheme = 0
themes = [
    #[navbar] [navback]backg    nav back navcolor titlclr  valcolor
    [0xFFFFFF,0xFFFFFF,0x333333,0x222222,0x666666,0xAAAAAA,0xFFFFFF], # 0 GREY THEME
    [0xFFFFFF,0xFFFFFF,0x1E2430,0x151A22,0x64748B,0x94A3B8,0xFFFFFF], # 1 DARK BLUE THEME
    [0xFFFFFF,0xFFFFFF,0x1C2521,0x121816,0x60756B,0x9AAFA5,0xFFFFFF], # 2 DARK GREEN THEME
    [0xFFFFFF,0xFFFFFF,0x211F2B,0x16151D,0x706A80,0xAAA4B8,0xFFFFFF], # 3 CYBERPUNK THEME
    [0xFFFFFF,0xFFFFFF,0x292722,0x1C1A17,0x756F63,0xADA79B,0xFFFFFF], # 4 AMBER / INDUSTRIAL
    [0x000000,0x00FF41,0x050805,0x0A120A,0x287A3D,0x5DBB72,0xD7FFD9], # 5 MATRIX
    [0x282A36,0xBD93F9,0x282A36,0x1E1F29,0x6272A4,0x8BE9FD,0xF8F8F2], # 6 DRACULA
    [0x2E3440,0x88C0D0,0x2E3440,0x242933,0x616E88,0xD8DEE9,0xECEFF4], # 7 NORD
    [0x001014,0x00E5FF,0x07181C,0x0B252B,0x39727C,0x76B9C2,0xD8FBFF], # 8 CYAN TERMINAL
    [0xFFFFFF,0xA855F7,0x17121F,0x0F0B14,0x6E5A7E,0xBFA8D1,0xFFFFFF], # 9 PURPLE NEON
    [0xFFFFFF,0xF97316,0x241A17,0x17110F,0x80675D,0xC9A99B,0xFFF7F2], # 10 SUNSET
    [0xFFFFFF,0x0EA5E9,0x0B1F2A,0x07151D,0x4D8299,0x8EC5DC,0xF0FAFF], # 11 OCEAN
    [0xFFFFFF,0x16A34A,0x101C15,0x0A120D,0x4C7659,0x9AC2A4,0xF0FFF3], # 12 FOREST
    [0x1A1200,0xFFB000,0x0F0C05,0x181207,0x80652A,0xC69D4D,0xFFE9A8], # 13 AMBER TERMINAL
    [0xFFFFFF,0xDC2626,0x1F1214,0x140A0C,0x7D4B52,0xC38B91,0xFFF5F5], # 14 BLOOD MOON
    [0x102027,0x67E8F9,0x15252B,0x0C171B,0x52727A,0xA5D8E0,0xECFEFF], # 15 ICE
    [0xFFF7ED,0xA16207,0x29211D,0x1C1512,0x78675D,0xC4B5AA,0xFFF7ED], # 16 COFFEE
    [0xFFFFFF,0x2563EB,0xF3F4F6,0xE5E7EB,0x6B7280,0x374151,0x111827], # 17 LIGHT
    [0x000000,0xFFFFFF,0x000000,0x080808,0x555555,0x888888,0xFFFFFF], # 18 MONO OLED
]

WIDGETS_INITIAL_X = 15
WIDGETS_INITIAL_Y = 20
NAVBAR_INITIAL_X = 30
NAVBAR_INITIAL_Y = 200

WIDGET_OFFSET_X = 100
WIDGET_OFFSET_Y = 90
VALUE_OFFSET_Y = 35

TITLE_TEXT_SIZE = 1.5
VALUE_TEXT_SIZE = 1.2

MAX_COLUMNS = 3


pcTitles = ["CPU", "RAM", "TEMP", "GPU", "VRAM", "TEMP"]
opi5Titles = ["CPU", "RAM", "TEMP", "DOWN", "SSD", "ZRAM"]
buttons = ["OPI5", "CLR", "PC"]

widgets = []
valueLabels = []
navbar  = []

OPI5_MODE = 0
CLR_MODE = 1
PC_MODE = 2

current_mode = 1
previous_mode = 0


def updateColors():
    global themePointer
    if themePointer == len(themes)-1:
        previousTheme = themePointer
        themePointer = 0
    else:
        previousTheme = themePointer
        themePointer = themePointer + 1

    Widgets.fillScreen(themes[themePointer][IDX_BACKGROUND_COLOR])

    widgets[0].setColor(themes[themePointer][IDX_TITLE_TEXT_COLOR], themes[themePointer][IDX_BACKGROUND_COLOR])
    widgets[1].setColor(themes[themePointer][IDX_TITLE_TEXT_COLOR], themes[themePointer][IDX_BACKGROUND_COLOR])
    widgets[2].setColor(themes[themePointer][IDX_TITLE_TEXT_COLOR], themes[themePointer][IDX_BACKGROUND_COLOR])
    widgets[3].setColor(themes[themePointer][IDX_TITLE_TEXT_COLOR], themes[themePointer][IDX_BACKGROUND_COLOR])
    widgets[4].setColor(themes[themePointer][IDX_TITLE_TEXT_COLOR], themes[themePointer][IDX_BACKGROUND_COLOR])
    widgets[5].setColor(themes[themePointer][IDX_TITLE_TEXT_COLOR], themes[themePointer][IDX_BACKGROUND_COLOR])

    valueLabels[0].setColor(themes[themePointer][IDX_VALUE_TEXT_COLOR], themes[themePointer][IDX_BACKGROUND_COLOR])
    valueLabels[1].setColor(themes[themePointer][IDX_VALUE_TEXT_COLOR], themes[themePointer][IDX_BACKGROUND_COLOR])
    valueLabels[2].setColor(themes[themePointer][IDX_VALUE_TEXT_COLOR], themes[themePointer][IDX_BACKGROUND_COLOR])
    valueLabels[3].setColor(themes[themePointer][IDX_VALUE_TEXT_COLOR], themes[themePointer][IDX_BACKGROUND_COLOR])
    valueLabels[4].setColor(themes[themePointer][IDX_VALUE_TEXT_COLOR], themes[themePointer][IDX_BACKGROUND_COLOR])
    valueLabels[5].setColor(themes[themePointer][IDX_VALUE_TEXT_COLOR], themes[themePointer][IDX_BACKGROUND_COLOR])

    navbar[0].setColor(themes[themePointer][IDX_NAV_TEXT_COLOR], themes[themePointer][IDX_NAV_BACKGROUND_COLOR])
    navbar[1].setColor(themes[themePointer][IDX_HIGHLIGHTED_NAV_TEXT_COLOR], themes[themePointer][IDX_HIGHLIGHTED_NAV_BACKGROUND_COLOR])
    navbar[2].setColor(themes[themePointer][IDX_NAV_TEXT_COLOR], themes[themePointer][IDX_NAV_BACKGROUND_COLOR])

def highligh(idx: int):
    global current_mode
    global previous_mode
    if idx == current_mode and themePointer == previousTheme:
        return
    previous_mode = current_mode
    current_mode = idx
    navbar[previous_mode].setColor(themes[themePointer][IDX_NAV_TEXT_COLOR], themes[themePointer][IDX_NAV_BACKGROUND_COLOR])
    navbar[current_mode].setColor(themes[themePointer][IDX_HIGHLIGHTED_NAV_TEXT_COLOR], themes[themePointer][IDX_HIGHLIGHTED_NAV_BACKGROUND_COLOR])

def button_a_handler(state):
    highligh(OPI5_MODE)

def button_b_handler(state):
    updateColors()
    highligh(CLR_MODE)

def button_c_handler(state):
    highligh(PC_MODE)

def buildWidgets(titles: list[str]):
    x_multiplier = 0
    y_multiplier = 0

    Widgets.fillScreen(themes[themePointer][IDX_BACKGROUND_COLOR])

    for idx, title in enumerate(titles):
        if idx != 0 and idx % MAX_COLUMNS == 0:
            x_multiplier = 0
            y_multiplier += 1

        x = WIDGETS_INITIAL_X + x_multiplier * WIDGET_OFFSET_X
        y = WIDGETS_INITIAL_Y + y_multiplier * WIDGET_OFFSET_Y

        widgets.append(
            Widgets.Label(title, x, y, TITLE_TEXT_SIZE, themes[themePointer][IDX_TITLE_TEXT_COLOR], themes[themePointer][IDX_BACKGROUND_COLOR], Widgets.FONTS.DejaVu18))

        valueLabels.append(
            Widgets.Label("0", x, y + VALUE_OFFSET_Y, VALUE_TEXT_SIZE, themes[themePointer][IDX_VALUE_TEXT_COLOR], themes[themePointer][IDX_BACKGROUND_COLOR], Widgets.FONTS.DejaVu24))

        x_multiplier += 1

    navbar.append(Widgets.Label(buttons[0], 30, 210, VALUE_TEXT_SIZE, themes[themePointer][IDX_NAV_TEXT_COLOR], themes[themePointer][IDX_NAV_BACKGROUND_COLOR], Widgets.FONTS.DejaVu24))
    navbar.append(Widgets.Label(buttons[1], 135, 210, VALUE_TEXT_SIZE, themes[themePointer][IDX_NAV_TEXT_COLOR], themes[themePointer][IDX_NAV_BACKGROUND_COLOR], Widgets.FONTS.DejaVu24))
    navbar.append(Widgets.Label(buttons[2], 233, 210, VALUE_TEXT_SIZE, themes[themePointer][IDX_NAV_TEXT_COLOR], themes[themePointer][IDX_NAV_BACKGROUND_COLOR], Widgets.FONTS.DejaVu24))


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
        if current_mode != PC_MODE:
            return
        dict = parse_kv(msg)
        widgets[3].setText(pcTitles[3]) # title GPU
        widgets[4].setText(pcTitles[4]) # title VRAM
        widgets[5].setText(pcTitles[5]) # title TEMP GPU

        valueLabels[0].setText(dict["cpu"])       # CPU
        valueLabels[1].setText(dict["ram"])       # RAM
        valueLabels[2].setText(dict["temp_cpu"])  # TEMP CPU

        valueLabels[3].setText(dict["gpu"])       # GPU
        valueLabels[4].setText(dict["vram"])      # VRAM
        valueLabels[5].setText(dict["temp_gpu"])  # TEMP GPU

    if topic == MQTT_OPI_TOPIC.encode('utf-8'):
        if current_mode != OPI5_MODE:
            return
        dict = parse_kv(msg)
        widgets[3].setText(opi5Titles[3])   # title DOWN SPD
        widgets[4].setText(opi5Titles[4])   # title SSD
        widgets[5].setText(opi5Titles[5])   # title ZRAM

        valueLabels[0].setText(dict["cpu"])      # CPU
        valueLabels[1].setText(dict["ram"])      # RAM
        valueLabels[2].setText(dict["temp_cpu"]) # TEMP CPU

        valueLabels[3].setText(dict["net_spd"]) # GPU
        valueLabels[4].setText(dict["ssd"])     # VRAM
        valueLabels[5].setText(dict["zram"])    # TEMP GPU

def connect_mqtt(conf: AppConfig):
    print("SSID:", conf.wifi_ssid)

    client = MQTTClient(MQTT_CLIENT_ID, conf.mqtt_broker_host, port=conf.mqtt_broker_port)
    client.set_callback(on_message)
    client.connect()
    client.subscribe(conf.desktop_topic)
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

    buildWidgets(opi5Titles)
    highligh(OPI5_MODE)

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

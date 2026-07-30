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

class ScreenConfig:
    def __init__(self):
        self.screen_key = ""
        self.header = ""
        self.mqtt_topic = ""
        self.widgets = []
        self.events = []
        self.theme = 0

    def _load_screen(self, data, i):
        self.screen_key = f"screen_{i}"
        self.header = data[self.screen_key]["header"]
        self.mqtt_topic = data[self.screen_key]["mqtt_topic"]
        self.widgets = list(data[self.screen_key]["widgets"])
        self.events = list(data[self.screen_key]["events"])
        self.theme = data[self.screen_key]["theme"]


class AppConfig:
    def __init__(self):
        self.wifi_ssid = "empty"
        self.wifi_pass = "empty"
        self.update_rate = 0.5
        self.mqtt_broker_host="192.168.31.169"
        self.mqtt_broker_port="1883"
        self.screens: list[ScreenConfig] = []
        self.screens_number=1

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
                screens_amount = int(data.get("screens_number"))
                self.screens_number = screens_amount 
                for i in range(1, self.screens_number+1):
                    sconf = ScreenConfig()
                    sconf._load_screen(data, i)
                    self.screens.append(sconf)

                    print("Loaded mqtt topic from config: ", sconf.mqtt_topic)

        except Exception as e:
            print("Failed to load conf:", e)


# =========================
# Wi-Fi connection
# =========================

def connect_wifi():
    global cfg
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if not wlan.isconnected():
        print("Connecting to Wi-Fi...")
        wlan.connect(cfg.wifi_ssid, cfg.wifi_pass)

        while not wlan.isconnected():
            time.sleep(0.5)

    print("Wi-Fi connected to ",cfg.wifi_ssid)
    print("Device IP address:",wlan.ifconfig()[0])


# =========================
# MQTT
# =========================

current_mode = 0
previous_mode = 1

MQTT_CLIENT_ID = b"m5stack-01"

def parse_kv(s: str) -> dict:
    if isinstance(s, bytes):
        s = s.decode('utf-8')
    return dict(pair.split(":", 1) for pair in s.split(","))

def on_message(topic, msg):
    global cfg
    for i in range(cfg.screens_number):
        cfg_topic = str(cfg.screens[i].mqtt_topic)
        if topic == cfg_topic.encode('utf-8') and current_mode == i:
            dict = parse_kv(msg)
            update(topic, dict, cfg.screens[i].widgets, cfg.screens[i].events)

def connect_mqtt():
    global cfg
    print("SSID:", cfg.wifi_ssid)

    client = MQTTClient(MQTT_CLIENT_ID, cfg.mqtt_broker_host, port=cfg.mqtt_broker_port)
    client.set_callback(on_message)
    client.connect()

    for i in range(cfg.screens_number):
        client.subscribe(cfg.screens[i].mqtt_topic)

    print("MQTT connected")

    return client


# =========================
# ANIMATIONS
# =========================

ANIMATION_STEPS = 10
ANIMATION_DELAY = 0.02

current_index = 0
visible_nav_labels = []

POSITIONS = [5, 70, 135]

def update_nav():
    global theme_pointer
    count = len(modes)

    for position in range(3):
        index = (current_index + position) % count
        label = visible_nav_labels[position]
        label.setText(modes[index])

        if position == 0:
            label.setColor(
                themes[theme_pointer][IDX_HIGHLIGHTED_NAV_TEXT_COLOR],
                themes[theme_pointer][IDX_HIGHLIGHTED_NAV_BACKGROUND_COLOR])
        else:
            label.setColor(
                themes[theme_pointer][IDX_NAV_TEXT_COLOR],
                themes[theme_pointer][IDX_BACKGROUND_COLOR])


def animate_nav(direction):
    global current_index

    count = len(modes)
    new_index = (current_index + direction) % count

    if direction == 1:
        start_positions = [5, 70, 135]
        end_positions = [-50, 5, 70]

    else:
        start_positions = [5, 70, 135]
        end_positions = [70, 135, 200]

    for step in range(1, ANIMATION_STEPS + 1):
        progress = step / ANIMATION_STEPS

        for i in range(3):
            start_x = start_positions[i]
            end_x = end_positions[i]

            x = int(start_x + (end_x - start_x) * progress)
            visible_nav_labels[i].setCursor(x, 2)

        M5.update()
        time.sleep(ANIMATION_DELAY)

    current_index = new_index

    for i, label in enumerate(visible_nav_labels):
        label.setCursor(POSITIONS[i], 2)

    update_nav()


# =========================
# UI
# =========================

IDX_HIGHLIGHTED_NAV_TEXT_COLOR = 0
IDX_HIGHLIGHTED_NAV_BACKGROUND_COLOR = 1
IDX_BACKGROUND_COLOR = 2
IDX_NAV_TEXT_COLOR = 3
IDX_TITLE_TEXT_COLOR = 4
IDX_VALUE_TEXT_COLOR = 5

themes = [
    #[navbar] [navback]backg    navcolor titlclr  valcolor
    [0xFFFFFF,0xFFFFFF,0x333333,0x666666,0xAAAAAA,0xFFFFFF], # 0 GREY THEME
    [0xFFFFFF,0xFFFFFF,0x1E2430,0x64748B,0x94A3B8,0xFFFFFF], # 1 DARK BLUE THEME
    [0xFFFFFF,0xFFFFFF,0x1C2521,0x60756B,0x9AAFA5,0xFFFFFF], # 2 DARK GREEN THEME
    [0xFFFFFF,0xFFFFFF,0x211F2B,0x706A80,0xAAA4B8,0xFFFFFF], # 3 CYBERPUNK THEME
    [0xFFFFFF,0xFFFFFF,0x292722,0x756F63,0xADA79B,0xFFFFFF], # 4 AMBER / INDUSTRIAL
    [0x000000,0x00FF41,0x050805,0x287A3D,0x5DBB72,0xD7FFD9], # 5 MATRIX
    [0x282A36,0xBD93F9,0x282A36,0x6272A4,0x8BE9FD,0xF8F8F2], # 6 DRACULA
    [0x2E3440,0x88C0D0,0x2E3440,0x616E88,0xD8DEE9,0xECEFF4], # 7 NORD
    [0x001014,0x00E5FF,0x07181C,0x39727C,0x76B9C2,0xD8FBFF], # 8 CYAN TERMINAL
    [0xFFFFFF,0xA855F7,0x17121F,0x6E5A7E,0xBFA8D1,0xFFFFFF], # 9 PURPLE NEON
    [0xFFFFFF,0xF97316,0x241A17,0x80675D,0xC9A99B,0xFFF7F2], # 10 SUNSET
    [0xFFFFFF,0x0EA5E9,0x0B1F2A,0x4D8299,0x8EC5DC,0xF0FAFF], # 11 OCEAN
    [0xFFFFFF,0x16A34A,0x101C15,0x4C7659,0x9AC2A4,0xF0FFF3], # 12 FOREST
    [0x1A1200,0xFFB000,0x0F0C05,0x80652A,0xC69D4D,0xFFE9A8], # 13 AMBER TERMINAL
    [0xFFFFFF,0xDC2626,0x1F1214,0x7D4B52,0xC38B91,0xFFF5F5], # 14 BLOOD MOON
    [0x102027,0x67E8F9,0x15252B,0x52727A,0xA5D8E0,0xECFEFF], # 15 ICE
    [0xFFF7ED,0xA16207,0x29211D,0x78675D,0xC4B5AA,0xFFF7ED], # 16 COFFEE
    [0xFFFFFF,0x2563EB,0xF3F4F6,0x6B7280,0x374151,0x111827], # 17 LIGHT
    [0x000000,0xFFFFFF,0x000000,0x555555,0x888888,0xFFFFFF], # 18 MONO OLED
]

WIDGETS_INITIAL_X = 20
WIDGETS_INITIAL_Y = 45

WIDGET_OFFSET_X = 100
WIDGET_OFFSET_Y = 90
VALUE_OFFSET_Y = 35

TITLE_TEXT_SIZE = 1.4
VALUE_TEXT_SIZE = 1.2
HEADER_TEXT_SIZE = 1.1
ANIM_TEXT_SIZE_FACTOR = 0.2

MAX_COLUMNS = 3

widgets = []
valueLabels = []
navButtons  = []

extraModes = ["clr"]

theme_pointer = 13
previousTheme = 0


def buildWidgets(titles: list[str]):
    global cfg, theme_pointer
    x_multiplier = 0
    y_multiplier = 0

    theme_pointer = cfg.screens[0].theme

    Widgets.fillScreen(themes[theme_pointer][IDX_BACKGROUND_COLOR])

    for idx, title in enumerate(titles):
        if idx != 0 and idx % MAX_COLUMNS == 0:
            x_multiplier = 0
            y_multiplier += 1

        x = WIDGETS_INITIAL_X + x_multiplier * WIDGET_OFFSET_X
        y = WIDGETS_INITIAL_Y + y_multiplier * WIDGET_OFFSET_Y

        widgets.append(
            Widgets.Label(title, x, y, TITLE_TEXT_SIZE, themes[theme_pointer][IDX_TITLE_TEXT_COLOR], themes[theme_pointer][IDX_BACKGROUND_COLOR], Widgets.FONTS.DejaVu18))

        valueLabels.append(
            Widgets.Label("0", x, y + VALUE_OFFSET_Y, VALUE_TEXT_SIZE, themes[theme_pointer][IDX_VALUE_TEXT_COLOR], themes[theme_pointer][IDX_BACKGROUND_COLOR], Widgets.FONTS.DejaVu24))

        x_multiplier += 1


    global visible_nav_labels
    for i in range(3):
        if i == 0:
            txt_color = themes[theme_pointer][IDX_HIGHLIGHTED_NAV_TEXT_COLOR]
            back_color = themes[theme_pointer][IDX_HIGHLIGHTED_NAV_BACKGROUND_COLOR]
        else:
            txt_color = themes[theme_pointer][IDX_NAV_TEXT_COLOR]
            back_color = themes[theme_pointer][IDX_BACKGROUND_COLOR]

        visible_nav_labels.append(Widgets.Label(modes[i], POSITIONS[i], 2, HEADER_TEXT_SIZE, txt_color, back_color, Widgets.FONTS.DejaVu24))

    navLines.append(Widgets.Rectangle(0, 0, 320, 2, themes[theme_pointer][IDX_HIGHLIGHTED_NAV_BACKGROUND_COLOR], themes[theme_pointer][IDX_HIGHLIGHTED_NAV_BACKGROUND_COLOR]))
    navLines.append(Widgets.Rectangle(0, 31, 320, 2, themes[theme_pointer][IDX_HIGHLIGHTED_NAV_BACKGROUND_COLOR], themes[theme_pointer][IDX_HIGHLIGHTED_NAV_BACKGROUND_COLOR]))

    navButtons.append(Widgets.Triangle(90, 219, 39, 229, 90, 240, themes[theme_pointer][IDX_NAV_TEXT_COLOR], themes[theme_pointer][IDX_NAV_TEXT_COLOR]))
    navButtons.append(Widgets.Rectangle(128, 219, 55, 21, themes[theme_pointer][IDX_NAV_TEXT_COLOR], themes[theme_pointer][IDX_NAV_TEXT_COLOR]))
    navButtons.append(Widgets.Triangle(219, 219, 276, 229, 219, 240, themes[theme_pointer][IDX_NAV_TEXT_COLOR], themes[theme_pointer][IDX_NAV_TEXT_COLOR]))


def switchTheme():
    global previousTheme, theme_pointer
    previousTheme = theme_pointer
    if theme_pointer == len(themes)-1:
        theme_pointer = 0
    else:
        theme_pointer = theme_pointer + 1


def updateTheme():
    global theme_pointer

    Widgets.fillScreen(themes[theme_pointer][IDX_BACKGROUND_COLOR])

    for i, widget in enumerate(widgets):
        widget.setColor(themes[theme_pointer][IDX_TITLE_TEXT_COLOR], themes[theme_pointer][IDX_BACKGROUND_COLOR])
        valueLabels[i].setColor(themes[theme_pointer][IDX_VALUE_TEXT_COLOR], themes[theme_pointer][IDX_BACKGROUND_COLOR])

    for line in navLines:
        line.setColor(themes[theme_pointer][IDX_HIGHLIGHTED_NAV_BACKGROUND_COLOR], themes[theme_pointer][IDX_HIGHLIGHTED_NAV_BACKGROUND_COLOR])

    update_nav()

    for navButton in navButtons:
        navButton.setColor(themes[theme_pointer][IDX_NAV_TEXT_COLOR], themes[theme_pointer][IDX_NAV_TEXT_COLOR])


def update(topic:str, dict: dict, titles:list, events: list):
    if len(valueLabels) == 0:
        return
 
    # same part between modes
    global cfg
    for i in range(cfg.screens_number):
        cfg_topic = cfg.screens[i].mqtt_topic
        if topic == cfg_topic.encode('utf-8'):
            widgets[0].setText(titles[0])
            widgets[1].setText(titles[1])
            widgets[2].setText(titles[2])
            widgets[3].setText(titles[3])
            widgets[4].setText(titles[4])
            widgets[5].setText(titles[5])

            valueLabels[0].setText(dict[events[0]])
            valueLabels[1].setText(dict[events[1]])
            valueLabels[2].setText(dict[events[2]])
            valueLabels[3].setText(dict[events[3]])
            valueLabels[4].setText(dict[events[4]])
            valueLabels[5].setText(dict[events[5]])


def printOnDisplay(str: str):
    M5.Display.fillScreen(themes[theme_pointer][IDX_BACKGROUND_COLOR])
    M5.Display.setCursor(10,10)
    M5.Display.print(str, themes[theme_pointer][IDX_HIGHLIGHTED_NAV_BACKGROUND_COLOR])

def highlightNavButton(idx: int):
    global highlighted
    if not highlighted:
        navButtons[idx].setColor(themes[theme_pointer][IDX_HIGHLIGHTED_NAV_BACKGROUND_COLOR], themes[theme_pointer][IDX_HIGHLIGHTED_NAV_BACKGROUND_COLOR])
        highlighted = True
        global onNextFrame
        onNextFrame = lambda: unhighlightNavButton(idx)

highlighted = False

onNextFrame = lambda: ()

def unhighlightNavButton(idx: int):
    global highlighted
    if highlighted:
        navButtons[idx].setColor(themes[theme_pointer][IDX_NAV_TEXT_COLOR], themes[theme_pointer][IDX_NAV_TEXT_COLOR])
        highlighted = False

current_focus = 0

def switchFocus(next:bool):
    global current_focus
    if next:
        if current_focus == len(modes)-1:
            current_focus = 0
        else:
            current_focus = current_focus + 1
    else:
        if current_focus == 0:
            current_focus = len(modes)-1
        else:
            current_focus = current_focus - 1

def button_a_handler(state):
    highlightNavButton(0)
    switchFocus(False)

def button_b_handler(state):
    highlightNavButton(1)
    global current_mode, theme_pointer, cfg
    for i, _ in enumerate(modes):
        if i == current_focus and i < cfg.screens_number:
            current_mode = i
            if theme_pointer != cfg.screens[i].theme:
                theme_pointer = cfg.screens[i].theme
                updateTheme()
        elif i == current_focus and i >= cfg.screens_number:
            if i - cfg.screens_number == 0: # first of extra screens
                current_mode = i
                switchTheme()
                updateTheme()


def button_c_handler(state):
    highlightNavButton(2)
    switchFocus(True)

navLines = []

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
    global cfg, current_mode, current_focus, mqtt, modes

    printOnDisplay("Reading config...")
    cfg = AppConfig()
    cfg.load_from_file("/sd/conf.json")


    print("SSID:", cfg.wifi_ssid)
    print("MQTT host:", cfg.mqtt_broker_host)
    print("MQTT port:", cfg.mqtt_broker_port)

    printOnDisplay("Connecting Wi-Fi...", )
    connect_wifi()

    printOnDisplay("Connecting MQTT...")

    mqtt = connect_mqtt()
    printOnDisplay("MQTT CONNECTED")

    modes = []
    for i in range(cfg.screens_number):
        modes.append(cfg.screens[i].header)
    for md in extraModes:
        modes.append(md)

    current_mode = 0
    current_focus = 0

    buildWidgets(cfg.screens[0].widgets)

    BtnA.setCallback(type=BtnA.CB_TYPE.WAS_CLICKED,cb=button_a_handler)
    BtnB.setCallback(type=BtnB.CB_TYPE.WAS_CLICKED,cb=button_b_handler)
    BtnC.setCallback(type=BtnC.CB_TYPE.WAS_CLICKED,cb=button_c_handler)


# =========================
# Main loop
# =========================

def loop():
    M5.update()
    global onNextFrame
    onNextFrame()

    if BtnA.wasPressed():
        animate_nav(-1)

    if BtnC.wasPressed():
        animate_nav(1)

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

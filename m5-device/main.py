import M5
import time
import network

from umqtt.simple import MQTTClient


# =========================
# Wi-Fi connection
# =========================

# WIFI_SSID = "TEST"
# WIFI_PASSWORD = "TEST"

# def connect_wifi():
#     wlan = network.WLAN(network.STA_IF)
#     wlan.active(True)

#     if not wlan.isconnected():
#         print("Connecting to Wi-Fi...")
#         wlan.connect(WIFI_SSID,WIFI_PASSWORD)

#         while not wlan.isconnected():
#             time.sleep(0.5)

#     print("Wi-Fi connected")
#     print("Device IP address:",wlan.ifconfig()[0])


# =========================
# MQTT
# =========================

MQTT_BROKER = "192.168.31.212"
MQTT_PORT = 1883
MQTT_CLIENT_ID = b"m5stack-01"
MQTT_TOPIC = "pc/data"

TEXT_COLOR = 0x0000ff
DELAY_UPDATE = 0.5

def parse_kv(s: str) -> dict:
    if isinstance(s, bytes):
        s = s.decode('utf-8')
    return dict(pair.split(":", 1) for pair in s.split(","))

def on_message(topic, msg):
    if topic == MQTT_TOPIC.encode('utf-8'):
        dict = parse_kv(msg)
        M5.Display.fillScreen(0x000000)
        M5.Display.setCursor(10,10)
        M5.Display.print('GPU  VRAM  CPU  RAM  TEMP', TEXT_COLOR)
        M5.Display.setCursor(10,30)
        M5.Display.print('{0:3d}%   {1:3d}%     {2:3d}%  {3:3d}G   {4:3d}°'.format(int(dict["gpu"]), int(dict["vram"]), int(dict["cpu"]), int(dict["ram"]), int(dict["temp"])), TEXT_COLOR)

def connect_mqtt():
    print("Connecting to MQTT broker:",MQTT_BROKER)

    client = MQTTClient(MQTT_CLIENT_ID,MQTT_BROKER,port=MQTT_PORT)
    client.set_callback(on_message)
    client.connect()
    # client.subscribe(MQTT_TOPIC_CPU)
    client.subscribe(MQTT_TOPIC)
    print("MQTT connected")

    return client


# =========================
# Setup
# =========================

def setup():
    M5.begin()

    Widgets.fillScreen(0x222222)
    label0 = Widgets.Label("Text", 38, 47, 1.0, 0xFFFFFF, 0x222222, Widgets.FONTS.DejaVu18)

    label0.setText(str("Label"))
    label0.setFont(Widgets.FONTS.DejaVu12)

    # M5.Display.fillScreen(0x000000)
    # M5.Display.setCursor(10,10)
    # M5.Display.print("Connecting Wi-Fi...")
    # connect_wifi()

    M5.Display.fillScreen(0x000000)
    M5.Display.setCursor(10,10)
    M5.Display.print("Connecting MQTT...")

    global mqtt
    mqtt = connect_mqtt()
    M5.Display.fillScreen(0x000000)
    M5.Display.setCursor(10,10)
    M5.Display.print("MQTT CONNECTED")


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

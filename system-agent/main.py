import paho.mqtt.client as mqtt
import time
import GPUtil
import psutil
import time


MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC = "pc/data"

DELAY_UPDATE = 0.5
GB = 1024*1024*1024


if __name__ == '__main__':
  client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

  print("Connecting to MQTT broker...")
  client.connect(MQTT_BROKER,MQTT_PORT)
  print("Connected")

  while True:
    gpu = GPUtil.getGPUs()[0]
    cpuLoad = psutil.cpu_percent(percpu=True)[0]
    ram = psutil.virtual_memory()
    temps = psutil.sensors_temperatures()
    temp_cpu = temps["k10temp"][0]

    client.publish(MQTT_TOPIC, 'gpu:{0:3.0f},vram:{1:3.0f},cpu:{2:3.0f},ram:{3:3.0f},temp:{4:3.0f}'.format(gpu.load*100, gpu.memoryUtil*100, cpuLoad * 100, ram.used/GB, temp_cpu.current))

    time.sleep(DELAY_UPDATE)


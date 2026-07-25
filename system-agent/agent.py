import paho.mqtt.client as mqtt
import time
import GPUtil
import psutil
import time


MQTT_BROKER = "192.168.31.169"
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
    cpuLoad = psutil.cpu_percent(percpu=False)
    ram = psutil.virtual_memory()
    temps = psutil.sensors_temperatures()
    temp_gpu = temps["amdgpu"][0]
    temp_cpu = temps["k10temp"][0]

    client.publish(MQTT_TOPIC, 
                   'gpu:{0:3.0f}%,vram:{1:3.1f}G,temp_gpu:{2:3.0f}°,cpu:{3:3.0f}%,ram:{4:3.1f}G,temp_cpu:{5:3.0f}°'.format(
                      gpu.load*100, gpu.memoryUtil * (gpu.memoryTotal / 1024), temp_gpu.current, cpuLoad * 100, ram.used/GB, temp_cpu.current))

    time.sleep(DELAY_UPDATE)


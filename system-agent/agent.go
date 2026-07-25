package main

import (
	"context"
	"fmt"
	"log"
	"time"

	"github.com/NVIDIA/go-nvml/pkg/nvml"
	mqtt "github.com/eclipse/paho.mqtt.golang"
	"github.com/shirou/gopsutil/v4/cpu"
	"github.com/shirou/gopsutil/v4/mem"
	"github.com/shirou/gopsutil/v4/sensors"
)

const (
	MQTT_TOPIC     = "pc/data"
	MQTT_BROKER    = "tcp://192.168.31.169:1883"
	CPU_SENSOR_KEY = "k10temp_tctl"
	UPDATE_DELAY   = time.Millisecond * 500
)

func main() {
	opts := mqtt.NewClientOptions()
	opts.AddBroker(MQTT_BROKER)
	mqtt := mqtt.NewClient(opts)
	fmt.Println("Connecting to MQTT broker...")
	_ = mqtt.Connect()
	fmt.Println("Connected")

	for {
		stats := getSystemStats()
		_ = mqtt.Publish(MQTT_TOPIC, 0, true,
			fmt.Sprintf("gpu:%d%%,vram:%.1fG,temp_gpu:%d°,cpu:%.0f%%,ram:%.1fG,temp_cpu:%.0f°",
				stats.gpuUtilPerc, stats.vramGb, stats.tempGpuCels, stats.cpuUtilPerc, stats.ramGb, stats.tempCpuCels))

		time.Sleep(UPDATE_DELAY)
	}
}

type Stats struct {
	gpuUtilPerc uint32
	cpuUtilPerc float64
	vramGb      float64
	ramGb       float64
	tempGpuCels uint32
	tempCpuCels float64
}

func getSystemStats() Stats {
	cpu_perc, _ := cpu.Percent(0, false)
	ram, _ := mem.VirtualMemory()

	// TODO: dump all sensors
	sensors, _ := sensors.TemperaturesWithContext(context.Background())
	var cpuTempCelsius float64
	for _, sensor := range sensors {
		if sensor.SensorKey == CPU_SENSOR_KEY {
			cpuTempCelsius = sensor.Temperature
		}
	}

	ret := nvml.Init()
	if ret != nvml.SUCCESS {
		log.Fatalf("Unable to initialize NVML: %v", nvml.ErrorString(ret))
	}
	defer func() {
		ret := nvml.Shutdown()
		if ret != nvml.SUCCESS {
			log.Fatalf("Unable to shutdown NVML: %v", nvml.ErrorString(ret))
		}
	}()

	device, _ := nvml.DeviceGetHandleByIndex(0)
	gpuUtilization, _ := nvml.DeviceGetUtilizationRates(device)
	vram, _ := device.GetMemoryInfo()
	gpuTempCelsius, _ := nvml.DeviceGetTemperature(device, nvml.TEMPERATURE_GPU)

	return Stats{
		gpuUtilPerc: gpuUtilization.Gpu,
		vramGb:      float64(vram.Used) / (1024 * 1024 * 1024),
		tempGpuCels: gpuTempCelsius,

		cpuUtilPerc: cpu_perc[0] * 100,
		ramGb:       float64(ram.Used) / (1024 * 1024 * 1024),
		tempCpuCels: cpuTempCelsius, // dont work
	}
}

package main

import (
	"context"
	"fmt"
	"log"
	"runtime"
	"sync"
	"time"

	"github.com/NVIDIA/go-nvml/pkg/nvml"
	mqtt "github.com/eclipse/paho.mqtt.golang"
	"github.com/shirou/gopsutil/v4/cpu"
	"github.com/shirou/gopsutil/v4/disk"
	"github.com/shirou/gopsutil/v4/load"
	"github.com/shirou/gopsutil/v4/mem"
	"github.com/shirou/gopsutil/v4/sensors"
)

const (
	MQTT_DESKTOP_TOPIC       = "pc/data"
	MQTT_ORANGEPI5_TOPIC     = "opi5/data"
	MQTT_BROKER              = "tcp://192.168.31.169:1883"
	DESKTOP_CPU_SENSOR_KEY   = "k10temp_tctl"
	ORANGEPI5_CPU_SENSOR_KEY = "soc_thermal"
	UPDATE_DELAY             = time.Millisecond * 500
)

func init() {
	log.Println("system:" + runtime.GOOS)
	sensors, _ := sensors.TemperaturesWithContext(context.Background())
	sync.OnceFunc(func() {
		for _, sensor := range sensors {
			log.Println(sensor)
		}
	})()
}

func main() {
	opts := mqtt.NewClientOptions()
	opts.AddBroker(MQTT_BROKER)
	mqtt := mqtt.NewClient(opts)
	fmt.Println("Connecting to MQTT broker...")
	_ = mqtt.Connect()
	fmt.Println("Connected")

	for {
		// pc
		opistats, _ := getSystemStats(ORANGE_PI5_DEVICE_TYPE)
		_ = mqtt.Publish(MQTT_ORANGEPI5_TOPIC, 0, true,
			fmt.Sprintf("cpu:%.0f%%,ram:%.1fG,temp_cpu:%.0f°,pwr:%d%%,ssd:%d%%,zram:%.0f",
				opistats.cpuUtilPerc, opistats.ramGb, opistats.tempCpuCels, opistats.power, opistats.ssdPerc, opistats.zram))

		// opistats, pcstats := getSystemStats(DESKTOP_DEVICE_TYPE)
		// _ = mqtt.Publish(MQTT_DESKTOP_TOPIC, 0, true,
		// 	fmt.Sprintf("gpu:%d%%,vram:%.1fG,temp_gpu:%d°,cpu:%.0f%%,ram:%.1fG,temp_cpu:%.0f°",
		// 		pcstats.gpuUtilPerc, pcstats.vramGb, pcstats.tempGpuCels, pcstats.cpuUtilPerc, pcstats.ramGb, pcstats.tempCpuCels))
		// opistats

		time.Sleep(UPDATE_DELAY)
	}
}

type OrangePi5Stats struct {
	cpuUtilPerc float64
	ramGb       float64
	tempCpuCels float64

	// optional
	power   uint32
	zram    float64
	ssdPerc uint32
}

type DesktopStats struct {
	cpuUtilPerc float64
	ramGb       float64
	tempCpuCels float64

	// optional
	gpuUtilPerc uint32
	vramGb      float64
	tempGpuCels uint32
}

type DeviceType byte

const (
	ORANGE_PI5_DEVICE_TYPE DeviceType = 0
	DESKTOP_DEVICE_TYPE    DeviceType = 1
)

var Retards = []string{"", ""}

func getSystemStats(typee DeviceType) (OrangePi5Stats, DesktopStats) {
	cpu_perc, err := cpu.Percent(0, false)
	if err != nil {
		log.Printf("Unable to get temperature: %v", err)
	}

	ram, err := mem.VirtualMemory()
	if err != nil {
		log.Printf("Unable to get temperature: %v", err)
	}

	var cpuTempCelsius float64
	sensors, err := sensors.TemperaturesWithContext(context.Background())
	if err != nil {
		log.Printf("Unable to get temperature: %v", err)
	}
	for _, sensor := range sensors {
		if typee == DESKTOP_DEVICE_TYPE && sensor.SensorKey == DESKTOP_CPU_SENSOR_KEY {
			cpuTempCelsius = sensor.Temperature
		}
		if typee == ORANGE_PI5_DEVICE_TYPE && sensor.SensorKey == ORANGEPI5_CPU_SENSOR_KEY {
			cpuTempCelsius = sensor.Temperature
		}
	}

	if typee == DESKTOP_DEVICE_TYPE {
		ret := nvml.Init()
		if ret != nvml.SUCCESS {
			log.Printf("Unable to initialize NVML: %v", nvml.ErrorString(ret))
		}
		defer func() {
			ret := nvml.Shutdown()
			if ret != nvml.SUCCESS {
				log.Printf("Unable to shutdown NVML: %v", nvml.ErrorString(ret))
			}
		}()

		device, err := nvml.DeviceGetHandleByIndex(0)
		if ret != nvml.SUCCESS {
			log.Printf("Unable to get device: %v", err)
		}

		gpuUtilization, ret := nvml.DeviceGetUtilizationRates(device)
		if ret != nvml.SUCCESS {
			log.Printf("Unable to get gpuUtilization: %v", err)
		}

		vram, ret := device.GetMemoryInfo()
		if ret != nvml.SUCCESS {
			log.Printf("Unable to get vram: %v", err)
		}

		gpuTempCelsius, ret := nvml.DeviceGetTemperature(device, nvml.TEMPERATURE_GPU)
		if ret != nvml.SUCCESS {
			log.Printf("Unable to get gpuTempCelsius: %v", err)
		}

		return OrangePi5Stats{}, DesktopStats{
			cpuUtilPerc: cpu_perc[0] * 100,
			ramGb:       float64(ram.Used) / (1024 * 1024 * 1024),
			tempCpuCels: cpuTempCelsius,

			gpuUtilPerc: gpuUtilization.Gpu,
			vramGb:      float64(vram.Used) / (1024 * 1024 * 1024),
			tempGpuCels: gpuTempCelsius,
		}
	}

	if typee == ORANGE_PI5_DEVICE_TYPE {
		misc, _ := load.Misc()
		fmt.Println("misc", misc)

		avg, _ := load.Avg()
		fmt.Println("avg", avg)

		str, _ := disk.Label("sd")
		fmt.Println("disk", str)

		return OrangePi5Stats{
			cpuUtilPerc: cpu_perc[0] * 100,
			ramGb:       float64(ram.Used) / (1024 * 1024 * 1024),
			tempCpuCels: cpuTempCelsius,
			power:       10,
			zram:        20,
			ssdPerc:     40,
		}, DesktopStats{}
	}

	return OrangePi5Stats{}, DesktopStats{}
}

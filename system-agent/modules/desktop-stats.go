package modules

import (
	"context"
	"fmt"

	"github.com/NVIDIA/go-nvml/pkg/nvml"
	"github.com/shirou/gopsutil/v4/cpu"
	"github.com/shirou/gopsutil/v4/mem"
	"github.com/shirou/gopsutil/v4/sensors"
)

type DesktopStats struct {
	CpuUtilPerc float64
	RamGb       float64
	TempCpuCels float64

	// optional
	GpuUtilPerc uint32
	VramGb      float64
	TempGpuCels uint32
}

type DeviceType byte

const (
	ORANGE_PI5_DEVICE_TYPE DeviceType = 0
	DESKTOP_DEVICE_TYPE    DeviceType = 1
	DESKTOP_CPU_SENSOR_KEY            = "k10temp_tctl"
)

func GetSystemDesktopStats(log *Logger) string {
	cpu_perc, err := cpu.Percent(0, false)
	if err != nil {
		log.Logf("Unable to get temperature: %v", err)
	}

	ram, err := mem.VirtualMemory()
	if err != nil {
		log.Logf("Unable to get temperature: %v", err)
	}

	var cpuTempCelsius float64
	sensors, err := sensors.TemperaturesWithContext(context.Background())
	if err != nil {
		log.Logf("Unable to get temperature: %v", err)
	}
	for _, sensor := range sensors {
		if sensor.SensorKey == DESKTOP_CPU_SENSOR_KEY {
			cpuTempCelsius = sensor.Temperature
		}
	}

	ret := nvml.Init()
	if ret != nvml.SUCCESS {
		log.Logf("Unable to initialize NVML: %v", nvml.ErrorString(ret))
	}
	defer func() {
		ret := nvml.Shutdown()
		if ret != nvml.SUCCESS {
			log.Logf("Unable to shutdown NVML: %v", nvml.ErrorString(ret))
		}
	}()

	device, err := nvml.DeviceGetHandleByIndex(0)
	if ret != nvml.SUCCESS {
		log.Logf("Unable to get device: %v", err)
	}

	gpuUtilization, ret := nvml.DeviceGetUtilizationRates(device)
	if ret != nvml.SUCCESS {
		log.Logf("Unable to get gpuUtilization: %v", err)
	}

	vram, ret := device.GetMemoryInfo()
	if ret != nvml.SUCCESS {
		log.Logf("Unable to get vram: %v", err)
	}

	gpuTempCelsius, ret := nvml.DeviceGetTemperature(device, nvml.TEMPERATURE_GPU)
	if ret != nvml.SUCCESS {
		log.Logf("Unable to get gpuTempCelsius: %v", err)
	}

	return fmt.Sprintf("cpu:%.0f%%,ram:%.1fG,temp_cpu:%.0f°,gpu:%d%%,vram:%.1fG,temp_gpu:%d°",
		cpu_perc[0]*100, float64(ram.Used)/(1024*1024*1024), cpuTempCelsius, gpuUtilization.Gpu, float64(vram.Used)/(1024*1024*1024), gpuTempCelsius)
}

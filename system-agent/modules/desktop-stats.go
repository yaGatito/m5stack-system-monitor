//go:build nvidia

package modules

import (
	"context"
	"strconv"
	"strings"
	"sync"
	"system-agent/util"
	"time"

	"github.com/NVIDIA/go-nvml/pkg/nvml"
	"github.com/shirou/gopsutil/v4/cpu"
	"github.com/shirou/gopsutil/v4/mem"
	"github.com/shirou/gopsutil/v4/sensors"
)

const DESKTOP_STATS_EVENT_KEYS = "cpu,ram,temp_cpu,gpu,vram,temp_gpu"

type DesktopStats struct {
	CpuUtilPerc float64
	RamGb       float64
	TempCpuCels float64

	// optional
	GpuUtilPerc float64
	VramGb      float64
	TempGpuCels float64
}

func GetSystemDesktopStats(log *util.Logger, cpuSensor string, updateDelay time.Duration) string {
	stats := fetchSystemDesktopStats(log, cpuSensor, updateDelay)
	return createDesktopStatsPayload(stats)
}

func fetchSystemDesktopStats(log *util.Logger, cpuSensor string, updateDelay time.Duration) DesktopStats {
	cpu_perc, err := cpu.Percent(updateDelay, false)
	if err != nil {
		log.Logf("Unable to get cpu: %v", err)
	}

	ram, err := mem.VirtualMemory()
	if err != nil {
		log.Logf("Unable to get ram: %v", err)
	}

	var cpuTempCelsius float64
	sensors, err := sensors.TemperaturesWithContext(context.Background())
	if err != nil {
		log.Logf("Unable to get temperature: %v", err)
	}
	for _, sensor := range sensors {
		if sensor.SensorKey == cpuSensor {
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

	return DesktopStats{
		CpuUtilPerc: cpu_perc[0] * 100,
		RamGb:       float64(ram.Used) / (1024 * 1024 * 1024),
		TempCpuCels: cpuTempCelsius,

		// optional
		GpuUtilPerc: float64(gpuUtilization.Gpu),
		VramGb:      float64(vram.Used) / (1024 * 1024 * 1024),
		TempGpuCels: float64(gpuTempCelsius),
	}
}

var desktopEvents []string

func createDesktopStatsPayload(stats DesktopStats) string {
	sync.OnceFunc(func() {
		desktopEvents = strings.Split(DESKTOP_STATS_EVENT_KEYS, ",")
	})()

	sb := strings.Builder{}

	sb.WriteString(desktopEvents[0])
	sb.WriteString(":")
	sb.WriteString(strconv.FormatFloat(stats.CpuUtilPerc, 'f', 0, 64))
	sb.WriteString("%,")

	sb.WriteString(desktopEvents[1])
	sb.WriteString(":")
	sb.WriteString(strconv.FormatFloat(stats.RamGb, 'f', 1, 64))
	sb.WriteString("G,")

	sb.WriteString(desktopEvents[2])
	sb.WriteString(":")
	sb.WriteString(strconv.FormatFloat(stats.TempCpuCels, 'f', 0, 64))
	sb.WriteString("°,")

	sb.WriteString(desktopEvents[3])
	sb.WriteString(":")
	sb.WriteString(strconv.FormatFloat(stats.GpuUtilPerc, 'f', 0, 64))
	sb.WriteString("%,")

	sb.WriteString(desktopEvents[4])
	sb.WriteString(":")
	sb.WriteString(strconv.FormatFloat(stats.VramGb, 'f', 1, 64))
	sb.WriteString("G,")

	sb.WriteString(desktopEvents[5])
	sb.WriteString(":")
	sb.WriteString(strconv.FormatFloat(stats.TempGpuCels, 'f', 0, 64))
	sb.WriteString("°")

	return sb.String()
}

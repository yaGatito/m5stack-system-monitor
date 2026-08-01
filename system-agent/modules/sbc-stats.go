package modules

import (
	"context"

	"github.com/shirou/gopsutil/v4/cpu"
	"github.com/shirou/gopsutil/v4/disk"
	"github.com/shirou/gopsutil/v4/mem"
	"github.com/shirou/gopsutil/v4/net"
	"github.com/shirou/gopsutil/v4/sensors"
)

type OrangePi5Stats struct {
	CpuUtilPerc float64
	RamGb       float64
	TempCpuCels float64

	// optional
	NetSpd  float64
	Zram    float64
	SsdPerc float64
}

const ORANGEPI5_CPU_SENSOR_KEY = "soc_thermal"

func GetSystemOrangePi5Stats(log *Logger) OrangePi5Stats {
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
		if sensor.SensorKey == ORANGEPI5_CPU_SENSOR_KEY {
			cpuTempCelsius = sensor.Temperature
		}
	}

	diskUsage, err := disk.Usage("/")
	if err != nil {
		log.Logf("Unable to get disk usage: %v", err)
	}

	netinf, err := net.IOCounters(false)
	if err != nil {
		log.Logf("Unable to get net information: %v", err)
	}

	swp, err := mem.SwapMemory()
	if err != nil {
		log.Logf("Unable to get swap info: %v", err)
	}

	return OrangePi5Stats{
		CpuUtilPerc: cpu_perc[0] * 100,
		RamGb:       float64(ram.Used) / (1024 * 1024 * 1024),
		TempCpuCels: cpuTempCelsius,

		NetSpd:  float64(netinf[0].BytesRecv) / (1024 * 1024),
		Zram:    float64(swp.Used) / (1024 * 1024 * 1024),
		SsdPerc: float64(diskUsage.Used) / (1024 * 1024 * 1024),
	}
}

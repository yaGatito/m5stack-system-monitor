package modules

import (
	"context"
	"strconv"
	"strings"
	"sync"
	"system-agent/util"
	"time"

	"github.com/shirou/gopsutil/v4/cpu"
	"github.com/shirou/gopsutil/v4/disk"
	"github.com/shirou/gopsutil/v4/mem"
	"github.com/shirou/gopsutil/v4/net"
	"github.com/shirou/gopsutil/v4/sensors"
)

const OPI5_STATS_EVENT_KEYS = "cpu,ram,temp_cpu,net_spd,ssd,zram"

type OrangePi5Stats struct {
	CpuUtilPerc float64
	RamGb       float64
	TempCpuCels float64

	// optional
	NetSpd  float64
	Zram    float64
	SsdPerc float64
}

func GetSystemOrangePi5Stats(log *util.Logger, cpuSensor string, updateDelay time.Duration) string {
	opiStats := fetchSystemOrangePi5Stats(log, cpuSensor, updateDelay)
	return createOrangeStatsPayload(opiStats)
}

func fetchSystemOrangePi5Stats(log *util.Logger, cpuSensor string, updateDelay time.Duration) OrangePi5Stats {
	cpu_perc, err := cpu.Percent(updateDelay, false)
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
		if sensor.SensorKey == cpuSensor {
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
		RamGb:       float64(ram.Used) / (1024 * 1024 * 1024), //Gb
		TempCpuCels: cpuTempCelsius,

		// optional
		NetSpd:  float64(netinf[0].BytesRecv) / (1024 * 1024), // Mb
		Zram:    float64(diskUsage.Used) / (1024 * 1024 * 1024), //Gb
		SsdPerc: float64(swp.Used) / (1024 * 1024), // Mb
	}
}

var sbcEvents []string

func createOrangeStatsPayload(stats OrangePi5Stats) string {
	sync.OnceFunc(func() {
		sbcEvents = strings.Split(OPI5_STATS_EVENT_KEYS, ",")
	})()

	sb := strings.Builder{}

	sb.WriteString(sbcEvents[0])
	sb.WriteString(":")
	sb.WriteString(strconv.FormatFloat(stats.CpuUtilPerc, 'f', 1, 64))
	sb.WriteString("%,")

	sb.WriteString(sbcEvents[1])
	sb.WriteString(":")
	sb.WriteString(strconv.FormatFloat(stats.RamGb, 'f', 1, 64))
	sb.WriteString("G,")

	sb.WriteString(sbcEvents[2])
	sb.WriteString(":")
	sb.WriteString(strconv.FormatFloat(stats.TempCpuCels, 'f', 1, 64))
	sb.WriteString("°,")

	sb.WriteString(sbcEvents[3])
	sb.WriteString(":")
	sb.WriteString(strconv.FormatFloat(stats.NetSpd, 'f', 1, 64))
	sb.WriteString("M,")

	sb.WriteString(sbcEvents[4])
	sb.WriteString(":")
	sb.WriteString(strconv.FormatFloat(stats.Zram, 'f', 1, 64))
	sb.WriteString("M,")

	sb.WriteString(sbcEvents[5])
	sb.WriteString(":")
	sb.WriteString(strconv.FormatFloat(stats.SsdPerc, 'f', 1, 64))
	sb.WriteString("G")

	return sb.String()
}

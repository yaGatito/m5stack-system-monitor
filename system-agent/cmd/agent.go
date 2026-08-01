package main

import (
	"context"
	"fmt"
	"log"
	"os"
	"runtime"
	"sync"
	"system-agent/modules"
	"time"

	mqtt "github.com/eclipse/paho.mqtt.golang"
	"github.com/shirou/gopsutil/v4/sensors"
)

const (
	MQTT_DESKTOP_TOPIC   = "data/desktop"
	MQTT_ORANGEPI5_TOPIC = "data/orangepi5"
	MQTT_FCST_TOPIC      = "data/fcst"
	MQTT_BROKER          = "tcp://192.168.31.169:1883"
	UPDATE_DELAY         = time.Millisecond * 500
)

func init() {
	logger = &modules.Logger{
		Logger: log.Default(),
	}

	logger.Log("system:" + runtime.GOOS)
	sensors, _ := sensors.TemperaturesWithContext(context.Background())
	sync.OnceFunc(func() {
		for _, sensor := range sensors {
			logger.Log(sensor.String())
		}
	})()
}

const DEVICE_AGENT = "DEVICE_AGENT"

var logger *modules.Logger

func main() {
	agentType := os.Getenv(DEVICE_AGENT)
	opts := mqtt.NewClientOptions()
	opts.AddBroker(MQTT_BROKER)
	mqtt := mqtt.NewClient(opts)
	mqttLock := sync.Mutex{}

	logger.Log("Connecting to MQTT broker...")
	_ = mqtt.Connect()
	logger.Log("Connected")

	weatherEnabled := os.Getenv("WEATHER_PLUGIN") == "true"
	coordsLat := os.Getenv("LOCATION_LAT")
	coordsLon := os.Getenv("LOCATION_LON")
	weatherToken := os.Getenv("WEATHER_TOKEN")

	wg := sync.WaitGroup{}
	// logs := make(chan string, 100)

	if weatherEnabled {
		wg.Add(1)
		go func() {
			for {
				weatherStats := modules.GetWeather(logger, coordsLat, coordsLon, weatherToken)

				mqttLock.Lock()
				_ = mqtt.Publish(MQTT_FCST_TOPIC, 0, true, weatherStats)
				mqttLock.Unlock()

				// _ = mqtt.Publish(MQTT_ORANGEPI5_TOPIC, 0, true,
				// 		fmt.Sprintf("cpu:%.0f%%,ram:%.1fG,temp_cpu:%.0f°,net_spd:%.1fM,ssd:%.1fG,zram:%.1fG",
				// 			opistats.CpuUtilPerc, opistats.RamGb, opistats.TempCpuCels, opistats.NetSpd, opistats.SsdPerc, opistats.Zram))

				time.Sleep(time.Minute)
			}
		}()
	}

	if agentType == "opi5" {
		wg.Add(1)
		go func() {
			for {
				opistats := modules.GetSystemOrangePi5Stats(logger)
				message := fmt.Sprintf("cpu:%.0f%%,ram:%.1fG,temp_cpu:%.0f°,net_spd:%.1fM,ssd:%.1fG,zram:%.1fG",
					opistats.CpuUtilPerc, opistats.RamGb, opistats.TempCpuCels, opistats.NetSpd, opistats.SsdPerc, opistats.Zram)
				// logger.Logf("OrangePi5 stats published: %s", message)

				mqttLock.Lock()
				_ = mqtt.Publish(MQTT_ORANGEPI5_TOPIC, 0, true, message)
				mqttLock.Unlock()

				time.Sleep(time.Second)
			}
		}()
	}

	if agentType == "pc" {
		wg.Add(1)
		go func() {
			for {
				pcstats := modules.GetSystemDesktopStats(logger)
				message := fmt.Sprintf("cpu:%.0f%%,ram:%.1fG,temp_cpu:%.0f°,gpu:%d%%,vram:%.1fG,temp_gpu:%d°",
					pcstats.CpuUtilPerc, pcstats.RamGb, pcstats.TempCpuCels, pcstats.GpuUtilPerc, pcstats.VramGb, pcstats.TempGpuCels)
				// logger.Logf("Desktop stats published: %s", message)

				mqttLock.Lock()
				_ = mqtt.Publish(MQTT_DESKTOP_TOPIC, 0, true, message)
				mqttLock.Unlock()

				// if received topic:"dev-id/status",message:"offline" then no sent updates while no "dev-id/status" message:"online"

				time.Sleep(time.Second)
			}
		}()
	}

	wg.Wait()

}

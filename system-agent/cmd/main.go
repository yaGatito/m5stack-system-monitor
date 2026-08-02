package main

import (
	"context"
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
	MQTT_STATUS_TOPIC    = "m5stack/status"

	DEVICE_AGENT_ENV         = "DEVICE_AGENT"
	DEVICE_AGENT_ORANGE_PI_5 = "opi5"
	DEVICE_AGENT_ODESKTOP    = "pc"
	LOCATION_LAT_ENV         = "LOCATION_LAT"
	LOCATION_LON_ENV         = "LOCATION_LON"
	WEATHER_TOKEN_ENV        = "WEATHER_TOKEN"
	WEATHER_PLUGIN_ENV       = "WEATHER_PLUGIN"
	MQTT_BROKER_ENV          = "MQTT_BROKER"

	UPDATE_DELAY         = time.Second
	UPDATE_WEATHER_DELAY = time.Minute * 5
	KEEP_ALIVE           = time.Second * 10
)

func init() {
	logger = &modules.Logger{
		Logger: log.Default(),
	}

	logger.Log("system:" + runtime.GOOS)
	sensors, _ := sensors.TemperaturesWithContext(context.Background())
	for _, sensor := range sensors {
		logger.Log(sensor.String())
	}
}

var logger *modules.Logger

type Agent struct {
	statusChannel chan bool
	logger        *modules.Logger

	mqttLock   sync.Mutex
	mqttClient mqtt.Client

	handler mqtt.MessageHandler

	status      bool
	statusRLock sync.RWMutex
}

func NewAgent(logger *modules.Logger, broker string, keepAlive time.Duration) *Agent {
	a := Agent{
		statusChannel: make(chan bool, 1),
		logger:        logger,
		mqttClient: mqtt.NewClient(mqtt.NewClientOptions().
			AddBroker(broker).
			SetCleanSession(false).
			SetKeepAlive(keepAlive)),
	}

	t1 := a.mqttClient.Connect()
	t1.Wait()

	return &a
}

func (a *Agent) Register(topic string, handler mqtt.MessageHandler) {
	logger.Log("Registered " + topic)
	t2 := a.mqttClient.Subscribe(MQTT_STATUS_TOPIC, 0, handler)
	t2.Wait()

	go func() {
		for {
			logger.Log("Waiting for device status signal..")

			for {
				select {
				case receivedStatus := <-a.statusChannel:
					a.SetActualDeviceStatus(receivedStatus)
					logger.Log("Status updated")
				default:
					time.Sleep(1 * time.Second)
				}
			}
		}
	}()
}

func (a *Agent) DeviceStatusHandler(client mqtt.Client, msg mqtt.Message) {
	if msg.Topic() == MQTT_STATUS_TOPIC {
		logger.Log("Device status received: " + string(msg.Payload()))
		a.statusChannel <- string(msg.Payload()) == "online"
	}
}

func (a *Agent) GetActualDeviceStatus() bool {
	a.statusRLock.RLock()
	defer a.statusRLock.RUnlock()
	return a.status
}

func (a *Agent) SetActualDeviceStatus(updatedStatus bool) {
	a.statusRLock.Lock()
	defer a.statusRLock.Unlock()
	a.status = updatedStatus
}

func (a *Agent) Publish(topic, message string) {
	a.mqttLock.Lock()
	logger.Log("Publishing message in topic: " + topic)
	t1 := a.mqttClient.Publish(topic, 0, true, message)
	t1.Wait()
	a.mqttLock.Unlock()
}

func main() {
	agentType := os.Getenv(DEVICE_AGENT_ENV)
	weatherEnabled := os.Getenv(WEATHER_PLUGIN_ENV) == "true"
	coordsLat := os.Getenv(LOCATION_LAT_ENV)
	coordsLon := os.Getenv(LOCATION_LON_ENV)
	weatherToken := os.Getenv(WEATHER_TOKEN_ENV)
	mqttBroker := os.Getenv(MQTT_BROKER_ENV)

	logger.Log("Connecting to MQTT broker...")

	agent := NewAgent(logger, mqttBroker, KEEP_ALIVE)
	agent.Register(MQTT_STATUS_TOPIC, agent.DeviceStatusHandler)

	wg := sync.WaitGroup{}

	// --- Desktop PC ---
	if agentType == DEVICE_AGENT_ODESKTOP {
		wg.Add(1)
		go func() {
			logger.Log("Waiting for signal to sent desktop updates..")

			for {
				if agent.GetActualDeviceStatus() {
					message := modules.GetSystemDesktopStats(logger)
					agent.Publish(MQTT_DESKTOP_TOPIC, message)
				}
				time.Sleep(UPDATE_DELAY)
			}
		}()
	}

	// --- Weather plugin ---
	if weatherEnabled {
		wg.Add(1)
		go func() {
			logger.Log("Waiting for signal to sent weather updates..")

			for {
				if agent.GetActualDeviceStatus() {
					message := modules.GetWeather(logger, coordsLat, coordsLon, weatherToken)
					agent.Publish(MQTT_FCST_TOPIC, message)
				}
				time.Sleep(UPDATE_WEATHER_DELAY)
			}
		}()
	}

	// --- OrangePi5 ---
	if agentType == DEVICE_AGENT_ORANGE_PI_5 {
		wg.Add(1)
		go func() {
			logger.Log("Waiting for signal to sent opi5 updates..")

			for {
				if agent.GetActualDeviceStatus() {
					message := modules.GetSystemOrangePi5Stats(logger)
					agent.Publish(MQTT_ORANGEPI5_TOPIC, message)
				}
				time.Sleep(UPDATE_DELAY)
			}
		}()
	}

	wg.Wait()
}

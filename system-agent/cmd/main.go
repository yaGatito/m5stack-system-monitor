package main

import (
	"context"
	"log"
	"os"
	"os/signal"
	"strconv"
	"sync"
	"syscall"
	"system-agent/modules"
	"system-agent/util"
	"time"

	mqtt "github.com/eclipse/paho.mqtt.golang"
	"github.com/shirou/gopsutil/v4/sensors"
)

const (
	MQTT_DESKTOP_TOPIC   = "data/desktop"
	MQTT_ORANGEPI5_TOPIC = "data/orangepi5"
	MQTT_FCST_TOPIC      = "data/fcst"
	MQTT_STATUS_TOPIC    = "m5stack/status"
	MQTT_HEALTH_TOPIC    = "agent/status"

	DESKTOP_DEFAULT_SENSOR_KEY     = "k10temp_tctl"
	ORANGE_PI_5_DEFAULT_SENSOR_KEY = "soc_thermal"

	DEVICE_AGENT_ORANGE_PI_5 = "opi5"
	DEVICE_AGENT_DESKTOP     = "desktop"
	DEVICE_AGENT_ENV         = "DEVICE_AGENT"
	CPU_SENSOR_KEY_ENV       = "CPU_SENSOR_KEY"
	LOCATION_LAT_ENV         = "LOCATION_LAT"
	LOCATION_LON_ENV         = "LOCATION_LON"
	WEATHER_TOKEN_ENV        = "WEATHER_TOKEN"
	WEATHER_PLUGIN_ENV       = "WEATHER_PLUGIN"
	MQTT_BROKER_ENV          = "MQTT_BROKER"
	DEBUG_ENV                = "DEBUG"
	KEEP_ALIVE_ENV           = "KEEP_ALIVE"

	DEFAULT_KEEP_ALIVE   = 10
	UPDATE_DELAY         = time.Second
	UPDATE_WEATHER_DELAY = time.Minute * 5
)

func init() {
	debugOn := os.Getenv(DEBUG_ENV) == "true"
	logger = &util.Logger{
		Logger:  log.Default(),
		DebugOn: debugOn,
	}

	sensors, _ := sensors.TemperaturesWithContext(context.Background())
	logger.Log("System sensors key dump. Use CPU_SENSOR_KEY env before running this agent to listen the corresponding sensor.")
	for _, sensor := range sensors {
		logger.Logf("sensor_key: %s; current_temp: %.1f", sensor.SensorKey, sensor.Temperature)
	}
}

var logger *util.Logger

type Agent struct {
	statusChannel chan bool
	logger        *util.Logger

	mqttLock   sync.Mutex
	mqttClient mqtt.Client

	handler mqtt.MessageHandler

	status      bool
	statusRLock sync.RWMutex

	Cfg Config
}

type Config struct {
	AgentType     string
	MqttBroker    string
	CpuSensorKey  string
	KeepAliveSecs time.Duration

	WeatherEnabled bool
	WeatherLong    string
	WeatherLat     string
	WeatherToken   string
}

func (c Config) Validate() bool {
	// Check mandatory fields
	if c.AgentType == "" {
		logger.Log("Empty agent type: " + c.AgentType)
		return false
	}
	if c.MqttBroker == "" {
		logger.Log("Empty mqtt broker: " + c.MqttBroker)
		return false
	}

	return true
}

func NewAgent(logger *util.Logger, cfg Config) *Agent {
	a := Agent{
		statusChannel: make(chan bool, 1),
		logger:        logger,
		mqttClient: mqtt.NewClient(mqtt.NewClientOptions().
			AddBroker(cfg.MqttBroker).
			SetCleanSession(true).
			SetKeepAlive(cfg.KeepAliveSecs)),
		Cfg: cfg,
	}

	t1 := a.mqttClient.Connect()
	t1.Wait()

	return &a
}

func (a *Agent) Register(topic string, handler mqtt.MessageHandler) {
	a.Publish(MQTT_HEALTH_TOPIC, "agent:"+a.Cfg.AgentType)
	logger.Log("Sent agent health status")

	logger.Log("Registered " + topic)
	t2 := a.mqttClient.Subscribe(MQTT_STATUS_TOPIC, 0, handler)
	t2.Wait()

	go func() {
		quit := make(chan os.Signal, 1)
		signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)

		for {
			logger.Log("Waiting for controller status signal..")

			for {
				select {
				case receivedStatus := <-a.statusChannel:
					a.SetActualDeviceStatus(receivedStatus)
					logger.Logf("Controller status updated")

				case _ = <-quit:
					logger.Log("Shutdown signal received, starting graceful shutdown...")
					a.mqttLock.Lock()
					a.mqttClient.Disconnect(0)
					a.mqttLock.Unlock()
					os.Exit(0)

				default:
					time.Sleep(1 * time.Second)
				}
			}
		}
	}()
}

func (a *Agent) Loop() {
	var cpuSensorKey string
	if a.Cfg.CpuSensorKey == "" {
		switch a.Cfg.AgentType {
		case DEVICE_AGENT_ORANGE_PI_5:
			cpuSensorKey = ORANGE_PI_5_DEFAULT_SENSOR_KEY
		case DEVICE_AGENT_DESKTOP:
			cpuSensorKey = DESKTOP_DEFAULT_SENSOR_KEY
		default:
			panic("No agent handler for " + a.Cfg.AgentType)
		}
	}

	wg := sync.WaitGroup{}

	// --- Desktop ---
	if a.Cfg.AgentType == DEVICE_AGENT_DESKTOP {
		wg.Add(1)
		go func() {
			logger.Log("Waiting for signal to sent desktop updates..")

			for {
				if a.GetActualDeviceStatus() {
					message := modules.GetSystemDesktopStats(logger, cpuSensorKey)
					a.Publish(MQTT_DESKTOP_TOPIC, message)
				}

				time.Sleep(UPDATE_DELAY)
			}
		}()
	}

	// --- Weather plugin ---
	if a.Cfg.WeatherEnabled {
		wg.Add(1)
		go func() {
			logger.Log("Waiting for signal to sent weather updates..")

			for {
				if a.GetActualDeviceStatus() {
					message := modules.GetWeather(logger, a.Cfg.WeatherLat, a.Cfg.WeatherLong, a.Cfg.WeatherToken)
					a.Publish(MQTT_FCST_TOPIC, message)
				}
				time.Sleep(UPDATE_WEATHER_DELAY)
			}
		}()
	}

	// --- OrangePi5 ---
	if a.Cfg.AgentType == DEVICE_AGENT_ORANGE_PI_5 {
		wg.Add(1)
		go func() {
			logger.Log("Waiting for signal to sent opi5 updates..")

			for {
				if a.GetActualDeviceStatus() {
					message := modules.GetSystemOrangePi5Stats(logger, cpuSensorKey)
					a.Publish(MQTT_ORANGEPI5_TOPIC, message)
				}
				time.Sleep(UPDATE_DELAY)
			}
		}()
	}

	wg.Wait()
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
	keepAlive, err := strconv.Atoi(os.Getenv(KEEP_ALIVE_ENV))
	if err != nil {
		logger.Log(err.Error())
		keepAlive = DEFAULT_KEEP_ALIVE
	}

	cfg := Config{
		AgentType:     os.Getenv(DEVICE_AGENT_ENV),
		CpuSensorKey:  os.Getenv(CPU_SENSOR_KEY_ENV),
		MqttBroker:    os.Getenv(MQTT_BROKER_ENV),
		KeepAliveSecs: time.Duration(keepAlive) * time.Second,

		WeatherEnabled: os.Getenv(WEATHER_PLUGIN_ENV) == "true",
		WeatherLong:    os.Getenv(LOCATION_LON_ENV),
		WeatherLat:     os.Getenv(LOCATION_LAT_ENV),
		WeatherToken:   os.Getenv(WEATHER_TOKEN_ENV),
	}

	if !cfg.Validate() {
		return
	}

	logger.Log("Connecting to MQTT broker: " + cfg.MqttBroker)

	agent := NewAgent(logger, cfg)

	agent.Register(MQTT_STATUS_TOPIC, agent.DeviceStatusHandler)
	agent.Loop()
}

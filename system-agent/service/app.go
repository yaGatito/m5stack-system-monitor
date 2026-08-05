package service

import (
	"errors"
	"os"
	"os/signal"
	"strconv"
	"sync"
	"syscall"
	"system-agent/modules"
	"system-agent/util"
	"time"

	mqtt "github.com/eclipse/paho.mqtt.golang"
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

	DEVICE_AGENT_ENV            = "DEVICE_AGENT"
	CPU_SENSOR_KEY_ENV          = "CPU_SENSOR_KEY"
	LOCATION_LAT_ENV            = "LOCATION_LAT"
	LOCATION_LON_ENV            = "LOCATION_LON"
	WEATHER_TOKEN_ENV           = "WEATHER_TOKEN"
	WEATHER_PLUGIN_ENV          = "WEATHER_PLUGIN"
	MQTT_BROKER_ENV             = "MQTT_BROKER"
	KEEP_ALIVE_ENV              = "KEEP_ALIVE"
	UPDATE_INTERVAL_ENV         = "SYS_UPDATE_INTERVAL"
	WEATHER_UPDATE_INTERVAL_ENV = "WEATHER_UPDATE_INTERVAL"

	DEFAULT_KEEP_ALIVE              = 10   // seconds
	DEFAULT_STATS_UPDATE_INTERVAL   = 1000 // ms
	DEFAULT_WEATHER_UPDATE_INTERVAL = 5    // minutes
)

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
	AgentType                 string
	MqttBroker                string
	CpuSensorKey              string
	KeepAliveSecs             time.Duration
	SystemStatsUpdateInterval time.Duration

	WeatherEnabled bool
	WeatherLong    string
	WeatherLat     string
	WeatherToken   string
	WeatherUpdate  time.Duration
}

func LoadConfig() (Config, error) {
	keepAlive, err := strconv.Atoi(os.Getenv(KEEP_ALIVE_ENV))
	if err != nil {
		keepAlive = DEFAULT_KEEP_ALIVE
	}
	sysUpdateInterval, err := strconv.Atoi(os.Getenv(UPDATE_INTERVAL_ENV))
	if err != nil {
		sysUpdateInterval = DEFAULT_STATS_UPDATE_INTERVAL
	}
	weatherUpdateInterval, err := strconv.Atoi(os.Getenv(WEATHER_UPDATE_INTERVAL_ENV))
	if err != nil {
		weatherUpdateInterval = DEFAULT_WEATHER_UPDATE_INTERVAL
	}

	cfg := Config{
		AgentType:    os.Getenv(DEVICE_AGENT_ENV),
		CpuSensorKey: os.Getenv(CPU_SENSOR_KEY_ENV),
		MqttBroker:   os.Getenv(MQTT_BROKER_ENV),

		WeatherEnabled: os.Getenv(WEATHER_PLUGIN_ENV) == "true",
		WeatherLong:    os.Getenv(LOCATION_LON_ENV),
		WeatherLat:     os.Getenv(LOCATION_LAT_ENV),
		WeatherToken:   os.Getenv(WEATHER_TOKEN_ENV),

		KeepAliveSecs:             time.Duration(keepAlive) * time.Second,
		SystemStatsUpdateInterval: time.Duration(sysUpdateInterval) * time.Millisecond,
		WeatherUpdate:             time.Duration(weatherUpdateInterval) * time.Minute,
	}

	if err := cfg.Validate(); err != nil {
		return Config{}, err
	}

	return cfg, nil
}

func (c Config) Validate() error {
	// Check mandatory fields
	if c.AgentType == "" {
		return errors.New("empty agent type")
	}
	if c.MqttBroker == "" {
		return errors.New("empty mqtt broker")
	}

	return nil
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

	a.logger.Log("Connecting to MQTT broker: " + cfg.MqttBroker)
	t1 := a.mqttClient.Connect()
	t1.Wait()

	return &a
}

func (a *Agent) Register(handler mqtt.MessageHandler) {
	a.Publish(MQTT_HEALTH_TOPIC, "agent:"+a.Cfg.AgentType)
	a.logger.Log("Sent agent health status")

	a.logger.Log("Registered " + MQTT_STATUS_TOPIC)
	t2 := a.mqttClient.Subscribe(MQTT_STATUS_TOPIC, 0, handler)
	t2.Wait()

	go func() {
		quit := make(chan os.Signal, 1)
		signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)

		for {
			a.logger.Log("Waiting for controller status signal..")

			for {
				select {
				case receivedStatus := <-a.statusChannel:
					a.SetActualDeviceStatus(receivedStatus)
					a.logger.Logf("Controller status updated")

				case _ = <-quit:
					a.logger.Log("Shutdown signal received, starting graceful shutdown...")
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
	if a.Cfg.CpuSensorKey != "" {
		cpuSensorKey = a.Cfg.CpuSensorKey
	} else {
		switch a.Cfg.AgentType {
		case DEVICE_AGENT_ORANGE_PI_5:
			cpuSensorKey = ORANGE_PI_5_DEFAULT_SENSOR_KEY
		case DEVICE_AGENT_DESKTOP:
			cpuSensorKey = DESKTOP_DEFAULT_SENSOR_KEY
		default:
			panic("No pre-default cpu sensor key for " + a.Cfg.AgentType)
		}
	}

	wg := sync.WaitGroup{}

	// --- Desktop ---
	if a.Cfg.AgentType == DEVICE_AGENT_DESKTOP {
		wg.Add(1)
		go func() {
			a.logger.Log("Waiting for signal to sent desktop updates..")

			for {
				if a.GetActualDeviceStatus() {
					message := modules.GetSystemDesktopStats(a.logger, cpuSensorKey, a.Cfg.SystemStatsUpdateInterval)
					a.Publish(MQTT_DESKTOP_TOPIC, message)
				}

				// As cpu.Percent(updateDelay, false) is called with interval
				// It will do the same job as here below,
				// So uncomment only if interval passed to get CPU stats is 0.
				// time.Sleep(a.Cfg.SystemStatsUpdateInterval)
			}
		}()
	}

	// --- Weather plugin ---
	if a.Cfg.WeatherEnabled {
		wg.Add(1)
		go func() {
			a.logger.Log("Waiting for signal to sent weather updates..")

			for {
				if a.GetActualDeviceStatus() {
					message := modules.GetWeather(a.logger, a.Cfg.WeatherLat, a.Cfg.WeatherLong, a.Cfg.WeatherToken)
					a.Publish(MQTT_FCST_TOPIC, message)
				}
				time.Sleep(a.Cfg.WeatherUpdate)
			}
		}()
	}

	// --- OrangePi5 ---
	if a.Cfg.AgentType == DEVICE_AGENT_ORANGE_PI_5 {
		wg.Add(1)
		go func() {
			a.logger.Log("Waiting for signal to sent opi5 updates..")

			for {
				if a.GetActualDeviceStatus() {
					message := modules.GetSystemOrangePi5Stats(a.logger, cpuSensorKey, a.Cfg.SystemStatsUpdateInterval)
					a.Publish(MQTT_ORANGEPI5_TOPIC, message)
				}

				// As cpu.Percent(updateDelay, false) is called with interval
				// It will do the same job as here below,
				// So uncomment only if interval passed to get CPU stats is 0.
				// time.Sleep(a.Cfg.SystemStatsUpdateInterval)
			}
		}()
	}

	wg.Wait()
}

func (a *Agent) ControllerStatusHandler(client mqtt.Client, msg mqtt.Message) {
	if msg.Topic() == MQTT_STATUS_TOPIC {
		a.logger.Log("Device status received: " + string(msg.Payload()))
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
	a.logger.Log("Publishing message in topic: " + topic)
	t1 := a.mqttClient.Publish(topic, 0, true, message)
	t1.Wait()
	a.mqttLock.Unlock()
}

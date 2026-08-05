package main

import (
	"context"
	"log"
	"os"
	"system-agent/service"
	"system-agent/util"

	"github.com/shirou/gopsutil/v4/sensors"
)

var logger *util.Logger

const DEBUG_ENV = "DEBUG"

func init() {
	debugOn := os.Getenv(DEBUG_ENV) == "true"

	logger = &util.Logger{
		Logger:  log.Default(),
		DebugOn: debugOn,
	}

	sensors, _ := sensors.TemperaturesWithContext(context.Background())
	logger.Log("System sensor keys dump. Use CPU_SENSOR_KEY env before running this agent to listen the corresponding sensor.")
	for _, sensor := range sensors {
		logger.Logf("sensor_key: %s; current_temp: %.1f", sensor.SensorKey, sensor.Temperature)
	}
}

func main() {
	cfg, err := service.LoadConfig()
	if err != nil {
		logger.Log("Error: " + err.Error())
		return
	}

	agent := service.NewAgent(logger, cfg)
	agent.Register(agent.ControllerStatusHandler)
	agent.Loop()
}

//go:build !nvidia

package modules

import (
	"log"
	"system-agent/util"
)

func init() {
	log.Default().Println("This device is not support nvidia GPU")
}

func GetSystemDesktopStats(log *util.Logger, cpuSensor string) string {
	return "cpu:0%,ram:0G,temp_cpu:0°,gpu:0%,vram:0G,temp_gpu:0°"
}

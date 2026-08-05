package util

import (
	"log"
	"sync"
)

var logger *Logger

type Logger struct {
	*log.Logger
	DebugOn  bool
	logMutex sync.Mutex
}

func (l *Logger) Log(msg string) {
	l.logMutex.Lock()
	defer l.logMutex.Unlock()
	l.Println(msg)
}

func (l *Logger) Logf(format string, args ...any) {
	l.logMutex.Lock()
	defer l.logMutex.Unlock()
	l.Printf(format, args...)
}

func (l *Logger) Debug(msg string) {
	if l.DebugOn {
		l.Log(msg)
	}
}

func (l *Logger) Debugf(format string, args ...any) {
	if l.DebugOn {
		l.Logf(format, args...)
	}
}

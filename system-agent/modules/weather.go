package modules

import (
	"encoding/json"
	"fmt"
	"net/http"
	"net/url"
	"strconv"
	"strings"
	"sync"
	"system-agent/util"
	"time"
)

const EVENT_KEYS = "temp,cond,humi,wind,press,vis"

// Weather agent: fetches weather data and publishes to MQTT
type WeatherData struct {
	Temperature float64
	Condition   string
	Humidity    float64
	WindSpeed   float64
	Pressure    float64
	Visibility  float64
	LastUpdated string
}

func GetWeather(log *util.Logger, lat, lon, token string) string {
	ticker := time.NewTicker(time.Minute)
	defer ticker.Stop()

	weather, err := fetchWeather(token, lat, lon)
	if err != nil {
		log.Logf("Failed to fetch weather: %v\n", err)
	}

	payload := createWeatherPayload(weather)

	return payload
}

var once sync.Once
var events []string

func createWeatherPayload(weather WeatherData) string {
	once.Do(func() {
		events = strings.Split(EVENT_KEYS, ",")
	})
	sb := strings.Builder{}

	sb.WriteString(events[0])
	sb.WriteString(":")
	sb.WriteString(strconv.FormatFloat(weather.Temperature, 'f', 1, 64))
	sb.WriteString("°")
	sb.WriteString(",")

	sb.WriteString(events[1])
	sb.WriteString(":")
	sb.WriteString(strings.ReplaceAll(weather.Condition, " ", "_"))
	sb.WriteString(",")

	sb.WriteString(events[2])
	sb.WriteString(":")
	sb.WriteString(strconv.FormatFloat(weather.Humidity, 'f', 1, 64))
	sb.WriteString("%,")

	sb.WriteString(events[3])
	sb.WriteString(":")
	sb.WriteString(strconv.FormatFloat(weather.WindSpeed, 'f', 1, 64))
	sb.WriteString("m/s,")

	sb.WriteString(events[4])
	sb.WriteString(":")
	sb.WriteString(strconv.FormatFloat(weather.Pressure, 'f', 1, 64))
	sb.WriteString(",")

	sb.WriteString(events[5])
	sb.WriteString(":")
	sb.WriteString(strconv.FormatFloat(weather.Visibility, 'f', 1, 64))
	sb.WriteString("km")
	return sb.String()
}

// fetchWeather calls OpenWeatherMap 2.5 API
func fetchWeather(token, lat, lon string) (WeatherData, error) {
	url := fmt.Sprintf(
		"https://api.openweathermap.org/data/2.5/weather?lat=%s&lon=%s&units=metric&appid=%s",
		url.QueryEscape(lat), url.QueryEscape(lon), token)

	resp, err := http.Get(url)
	if err != nil {
		return WeatherData{}, fmt.Errorf("weather API request failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return WeatherData{}, fmt.Errorf("weather API returned status %d", resp.StatusCode)
	}

	var result struct {
		Weather []struct {
			Main        string `json:"main"`
			Description string `json:"description"`
		} `json:"weather"`
		Main struct {
			Temperature float64 `json:"temp"`
			Pressure    int     `json:"pressure"`
			Humidity    int     `json:"humidity"`
		} `json:"main"`
		Visibility int `json:"visibility"`
		Wind       struct {
			Speed float64 `json:"speed"`
		} `json:"wind"`
	}

	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return WeatherData{}, fmt.Errorf("failed to decode weather data: %w", err)
	}

	condition := "clear"
	for _, w := range result.Weather {
		condition = w.Main
		break
	}

	return WeatherData{
		Temperature: result.Main.Temperature,
		Condition:   condition,
		Humidity:    float64(result.Main.Humidity),
		WindSpeed:   result.Wind.Speed,
		Pressure:    float64(result.Main.Pressure),
		Visibility:  float64(result.Visibility) / 1000, // km
		LastUpdated: time.Now().UTC().Format(time.RFC3339),
	}, nil
}

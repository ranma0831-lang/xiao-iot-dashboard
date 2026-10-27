// XIAO ESP32S3: 센서값을 서버로 HTTP POST, 응답으로 LED 상태를 받아 반영 (폴링)
// 서버가 인터넷(Render)에 있으므로 보드와 대시보드가 다른 WiFi여도 동작
#include <WiFi.h>
#include <HTTPClient.h>
#include <WiFiClientSecure.h>
#include "secrets.h"  // WIFI_SSID, WIFI_PASS, API_URL, DEVICE_KEY

const int LED_PIN = LED_BUILTIN;  // XIAO ESP32S3 내장 LED(GPIO21), LOW일 때 켜짐
const unsigned long INTERVAL_MS = 3000;

void connectWifi() {
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  Serial.print("WiFi connecting");
  while (WiFi.status() != WL_CONNECTED) { delay(500); Serial.print("."); }
  Serial.printf("\nconnected: %s\n", WiFi.localIP().toString().c_str());
}

void setup() {
  Serial.begin(115200);
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, HIGH);
  connectWifi();
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) connectWifi();

  WiFiClientSecure client;
  client.setInsecure();  // shortcut: 서버 인증서 검증 생략, 실서비스면 루트 CA를 setCACert로 넣을 것
  HTTPClient http;
  http.setTimeout(60000);  // Render 무료 플랜은 잠들었다 깨어나는 데 수십 초 걸림
  http.begin(client, String(API_URL) + "/device/readings");
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-Device-Key", DEVICE_KEY);

  String body = "{\"temperature\":" + String(temperatureRead(), 1) + ",\"rssi\":" + String(WiFi.RSSI()) + "}";
  int code = http.POST(body);
  if (code == 200) {
    bool on = http.getString().indexOf("\"led\":true") >= 0;
    digitalWrite(LED_PIN, on ? LOW : HIGH);
    Serial.printf("sent %s -> led %s\n", body.c_str(), on ? "ON" : "OFF");
  } else {
    Serial.printf("HTTP error %d\n", code);
  }
  http.end();
  delay(INTERVAL_MS);
}

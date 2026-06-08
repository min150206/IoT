#include <Wire.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include "soc/gpio_reg.h"

// --- WiFi Config ---
#define WIFI_SSID     "Min"
#define WIFI_PASSWORD "Min12345"
#define SERVER_URL    "192.168.137.1"  // IP máy bạn

// --- GPIO PIN DEFINITIONS ---
#define PIN_SIOC   1
#define PIN_SIOD   2
#define PIN_VSYNC  3
#define PIN_WRST   4
#define PIN_WR     5
#define PIN_RCLK   6
#define PIN_RRST   7
#define PIN_OE     8
#define D_START_PIN 9

#define OV7670_I2C_ADDR 0x21
#define IMG_WIDTH  640
#define IMG_HEIGHT 480
#define FRAME_SIZE (IMG_WIDTH * IMG_HEIGHT)  // Grayscale: 1 byte/pixel

// Frame buffer
uint8_t frameBuffer[FRAME_SIZE];

void writeRegister(uint8_t reg, uint8_t val) {
  Wire.beginTransmission(OV7670_I2C_ADDR);
  Wire.write(reg);
  Wire.write(val);
  Wire.endTransmission();
  delay(1);
}

void initOV7670Registers() {
  writeRegister(0x12, 0x80);
  delay(100);
  writeRegister(0x12, 0x00);
  writeRegister(0x14, 0x1A);
  writeRegister(0x3C, 0x00);
  writeRegister(0x11, 0x01);
  writeRegister(0x40, 0xC0);
  writeRegister(0x3D, 0x40);
}

void LED_off() {
  rgbLedWrite(RGB_BUILTIN, 0, 0, 0);
}

void captureFrame() {
  // Wait for VSYNC falling edge
  while (digitalRead(PIN_VSYNC) == LOW);
  while (digitalRead(PIN_VSYNC) == HIGH);

  // Reset write pointer & enable write
  digitalWrite(PIN_WRST, LOW);
  digitalWrite(PIN_RCLK, LOW); digitalWrite(PIN_RCLK, HIGH);
  digitalWrite(PIN_WRST, HIGH);
  digitalWrite(PIN_WR, HIGH);

  // Wait full frame captured
  while (digitalRead(PIN_VSYNC) == LOW);
  digitalWrite(PIN_WR, LOW);

  // Prepare FIFO read
  digitalWrite(PIN_RRST, LOW);
  digitalWrite(PIN_RCLK, LOW); digitalWrite(PIN_RCLK, HIGH);
  digitalWrite(PIN_RRST, HIGH);
  digitalWrite(PIN_OE, LOW);

  // Read pixels into buffer
  for (int i = 0; i < FRAME_SIZE; i++) {
    digitalWrite(PIN_RCLK, LOW);
    uint32_t gpio_reg_state = REG_READ(GPIO_IN_REG);
    frameBuffer[i] = (uint8_t)((gpio_reg_state >> D_START_PIN) & 0xFF);
    digitalWrite(PIN_RCLK, HIGH);

    // Discard chroma byte
    digitalWrite(PIN_RCLK, LOW);
    digitalWrite(PIN_RCLK, HIGH);
  }

  digitalWrite(PIN_OE, HIGH);
}

void sendFrame() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi disconnected!");
    return;
  }

  HTTPClient http;
  http.begin(SERVER_URL);
  http.addHeader("Content-Type", "application/octet-stream");
  http.addHeader("X-Image-Width", String(IMG_WIDTH));
  http.addHeader("X-Image-Height", String(IMG_HEIGHT));

  int httpCode = http.POST(frameBuffer, FRAME_SIZE);

  if (httpCode == 200) {
    String response = http.getString();
    Serial.println("Plate: " + response);
  } else {
    Serial.printf("HTTP Error: %d\n", httpCode);
  }

  http.end();
}

void setup() {
  LED_off();
  Serial.begin(115200);

  // Pin setup
  pinMode(PIN_WRST, OUTPUT);
  pinMode(PIN_WR, OUTPUT);
  pinMode(PIN_RCLK, OUTPUT);
  pinMode(PIN_RRST, OUTPUT);
  pinMode(PIN_OE, OUTPUT);
  pinMode(PIN_VSYNC, INPUT);
  for (int i = 0; i < 8; i++) pinMode(D_START_PIN + i, INPUT);

  digitalWrite(PIN_WR, LOW);
  digitalWrite(PIN_OE, HIGH);
  digitalWrite(PIN_RCLK, HIGH);
  digitalWrite(PIN_WRST, HIGH);
  digitalWrite(PIN_RRST, HIGH);

  // I2C + Camera init
  Wire.begin(PIN_SIOD, PIN_SIOC, 100000);
  initOV7670Registers();

  // WiFi connect
  Serial.printf("Connecting to %s", WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected! IP: " + WiFi.localIP().toString());
}

void loop() {
  Serial.println("Capturing frame...");
  captureFrame();

  Serial.println("Sending to server...");
  sendFrame();

  delay(3000);
}
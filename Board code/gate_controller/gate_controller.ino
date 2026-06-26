#include <WiFi.h>
#include <WebServer.h>

// ==================== WIFI CONFIG ====================
#define WIFI_SSID     "Min"
#define WIFI_PASSWORD "Min12345"

// ==================== STATIC IP CONFIG ====================
// Change these to match your hotspot/router's subnet.
// For Windows Mobile Hotspot, the gateway is usually 192.168.137.1,
// so pick a free IP in that same range, e.g. 192.168.137.50
IPAddress staticIP(192, 168, 137, 50);
IPAddress gateway(192, 168, 137, 1);
IPAddress subnet(255, 255, 255, 0);
IPAddress dns(192, 168, 137, 1);

// ==================== PIN DEFINITIONS ====================
// HLK-LD2410C
#define PIN_LD2410_OUT 39

// ==================== TIMING ====================
#define NO_PRESENCE_CONFIRM_MS 2000   // time with no presence before closing
#define MAX_OPEN_TIME_MS       15000  // safety: force close after this even if sensor fails
#define BLINK_INTERVAL_MS      300    // blue blink speed while checking

WebServer server(80);

enum GateState { CLOSED, CHECKING, OPEN };
GateState currentState = CLOSED;

unsigned long openedAt = 0;
unsigned long lastNoPresenceAt = 0;
bool waitingForClear = false;


// ==================== RGB LED HELPERS ====================

void ledRed() {
  rgbLedWrite(RGB_BUILTIN, 255, 0, 0);
}

void ledBlue() {
  rgbLedWrite(RGB_BUILTIN, 0, 0, 255);
}

void ledGreen() {
  rgbLedWrite(RGB_BUILTIN, 0, 255, 0);
}

void ledOff() {
  rgbLedWrite(RGB_BUILTIN, 0, 0, 0);
}


// ==================== GATE ACTIONS ====================

void closeGate() {
  currentState = CLOSED;
  ledRed();   // solid red
  waitingForClear = false;
  Serial.println("[GATE] Closed (solid red).");
}

void openGate() {
  currentState = OPEN;
  ledGreen();  // solid green, no blinking
  openedAt = millis();
  waitingForClear = false;
  Serial.println("[GATE] Opened (solid green).");
}

void setChecking() {
  currentState = CHECKING;   // actual blinking is handled in loop()
  Serial.println("[GATE] Checking plate (blue blink)...");
}


// ==================== HTTP HANDLERS ====================

void handleChecking() {
  setChecking();
  server.send(200, "text/plain", "OK: checking");
}

void handleOpen() {
  openGate();
  server.send(200, "text/plain", "OK: open");
}

void handleClosed() {
  closeGate();
  server.send(200, "text/plain", "OK: closed");
}

void handleStatus() {
  String state;
  switch (currentState) {
    case CLOSED:   state = "closed"; break;
    case CHECKING: state = "checking"; break;
    case OPEN:     state = "open"; break;
  }
  bool presence = digitalRead(PIN_LD2410_OUT) == HIGH;
  String json = "{\"state\":\"" + state + "\",\"presence\":" + (presence ? "true" : "false") + "}";
  server.send(200, "application/json", json);
}


// ==================== SETUP ====================

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("\n--- Parking Gate Controller (with LD2410C) ---");

  pinMode(PIN_LD2410_OUT, INPUT);

  closeGate();  // start in closed state

  // WiFi
  WiFi.mode(WIFI_STA);

  if (!WiFi.config(staticIP, gateway, subnet, dns)) {
    Serial.println("Static IP configuration failed!");
  }

  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.printf("Connecting to %s", WIFI_SSID);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected!");
  Serial.println("ESP32 IP: " + WiFi.localIP().toString());

  // HTTP routes
  server.on("/checking", handleChecking);
  server.on("/open", handleOpen);
  server.on("/closed", handleClosed);
  server.on("/status", handleStatus);
  server.begin();
  Serial.println("HTTP server started.");
}


// ==================== LOOP ====================

void loop() {
  server.handleClient();

  // Blue LED blink while checking
  static unsigned long lastBlink = 0;
  static bool blinkOn = false;
  if (currentState == CHECKING) {
    if (millis() - lastBlink > BLINK_INTERVAL_MS) {
      lastBlink = millis();
      blinkOn = !blinkOn;
      if (blinkOn) ledBlue();
      else ledOff();
    }
  }

  // Auto-close logic when gate is OPEN (driven entirely by the sensor)
  if (currentState == OPEN) {
    bool presence = digitalRead(PIN_LD2410_OUT) == HIGH;

    if (presence) {
      // Vehicle/person still in range, reset the "clear" timer
      waitingForClear = false;
    } else {
      // No presence detected
      if (!waitingForClear) {
        waitingForClear = true;
        lastNoPresenceAt = millis();
      } else if (millis() - lastNoPresenceAt > NO_PRESENCE_CONFIRM_MS) {
        // Confirmed clear for long enough -> close gate
        closeGate();
      }
    }

    // Safety: force close if open too long regardless of sensor
    if (millis() - openedAt > MAX_OPEN_TIME_MS) {
      Serial.println("[GATE] Max open time reached, forcing close.");
      closeGate();
    }
  }
}

// Standalone test: HLK-LD2410C presence sensor + onboard RGB LED
// Green  = presence detected
// Blue   = no presence
//
// Wiring: VCC -> 5V, GND -> GND, OUT -> GPIO 39

#define PIN_LD2410_OUT 39

void ledGreen() {
  rgbLedWrite(RGB_BUILTIN, 0, 255, 0);
}

void ledBlue() {
  rgbLedWrite(RGB_BUILTIN, 0, 0, 255);
}

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("LD2410C presence test starting...");

  pinMode(PIN_LD2410_OUT, INPUT);
}

void loop() {
  bool presence = digitalRead(PIN_LD2410_OUT) == HIGH;

  if (presence) {
    ledGreen();
    Serial.println("Presence: DETECTED");
  } else {
    ledBlue();
    Serial.println("Presence: empty");
  }

  delay(300);
}

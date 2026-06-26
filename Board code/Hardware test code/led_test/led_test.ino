// Quick test: does the onboard RGB LED actually work on this board?
// Upload this alone first, before touching the full gate controller.

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("RGB LED test starting...");
  Serial.print("RGB_BUILTIN pin = ");
  Serial.println(RGB_BUILTIN);
}

void loop() {
  Serial.println("RED");
  rgbLedWrite(RGB_BUILTIN, 255, 0, 0);
  delay(1000);

  Serial.println("GREEN");
  rgbLedWrite(RGB_BUILTIN, 0, 255, 0);
  delay(1000);

  Serial.println("BLUE");
  rgbLedWrite(RGB_BUILTIN, 0, 0, 255);
  delay(1000);

  Serial.println("OFF");
  rgbLedWrite(RGB_BUILTIN, 0, 0, 0);
  delay(1000);
}

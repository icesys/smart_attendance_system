// D2 - I2C scanner: lists every device that answers on the I2C bus (SDA = GPIO9, SCL = GPIO8).
#include <Arduino.h>
#include <Wire.h>

void setup() {
  Serial.begin(115200);
  Wire.begin(9, 8);
  delay(1500);
}

void loop() {
  for (byte a = 1; a < 127; a++) {
    Wire.beginTransmission(a);
    if (Wire.endTransmission() == 0) Serial.printf("Found 0x%02X\n", a);
  }
  Serial.println("---");
  delay(3000);
}

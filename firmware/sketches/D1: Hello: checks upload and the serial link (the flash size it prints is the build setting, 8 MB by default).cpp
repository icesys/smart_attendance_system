// D1 - Hello: checks that the ESP32-S3 works and that uploading works.
// The flash size printed is the one the firmware was built for (8 MB with the default settings), not a measurement of the chip.
#include <Arduino.h>

void setup() {
  Serial.begin(115200);
}

void loop() {
  Serial.printf("ESP32-S3 OK, flash %u MB\n", (unsigned)(ESP.getFlashChipSize() / (1024 * 1024)));
  delay(1000);
}

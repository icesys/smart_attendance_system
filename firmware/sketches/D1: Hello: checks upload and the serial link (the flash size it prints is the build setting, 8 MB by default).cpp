// D1 - Hello: checks that the ESP32-S3 works and that uploading works.
// The flash size printed is the one the firmware was built for (8 MB with the default settings), not a measurement of the chip.
#include <Arduino.h>                                                  // core Arduino functions and Serial

void setup() {                                                        // runs once at power-up
  Serial.begin(115200);                                               // start the USB serial link at 115200 baud
}                                                                     // end of setup

void loop() {                                                         // runs again and again
  Serial.printf("ESP32-S3 OK, flash %u MB\n", (unsigned)(ESP.getFlashChipSize() / (1024 * 1024))); // print the flash size in MB (8 with the default settings)
  delay(1000);                                                        // wait one second between messages
}                                                                     // end of loop
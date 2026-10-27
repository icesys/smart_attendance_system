// D2 - I2C scanner: lists every device that answers on the I2C bus (SDA = GPIO9, SCL = GPIO8).
#include <Arduino.h>                                                  // core Arduino functions and Serial
#include <Wire.h>                                                     // I2C bus driver

void setup() {                                                        // runs once at power-up
  Serial.begin(115200);                                               // start the USB serial link
  Wire.begin(9, 8);                                                   // start I2C: first number = SDA pin, second = SCL pin
  delay(1500);                                                        // give the serial monitor time to open
}                                                                     // end of setup

void loop() {                                                         // runs again and again
  for (byte a = 1; a < 127; a++) {                                    // try every possible I2C address
    Wire.beginTransmission(a);                                        // start talking to address a
    if (Wire.endTransmission() == 0) Serial.printf("Found 0x%02X\n", a); // 0 means a device answered: print its address
  }                                                                   // end of the address loop
  Serial.println("---");                                              // separator between scans
  delay(3000);                                                        // wait three seconds, then scan again
}                                                                     // end of loop
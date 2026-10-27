// D4 - microSD test: CS = GPIO10, SCK = GPIO11, MOSI = GPIO12, MISO = GPIO13.
#include <Arduino.h>                                                  // core Arduino functions and Serial
#include <SPI.h>                                                      // SPI bus driver
#include <SD.h>                                                       // microSD library

void setup() {                                                        // runs once at power-up
  Serial.begin(115200);                                               // start the USB serial link
  delay(1500);                                                        // give the serial monitor time to open
  SPI.begin(11, 13, 12, 10);                                          // SPI pins in this order: SCK, MISO, MOSI, CS
  if (!SD.begin(10, SPI)) {                                           // try to mount the card (CS = GPIO10)
    Serial.println("SD FAIL");                                        // report failure
    return;                                                           // nothing more to do
  }                                                                   // end of "mount failed"
  Serial.printf("SD OK, size %llu MB\n", (unsigned long long)(SD.cardSize() / (1024ULL * 1024ULL))); // card size in MB
  File f = SD.open("/test.txt", FILE_WRITE);                          // create (or overwrite) a test file
  f.println("hello");                                                 // write one line into it
  f.close();                                                          // close it so the data is saved
  Serial.println("write done");                                       // report success
}                                                                     // end of setup

void loop() {}                                                        // nothing to repeat
// D4 - microSD test: CS = GPIO10, SCK = GPIO11, MOSI = GPIO12, MISO = GPIO13.
#include <Arduino.h>
#include <SPI.h>
#include <SD.h>

void setup() {
  Serial.begin(115200);
  delay(1500);
  SPI.begin(11, 13, 12, 10);
  if (!SD.begin(10, SPI)) {
    Serial.println("SD FAIL");
    return;
  }
  Serial.printf("SD OK, size %llu MB\n", (unsigned long long)(SD.cardSize() / (1024ULL * 1024ULL)));
  File f = SD.open("/test.txt", FILE_WRITE);
  f.println("hello");
  f.close();
  Serial.println("write done");
}

void loop() {}

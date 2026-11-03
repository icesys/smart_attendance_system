// D5 - RDM6300 raw test: prints the bytes the reader sends (reader TX -> GPIO18, 9600 baud).
#include <Arduino.h>

HardwareSerial RFID(1);

void setup() {
  Serial.begin(115200);
  RFID.begin(9600, SERIAL_8N1, 18, -1);
}

void loop() {
  while (RFID.available()) {
    int c = RFID.read();
    Serial.printf("%02X ", c);
    if (c == 0x03) Serial.println();
  }
}

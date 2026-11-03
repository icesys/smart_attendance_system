// D7 - Card read with LED and buzzer feedback (works without the PC: GPIO1 green LED, GPIO42 buzzer).
#include <Arduino.h>

HardwareSerial RFID(1);
const int GREEN = 1, BUZ = 42;

void setup() {
  pinMode(GREEN, OUTPUT);
  pinMode(BUZ, OUTPUT);
  RFID.begin(9600, SERIAL_8N1, 18, -1);
}

void loop() {
  if (RFID.available()) {
    while (RFID.available()) RFID.read();
    digitalWrite(GREEN, HIGH);
    digitalWrite(BUZ, HIGH);
    delay(150);
    digitalWrite(BUZ, LOW);
    delay(350);
    digitalWrite(GREEN, LOW);
    while (RFID.available()) RFID.read();
  }
}

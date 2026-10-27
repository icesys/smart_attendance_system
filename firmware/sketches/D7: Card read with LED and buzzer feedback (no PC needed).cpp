// D7 - Card read with LED and buzzer feedback (works without the PC: GPIO1 green LED, GPIO42 buzzer).
#include <Arduino.h>                                                  // core Arduino functions

HardwareSerial RFID(1);                                               // UART1 for the reader
const int GREEN = 1, BUZ = 42;                                        // feedback pins

void setup() {                                                        // runs once at power-up
  pinMode(GREEN, OUTPUT);                                             // green LED pin is an output
  pinMode(BUZ, OUTPUT);                                               // buzzer pin is an output
  RFID.begin(9600, SERIAL_8N1, 18, -1);                               // reader on GPIO18, 9600 baud, no transmit pin
}                                                                     // end of setup

void loop() {                                                         // runs again and again
  if (RFID.available()) {                                             // the reader sent something: a card is on it
    while (RFID.available()) RFID.read();                             // empty the receive buffer
    digitalWrite(GREEN, HIGH);                                        // green LED on
    digitalWrite(BUZ, HIGH);                                          // buzzer on
    delay(150);                                                       // beep for 0.15 s
    digitalWrite(BUZ, LOW);                                           // buzzer off
    delay(350);                                                       // keep the LED on a little longer
    digitalWrite(GREEN, LOW);                                         // green LED off
    while (RFID.available()) RFID.read();                             // drop the repeats sent while the card stayed on the coil
  }                                                                   // end of "card present"
}                                                                     // end of loop
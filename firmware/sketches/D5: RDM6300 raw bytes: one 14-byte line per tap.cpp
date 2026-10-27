// D5 - RDM6300 raw test: prints the bytes the reader sends (reader TX -> GPIO18, 9600 baud).
#include <Arduino.h>                                                  // core Arduino functions and Serial

HardwareSerial RFID(1);                                               // use hardware UART number 1 for the reader

void setup() {                                                        // runs once at power-up
  Serial.begin(115200);                                               // USB serial link to the PC
  RFID.begin(9600, SERIAL_8N1, 18, -1);                               // reader link: 9600 baud, receive on GPIO18, no transmit pin
}                                                                     // end of setup

void loop() {                                                         // runs again and again
  while (RFID.available()) {                                          // while bytes are waiting from the reader
    int c = RFID.read();                                              // take one byte
    Serial.printf("%02X ", c);                                        // print it as two hex digits
    if (c == 0x03) Serial.println();                                  // 0x03 ends a frame: start a new line
  }                                                                   // end of the loop
}                                                                     // end of loop
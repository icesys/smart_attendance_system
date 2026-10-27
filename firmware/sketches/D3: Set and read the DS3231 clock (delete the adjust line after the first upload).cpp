// D3 - Set and read the DS3231 clock. Upload once to set the time, then delete the adjust line.
#include <Arduino.h>                                                  // core Arduino functions and Serial
#include <Wire.h>                                                     // I2C bus driver
#include <RTClib.h>                                                   // DS3231 library

RTC_DS3231 rtc;                                                       // the clock chip object

void setup() {                                                        // runs once at power-up
  Serial.begin(115200);                                               // start the USB serial link
  Wire.begin(9, 8);                                                   // start I2C: SDA = GPIO9, SCL = GPIO8
  if (!rtc.begin(&Wire)) {                                            // look for the clock on the I2C bus
    Serial.println("RTC not found");                                  // report that it did not answer
    while (1) delay(1000);                                            // stop here forever
  }                                                                   // end of "not found"
  rtc.adjust(DateTime(F(__DATE__), F(__TIME__)));                     // set the clock to the moment this sketch was compiled (delete this line after the first upload)
}                                                                     // end of setup

void loop() {                                                         // runs again and again
  DateTime now = rtc.now();                                           // read the clock
  Serial.printf("%04d-%02d-%02d %02d:%02d:%02d\n", now.year(), now.month(), now.day(), now.hour(), now.minute(), now.second()); // print the date and time
  delay(1000);                                                        // once per second
}                                                                     // end of loop
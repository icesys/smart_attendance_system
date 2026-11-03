// D3 - Set and read the DS3231 clock. Upload once to set the time, then delete the adjust line.
#include <Arduino.h>
#include <Wire.h>
#include <RTClib.h>

RTC_DS3231 rtc;

void setup() {
  Serial.begin(115200);
  Wire.begin(9, 8);
  if (!rtc.begin(&Wire)) {
    Serial.println("RTC not found");
    while (1) delay(1000);
  }
  rtc.adjust(DateTime(F(__DATE__), F(__TIME__)));   // delete this line after the first upload
}

void loop() {
  DateTime now = rtc.now();
  Serial.printf("%04d-%02d-%02d %02d:%02d:%02d\n", now.year(), now.month(), now.day(), now.hour(), now.minute(), now.second());
  delay(1000);
}

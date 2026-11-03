// D9 - DS3231 diagnosis: shows WHY the clock stops when the main power is removed, and can fix the setting that causes it.
// Reads the two DS3231 registers that matter:
//   0x0E control: bit 7 = EOSC. 1 means "stop the oscillator when running on the coin cell" -> time is lost at every unplug.
//   0x0F status : bit 7 = OSF.  1 means "the oscillator stopped at some point" -> the main firmware says "RTC lost power".
// Serial commands (115200 baud, type then Enter):
//   E                          clear EOSC so the clock keeps running on the coin cell
//   S YYYY-MM-DD HH:MM:SS      set the time (this also clears OSF)
//   R                          read and explain the registers again
// The report is also printed by itself every 10 seconds, so nothing has to be typed to read it.
#include <Arduino.h>
#include <Wire.h>
#include <RTClib.h>

constexpr uint8_t DS3231_ADDR = 0x68;
constexpr uint8_t REG_CONTROL = 0x0E;
constexpr uint8_t REG_STATUS  = 0x0F;

RTC_DS3231 rtc;
char line[40];
uint8_t len = 0;

uint8_t readReg(uint8_t reg) {
  Wire.beginTransmission(DS3231_ADDR);
  Wire.write(reg);
  Wire.endTransmission();
  Wire.requestFrom(DS3231_ADDR, (uint8_t)1);
  return Wire.available() ? Wire.read() : 0xFF;
}

void writeReg(uint8_t reg, uint8_t value) {
  Wire.beginTransmission(DS3231_ADDR);
  Wire.write(reg);
  Wire.write(value);
  Wire.endTransmission();
}

void explain() {
  uint8_t ctrl = readReg(REG_CONTROL);
  uint8_t stat = readReg(REG_STATUS);
  Serial.printf("\nControl 0x0E = 0x%02X   Status 0x0F = 0x%02X\n", ctrl, stat);
  if (ctrl & 0x80) Serial.println("EOSC = 1  -> PROBLEM: the clock STOPS on the coin cell. Type E to fix it.");
  else             Serial.println("EOSC = 0  -> good: the clock runs on the coin cell.");
  if (stat & 0x80) Serial.println("OSF  = 1  -> the clock stopped at some point. Set the time with S YYYY-MM-DD HH:MM:SS.");
  else             Serial.println("OSF  = 0  -> the clock has not stopped since the time was set.");
  Serial.println("Test: set the time, unplug ALL power for 1 minute, plug back in and look at OSF and the time.\n");
}

void handle(char* cmd) {
  if ((cmd[0] == 'E' || cmd[0] == 'e') && cmd[1] == 0) {
    writeReg(REG_CONTROL, readReg(REG_CONTROL) & 0x7F);
    Serial.println("EOSC cleared.");
    explain();
  } else if (cmd[0] == 'S' || cmd[0] == 's') {
    int y, mo, d, h, mi, s;
    if (sscanf(cmd + 1, "%d-%d-%d %d:%d:%d", &y, &mo, &d, &h, &mi, &s) == 6) {
      rtc.adjust(DateTime(y, mo, d, h, mi, s));
      Serial.println("Time set.");
      explain();
    } else {
      Serial.println("Usage: S 2026-11-03 19:45:00");
    }
  } else if (cmd[0] == 'R' || cmd[0] == 'r') {
    explain();
  }
}

void setup() {
  Serial.begin(115200);
  delay(1500);
  Wire.begin(9, 8);
  if (!rtc.begin(&Wire)) {
    Serial.println("RTC not found: check SDA = GPIO9, SCL = GPIO8, 3V3 and GND.");
    while (1) delay(1000);
  }
  explain();
}

void loop() {
  static uint32_t last = 0;
  static uint32_t lastReport = 0;
  if (millis() - lastReport >= 10000) {
    lastReport = millis();
    explain();
  }
  if (millis() - last >= 1000) {
    last = millis();
    DateTime now = rtc.now();
    Serial.printf("%04d-%02d-%02d %02d:%02d:%02d\n", now.year(), now.month(), now.day(), now.hour(), now.minute(), now.second());
  }
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\r' || c == '\n') {
      if (len) { line[len] = 0; handle(line); len = 0; }
      continue;
    }
    else if (len < sizeof(line) - 1) line[len++] = c;
  }
}

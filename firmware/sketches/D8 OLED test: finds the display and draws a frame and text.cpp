// D9 - OLED test: finds the OLED on the I2C bus (0x3C or 0x3D), then draws a frame and some text.
#include <Arduino.h>                                                  // core Arduino functions and Serial
#include <Wire.h>                                                     // I2C bus driver
#include <Adafruit_GFX.h>                                             // graphics library used by the OLED driver
#include <Adafruit_SSD1306.h>                                         // driver of the SSD1306 OLED

Adafruit_SSD1306 oled(128, 64, &Wire, -1);                            // 128x64 OLED on the I2C bus, no reset pin (use 32 instead of 64 for a 128x32 OLED)

bool present(uint8_t addr) {                                          // true if a device answers at this address
  Wire.beginTransmission(addr);                                       // start talking to the address
  return Wire.endTransmission() == 0;                                 // 0 = a device acknowledged
}                                                                     // end of present

void setup() {                                                        // runs once at power-up
  Serial.begin(115200);                                               // serial link to the PC
  Wire.begin(9, 8);                                                   // start I2C: SDA = GPIO9, SCL = GPIO8
  delay(1500);                                                        // give the serial monitor time to open
  uint8_t addr = present(0x3C) ? 0x3C : (present(0x3D) ? 0x3D : 0);   // look for the OLED at its two possible addresses
  if (!addr) {                                                        // nothing answered
    Serial.println("No OLED at 0x3C or 0x3D. Check VCC (3V3), GND, SDA (GPIO9), SCL (GPIO8)."); // explain
    return;                                                           // nothing more to do
  }                                                                   // end of "not found"
  Serial.printf("OLED found at 0x%02X\n", addr);                      // report the address
  if (!oled.begin(SSD1306_SWITCHCAPVCC, addr, true, false)) {         // start the driver (false = I2C already started)
    Serial.println("OLED init failed");                               // report
    return;                                                           // nothing more to do
  }                                                                   // end of "init failed"
  oled.clearDisplay();                                                // erase the screen buffer
  oled.drawRect(0, 0, 128, 64, SSD1306_WHITE);                        // draw a frame around the whole screen: shows the real size
  oled.setTextSize(1);                                                // smallest text
  oled.setTextColor(SSD1306_WHITE);                                   // white on black
  oled.setCursor(8, 10);                                              // position of the first line
  oled.print("OLED works!");                                          // first line
  oled.setCursor(8, 28);                                              // position of the second line
  oled.printf("Address 0x%02X", addr);                                // second line: the I2C address
  oled.display();                                                     // send the buffer to the screen
}                                                                     // end of setup

void loop() {}                                                        // nothing to repeat
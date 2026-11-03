// D9 - OLED test: finds the OLED on the I2C bus (0x3C or 0x3D), then draws a frame and some text.
#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

Adafruit_SSD1306 oled(128, 64, &Wire, -1);

bool present(uint8_t addr) {
  Wire.beginTransmission(addr);
  return Wire.endTransmission() == 0;
}

void setup() {
  Serial.begin(115200);
  Wire.begin(9, 8);
  delay(1500);
  uint8_t addr = present(0x3C) ? 0x3C : (present(0x3D) ? 0x3D : 0);
  if (!addr) {
    Serial.println("No OLED at 0x3C or 0x3D. Check VCC (3V3), GND, SDA (GPIO9), SCL (GPIO8).");
    return;
  }
  Serial.printf("OLED found at 0x%02X\n", addr);
  if (!oled.begin(SSD1306_SWITCHCAPVCC, addr, true, false)) {
    Serial.println("OLED init failed");
    return;
  }
  oled.clearDisplay();
  oled.drawRect(0, 0, 128, 64, SSD1306_WHITE);
  oled.setTextSize(1);
  oled.setTextColor(SSD1306_WHITE);
  oled.setCursor(8, 10);
  oled.print("OLED works!");
  oled.setCursor(8, 28);
  oled.printf("Address 0x%02X", addr);
  oled.display();
}

void loop() {}

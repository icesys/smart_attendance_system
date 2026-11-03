// D6 - LEDs, buzzer and buttons test (green = GPIO1, red = GPIO2, buzzer = GPIO42, button 1 = GPIO40, button 2 = GPIO41).
#include <Arduino.h>

const int GREEN = 1, RED = 2, BUZ = 42, pin_1 = 40, pin_2 = 41;

void beep(int ms) {
  digitalWrite(BUZ, HIGH);
  delay(ms);
  digitalWrite(BUZ, LOW);
}

void setup() {
  pinMode(GREEN, OUTPUT);
  pinMode(RED, OUTPUT);
  pinMode(BUZ, OUTPUT);
  pinMode(pin_1, INPUT_PULLUP);
  pinMode(pin_2, INPUT_PULLUP);
}

void loop() {
  if (digitalRead(pin_1) == LOW) {
    digitalWrite(GREEN, HIGH);
    beep(150);
    delay(200);
    return;
  }
  if (digitalRead(pin_2) == LOW) {
    digitalWrite(RED, HIGH);
    beep(100);
    delay(100);
    beep(100);
    delay(200);
    return;
  }
  digitalWrite(GREEN, HIGH);
  delay(300);
  digitalWrite(GREEN, LOW);
  digitalWrite(RED, HIGH);
  delay(300);
  digitalWrite(RED, LOW);
}

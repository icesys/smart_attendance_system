// D6 - LEDs, buzzer and buttons test (green = GPIO1, red = GPIO2, buzzer = GPIO42, button 1 = GPIO40, button 2 = GPIO41).
#include <Arduino.h>                                                  // core Arduino functions

const int GREEN = 1, RED = 2, BUZ = 42, pin_1 = 40, pin_2 = 41;             // pin numbers of the parts

void beep(int ms) {                                                   // sounds the buzzer for ms milliseconds
  digitalWrite(BUZ, HIGH);                                            // transistor on, buzzer sounds
  delay(ms);                                                          // wait
  digitalWrite(BUZ, LOW);                                             // transistor off, buzzer silent
}                                                                     // end of beep

void setup() {                                                        // runs once at power-up
  pinMode(GREEN, OUTPUT);                                             // green LED pin is an output
  pinMode(RED, OUTPUT);                                               // red LED pin is an output
  pinMode(BUZ, OUTPUT);                                               // buzzer pin is an output
  pinMode(pin_1, INPUT_PULLUP);                                          // button 1 pin is an input with pull-up
  pinMode(pin_2, INPUT_PULLUP);                                          // button 2 pin is an input with pull-up
}                                                                     // end of setup

void loop() {                                                         // runs again and again
  if (digitalRead(pin_1) == LOW) {                                       // button 1 pressed (pulled to GND)
    digitalWrite(GREEN, HIGH);                                        // green LED stays on
    beep(150);                                                        // one beep
    delay(200);                                                       // small pause
    return;                                                           // start the loop again
  }                                                                   // end of button 1
  if (digitalRead(pin_2) == LOW) {                                       // button 2 pressed
    digitalWrite(RED, HIGH);                                          // red LED stays on
    beep(100);                                                        // first beep
    delay(100);                                                       // pause
    beep(100);                                                        // second beep
    delay(200);                                                       // small pause
    return;                                                           // start the loop again
  }                                                                   // end of button 2
  digitalWrite(GREEN, HIGH);                                          // no button: green LED on
  delay(300);                                                         // for 0.3 s
  digitalWrite(GREEN, LOW);                                           // green LED off
  digitalWrite(RED, HIGH);                                            // red LED on
  delay(300);                                                         // for 0.3 s
  digitalWrite(RED, LOW);                                             // red LED off
}                                                                     // end of loop
/**********************************************************************************/
/*                                                         / - ice.               */
/*   SMART ATTENDANCE SYSTEM                              /                       */
/*   ----------------------------               :+:   .:#/ #:.   .:#/#:.          */
/*   Code By : ice.                                  +:         #:   ##           */
/*   GitHub : https://github.com/icesys       #+#   +:         #+::##"            */
/*   Created : 20-10-2026                    #+#   #+         #+                  */
/*   Updated : 20-10-2026                   #+#   ##    ##   ##    ##             */
/*                                         ###    #+./ #+    #+. /#+    #         */
/*                                                  /                             */
/*                                                 /                              */
/**********************************************************************************/

#include <Arduino.h>
#include <Wire.h>
void setup() { Serial.begin(115200); Wire.begin(8, 9); delay(1500); }
void loop() {
for (byte a = 1; a < 127; a++) {
Wire.beginTransmission(a);
if (Wire.endTransmission() == 0) Serial.printf("Found 0x%02X\n", a);
}
Serial.println("---");
delay(3000);
}
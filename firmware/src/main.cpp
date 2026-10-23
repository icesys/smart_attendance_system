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

void setup() {
    Serial.begin(115200);
    delay(2000);

    Serial.println();
    Serial.println("ESP32-S3 board test");
    Serial.printf("Chip: %s\n", ESP.getChipModel());
    Serial.printf("Flash: %u MB\n",
                  ESP.getFlashChipSize() / (1024 * 1024));
    Serial.printf("PSRAM detected: %s\n",
                  psramFound() ? "YES" : "NO");
    Serial.printf("PSRAM size: %u bytes\n",
                  ESP.getPsramSize());
}

void loop() {
    Serial.println("Board is running!");
    delay(2000);
}
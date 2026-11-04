# datasheets

| File | Part | Used as | Source |
|---|---|---|---|
| `ESP32-S3_datasheet.pdf` | ESP32-S3 chip | Microcontroller | Espressif |
| `ESP32-S3-WROOM-1_module.pdf` | ESP32-S3-WROOM-1 (N16R8 module on the dev board) | Microcontroller module | Espressif |
| `DS3231_RTC.pdf` | DS3231 | Real-time clock (J206) | Maxim / Analog Devices |
| `SSD1306_OLED_controller.pdf` | SSD1306 | OLED display controller (J2) | Solomon Systech |
| `TP4056_charger.pdf` | TP4056 | Li-ion charger (J203) | NanJing Top Power |
| `MT3608_boost.pdf` | MT3608 | 5 V boost converter (J204) | Aerosemi |
| `1N5819_schottky.pdf` | 1N5817 / 1N5818 / 1N5819 | Schottky diode D101 | Vishay |
| `1N4148_diode.pdf` | 1N4148 | Buzzer flyback diode D4 | Vishay |
| `2N2222A_transistor.pdf` | 2N2222A | Buzzer driver Q1 (the board uses the TO-92 version; ratings are the same) | Microsemi |

## Not downloaded (no official PDF online)
| Part | Where to find it |
|---|---|
| RDM6300 / RDM630 125 kHz reader | Specification copy: <https://mikrocontroller.net/attachment/147252/RDM630-Spec.pdf>. 5 V, < 50 mA, 9600 baud, frame `0x02` + 10 ASCII hex (UID) + 2 ASCII hex (XOR checksum) + `0x03` |
| EM4100 card protocol | <https://www.priority1design.com.au/em4100_protocol.html> |
| DW01A + FS8205A (protection on the TP4056 module) | Search "DW01A datasheet" / "FS8205A datasheet" (Fortune Semiconductor) |
| microSD SPI module, 18650 cell | Generic parts, no datasheet; see `documentation/bill_of_materials.md` |

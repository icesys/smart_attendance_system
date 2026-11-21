# Bill of Materials

The per-reference list used for the PCBs is [`hardware/schematics/kicad/sas_pcb/documentation/BOM.csv`](../hardware/schematics/kicad/sas_pcb/documentation/BOM.csv). This page groups it by function and adds the parts that are not on the boards. Datasheets are in [`hardware/datasheets/`](../hardware/datasheets/).

## 1. Modules

| Item | Qty | Reference | Board | Notes |
|---|---|---|---|---|
| ESP32-S3 N16R8 dev board (2 × 22 pins, 25.4 mm between rows) | 1 | J101, J102 (sockets) | MIDDLE | 16 MB flash, 8 MB PSRAM, native USB-C + UART USB-C. IN-OUT pads soldered so the 5V pin is powered from 5V_SYS |
| RDM6300 125 kHz reader + 35 × 46 mm coil | 1 | J103 (reader), J3 (coil) | MIDDLE / TOP | EM4100, UART 9600 baud, 5 V |
| DS3231 RTC module + CR2032 | 1 | J206 | BOTTOM | **Remove the charge resistor**: the CR2032 is not rechargeable |
| microSD module (SPI, 6 pins) + microSD card 8–16 GB, FAT32 | 1 | J205 | BOTTOM | Powered from 5V_SYS |
| 0.96" SSD1306 OLED, I2C, 128 × 64, 4 pins | 1 | J2 | TOP | Address 0x3C, 3.3 V |
| TP4056 charger, USB-C, with protection (DW01A + FS8205A) | 1 | J203 | BOTTOM | System ground is **OUT−**, not B− |
| MT3608 boost module | 1 | J204 | BOTTOM | **Set to 5.0 V with a multimeter before connecting anything** |
| 18650 Li-ion cell + 1-cell holder (20 × 75 mm) | 1 | J202 | under BOTTOM | Wired to J202 |

## 2. Discrete components

| Item | Qty | References | Board |
|---|---|---|---|
| Schottky diode 1 A, 1N5819 (DO-41) | 1 | D101 | MIDDLE |
| Signal diode 1N4148 (buzzer flyback) | 1 | D4 | TOP |
| NPN transistor 2N2222A (TO-92) | 1 | Q1 | TOP |
| LED 5 mm blue (power) | 1 | D1 | TOP |
| LED 5 mm green | 1 | D2 | TOP |
| LED 5 mm red | 1 | D3 | TOP |
| Resistor 220 Ω, ¼ W | 3 | R1, R2, R3 | TOP |
| Resistor 1 kΩ, ¼ W | 1 | R4 | TOP |
| Resistor 100 kΩ, ¼ W | 1 | R5 | TOP |
| Electrolytic capacitor 470 µF 10 V (10 mm, 5 mm pitch) | 1 | C201 | BOTTOM |
| Ceramic capacitor 10 µF (5 mm pitch) | 2 | C101, C2 | MIDDLE, TOP |
| Ceramic capacitor 100 nF (5 mm pitch) | 5 | C202, C102, C103, C1, C3 | all |
| Buzzer 12 mm (8 mm pin pitch) | 1 | BZ1 | TOP |
| Push button 6 × 6 mm | 2 | SW1 (session), SW2 (info) | TOP |
| Slide switch, 6 pins | 1 | SW201 | BOTTOM |
| Solder jumper, 3 pads (buzzer supply, 1-2 = 3V3) | 1 | JP1 | TOP |

## 3. Connectors and mechanics

| Item | Qty | References / notes |
|---|---|---|
| 1 × 22 female header, 2.54 mm | 2 | J101, J102 (ESP32-S3 sockets) |
| 2 × 8 IDC box header, 2.54 mm | 4 | J1, J105 (cable 1); J106, J201 (cable 2) |
| 16-wire ribbon cable with two 2 × 8 IDC sockets, about 10 cm | 2 | Same pin number at both ends |
| 1 × 2 pin header, 2.54 mm | 2 | J202 (battery), J3 (coil) |
| Female headers for the modules | as needed | OLED, microSD, DS3231, RDM6300, TP4056, MT3608 |
| M3 screws + standoffs | 12 | 4 holes per board, same positions on all three |
| PCB 95 × 60 mm, 2 layers | 3 | TOP, MIDDLE, BOTTOM (Gerbers in `hardware/gerbers/`) |

## 4. Prototype only (breadboard, already bought)

| Item | Qty | Notes |
|---|---|---|
| Breadboards | 2 | Prototype only |
| Solid-core wire 22 AWG | 7 m | 2 m black, 2 m red, 3 m green |
| Dupont jumper wires | 40 | 600 DA; too flexible, used only for short links |
| EM4100 test cards / tags | a few | To test without a real student card |

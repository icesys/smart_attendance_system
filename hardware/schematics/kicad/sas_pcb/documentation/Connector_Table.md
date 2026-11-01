# Connector table (both ribbon cables: same pin number at both ends, pin 1 marked on every header)

## Cable 1: TOP J1 <-> MIDDLE J105 (vertical, at x 87.95 mm, y 26.5 mm from the board corner on both boards)

| Pin | Signal | Pin | Signal |
|---|---|---|---|
| 1 | 3V3 | 2 | GND |
| 3 | 5V_SYS | 4 | GPIO42 |
| 5 | GPIO5 | 6 | GPIO1 |
| 7 | GPIO2 | 8 | GND |
| 9 | GPIO40 | 10 | GPIO41 |
| 11 | SCL | 12 | SDA |
| 13 | GND | 14 | COIL_A |
| 15 | COIL_B | 16 | GND |

## Cable 2: MIDDLE J106 <-> BOTTOM J201 (horizontal, at x 25.29 mm, y 44.75 mm on both boards)

| Pin | Signal | Pin | Signal |
|---|---|---|---|
| 1 | 5V_BOOST | 2 | GND |
| 3 | 5V_BOOST | 4 | GND |
| 5 | 5V_SYS | 6 | 3V3 |
| 7 | GND | 8 | SDA |
| 9 | SCL | 10 | GND |
| 11 | SD_CS | 12 | SD_SCK |
| 13 | GND | 14 | SD_MOSI |
| 15 | SD_MISO | 16 | GND |

IDC numbering: odd pins are on one row, even pins on the other; pin 1 is the square pad / arrow.

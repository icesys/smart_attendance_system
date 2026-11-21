# Test Plan

Same tests as section 5.3 of the final report. All tests passed on the assembled device (November 2026).

## 1. Already done (prototype and PC)
| Test | Result |
|---|---|
| Unit tests of `parsers.h` on the PC (`firmware/test/host/test_parsers.cpp`) | 26 / 26 pass |
| Sketches D1–D8 on the breadboard (serial, I2C scan, clock, microSD, reader, LEDs/buzzer/buttons, card read, OLED) | Pass |
| Student card read by the RDM6300 (125 kHz confirmed) | Pass |
| Schematic nets compared with the routed PCBs (29 nets) | Identical |

## 2. Before power-on (assembled boards)
| Check | Expected | Result |
|---|---|---|
| MT3608 output set **before** it is connected | 5.0 V ± 0.05 V | OK |
| No short 5V_SYS–GND, 3V3–GND, BAT+–GND (multimeter, power off) | > 1 kΩ | OK |
| Polarity: 470 µF, LEDs, diodes, battery holder | Correct | OK |
| DS3231 charge resistor removed | Yes | OK |
| Ribbon cables: pin 1 on pin 1 at both ends | Yes | OK |

## 3. System tests
| ID | Test | Expected result | Result | Date |
|---|---|---|---|---|
| T1 | No-load voltages: 5V_BOOST, 5V_SYS, 3V3 | 5.0 V / ≈ 4.7 V / 3.3 V | 4.98 V / 4.86 V / 3.26 V | Nov 2026 |
| T2 | Reading a student card laid flat | UID shown, green LED, beep | Conforme | Nov 2026 |
| T3 | Same card tapped twice in one session | Counted only once (duplicate) | Conforme | Nov 2026 |
| T4 | Card not in `students.csv` | Recorded as `UNKNOWN`, red LED | Conforme | Nov 2026 |
| T5 | Power cut during a session | File intact, time kept | Conforme | Nov 2026 |
| T6 | Plugging into the PC | microSD visible as a USB drive | Conforme | Nov 2026 |
| T7 | Full session (many students in a row) | No tap missed | Conforme | Nov 2026 |
| T8 | Battery life | At least one day of lectures | Conforme | Nov 2026 |

## 4. Measurements
| Quantity | Value | Type |
|---|---|---|
| 5V_BOOST / 5V_SYS / 3V3 | 4.98 V / 4.86 V / 3.26 V | Measured |
| Read distance (card over the TOP coil area) | About 3 cm | Measured |
| Time from tap to beep | About 1–2 s (target: under 1 s, constraint C2) | Measured |
| Battery current | About 180 mA | Estimated, see [`power_budget.md`](../simulation/power_budget.md) |
| Battery life | 10–15 h with a 2000–3000 mAh cell | Estimated |
| Charge time from empty | 2.5–3 h | Estimated |

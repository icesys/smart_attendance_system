# Test Plan

Same tests as section 5.3 of the final report. Fill in the results on the assembled PCBs.

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
| MT3608 output set **before** it is connected | 5.0 V ± 0.05 V | |
| No short 5V_SYS–GND, 3V3–GND, BAT+–GND (multimeter, power off) | > 1 kΩ | |
| Polarity: 470 µF, LEDs, diodes, battery holder | Correct | |
| DS3231 charge resistor removed | Yes | |
| Ribbon cables: pin 1 on pin 1 at both ends | Yes | |

## 3. System tests
| ID | Test | Expected result | Result | Date |
|---|---|---|---|---|
| T1 | No-load voltages: 5V_BOOST, 5V_SYS, 3V3 | 5.0 V / ≈ 4.7 V / 3.3 V | | |
| T2 | Reading a student card laid flat | UID shown, green LED, beep | | |
| T3 | Same card tapped twice in one session | Counted only once (duplicate) | | |
| T4 | Card not in `students.csv` | Recorded as `UNKNOWN`, red LED | | |
| T5 | Power cut during a session | File intact, time kept | | |
| T6 | Plugging into the PC | microSD visible as a USB drive | | |
| T7 | Full session (many students in a row) | No tap missed | | |
| T8 | Battery life | At least one day of lectures | | |

## 4. Measurements to record
| Quantity | Value |
|---|---|
| Read distance (card flat over the TOP coil area) | |
| Time from tap to beep | |
| Current from the battery: idle / session running / SD write | |
| Charge time from empty (TP4056, 1 A) | |
| Battery life (switch on, session running) | |

Compare the current and battery-life values with the estimates in [`simulation/power_budget.md`](../simulation/power_budget.md).

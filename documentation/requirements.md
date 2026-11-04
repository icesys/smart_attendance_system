# Requirements

Same list as section 2.2 of the final report. Each "Must" is checked by a test in [`test_plan.md`](test_plan.md).

## Functional
| ID | Requirement | Priority | Met by |
|---|---|---|---|
| F1 | Detect a student card placed on the reader and read its identifier (UID) | Must | RDM6300 (125 kHz, EM4100), frame checked by XOR checksum |
| F2 | Record each tap with the date and time | Must | DS3231 clock with CR2032 backup |
| F3 | Ignore repeated taps of the same card during a session | Must | Seen-list per session + 1.5 s same-card filter |
| F4 | Keep the data after a power cut | Must | One CSV line appended per tap; the file is closed after every write |
| F5 | Let the lecturer retrieve the files on a PC after the lecture | Must | USB drive mode on the native USB-C port, plus serial commands |
| F6 | Show the result of each tap (LEDs, buzzer, display) | Should | 3 LEDs, buzzer, 0.96" OLED |
| F7 | Match the card identifier to the student's name and registration number | Should | `/students.csv` on the microSD; final list sorted by surname |

## Constraints
| ID | Constraint |
|---|---|
| C1 | Battery operation on one 18650 Li-ion cell, charged over USB-C (no cable during the lecture) |
| C2 | Card laid flat, no aiming; read in less than one second |
| C3 | PCBs designed in KiCad; ESP32-S3 dev board mounted on sockets (removable) |
| C4 | Complete project (hardware, software, documentation) finished by February 2027 |

## Answers to the early open questions
| Question | Answer | See |
|---|---|---|
| Card frequency? | 125 kHz (EM4100) | `decisions_log.md`, 2026-10-21 |
| Storage medium? | microSD card, FAT32, CSV files | `decisions_log.md` |
| How does the PC get the data? | microSD shown as a USB drive (TinyUSB MSC) on the native port | `decisions_log.md` |
| How are students identified? | UID looked up in `/students.csv` (UID, surname, names, registration number) | `firmware/data/students.csv` |
| Battery life target? | At least one day of lectures per charge (test T8) | `simulation/power_budget.md` |

# Requirements

## Functional
| ID | Requirement | Priority |
|---|---|---|
| F1 | Detect a student card placed on the reader and read its identifier | Must |
| F2 | Record each tap with a timestamp | Must |
| F3 | Ignore repeated taps of the same card within one session (no duplicates) | Must |
| F4 | Store attendance data in a file that survives power-off | Must |
| F5 | Let the lecturer retrieve the attendance files from a PC after the lecture | Must |
| F6 | Give feedback on each tap (for example LED and/or buzzer) | Should |
| F7 | Match card identifiers to student names/details | Could |

## Non-functional
| ID | Requirement |
|---|---|
| N1 | Fully wireless in use: runs on batteries (2 × 18650 in parallel) |
| N2 | Card is placed flat on the reader, no pointing or aiming |
| N3 | Final board is a custom PCB designed in KiCad, with the ESP32-S3 dev board mounted on it |
| N4 | Complete project finished by February 2027 |

## Open questions
- Card frequency: 125 kHz or 13.56 MHz? (see `decisions_log.md`)
- Storage medium (internal flash, SD card, other).
- How the PC accesses the data (USB, Wi-Fi, removable card).
- How students are identified (identifier only, or mapped to a student list).
- Battery life target per session and per charge.

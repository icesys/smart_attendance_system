# Decisions Log

| Date | Decision | Reason / context |
|---|---|---|
| 2026-10 | Device fully wireless in use; data collected on a PC afterwards | Lecturer holds it at the door, no cables |
| 2026-10 | Design and build the PCB in KiCad | Chosen over Altium |
| 2026-10-21 | Buy only the 125 kHz reader for now, no 13.56 MHz module | Card frequency unconfirmed (an iPhone with NFC Tools detected nothing; an Android phone read a passport but not the card). Reassess if the reader does not work |
| 2026-10-22 | Final PCB carries the ESP32-S3 dev board on a footprint | Chip-level ESP32 design judged too complicated |
| 2026-10-22 | Other parts may go on the PCB as chips if simple | Keep the design manageable |
| 2026-10-22 | Use 2 × 18650 in parallel instead of 1 | More capacity |
| 2026-10-22 | Buy 22 AWG solid-core wire for the breadboard (2 m black, 2 m red, 3 m green) | The 40 Dupont jumpers (600 DA) are too flexible |
| 2026-10-22 | Organize the project as a professional repository | Same structure as the traffic light control system project |

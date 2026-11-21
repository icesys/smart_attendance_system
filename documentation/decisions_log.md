# Decisions Log

| Date | Decision | Reason / context |
|---|---|---|
| 2026-10 | Device fully wireless in use; data collected on a PC afterwards | Lecturer holds it at the door, no cables |
| 2026-10 | Design and build the PCBs in KiCad | Chosen over Altium (free, runs on every PC used) |
| 2026-10-21 | Buy only the 125 kHz reader (RDM6300), no 13.56 MHz module | An iPhone (NFC Tools) and an Android phone did not detect the card, although the Android phone read a 13.56 MHz passport. Confirmed later: the RDM6300 reads the card |
| 2026-10-22 | ESP32-S3 dev board on sockets, not the bare chip | Chip-level design (antenna, flash, boot circuit) judged too risky; the board stays removable |
| 2026-10-22 | Ready-made modules (RTC, microSD, OLED, charger, boost) instead of bare chips | Available locally, already tested, easy to replace |
| 2026-10-22 | 22 AWG solid-core wire for the breadboard (2 m black, 2 m red, 3 m green) | The 40 Dupont jumpers (600 DA) are too flexible |
| 2026-10-22 | Organise the project as a professional repository | Same structure as the traffic light control system project |
| 2026-10 | ESP32-S3 **N16R8** variant | 16 MB flash and 8 MB PSRAM; native USB needed for drive mode |
| 2026-10 | Storage on a **microSD card** (FAT32, CSV) | Survives power cuts, opens in Excel, large capacity |
| 2026-10 | **DS3231** real-time clock with CR2032 | Accurate (± 2 ppm) time stamps without Wi-Fi |
| 2026-10 | Retrieve data as a **USB drive** (TinyUSB MSC on the native port) | No software to install on the lecturer's PC |
| 2026-10 | Breadboard prototype powered by USB / power bank; battery chain postponed | The battery chain needs soldering |
| 2026-10 | Add a 0.96" SSD1306 OLED, 3 LEDs and a transistor-driven buzzer | Clear feedback for every tap (present, unknown, duplicate, error) |
| 2026-10 | `students.csv` with UID, surname, names, registration number; final list sorted by surname | Lists usable directly by the lecturer; unknown cards are added as `UNKNOWN` lines to fill in |
| 2026-11 | **One 18650 cell** on the PCB instead of 2 in parallel | Keeps the stack hand-sized; one cell covers a day of lectures (see `simulation/power_budget.md`) |
| 2026-11 | Power path: 18650 → protected TP4056 → switch → MT3608 (5.0 V) → Schottky 1N5819 → 5V_SYS | The diode lets USB and battery share the 5 V rail without back-feeding |
| 2026-11 | System ground is TP4056 **OUT−**, not B− | B− sits behind the protection transistors |
| 2026-11 | Remove the charge resistor of the DS3231 module | The CR2032 is not rechargeable |
| 2026-11 | Clear the DS3231 EOSC bit with sketch D9; set the time with `firmware/tools/set_clock.py` | With EOSC set the clock stops on the coin cell and the time is lost at every unplug |
| 2026-11 | Three stacked 95 × 60 mm two-layer boards (TOP, MIDDLE, BOTTOM) joined by two 16-wire ribbon cables | A single board would be too wide to hold in one hand |
| 2026-11 | No copper in the RFID coil area of the TOP board (x 8–54, y 22–57 mm) | Copper would weaken the 125 kHz field |
| 2026-11 | Module footprints drawn from caliper measurements and checked on a 1:1 printout | No library footprints exist for these modules |
| 2026-11 | Buzzer supply selectable with solder jumper JP1 (default 3V3) | 5 V option if the buzzer is too quiet |
| 2026-11 | Deliver the device as an open three-board stack, without an enclosure | The stack is complete and working; a 3D-printed case stays a future improvement |

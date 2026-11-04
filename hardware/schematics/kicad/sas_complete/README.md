# sas_complete: the whole system as one circuit

Open `sas_complete.kicad_pro` in KiCad. One A3 sheet with the full Smart Attendance System drawn as if it were a single board:
- no TOP / MIDDLE / BOTTOM sections;
- no board-to-board connectors (J1, J105, J106, J201) and no ribbon cables;
- no mounting holes.

Every connection is a wire. The ESP32-S3 dev board and the modules are drawn as blocks with named pins, and their pins also carry the net name. `sas_complete_preview.png` is a quick preview image.

Layout: power supply along the top, ESP32-S3 in the centre, RFID / microSD / clock / OLED on the right, LEDs, buttons and buzzer on the left.

This schematic documents the circuit (figure 1 of the report). The boards that are manufactured are the three-board design in `../sas_pcb`. It has **29 nets**, identical to the pad nets of the three routed PCBs once the four cable connectors are removed.

## References compared with the three-board design
| Here | Three boards | | Here | Three boards |
|---|---|---|---|---|
| U1 (pins 1-22 / 23-44) | J101 / J102 (ESP32-S3 sockets) | | C1, C2 | C201, C202 |
| U2 RDM6300 | J103 | | C3, C4, C5 | C101, C102, C103 |
| U3 DS3231 | J206 | | C6, C7, C8 | C1, C2, C3 |
| U4 microSD | J205 | | D5 (Schottky) | D101 |
| U5 OLED | J2 | | SW1 (slide switch) | SW201 |
| U6 TP4056 | J203 | | SW2, SW3 (buttons) | SW1, SW2 |
| U7 MT3608 | J204 | | BT1 (18650) | J202 |
| L1 (antenna coil) | J3 | | D1-D4, R1-R5, Q1, BZ1, JP1 | unchanged |

## Libraries
- `sas_complete_symbols.kicad_sym`: the project symbols, including the module blocks.
- Footprints come from `../sas_schematics/smart_attendance.pretty` (keep the folders side by side).

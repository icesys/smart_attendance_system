# sas_complete: the whole system as ONE circuit

Open `sas_complete.kicad_pro` in KiCad. It's one A3 sheet with the full Smart Attendance System drawn as if it were a single PCB:
- no TOP / MIDDLE / BOTTOM sections;
- no board-to-board connectors (J1, J105, J106, J201) and no ribbon cables;
- no mounting holes.

Every connection is a wire. The ESP32-S3 dev board and the modules are drawn as blocks with named pins, and their pins also carry the net name. `sas_complete_preview.png` is a quick preview drawn by script, not a KiCad export.

Layout: power supply along the top, ESP32-S3 in the centre, RFID / microSD / clock / OLED on the right (pins facing the ESP32), LEDs, buttons and buzzer on the left.

## Checked (`tools/check_complete_schematic.py`)
The saved file is read back and its connectivity rebuilt: **29 nets, all as expected**. Once the four cable connectors are removed, these nets are **identical to the pad nets of the three routed PCBs**. Not run: KiCad's own ERC (please run Inspect > Electrical Rules Checker once).

## References (renumbered for one design) against the three-board design
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

## Files
- `sas_complete_symbols.kicad_sym`: the project symbols, including the module blocks.
- Footprints come from `../sas_schematics/smart_attendance.pretty`.
- Every part keeps its footprint from the three-board design, except U1 (the ESP32-S3 dev board is two 1 × 22 sockets there). This schematic documents the circuit; the real PCBs are the three-board design in `../sas_pcb`.
- Regenerate with `python3 tools/gen_complete_schematic.py`, then run `python3 tools/check_complete_schematic.py`.

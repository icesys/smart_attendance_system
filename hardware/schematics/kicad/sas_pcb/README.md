# sas_pcb: the three routed boards

Open the `.kicad_pro` of the board you want (KiCad 10):

| Project | Board | Parts | Track segments / vias |
|---|---|---|---|
| `pcb_top/pcb_top.kicad_pro` | TOP 95 × 60 mm: OLED, LEDs, buttons, buzzer, RFID coil area | 20 + 4 M3 holes | 245 / 21 |
| `pcb_middle/pcb_middle.kicad_pro` | MIDDLE 95 × 60 mm: ESP32-S3 sockets, RDM6300, Schottky diode | 9 + 4 M3 holes | 343 / 45 |
| `pcb_bottom/pcb_bottom.kicad_pro` | BOTTOM 95 × 60 mm: TP4056, switch, MT3608, microSD, DS3231 | 9 + 4 M3 holes | 180 / 23 |

| Folder / file | Content |
|---|---|
| `smart_attendance.pretty/` | All footprints used: 8 module footprints drawn from caliper measurements + copies of the standard ones |
| `sas_symbols.kicad_sym` | All symbols used |
| `documentation/BOM.csv` | Bill of materials per reference |
| `documentation/Connector_Table.md` | Pinout of both ribbon cables |
| `documentation/Power_Distribution.md` | Power path, rails, track widths |
| `printouts_1to1/` | 1:1 PDFs to check the module footprints with the real modules |

Gerber and drill files: `../../../gerbers/`.

## Layout
- M3 holes (3.2 mm) at (4,4), (91,4), (4,56), (91,56) mm on all boards.
- Cable 1 (TOP J1 = MIDDLE J105) at (87.95, 26.5); cable 2 (MIDDLE J106 = BOTTOM J201) at (25.29, 44.75), same orientation on both boards of a pair.
- TOP: RFID coil area x 8–54, y 22–57 mm is a keep-out (no tracks, vias or copper).
- MIDDLE: the ESP32-S3 USB-C ports face the left edge.
- BOTTOM: TP4056 USB-C against the top edge; battery holder under the board, wired to J202.

## Design rules
2 copper layers, 1.6 mm. Clearance 0.3 mm. Tracks: signals 0.3 mm, GND 0.4, 3V3 0.5, 5V_SYS 0.6, 5V_BOOST 0.8, BAT+, BAT−, CHG_OUT+, SW_OUT 1.0 mm. Vias 0.8 mm pad / 0.4 mm drill. Copper at least 0.55 mm from the board edge. Every net, GND included, is connected by tracks; GND also has a copper pour on both layers with solid pad connections.

## Checks
- Every pad on the net of the schematic (0 mismatches); 29 nets, identical to the schematics.
- DRC in KiCad 10: 0 unconnected items on all three boards.
- Footprints checked by laying the real modules on the 1:1 printouts.

Before re-plotting the Gerbers after any change: press **B** (Edit > Fill All Zones), run **Inspect > Design Rules Checker**, then **File > Fabrication Outputs**.

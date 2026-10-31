# sas_pcb: the three boards, placed, NOT routed (v0.1)

Three small KiCad projects, one per board. Open the `.kicad_pro` of the board you want:

| Project | Board | Footprints |
|---|---|---|
| `pcb_top/pcb_top.kicad_pro` | TOP 95 x 60 mm | 20 parts + 4 M3 holes |
| `pcb_middle/pcb_middle.kicad_pro` | MIDDLE 95 x 60 mm | 9 parts + 4 M3 holes |
| `pcb_bottom/pcb_bottom.kicad_pro` | BOTTOM 95 x 60 mm | 9 parts + 4 M3 holes |

Each project has its own single-sheet schematic, generated from the same script as `sas_schematics` (same references, same nets), and a `.kicad_pcb` with the outline, the footprints placed and every pad already on its net. **There are no tracks**: the thin lines you see are the connections to draw (the ratsnest). Libraries are shared from this folder (`smart_attendance.pretty`, `sas_symbols.kicad_sym`).

## Fixed by design
- Board 95 x 60 mm, origin at the top-left corner; M3 holes (3.2 mm) at (4,4), (91,4), (4,56), (91,56) on all three boards.
- **Cable 1** (TOP J1 = MIDDLE J105): both at (87.95, 26.5), vertical, same orientation.
- **Cable 2** (MIDDLE J106 = BOTTOM J201): both at (25.29, 44.75), horizontal, same orientation.
- TOP: RFID coil area 46 x 35 mm (x 8-54, y 22-57) is a copper/track/via keep-out zone on both layers. Coil terminals J3 sit at its edge. OLED and buttons on the right, buzzer block with the other small parts.
- MIDDLE: ESP32-S3 on two 1x22 sockets 25.4 mm apart, **USB-C ports on the left edge** (area in front of them kept free). Silkscreen rectangle shows the ESP32 board.
- BOTTOM: TP4056 with its **USB-C end against the top edge**; battery wires come up to J202 (the 18650 holder sits under the board); slide switch near an edge.

## How the placement was made and checked
Fixed parts by hand, the rest by a search that avoids overlaps, edges and mounting holes and keeps connected parts close. A script checked: no footprint overlaps another, none touches the board edge or a mounting-hole circle (3.5 mm), every pad net equals the schematic netlist, no tracks exist. **KiCad's own DRC was not run** (KiCad 7's command line has none): run Inspect > Design Rules Checker after you open each board.

## Before ordering anything
Print `printouts_1to1/pcb_*_1to1.pdf` at 100 % (checked: the plot is true 1:1, 95 mm wide). Lay the real modules on the paper, **upside-down for the header-mounted ones (OLED, SD, DS3231, RDM6300)**, and check that every pin lands on the pad with the same name, that the TP4056 USB-C and the ESP32 ports are reachable, and that nothing collides.

## If you change a schematic
Edit the board's own schematic in its project, then press F8 in the PCB editor: placement is kept (footprints are linked to the schematic symbols). Keep `sas_schematics` in step, or regenerate both with `sas_schematics/tools/gen_schematics.py`.

`tools/` holds `pcblib.py` and `gen_pcb.py` (the board generator).

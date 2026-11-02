# sas_pcb: the three boards, placed AND routed (v0.3)

Open the `.kicad_pro` of the board you want:

| Project | Board | Parts | Tracks / vias |
|---|---|---|---|
| `pcb_top/pcb_top.kicad_pro` | TOP 95 x 60 mm | 20 + 4 M3 holes | 167 / 21 |
| `pcb_middle/pcb_middle.kicad_pro` | MIDDLE 95 x 60 mm | 9 + 4 M3 holes | 234 / 45 |
| `pcb_bottom/pcb_bottom.kicad_pro` | BOTTOM 95 x 60 mm | 9 + 4 M3 holes | 131 / 23 |

Libraries are shared from this folder: `smart_attendance.pretty` now holds ALL footprints used (8 custom module footprints + copies of the 13 standard ones), and `sas_symbols.kicad_sym` all symbols, so the boards open identically in any KiCad version and DRC shows no "does not match library" warnings. `documentation/` has the BOM, the connector table and the power-distribution note; `printouts_1to1/` has the 1:1 PDFs.

## Layout (unchanged since the test print, except the OLED header which is now 1.5 mm from the module edge)
- M3 holes (3.2 mm) at (4,4), (91,4), (4,56), (91,56) on all boards. Cable 1 (TOP J1 = MIDDLE J105) at (87.95, 26.5); cable 2 (MIDDLE J106 = BOTTOM J201) at (25.29, 44.75), same orientation on both boards of a pair.
- TOP: RFID coil area x 8-54, y 22-57 is a keep-out (no tracks, vias or copper). MIDDLE: ESP32-S3 USB-C ports face the left edge. BOTTOM: TP4056 USB-C against the top edge; battery holder under the board, wires to J202.

## Routing rules used
2 copper layers. Clearance 0.3 mm in the router (KiCad's default minimum is 0.2). Tracks: signals 0.3 mm, GND 0.4, 3V3 0.5, 5V_SYS 0.6, 5V_BOOST 0.8, BAT+, BAT-, CHG_OUT+, SW_OUT 1.0 mm. Vias 0.8 mm pad / 0.4 mm drill. Copper at least 0.55 mm from the board edge, 3.3 mm from the hole centres. **Every net, GND included, is connected by real copper tracks**; GND also has a copper pour on both layers.

## What was checked (my own scripts, in `tools/check_pcb.py`)
For all three boards: every footprint present, every pad on the net of the schematic netlist (0 mismatches), every net with 2 or more pads connected by copper (including GND, without relying on the pour), no copper closer than 0.2 mm to a different net, copper at least 0.5 mm from the board edge, hole-to-hole at least 0.25 mm, no track or via inside the coil keep-out, the GND pours (emulated) reach every GND pad as one system, and KiCad's command line opens and plots all three files.

## DRC round 1 (your KiCad 10 run) and what changed
Your DRC showed 0 unconnected items on all boards (every net, GND included, is connected). It showed 3 errors on MIDDLE (thermal-relief spokes of 3 GND pads touching a small pour island) and 27-40 warnings per board. Fixes: GND pour pads are now **solid connections** (no spokes, so that error cannot occur); all standard footprints are copied into the project library (library-mismatch warnings); pin-name texts are 0.8 mm and vertical (text-height warnings); module outlines moved to F.Fab, notes and keep-out labels to Dwgs.User, reference designators placed on the silkscreen only where there is free room (otherwise on F.Fab), mounting-hole references hidden (silkscreen-clipped and silkscreen-clearance warnings).

## What was NOT checked
**KiCad's own Design Rules Checker** (KiCad 7's command line has none). The pours are stored empty: KiCad fills them when you press **B** (Edit > Fill All Zones) or run DRC with "Refill all zones" ticked. A few cosmetic silkscreen warnings may remain.

## Next step
Open each board, press B, run Inspect > Design Rules Checker, and send me the lists. When it is clean I prepare the fabrication files (Gerbers and drill) with the zones filled.

## Regenerating
`sas_schematics/tools/gen_schematics.py`, `gen_footprints.py`, then `tools/gen_pcb.py` (placement), `route_pcb.py` (routing) and `check_pcb.py` (checks).

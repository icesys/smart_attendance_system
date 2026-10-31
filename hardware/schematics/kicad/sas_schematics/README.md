# sas_schematics: Smart Attendance System, electrical schematics (v0.7)

Open `sas_schematics.kicad_pro` in KiCad 7 or newer (tested here with 7.0.11; you use 10, which converts the files when you save).
The root sheet shows the three boards; double-click a box to open it.

| Sheet | File | References |
|---|---|---|
| TOP | `top.kicad_sch` | 1-99 |
| MIDDLE | `middle.kicad_sch` | 101-199 |
| BOTTOM | `bottom.kicad_sch` | 201-299 |

Each sheet also carries its 4 M3 mounting holes (H1-H4, H101-H104, H201-H204) so they exist in the PCB too.

The sheets are separate boards: nothing joins them inside KiCad. The two ribbon cables use the same pin numbers at both ends (TOP J1 = MIDDLE J105, MIDDLE J106 = BOTTOM J201); the pinouts are listed on the root sheet.

## Libraries in this folder (so it opens the same in any KiCad version)
- `sas_symbols.kicad_sym` (nickname SAS): copies of the standard symbols used. Declared in `sym-lib-table`.
- `smart_attendance.pretty`: the 8 custom module footprints, built from your drawings. Declared in `fp-lib-table`.

## Power path
18650 -> TP4056 (protected, USB-C) -> slide switch -> MT3608 (set to 5.0 V with a multimeter first) -> cable 2 pins 1 and 3 (5V_BOOST) -> MIDDLE Schottky diode -> 5V_SYS (ESP32 5V pin, RDM6300, SD module, buzzer option). 3V3 comes from the ESP32 board. BAT- is not ground (OUT- is). On battery the board sits at about 4.7 V; USB (about 5 V) takes over when plugged in.

## Footprint orientation rule
Header-mounted modules (OLED, SD, DS3231, RDM6300) plug in pin-down, so each footprint is the MIRROR of your hand drawing (which shows the face the pin tips point to). TP4056 and MT3608 are drawn component-side up as in your drawings. **Check with a 1:1 print before ordering**: put the real module upside-down on the printout; every pin must land on the pad with the same name.

## What was verified (KiCad 7.0.11 command line)
- Every net of the wired schematics matches the intended connections exactly (script comparison against the exported netlist); no duplicate references; every footprint name exists.
- Your ERC runs: MIDDLE and BOTTOM 0 errors, 0 warnings. TOP had 5 warnings caused by KiCad 10's library differing from KiCad 7's; they disappear now that the symbols come from `sas_symbols.kicad_sym`. Please run ERC once more.

## Remaining small assumptions (outline only, no electrical effect)
Distance from each header row to the module's top edge (OLED 2.5 mm, SD and DS3231 2.0 mm, RDM6300 1.0 mm), TP4056 pad row 2.0 mm from its bottom edge, buzzer + pin, slide-switch body orientation.

`tools/` holds the generators (`gen_schematics.py`, `gen_footprints.py`).

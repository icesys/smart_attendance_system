# sas_schematics: one sheet per board

Open `sas_schematics.kicad_pro` in KiCad. The root sheet shows the three boards; double-click a box to open it.

| Sheet | File | References |
|---|---|---|
| TOP | `top.kicad_sch` | 1-99 |
| MIDDLE | `middle.kicad_sch` | 101-199 |
| BOTTOM | `bottom.kicad_sch` | 201-299 |

Each sheet also carries its 4 M3 mounting holes (H1-H4, H101-H104, H201-H204).

The sheets are separate boards: nothing joins them inside KiCad. The two ribbon cables use the same pin numbers at both ends (TOP J1 = MIDDLE J105, MIDDLE J106 = BOTTOM J201); the pinouts are on the root sheet and in `../sas_pcb/documentation/Connector_Table.md`.

## Libraries (in this folder, so the project opens the same in any KiCad version)
- `sas_symbols.kicad_sym` (nickname SAS): copies of the standard symbols used.
- `smart_attendance.pretty`: the 8 module footprints drawn from caliper measurements, plus copies of every standard footprint used.

## Power path
18650 → TP4056 (protected, USB-C) → slide switch → MT3608 (set to 5.0 V with a multimeter first) → cable 2 pins 1 and 3 (5V_BOOST) → MIDDLE Schottky diode → 5V_SYS (ESP32 5V pin, RDM6300, microSD module, buzzer option). 3V3 comes from the ESP32 board. B− is not ground (OUT− is). On battery 5V_SYS is about 4.7 V; with USB plugged in (about 5 V), USB takes over.

## Footprint orientation
Header-mounted modules (OLED, microSD, DS3231, RDM6300) plug in pin-down, so each footprint is the **mirror** of the module seen from its component side. TP4056 and MT3608 are drawn component-side up. Check with the 1:1 printouts in `../sas_pcb/printouts_1to1/`: put the real module upside-down on the paper; every pin must land on the pad with the same name.

## Checks
- Every net matches the routed PCBs (29 nets).
- ERC: MIDDLE and BOTTOM 0 errors, 0 warnings. TOP had 5 warnings caused by KiCad library differences, fixed by using the local `sas_symbols.kicad_sym`; run ERC on TOP once more to confirm.

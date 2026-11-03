# sas_full_system: complete electrical schematic (v1.0)

Open `sas_full_system.kicad_pro` in KiCad (written in KiCad 7 format; KiCad 10 converts it when you save).

One flat **A1** sheet with the whole Smart Attendance System:

| Area of the sheet | Board | References |
|---|---|---|
| top left | MIDDLE: ESP32-S3 sockets, RDM6300, Schottky diode | 101-199 |
| top right | BOTTOM: 18650, TP4056, slide switch, MT3608, microSD, DS3231 | 201-299 |
| bottom left | TOP: LEDs, buzzer driver, buttons, OLED, RFID coil | 1-99 |
| bottom right | Notes: both cable pinouts, power path, GPIO map | |

Unlike `../sas_schematics` (one sheet per board, joined only by matching labels), here the boards are **wired to each other**:
- **Cable 1** (MIDDLE J105 <-> TOP J1) is drawn as 16 wires down the left margin.
- **Cable 2** (MIDDLE J106 <-> BOTTOM J201) is drawn as 16 wires between the two upper frames.

Pin k at one end goes to pin k at the other end. Every connection on the boards is also a wire, and connector pins carry their net name.

Parts, values, footprints and references are identical to `../sas_schematics` and the three PCBs in `../sas_pcb`. The libraries are shared from `../sas_schematics` (`sas_symbols.kicad_sym`, `smart_attendance.pretty`), so keep the folders side by side.

## What was checked (`tools/check_full_schematic.py`)
- The saved file is read back and its connectivity rebuilt from pins, wires, junctions and labels: **29 nets, exactly the expected ones**.
- These nets are **identical to the pad nets of the three routed PCBs** (merged by net name).
- No wire end sits in the middle of another wire, no unneeded junction, every unused pin has a no-connect flag.
- Not run: KiCad's own ERC (no KiCad on the machine that generated it). Please run **Inspect > Electrical Rules Checker** once.

## Regenerating
```
pip install kiutils
python3 tools/gen_full_schematic.py
python3 tools/check_full_schematic.py
```
The generator reuses the board definitions in `../sas_schematics/tools/gen_schematics.py`. Change a board there, then rerun both.

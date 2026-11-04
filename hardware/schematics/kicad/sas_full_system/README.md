# sas_full_system: the three boards and both cables on one sheet

Open `sas_full_system.kicad_pro` in KiCad. One flat **A1** sheet (appendix A of the report):

| Area of the sheet | Board | References |
|---|---|---|
| top left | MIDDLE: ESP32-S3 sockets, RDM6300, Schottky diode | 101-199 |
| top right | BOTTOM: 18650, TP4056, slide switch, MT3608, microSD, DS3231 | 201-299 |
| bottom left | TOP: LEDs, buzzer driver, buttons, OLED, RFID coil | 1-99 |
| bottom right | Notes: both cable pinouts, power path, GPIO map | |

Unlike `../sas_schematics` (one sheet per board, joined only by matching labels), here the boards are **wired to each other**:
- **Cable 1** (MIDDLE J105 ↔ TOP J1) is drawn as 16 wires down the left margin.
- **Cable 2** (MIDDLE J106 ↔ BOTTOM J201) is drawn as 16 wires between the two upper frames.

Pin k at one end goes to pin k at the other end. The sheet has **29 nets**, identical to the pad nets of the three routed PCBs.

Parts, values, footprints and references are the same as `../sas_schematics` and `../sas_pcb`. The libraries are shared from `../sas_schematics` (`sas_symbols.kicad_sym`, `smart_attendance.pretty`), so keep the folders side by side.

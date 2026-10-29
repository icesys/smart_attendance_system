# sas_schematics: Smart Attendance System, electrical schematics (v0.5)

Open `sas_schematics.kicad_pro` in KiCad 7 or newer. The root sheet shows the three boards; double-click a box to open it.

| Sheet | File | References |
|---|---|---|
| TOP | `top.kicad_sch` | 1-99 (R1, D1, J1 ...) |
| MIDDLE | `middle.kicad_sch` | 101-199 (J101, D101 ...) |
| BOTTOM | `bottom.kicad_sch` | 201-299 (J201, SW201 ...) |

The three sheets are separate boards: nothing joins them electrically inside KiCad; the two ribbon cables are listed on the root sheet and use the same pin numbers at both ends (TOP J1 = MIDDLE J105, MIDDLE J106 = BOTTOM J201).

## Power path
18650 -> TP4056 (protected, USB-C) -> slide switch -> MT3608 (set to 5.0 V with a multimeter first) -> cable 2 pins 1 and 3 (5V_BOOST) -> MIDDLE Schottky diode -> 5V_SYS (ESP32 5V pin, RDM6300, SD module, buzzer option). 3V3 comes from the ESP32 board and feeds the OLED, the DS3231 and the buzzer jumper default. BAT- is not ground (OUT- is).
With the Schottky, the board sits at about 4.7 V on battery. When USB is plugged in it supplies about 5 V and takes over; the battery supplies the board again when USB is unplugged.

## What was verified (KiCad 7.0.11 command line)
- Every wire was routed by script and the exported netlist was compared with the intended connections: every net matches exactly, no short and no missing pin.
- All footprint names exist (standard KiCad libraries, or `smart_attendance.pretty` in this folder).
- **ERC was not run** (KiCad 7's command line has no ERC): run Inspect > Electrical Rules Checker yourself.

## Estimates still to confirm
OLED size and hole spacing; SD module and DS3231 sizes; pad positions of TP4056 and MT3608; buzzer + pin; switch body orientation; ESP32 antenna-end pin offset (about 2.2 mm, computed).

`tools/` holds the generators (`gen_schematics.py`, `gen_footprints.py`).

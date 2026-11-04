# Assembly Guide (PCBs)

For the breadboard prototype, see [`Breadboard_Assembly_Guide_No_Soldering.pdf`](Breadboard_Assembly_Guide_No_Soldering.pdf).
Parts: [`bill_of_materials.md`](bill_of_materials.md). Cable pinouts and power notes: [`hardware/schematics/kicad/sas_pcb/documentation/`](../hardware/schematics/kicad/sas_pcb/documentation/). 1:1 board printouts: [`hardware/schematics/kicad/sas_pcb/printouts_1to1/`](../hardware/schematics/kicad/sas_pcb/printouts_1to1/).

## Before you start
- [ ] All parts from the BOM present; resistor values checked with the multimeter (220 Ω, 1 kΩ, 100 kΩ)
- [ ] Bare boards inspected: no shorts or broken tracks, holes drilled, M3 holes at (4,4), (91,4), (4,56), (91,56) mm
- [ ] **MT3608 set to 5.0 V** on the bench (powered from a 3.7 V source, multimeter on VOUT+ / VOUT−) **before** it goes on the board
- [ ] **DS3231 module: charge resistor removed** (the CR2032 is not rechargeable)
- [ ] ESP32-S3 dev board: IN-OUT pads soldered so the 5V pin is fed from 5V_SYS

## Rules
- Solder the lowest parts first (resistors, diodes), then capacitors, sockets and headers, then the tallest parts.
- Check polarity twice: LEDs (long leg = anode), 1N5819 and 1N4148 (band = cathode), 470 µF (stripe = −), buzzer (+ marked), battery holder.
- Header-mounted modules (OLED, microSD, DS3231, RDM6300) plug in **pin-down**: lay each real module upside-down on the 1:1 printout first; every pin must land on the pad with the same name.
- Pin 1 of every IDC header is the square pad / arrow. Both ribbon cables connect pin 1 to pin 1.

## BOTTOM board (power, microSD, clock)
1. C202 (100 nF), then C201 (470 µF, check polarity).
2. SW201 slide switch.
3. Female headers for J203 (TP4056: OUT+ B+ B− OUT−), J204 (MT3608), J205 (microSD), J206 (DS3231).
4. J201 (2 × 8 IDC, cable 2) and J202 (battery, 2 pins).
5. Battery holder under the board, wires to J202 (red to +).
6. Check with the multimeter, no battery: no short between BAT+, CHG_OUT+, 5V_BOOST and GND (OUT−).
7. Insert the TP4056 and the battery. Switch on: 5V_BOOST must read 5.0 V. Switch off.
8. Insert the microSD and DS3231 modules.

> B− of the protected TP4056 is **not** ground. The system ground is OUT−.

## MIDDLE board (ESP32-S3, RDM6300)
1. D101 (1N5819, band towards 5V_SYS as printed).
2. C102, C103 (100 nF), C101 (10 µF).
3. J101, J102 (1 × 22 female sockets): put them on the ESP32-S3 board first, then solder so they stay straight.
4. Female headers for J103 (RDM6300: TX RX nc GND 5V | ANT1 ANT2).
5. J105 (cable 1) and J106 (cable 2).
6. Plug the ESP32-S3 with its USB-C ports towards the left edge, as on the silkscreen.

## TOP board (interface and coil)
1. R1–R3 (220 Ω), R4 (1 kΩ), R5 (100 kΩ), D4 (1N4148).
2. C1, C3 (100 nF), C2 (10 µF).
3. Q1 (2N2222A, flat face as on the silkscreen), BZ1.
4. LEDs D1 blue, D2 green, D3 red.
5. SW1 (session), SW2 (info).
6. JP1: leave pads 1-2 bridged (buzzer on 3V3). Cut 1-2 and bridge 2-3 only if the buzzer is too quiet (5 V).
7. Female header for J2 (OLED: GND VCC SCL SDA), J1 (cable 1), J3 (coil).
8. Lay the 35 × 46 mm coil flat in the copper-free area (x 8–54, y 22–57 mm) and connect it to J3.

## Stacking
1. Fit 4 M3 standoffs on BOTTOM, mount MIDDLE, 4 more standoffs, mount TOP.
2. Cable 2: MIDDLE J106 ↔ BOTTOM J201. Cable 1: TOP J1 ↔ MIDDLE J105. Pin 1 to pin 1.

## First power-on
- [ ] Switch on and measure: 5V_BOOST 5.0 V, 5V_SYS ≈ 4.7 V, 3V3 3.3 V (test T1)
- [ ] Upload sketch D1 over the UART USB-C port: the serial monitor prints its message
- [ ] Upload sketch D2 (I2C scanner): finds 0x68 (DS3231) and 0x3C (OLED)
- [ ] Sketches D4 (microSD), D5 (reader), D6 (LEDs, buzzer, buttons), D8 (OLED)
- [ ] Sketch D9: EOSC cleared (the clock keeps running on the coin cell)
- [ ] Main firmware + `firmware/tools/set_clock.py`: clock set to the PC time
- [ ] Copy `students.csv` to the microSD, run the test plan (`test_plan.md`)

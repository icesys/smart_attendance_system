# Power distribution

18650 cell -> TP4056 (1 A, protected, USB-C charging) -> slide switch (both poles in parallel) -> MT3608 boost (set to 5.0 V with a multimeter BEFORE connecting anything) -> 470 uF + 100 nF -> cable 2 pins 1 and 3 (5V_BOOST) -> MIDDLE Schottky diode -> 5V_SYS.

5V_SYS feeds: ESP32-S3 5V pin (the IN-OUT pads of the dev board are soldered), RDM6300 (TX, GND, 5V), the SD module (via cable 2 pin 5) and the buzzer jumper option (via cable 1 pin 3). 3V3 comes from the ESP32 board regulator and feeds the OLED, the DS3231 (via cable 2 pin 6) and the default buzzer supply.

- BAT- is NOT ground: on the protected TP4056 it sits behind the protection FETs; OUT- is the system ground (the GND net).
- On battery the board sits at about 4.7 V (5.0 V minus the Schottky drop). With USB plugged in (about 5 V) USB supplies the board and the battery boost does not push into the USB port; unplug USB and the battery takes over.
- DS3231 is powered from 3V3 only; its 200 ohm charge resistor must be removed (CR2032 is not rechargeable).
- Track widths used: BAT+, BAT-, CHG_OUT+, SW_OUT 1.0 mm; 5V_BOOST 0.8 mm; 5V_SYS 0.6 mm; 3V3 0.5 mm; signals 0.3 mm. GND is a copper pour on both layers.

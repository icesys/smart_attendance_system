# Power budget and battery life (estimate)

Paper calculation from the datasheets in `hardware/datasheets/`. These values are design estimates, not measurements.

## 1. Current per part

| Part | Rail | Typical current | Source |
|---|---|---|---|
| ESP32-S3 (Wi-Fi and Bluetooth off, CPU running) | 3V3 | 40–60 mA, use **50 mA** | ESP32-S3 datasheet, active mode without RF |
| OLED 0.96" (text, partly lit) | 3V3 | 10–20 mA, use **15 mA** | SSD1306 datasheet + typical module |
| DS3231 | 3V3 | 0.2 mA | DS3231 datasheet |
| LEDs (blue heartbeat, short green/red flashes) | 3V3 | average **2 mA** | 220 Ω → about 5–6 mA while on |
| Dev board power LED | 3V3 | **3 mA** | typical |
| RDM6300 (field always on) | 5V_SYS | < 50 mA, use **40 mA** | Module specification |
| microSD module (idle, short writes) | 5V_SYS | average **5 mA** (writes 30–100 mA for a few ms) | typical |
| Buzzer (short beeps only) | 3V3 | negligible on average | — |

The 3V3 loads come through the linear regulator of the ESP32 board, so they draw the same current from 5V_SYS.

**Total on 5V_SYS ≈ 50 + 15 + 0.2 + 2 + 3 + 40 + 5 ≈ 115 mA.**

## 2. Power taken from the battery

- The MT3608 delivers 5.0 V; the 1N5819 drops about 0.3 V (5V_SYS ≈ 4.7 V).
- Boost output power: 5.0 V × 0.115 A ≈ 0.58 W.
- MT3608 efficiency at this load: about 85–90 %, use 87 % → input power ≈ 0.66 W.
- Battery current at 3.7 V (average cell voltage): 0.66 / 3.7 ≈ **180 mA**. At the end of discharge (3.0 V): about 220 mA, well inside the MT3608 and TP4056 protection limits.

## 3. Battery life

| 18650 capacity | Usable (≈ 90 %) | Running time at 180 mA |
|---|---|---|
| 2000 mAh | 1800 mAh | ≈ 10 h |
| 2500 mAh | 2250 mAh | ≈ 12.5 h |
| 3000 mAh | 2700 mAh | ≈ 15 h |

The device only needs to be on while students tap their cards (about 10–15 minutes per lecture). Even left on all day (8 h), one charge of a 2500 mAh cell is enough: the target of test T8 ("at least one day of lectures") **should be met with margin**.

## 4. Charging

The TP4056 module charges at 1 A (programming resistor 1.2 kΩ on the usual modules). Constant current then constant voltage: about **2.5–3 h** from empty for a 2500 mAh cell.

## 5. Peaks

At start-up and during microSD writes the current on 5V_SYS is higher for a few milliseconds. The 470 µF + 100 nF at the MT3608 output and the 10 µF / 100 nF on each board cover these peaks.

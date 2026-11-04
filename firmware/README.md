# firmware

PlatformIO project (Arduino framework) for the ESP32-S3 N16R8. Environment: `esp32-s3-n16r8`.

| Path | Content |
|---|---|
| `src/main.cpp` | Main program: sessions, card handling, LED/buzzer patterns, OLED, USB drive mode, serial commands |
| `include/config.h` | Every pin, timing and option in one place |
| `include/parsers.h` | Plain C++ helpers (RDM6300 frames, CSV lines, sorting), testable on a PC |
| `test/host/test_parsers.cpp` | 26 unit tests for `parsers.h`, run on the PC |
| `sketches/` | Hardware test sketches D1–D9 (copy one into `src/` in place of `main.cpp` to run it) |
| `data/students.csv` | Template of the student list, to copy to the root of the microSD card |
| `tools/set_clock.py` | Sets the DS3231 to the PC time over the serial port (`SETTIME` command) |

## Test sketches
| Sketch | Checks |
|---|---|
| D1 | Upload and serial link |
| D2 | I2C scanner: 0x68 (clock) and 0x3C (OLED) |
| D3 | Set and read the DS3231 |
| D4 | microSD: writes `test.txt` |
| D5 | RDM6300 raw bytes, one 14-byte frame per tap |
| D6 | LEDs, buzzer, buttons (GPIO40, GPIO41) |
| D7 | Card read with LED and buzzer feedback, no PC needed |
| D8 | OLED: frame and text |
| D9 | DS3231 diagnosis: why the clock stops without power; clears the EOSC bit |

## Build, flash, test
```bash
pio run                # build
pio run -t upload      # flash (hold BOOT if it fails at "Connecting...")
pio device monitor     # 115200 baud, then type HELP
g++ -std=c++17 -Iinclude test/host/test_parsers.cpp -o t && ./t    # unit tests on the PC
~/.platformio/penv/bin/python tools/set_clock.py                   # set the clock (close the monitor first)
```

Serial output goes to the **UART** USB-C port; the **native** USB-C port is the USB drive (TinyUSB). See the main [README](../README.md) for the commands, LED/buzzer patterns and file formats.

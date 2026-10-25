# Smart Attendance System: Complete Code (v2)

Everything for the prototype, **updated from your own files**: your button pins (40 and 41), your banner and your limits are kept. New in this version: a **power LED** on GPIO5, a **USB drive mode** on button 2, and a safer **OLED start-up check**. Every line of code has a comment that says what it does and why.

## What changed compared with the files you uploaded
- **config.h:** new `PIN_LED_POWER = 5`, new `USE_DRIVE_MODE` option, two heartbeat timing constants. Nothing of yours was changed.
- **main.cpp (additions only):** power LED blink (`powerLedUpdate`), drive mode (`startDriveMode`, the three USB callbacks, `rebootNow`), commands `DRIVE` and `REBOOT`, a drive-mode screen and LED pattern, a guard so cards and SD commands are ignored in drive mode, and a new OLED start-up that checks whether the display really answers (0x3C, then 0x3D) and shows a start screen.
- **platformio.ini:** now has two environments. The main one uses the **UART port** for upload and the serial monitor and keeps the **native USB port** free for drive mode. The second one (`native-serial`) is your old way, without drive mode.
- **parsers.h and test_parsers.cpp:** unchanged.

```diff
@@ -21,6 +21,7 @@
 constexpr int PIN_LED_GREEN = 1;                // green LED (through 220 ohm)
 constexpr int PIN_LED_RED   = 2;                // red LED (through 220 ohm)
 constexpr int PIN_BUZZER    = 42;               // buzzer transistor base (through 1 kohm)
+constexpr int PIN_LED_POWER = 5;               // second green LED (through 220 ohm): blinks twice every 3 s = "the system is on"
 
 // ---- Buttons (other leg to GND, internal pull-up resistor is used) ----
 constexpr int PIN_BTN_SESSION = 40;             // short press = start session, long press = stop session
@@ -28,6 +29,9 @@
 
 // ============================== OPTIONS ======================================
 #define USE_OLED 1                              // 1 = use the OLED, 0 = build without it
+#ifndef USE_DRIVE_MODE                          // platformio.ini can set this; if it does not, use the default below
+#define USE_DRIVE_MODE 1                        // 1 = long press of button 2 shows the SD card as a USB drive, 0 = build without it
+#endif                                          // end of the USE_DRIVE_MODE default
 constexpr uint8_t OLED_ADDR = 0x3C;             // I2C address of the OLED (try 0x3D if not found)
 constexpr int OLED_W = 128;                     // OLED width in pixels
 constexpr int OLED_H = 64;                      // OLED height in pixels (use 32 for a 128x32 OLED)
@@ -35,9 +39,11 @@
 constexpr uint32_t SAME_CARD_IGNORE_MS = 1500;  // a card left on the reader is counted only once
 constexpr uint32_t DEBOUNCE_MS   = 40;          // ignore button contact bounce shorter than this
 constexpr uint32_t LONG_PRESS_MS = 1500;        // holding a button this long counts as a long press
+constexpr uint32_t HEARTBEAT_PERIOD_MS = 3000;  // the power LED repeats its double blink every 3 seconds
+constexpr uint32_t HEARTBEAT_BLINK_MS  = 80;    // each of the two blinks, and the gap between them, lasts 80 ms (fast)
 constexpr size_t   MAX_STUDENTS  = 1000;        // maximum number of students loaded from the card
 constexpr size_t   MAX_SEEN      = 1000;        // maximum number of taps remembered in one session
 
 // ---- Names of files and folders on the microSD card ----
 constexpr char FILE_STUDENTS[]  = "/students.csv"; // list of students: one "UID,Name" per line
-constexpr char DIR_ATTENDANCE[] = "/attendance";   // folder where one file per session is saved
\ No newline at end of file
+constexpr char DIR_ATTENDANCE[] = "/attendance";   // folder where one file per session is saved
```

## Contents
1. [Working with the board now: two USB-C ports](#1-working-with-the-board-now-two-usb-c-ports)
2. [Project layout](#2-project-layout)
3. [platformio.ini](#3-platformioini)
4. [include/config.h](#4-includeconfigh)
5. [include/parsers.h](#5-includeparsersh)
6. [src/main.cpp (the firmware)](#6-srcmaincpp-the-firmware)
7. [data/students.csv](#7-datastudentscsv-goes-on-the-microsd-card)
8. [Test sketches D1 to D9](#8-test-sketches-d1-to-d9)
9. [The PC test of the parsers: what it is and why](#9-the-pc-test-of-the-parsers-what-it-is-and-why)
10. [What happens when a new card is scanned](#10-what-happens-when-a-new-card-is-scanned)
11. [USB drive mode](#11-usb-drive-mode)
12. [Reference: buttons, lights, commands, files](#12-reference-buttons-lights-commands-files)
13. [What was tested](#13-what-was-tested)
14. [Troubleshooting](#14-troubleshooting)

---

## 1. Working with the board now: two USB-C ports

Your board has two USB-C ports and this version uses them for different jobs:

| Port | Used for |
|---|---|
| **UART port** (the one with the USB-to-serial chip) | Power, uploading, and the serial monitor. This is your everyday development port (`/dev/ttyUSB0` on Linux). |
| **Native USB port** | Only for **drive mode**: the SD card appears as a USB drive on your computer. Plug a second cable here when you want to see the files. |

Check the port names with `pio device list` and change `upload_port` and `monitor_port` in `platformio.ini` if yours differ. If you prefer the old way (everything over the native port, no drive mode), build with `pio run -e native-serial -t upload`.

Daily workflow:
1. UART port connected: upload (`pio run -t upload`) and open the monitor (`pio device monitor`).
2. Start a session with button 1 (short press), tap cards, stop with a long press of button 1.
3. To see the files as a drive: with no session running, **hold button 2 for 1.5 s**, then plug a cable into the native USB port. Details in section 11.

---

## 2. Project layout

```
smart_attendance/
├── platformio.ini            build settings (two environments)
├── include/
│   ├── config.h              pins and options
│   └── parsers.h             reader and CSV parsers (no Arduino code)
├── src/
│   └── main.cpp              the firmware
├── data/
│   └── students.csv          copy to the root of the microSD card
├── sketches/                 test sketches D1 to D9 (copy one at a time into src/main.cpp)
└── test/host/
    └── test_parsers.cpp      runs on a PC
```

---

## 3. platformio.ini


```ini
; ---------------------------------------------------------------------------
; platformio.ini - build settings for the Smart Attendance System
; (comments are on their own lines because PlatformIO does not always accept
;  comments at the end of a setting line)
; ---------------------------------------------------------------------------

; Only the first environment is built by default (pio run). The second one is an alternative.
[platformio]
default_envs = esp32-s3-n16r8

; ======== MAIN BUILD: UART port for work, native USB port for drive mode ========
; Name of this build environment (any name you like)
[env:esp32-s3-n16r8]
; The chip family package that PlatformIO downloads (ESP32 toolchain + Arduino core)
platform = espressif32
; The closest built-in board definition for your S3-N16R8 board
board = esp32-s3-devkitc-1
; Use the Arduino programming style (setup() and loop())
framework = arduino
; Speed of the serial monitor; must match Serial.begin(115200) in the code
monitor_speed = 115200
; Upload and serial monitor use the UART port (the USB-to-serial chip). Check the name with: pio device list
upload_port = /dev/ttyUSB0
; Serial monitor on the same UART port
monitor_port = /dev/ttyUSB0
; Reset method that matches the USB-to-serial chip on the UART port
upload_resetmethod = nodemcu
; Tell the uploader that the flash chip is really 16 MB
board_upload.flash_size = 16MB
; Flash is quad (qio) and PSRAM is octal (opi) on the N16R8 module
board_build.arduino.memory_type = qio_opi
; Type of the PSRAM chip (octal)
board_build.psram_type = opi
; Partition table that uses all 16 MB of flash
board_build.partitions = default_16MB.csv
; Remove the USB flags that the board definition sets, because drive mode needs different ones
build_unflags =
    -DARDUINO_USB_MODE=1
    -DARDUINO_USB_CDC_ON_BOOT=1
; Extra compiler flags, one per line
build_flags =
    ; Switch the 8 MB PSRAM on
    -DBOARD_HAS_PSRAM
    ; Make sure no old USB mode value is left
    -UARDUINO_USB_MODE
    ; TinyUSB mode: the native USB-C port can act as a USB drive (needed for drive mode)
    -DARDUINO_USB_MODE=0
    ; Serial.print() goes to the UART port, the native USB port stays free for drive mode
    -DARDUINO_USB_CDC_ON_BOOT=0
    ; Build with drive mode (see config.h)
    -DUSE_DRIVE_MODE=1
; Libraries that PlatformIO downloads automatically
lib_deps =
    ; DS3231 real-time clock
    adafruit/RTClib
    ; SSD1306 OLED driver
    adafruit/Adafruit SSD1306
    ; Graphics library that the OLED driver needs
    adafruit/Adafruit GFX Library

; ======== ALTERNATIVE: the old way, Serial over the native USB-C port, no drive mode ========
; Build and upload it with: pio run -e native-serial -t upload
[env:native-serial]
; Start from the main environment and change only what differs
extends = env:esp32-s3-n16r8
; Upload through the native USB-C port
upload_port = /dev/ttyACM0
; Serial monitor on the native USB-C port
monitor_port = /dev/ttyACM0
; Remove the TinyUSB flag of the main build
build_unflags =
    -DARDUINO_USB_MODE=0
; Flags of the old setup
build_flags =
    ; Switch the 8 MB PSRAM on
    -DBOARD_HAS_PSRAM
    ; Built-in USB serial/JTAG mode
    -DARDUINO_USB_MODE=1
    ; Serial.print() goes out through the native USB-C port
    -DARDUINO_USB_CDC_ON_BOOT=1
    ; No drive mode in this build
    -DUSE_DRIVE_MODE=0
```


---

## 4. include/config.h


```cpp
// config.h - every pin number and option of the project in ONE place.
#pragma once                                    // include this file only once per build
#include <stddef.h>                             // defines size_t used below
#include <stdint.h>                             // defines uint8_t, uint32_t used below

// ======================= PINS (see the assembly guide) =======================
// ---- I2C bus: DS3231 clock (address 0x68) and OLED (address 0x3C) ----
constexpr int PIN_SDA = 9;                      // I2C data wire (SDA) is on GPIO9
constexpr int PIN_SCL = 8;                      // I2C clock wire (SCL) is on GPIO8

// ---- microSD module on the SPI bus ----
constexpr int PIN_SD_CS   = 10;                 // chip select: tells the card "I am talking to you"
constexpr int PIN_SD_SCK  = 11;                 // SPI clock
constexpr int PIN_SD_MOSI = 12;                 // data from the ESP32 to the card
constexpr int PIN_SD_MISO = 13;                 // data from the card to the ESP32

// ---- RDM6300 125 kHz reader ----
constexpr int PIN_RFID_RX = 18;                 // the reader's TX wire goes to this GPIO (9600 baud)

// ---- Feedback parts (J3 row of the ESP32-S3) ----
constexpr int PIN_LED_GREEN = 1;                // green LED (through 220 ohm)
constexpr int PIN_LED_RED   = 2;                // red LED (through 220 ohm)
constexpr int PIN_BUZZER    = 42;               // buzzer transistor base (through 1 kohm)
constexpr int PIN_LED_POWER = 5;               // second green LED (through 220 ohm): blinks twice every 3 s = "the system is on"

// ---- Buttons (other leg to GND, internal pull-up resistor is used) ----
constexpr int PIN_BTN_SESSION = 40;             // short press = start session, long press = stop session
constexpr int PIN_BTN_MUTE    = 41;             // short press = mute / unmute the buzzer

// ============================== OPTIONS ======================================
#define USE_OLED 1                              // 1 = use the OLED, 0 = build without it
#ifndef USE_DRIVE_MODE                          // platformio.ini can set this; if it does not, use the default below
#define USE_DRIVE_MODE 1                        // 1 = long press of button 2 shows the SD card as a USB drive, 0 = build without it
#endif                                          // end of the USE_DRIVE_MODE default
constexpr uint8_t OLED_ADDR = 0x3C;             // I2C address of the OLED (try 0x3D if not found)
constexpr int OLED_W = 128;                     // OLED width in pixels
constexpr int OLED_H = 64;                      // OLED height in pixels (use 32 for a 128x32 OLED)

constexpr uint32_t SAME_CARD_IGNORE_MS = 1500;  // a card left on the reader is counted only once
constexpr uint32_t DEBOUNCE_MS   = 40;          // ignore button contact bounce shorter than this
constexpr uint32_t LONG_PRESS_MS = 1500;        // holding a button this long counts as a long press
constexpr uint32_t HEARTBEAT_PERIOD_MS = 3000;  // the power LED repeats its double blink every 3 seconds
constexpr uint32_t HEARTBEAT_BLINK_MS  = 80;    // each of the two blinks, and the gap between them, lasts 80 ms (fast)
constexpr size_t   MAX_STUDENTS  = 1000;        // maximum number of students loaded from the card
constexpr size_t   MAX_SEEN      = 1000;        // maximum number of taps remembered in one session

// ---- Names of files and folders on the microSD card ----
constexpr char FILE_STUDENTS[]  = "/students.csv"; // list of students: one "UID,Name" per line
constexpr char DIR_ATTENDANCE[] = "/attendance";   // folder where one file per session is saved
```


---

## 5. include/parsers.h

Unchanged. Plain C++ with no Arduino code (see section 9 for why that matters).


```cpp
// parsers.h - plain C++ helpers with NO Arduino code, so they can be tested on a PC too.
#pragma once                                      // include this file only once per build
#include <stddef.h>                               // size_t
#include <stdint.h>                               // uint8_t, uint64_t
#include <stdlib.h>                               // general utilities
#include <string.h>                               // strlen, strchr, strcpy

// Converts one hex character ('0'-'9', 'A'-'F', 'a'-'f') to its value 0-15; returns -1 if it is not hex.
inline int hexVal(int c) {                        // "inline" lets the function live in a header file
  if (c >= '0' && c <= '9') return c - '0';       // digits: '0' -> 0 ... '9' -> 9
  if (c >= 'A' && c <= 'F') return c - 'A' + 10;  // capital letters: 'A' -> 10 ... 'F' -> 15
  if (c >= 'a' && c <= 'f') return c - 'a' + 10;  // small letters: 'a' -> 10 ... 'f' -> 15
  return -1;                                      // anything else is not a hex digit
}                                                 // end of hexVal

// Reads the bytes sent by the RDM6300 and recognises one complete, correct frame.
// A frame has 14 bytes: 0x02, 10 ASCII hex characters (the card), 2 ASCII hex characters
// (checksum = XOR of the 5 card bytes), and 0x03.
class Rdm6300Parser {                             // a small state machine that remembers the bytes so far
 public:                                          // the part that other code can use
  // Give it one received byte. It returns true when a whole valid frame has just arrived;
  // then uid10 holds the 10 hex characters of the card plus a closing '\0'.
  bool feed(uint8_t c, char uid10[11]) {          // called once for every byte coming from the reader
    if (n_ == 0) {                                // we are not inside a frame yet
      if (c == 0x02) buf_[n_++] = c;              // 0x02 is the start marker: store it and start collecting
      return false;                               // nothing complete yet
    }                                             // end of "not inside a frame"
    if (c == 0x02) {                              // a new start marker appeared in the middle of a frame
      n_ = 0;                                     // throw away the broken frame
      buf_[n_++] = c;                             // and start again from this marker
      return false;                               // nothing complete yet
    }                                             // end of resynchronise
    buf_[n_++] = c;                               // store the byte in the next free place
    if (n_ < 14) return false;                    // the frame is not full yet, wait for more bytes
    n_ = 0;                                       // the frame is full: get ready for the next one
    if (buf_[13] != 0x03) return false;           // the last byte must be the end marker 0x03
    uint8_t x = 0;                                // x will hold the XOR of the 5 card bytes
    for (int i = 0; i < 5; i++) {                 // go through the 5 card bytes (2 hex characters each)
      int h = hexVal(buf_[1 + 2 * i]);            // first (high) hex character of this byte
      int l = hexVal(buf_[2 + 2 * i]);            // second (low) hex character of this byte
      if (h < 0 || l < 0) return false;           // a character is not hex: the frame is damaged
      x ^= (uint8_t)((h << 4) | l);               // join the two characters into one byte and XOR it in
    }                                             // end of the loop over the card bytes
    int ch = hexVal(buf_[11]);                    // high hex character of the checksum sent by the reader
    int cl = hexVal(buf_[12]);                    // low hex character of the checksum sent by the reader
    if (ch < 0 || cl < 0) return false;           // the checksum characters are not hex: damaged frame
    if (x != (uint8_t)((ch << 4) | cl)) return false; // our XOR must equal the checksum, otherwise reject
    for (int i = 0; i < 10; i++) {                // copy the 10 card characters to the caller
      char k = (char)buf_[1 + i];                 // take one character
      if (k >= 'a' && k <= 'f') k = (char)(k - 32); // make small letters capital so the text is always the same
      uid10[i] = k;                               // store it in the caller's text
    }                                             // end of the copy loop
    uid10[10] = 0;                                // close the text with '\0'
    return true;                                  // a valid card frame was received
  }                                               // end of feed

 private:                                         // the part only this class uses
  uint8_t buf_[14] = {0};                         // the bytes of the frame collected so far
  uint8_t n_ = 0;                                 // how many bytes are in buf_
};                                                // end of class Rdm6300Parser

// Turns the text "0A00B2C3D4" into a 40-bit number. Returns false if it is not exactly 10 hex digits.
inline bool parseUid10(const char* s, uint64_t& out) { // "out" receives the number
  if (strlen(s) != 10) return false;              // a card number must be exactly 10 characters
  uint64_t v = 0;                                 // the number we are building
  for (int i = 0; i < 10; i++) {                  // go through the 10 characters
    int h = hexVal(s[i]);                         // value of this character, 0-15
    if (h < 0) return false;                      // not a hex digit: reject the text
    v = (v << 4) | (uint64_t)h;                   // shift the number 4 bits left and add the new digit
  }                                               // end of the loop
  out = v;                                        // give the result to the caller
  return true;                                    // success
}                                                 // end of parseUid10

// One line of the student list: the card number and the name.
struct StudentRec {                               // a small record type
  uint64_t id;                                    // card number as a 40-bit number (fast to compare)
  char name[32];                                  // student name, up to 31 characters
};                                                // end of StudentRec

// Reads one line "UID,Name" of students.csv. The line text is modified while reading.
// Returns false for empty lines, comment lines (starting with #), the header line and bad lines.
inline bool parseStudentLine(char* line, StudentRec& out) { // "out" receives the result
  while (*line == ' ' || *line == '\t') line++;   // skip spaces at the start of the line
  size_t len = strlen(line);                      // length of the rest of the line
  while (len && (line[len - 1] == '\r' || line[len - 1] == '\n' || line[len - 1] == ' ' || line[len - 1] == '\t'))
    line[--len] = 0;                              // cut off line-end characters and spaces at the end
  if (len == 0 || line[0] == '#') return false;   // empty line or comment: nothing to read
  char* comma = strchr(line, ',');                // find the comma that separates the UID from the name
  if (!comma) return false;                       // no comma: not a valid line
  *comma = 0;                                     // end the UID text at the comma
  size_t ul = strlen(line);                       // length of the UID text
  while (ul && (line[ul - 1] == ' ' || line[ul - 1] == '\t')) line[--ul] = 0; // remove spaces after the UID
  uint64_t id;                                    // will hold the UID as a number
  if (!parseUid10(line, id)) return false;        // the header line "uid,name" fails here and is skipped
  char* name = comma + 1;                         // the name starts right after the comma
  while (*name == ' ' || *name == '\t') name++;   // skip spaces before the name
  size_t j = 0;                                   // how many name characters we copied
  for (; *name && j < sizeof(out.name) - 1; name++) { // copy the name, leaving room for the closing '\0'
    char c = *name;                               // the character to copy
    if (c == ',' || c == '"') c = ' ';            // commas and quotes would break the CSV output, so use a space
    out.name[j++] = c;                            // store it
  }                                               // end of the copy loop
  out.name[j] = 0;                                // close the name text
  if (j == 0) strcpy(out.name, "(no name)");      // use a placeholder if the name is empty
  out.id = id;                                    // store the card number in the record
  return true;                                    // the line was valid
}                                                 // end of parseStudentLine
```


---

## 6. src/main.cpp (the firmware)


```cpp
/**********************************************************************************/
/*                                                         / - ice.               */
/*   SMART ATTENDANCE SYSTEM                              /                       */
/*   ----------------------------               :+:   .:#/ #:.   .:#/#:.          */
/*   Code By : ice.                                  +:         #:   ##           */
/*   GitHub : https://github.com/icesys       #+#   +:         #+::##"            */
/*   Created : 20-10-2026                    #+#   #+         #+                  */
/*   Updated : 25-10-2026                   #+#   ##    ##   ##    ##             */
/*                                         ###    #+./ #+    #+. /#+    #         */
/*                                                  /                             */
/*                                                 /                              */
/**********************************************************************************/

// ===========================================================================
// Smart Attendance System - main firmware for the ESP32-S3 (N16R8)
//
// What it does:
//   1. A lecturer presses button 1 to start a "session" (one lecture).
//   2. Each student taps a 125 kHz card on the RDM6300 reader.
//   3. The ESP32 looks the card up in /students.csv, reads the time from the DS3231
//      and appends one line to a session file on the microSD card.
//   4. The LEDs, the buzzer and the OLED tell the student what happened.
//   5. A long press on button 1 ends the session.
// With the USB-C cable connected to the PC you can also type commands in the serial
// monitor (type HELP) to set the clock and to read the attendance files.
// ===========================================================================

#include <Arduino.h>            // core Arduino functions: pinMode, digitalWrite, millis, Serial ...
#include <SPI.h>                // SPI bus driver, used by the microSD module
#include <SD.h>                 // microSD file system library (FAT32 cards)
#include <Wire.h>               // I2C bus driver, used by the clock and the OLED
#include <RTClib.h>             // DS3231 real-time clock library
#include <ctype.h>              // toupper(), used to read serial commands in any letter case
#include <stdio.h>              // snprintf() and sscanf() for building and reading text
#include <string.h>             // strcmp(), strchr(), strcpy() and other text functions
#include <vector>               // std::vector, lists that can grow while the program runs
#include "config.h"             // our pins and options
#include "parsers.h"            // our RDM6300 and CSV parsers
#if USE_DRIVE_MODE && ARDUINO_USB_MODE   // drive mode only works when the USB port runs in TinyUSB (OTG) mode
#error "USE_DRIVE_MODE needs -DARDUINO_USB_MODE=0 in platformio.ini (see the comments there)" // stop the build with a clear message
#endif                          // end of the USB mode check
#if USE_DRIVE_MODE            // USB drive mode needs the USB (TinyUSB) libraries of the Arduino core
#include "USB.h"                // starts the native USB-C port as a USB device
#include "USBMSC.h"             // USB mass storage class: makes the SD card show up as a drive on the PC
#endif                          // end of the USB include block
#if USE_OLED                    // include the OLED libraries only if the OLED is enabled in config.h
#include <Adafruit_GFX.h>       // graphics base library of the OLED
#include <Adafruit_SSD1306.h>   // driver of the SSD1306 OLED
#endif                          // end of the OLED include block

// ------------------------------ GLOBAL OBJECTS -----------------------------
HardwareSerial RFID(1);         // use hardware UART number 1 to talk to the RDM6300
RTC_DS3231 rtc;                 // the DS3231 clock chip
Rdm6300Parser rdm;              // decodes the bytes that come from the RDM6300
#if USE_OLED                    // OLED objects exist only if the OLED is enabled
Adafruit_SSD1306 oled(OLED_W, OLED_H, &Wire, -1); // OLED on the I2C bus, no reset pin (-1)
bool oledOk = false;            // becomes true when the OLED answered at start-up
#endif                          // end of the OLED object block

// ------------------------------ GLOBAL STATE -------------------------------
bool rtcOk = false;             // true when the clock is found and has a valid time
bool sdOk = false;              // true when the microSD card is working
bool muted = false;             // true when the buzzer is switched off with button 2
bool driveMode = false;        // true while the SD card is shown to the PC as a USB drive
volatile bool mscEjected = false; // true after the PC has "ejected" the drive (set by the USB task)
#if USE_DRIVE_MODE              // the USB drive object exists only if drive mode is enabled
USBMSC msc;                     // the USB mass storage "disk" shown to the PC
#endif                          // end of the drive object block
std::vector<StudentRec> students;   // all students loaded from /students.csv
std::vector<uint64_t> seen;     // cards already tapped in the current session
bool sessionActive = false;     // true between "start session" and "stop session"
char sessionPath[64] = "";      // full path of the current session file on the card
uint16_t presentCount = 0;      // number of known students counted in this session
uint16_t unknownCount = 0;      // number of unknown cards tapped in this session
char lastLine[32] = "";         // text of the last tap, shown on the OLED
uint64_t lastUid = 0;           // card number of the last card read by the reader
uint32_t lastSeenMs = 0;        // time (millis) when that card was last read

// ------------------- FEEDBACK PATTERNS (LEDs + BUZZER) ---------------------
struct Step {                   // one step of a light-and-sound pattern
  uint8_t leds;                 // which LEDs are on during this step (bit 0 = green, bit 1 = red)
  bool buzz;                    // true = buzzer on during this step
  uint16_t ms;                  // how long the step lasts in milliseconds; 0 marks the end of the pattern
};                              // end of Step

enum : uint8_t { LED_G = 1, LED_R = 2 }; // bit values used in Step.leds

const Step P_BOOT[] = {         // played at power-up when everything is fine: three rising beeps
  {LED_G, true, 80}, {0, false, 80},        // short green blink + beep, then a pause
  {LED_G, true, 80}, {0, false, 80},        // second short blink + beep, then a pause
  {LED_G, true, 200}, {0, false, 0}         // long blink + beep, then the end marker (ms = 0)
};                         
const Step P_OK[] = {           // a known student was counted
  {LED_G, true, 120}, {LED_G, false, 250},  // green with a short beep, then green alone for a moment
  {0, false, 0}                             // end marker
};                              // end of P_OK
const Step P_DUP[] = {          // the same card was tapped twice in this session
  {LED_R, true, 80}, {0, false, 80},        // red + beep, pause
  {LED_R, true, 80}, {LED_R, false, 200},   // red + beep again, then red alone
  {0, false, 0}                             // end marker
};                              // end of P_DUP
const Step P_UNKNOWN[] = {      // the card is not in students.csv
  {LED_R, true, 600}, {LED_R, false, 200},  // one long red + beep, then red alone
  {0, false, 0}                             // end marker
};                              // end of P_UNKNOWN
const Step P_NOSESSION[] = {    // a card was tapped but no session is running
  {LED_R, true, 150}, {0, false, 150},      // red + beep, pause
  {LED_R, true, 150}, {0, false, 0}         // red + beep, end marker
};                              // end of P_NOSESSION
const Step P_START[] = {        // session started
  {LED_G, true, 100}, {0, false, 100},      // blink + beep, pause
  {LED_G, true, 100}, {0, false, 100},      // blink + beep, pause
  {LED_G, true, 300}, {0, false, 0}         // long blink + beep, end marker
};                              // end of P_START
const Step P_STOP[] = {         // session stopped
  {LED_R, true, 300}, {0, false, 100},      // long red + beep, pause
  {LED_R, true, 300}, {0, false, 0}         // long red + beep, end marker
};                              // end of P_STOP
const Step P_ERROR[] = {        // something is wrong (no SD card, no clock, write failed)
  {LED_R, true, 300}, {LED_R, false, 300},  // red + beep, red alone
  {LED_R, true, 300}, {LED_R, false, 300},  // red + beep, red alone
  {LED_R, true, 300}, {0, false, 0}         // red + beep, end marker
};                              // end of P_ERROR
const Step P_MUTE[] = {         // confirms that mute was switched on or off (both LEDs, no sound)
  {LED_G | LED_R, false, 150}, {0, false, 0} // both LEDs for a moment, end marker
};                              // end of P_MUTE
const Step P_DRIVE[] = {        // drive mode switched on: both LEDs and two beeps
  {LED_G | LED_R, true, 200}, {0, false, 100},  // both LEDs + beep, pause
  {LED_G | LED_R, true, 200}, {0, false, 0}     // both LEDs + beep, end marker
};                              // end of P_DRIVE

const Step* patCur = nullptr;   // the step being played now (nullptr = no pattern playing)
uint32_t patT0 = 0;             // time (millis) when the current step started

// Switches the LEDs and the buzzer to what one step asks for.
void applyStep(const Step& s) {                                   // s = the step to show
  digitalWrite(PIN_LED_GREEN, (s.leds & LED_G) ? HIGH : LOW);    // green LED on if bit 0 is set
  digitalWrite(PIN_LED_RED, (s.leds & LED_R) ? HIGH : LOW);      // red LED on if bit 1 is set
  digitalWrite(PIN_BUZZER, (s.buzz && !muted) ? HIGH : LOW);     // buzzer on only if asked AND not muted
}                                                                 // end of applyStep

// Starts playing a pattern. It plays in the background: loop() keeps running.
void startPattern(const Step* p) {                                // p = first step of the pattern
  patCur = p;                                                     // remember the pattern position
  patT0 = millis();                                               // remember when this step began
  applyStep(*patCur);                                             // show the first step immediately
}                                                                 // end of startPattern

// Called from loop(): moves to the next step when the current one has lasted long enough.
void patternUpdate() {                                            // no waiting inside, so it never blocks
  if (!patCur) return;                                            // no pattern playing: nothing to do
  if (millis() - patT0 >= patCur->ms) {                           // has the current step lasted long enough?
    patCur++;                                                     // move to the next step
    patT0 = millis();                                             // the next step starts now
    if (patCur->ms == 0) {                                        // the end marker: the pattern is finished
      patCur = nullptr;                                           // no pattern is playing any more
      digitalWrite(PIN_BUZZER, LOW);                              // make sure the buzzer is off
      digitalWrite(PIN_LED_GREEN, LOW);                           // green LED off
      digitalWrite(PIN_LED_RED, LOW);                             // red LED off
      return;                                                     // done
    }                                                             // end of "pattern finished"
    applyStep(*patCur);                                           // show the new step
  }                                                               // end of "step finished"
}                                                                 // end of patternUpdate

// When no pattern is playing, the LEDs show the state of the device.
void idleLedUpdate() {                                            // called from loop()
  if (patCur) return;                                             // a pattern is playing: do not disturb it
  uint32_t t = millis();                                          // current time in milliseconds
  bool fault = !sdOk || !rtcOk;                                   // a fault exists if the card or the clock is not OK
  bool g = false;                                                 // green LED state to apply
  bool r = false;                                                 // red LED state to apply
  if (driveMode) { g = (t % 1000) < 500; r = !g; }                // drive mode: green and red LEDs take turns every half second
  else if (fault) r = (t % 1000) < 100;                           // fault: short red blink every second
  else if (sessionActive) g = true;                               // session running: steady green
  else g = (t % 2000) < 80;                                       // ready: short green blink every 2 seconds
  digitalWrite(PIN_LED_GREEN, g ? HIGH : LOW);                    // apply the green LED state
  digitalWrite(PIN_LED_RED, r ? HIGH : LOW);                      // apply the red LED state
}                                                                 // end of idleLedUpdate

// The power LED: two fast blinks every 3 seconds, so you can see that the system is on.
void powerLedUpdate() {                                           // called from loop(); never waits
  uint32_t p = millis() % HEARTBEAT_PERIOD_MS;                    // position inside the 3-second cycle (0 to 2999 ms)
  bool on = (p < HEARTBEAT_BLINK_MS) ||                           // first blink: 0 to 80 ms
            (p >= 2 * HEARTBEAT_BLINK_MS && p < 3 * HEARTBEAT_BLINK_MS); // second blink: 160 to 240 ms
  digitalWrite(PIN_LED_POWER, on ? HIGH : LOW);                   // LED on during the blinks, off for the rest of the cycle
}                                                                 // end of powerLedUpdate

// ------------------------------ PUSH BUTTONS -------------------------------
enum BtnEvent : uint8_t { BTN_NONE, BTN_SHORT, BTN_LONG };        // what a button can report

struct Button {                                                   // one debounced push button
  int pin = 0;                                                    // GPIO the button is wired to
  bool raw = false;                                               // last raw reading (true = pressed)
  bool down = false;                                              // true while the press is accepted as real
  bool longFired = false;                                         // true once the long press was reported
  uint32_t tChange = 0;                                           // time when the raw reading last changed
  uint32_t tDown = 0;                                             // time when the press was accepted

  void begin(int p) {                                             // set the button up
    pin = p;                                                      // remember the pin
    pinMode(pin, INPUT_PULLUP);                                   // input with the internal pull-up: pressed = LOW
  }                                                               // end of begin

  BtnEvent poll() {                                               // call this often; it returns an event or BTN_NONE
    bool r = (digitalRead(pin) == LOW);                           // pressed when the pin is pulled to GND
    uint32_t now = millis();                                      // current time
    if (r != raw) {                                               // the reading changed
      raw = r;                                                    // remember the new reading
      tChange = now;                                              // and when it changed
    }                                                             // end of "reading changed"
    if (now - tChange < DEBOUNCE_MS) return BTN_NONE;             // still bouncing: ignore for now
    if (r && !down) {                                             // a new stable press
      down = true;                                                // accept it
      longFired = false;                                          // the long press was not reported yet
      tDown = now;                                                // remember when it began
      return BTN_NONE;                                            // report later, when we know short or long
    }                                                             // end of "new press"
    if (r && down && !longFired && now - tDown >= LONG_PRESS_MS) { // still held for long enough
      longFired = true;                                           // report the long press only once
      return BTN_LONG;                                            // tell the caller
    }                                                             // end of "long press"
    if (!r && down) {                                             // the button was released
      down = false;                                               // the press is over
      if (!longFired) return BTN_SHORT;                           // it was a short press (no long press reported)
    }                                                             // end of "released"
    return BTN_NONE;                                              // nothing to report
  }                                                               // end of poll
};                                                                // end of Button

Button btnSession;                                                // button 1: start / stop the session
Button btnMute;                                                   // button 2: mute / unmute the buzzer

// ------------------------------ TIME HELPERS -------------------------------
void fmtDate(const DateTime& d, char* out, size_t n) {            // writes "YYYY-MM-DD" into out
  snprintf(out, n, "%04d-%02d-%02d", d.year(), d.month(), d.day()); // build the text from the date parts
}                                                                 // end of fmtDate

void fmtTime(const DateTime& d, char* out, size_t n) {            // writes "HH:MM:SS" into out
  snprintf(out, n, "%02d:%02d:%02d", d.hour(), d.minute(), d.second()); // build the text from the time parts
}                                                                 // end of fmtTime

// ------------------------------ MICROSD CARD -------------------------------
bool mountSd() {                                                  // (re)starts the microSD card
  SPI.begin(PIN_SD_SCK, PIN_SD_MISO, PIN_SD_MOSI, PIN_SD_CS);     // start the SPI bus on our own pins
  sdOk = SD.begin(PIN_SD_CS, SPI);                                // try to mount the card (FAT32)
  return sdOk;                                                    // tell the caller if it worked
}                                                                 // end of mountSd

// Adds one line of text at the end of a file (creates the file if it does not exist).
bool appendLine(const char* path, const char* text) {             // returns true on success
  File f = SD.open(path, FILE_APPEND);                            // open for appending (FILE_WRITE would erase the file)
  if (!f) return false;                                           // could not open: card removed or full
  size_t w = f.println(text);                                     // write the text plus a line break
  f.close();                                                      // close the file so the data is really saved
  return w > 0;                                                   // success if at least one byte was written
}                                                                 // end of appendLine

// Reads /students.csv into the "students" list. Returns how many students were loaded.
size_t loadStudents() {                                           // called at start-up and by the RELOAD command
  students.clear();                                               // forget the old list
  File f = SD.open(FILE_STUDENTS, FILE_READ);                     // open the student list for reading
  if (!f) return 0;                                               // file missing: no students
  char line[96];                                                  // buffer that holds one line of text
  size_t n = 0;                                                   // how many characters are in the buffer
  while (f.available()) {                                         // until the end of the file
    int c = f.read();                                             // read one character
    if (c < 0) break;                                             // read error: stop
    if (c == '\n' || n >= sizeof(line) - 1) {                     // end of a line (or the line is too long)
      line[n] = 0;                                                // close the text
      n = 0;                                                      // start a new line
      StudentRec s;                                               // place for the result
      if (parseStudentLine(line, s) && students.size() < MAX_STUDENTS) students.push_back(s); // keep valid lines
      if (c != '\n') {                                            // the line was too long
        while (f.available()) {                                   // skip the rest of that line
          int d = f.read();                                       // read the next character
          if (d == '\n' || d < 0) break;                          // stop at the line end
        }                                                         // end of skipping
      }                                                           // end of "too long"
    } else {                                                      // a normal character
      line[n++] = (char)c;                                        // add it to the buffer
    }                                                             // end of the if/else
  }                                                               // end of the file loop
  if (n > 0) {                                                    // the last line had no line break
    line[n] = 0;                                                  // close the text
    StudentRec s;                                                 // place for the result
    if (parseStudentLine(line, s) && students.size() < MAX_STUDENTS) students.push_back(s); // keep it if valid
  }                                                               // end of "last line"
  f.close();                                                      // close the file
  return students.size();                                         // report how many students we have
}                                                                 // end of loadStudents

const StudentRec* findStudent(uint64_t id) {                      // returns the student with this card, or nullptr
  for (const StudentRec& s : students) {                          // look at every student
    if (s.id == id) return &s;                                    // found: give back a pointer to the record
  }                                                               // end of the loop
  return nullptr;                                                 // not found: unknown card
}                                                                 // end of findStudent

bool alreadySeen(uint64_t id) {                                   // true if this card was already tapped in this session
  for (uint64_t v : seen) {                                       // look at every card tapped so far
    if (v == id) return true;                                     // same card found
  }                                                               // end of the loop
  return false;                                                   // new card
}                                                                 // end of alreadySeen

// ------------------------------ SESSIONS -----------------------------------
bool startSession() {                                             // begins a new lecture session; returns true on success
  if (sessionActive) return true;                                 // already running: nothing to do
  if (driveMode) {                                                // the PC owns the SD card in drive mode
    Serial.println("Drive mode is on: hold button 2 (or type REBOOT) to leave it first."); // explain
    startPattern(P_ERROR);                                        // signal the error
    return false;                                                 // failed
  }                                                               // end of the drive-mode check
  if (!rtcOk || !sdOk) {                                          // we need the clock (for time stamps) and the card (for files)
    Serial.println("Cannot start: clock or SD card not ready. Type STATUS."); // tell the PC user why
    startPattern(P_ERROR);                                        // tell the lecturer with LEDs and buzzer
    return false;                                                 // failed
  }                                                               // end of the readiness check
  if (!SD.exists(DIR_ATTENDANCE) && !SD.mkdir(DIR_ATTENDANCE)) {  // make sure the /attendance folder exists
    Serial.println("Cannot create the /attendance folder.");      // explain the failure
    startPattern(P_ERROR);                                        // signal the error
    return false;                                                 // failed
  }                                                               // end of the folder check
  DateTime now = rtc.now();                                       // read the current date and time
  snprintf(sessionPath, sizeof(sessionPath), "%s/%04d%02d%02d_%02d%02d%02d.csv", DIR_ATTENDANCE, // file name = date and time
           now.year(), now.month(), now.day(), now.hour(), now.minute(), now.second()); // e.g. /attendance/20261025_143012.csv
  if (!appendLine(sessionPath, "uid,name,date,time,result")) {    // create the file with its header line
    Serial.println("Cannot create the session file.");            // explain the failure
    sdOk = false;                                                 // the card is not working
    startPattern(P_ERROR);                                        // signal the error
    return false;                                                 // failed
  }                                                               // end of the file creation check
  seen.clear();                                                   // nobody has tapped yet
  presentCount = 0;                                               // reset the counters
  unknownCount = 0;                                               // reset the counters
  lastUid = 0;                                                    // forget the last card so the first tap is never ignored
  lastLine[0] = 0;                                                // clear the "last tap" text
  sessionActive = true;                                           // the session is now running
  Serial.printf("SESSION START -> %s\n", sessionPath);            // report on the serial monitor
  startPattern(P_START);                                          // beep and blink for the lecturer
  return true;                                                    // success
}                                                                 // end of startSession

void stopSession() {                                              // ends the current session
  if (!sessionActive) return;                                     // nothing to stop
  char d[11];                                                     // room for "YYYY-MM-DD" plus '\0'
  char t[9];                                                      // room for "HH:MM:SS" plus '\0'
  DateTime now = rtc.now();                                       // current date and time
  fmtDate(now, d, sizeof(d));                                     // date as text
  fmtTime(now, t, sizeof(t));                                     // time as text
  char line[96];                                                  // buffer for the summary line
  snprintf(line, sizeof(line), "# end,%s,%s,present=%u,unknown=%u", d, t, (unsigned)presentCount, (unsigned)unknownCount); // summary
  appendLine(sessionPath, line);                                  // add it to the file (starts with # so it is easy to ignore)
  sessionActive = false;                                          // the session is over
  Serial.printf("SESSION STOP: present=%u unknown=%u file=%s\n", (unsigned)presentCount, (unsigned)unknownCount, sessionPath); // report
  startPattern(P_STOP);                                           // tell the lecturer
}                                                                 // end of stopSession

// Called every time a NEW card is read by the reader.
void handleTap(const char* uidStr, uint64_t id) {                 // uidStr = card as text, id = card as number
  if (!sessionActive) {                                           // nobody started a session
    Serial.printf("TAP %s ignored: no session (press button 1 or type START)\n", uidStr); // explain on the PC
    startPattern(P_NOSESSION);                                    // tell the student with red LED and beeps
    return;                                                       // nothing else to do
  }                                                               // end of "no session"
  if (alreadySeen(id)) {                                          // this card was already counted in this session
    Serial.printf("TAP %s DUPLICATE\n", uidStr);                  // report on the PC
    startPattern(P_DUP);                                          // double red blink + double beep
    return;                                                       // do not write it again
  }                                                               // end of "duplicate"
  if (seen.size() >= MAX_SEEN) {                                  // safety limit for memory
    Serial.println("Session is full.");                           // report
    startPattern(P_ERROR);                                        // signal
    return;                                                       // stop here
  }                                                               // end of "session full"
  const StudentRec* st = findStudent(id);                         // look the card up in the student list
  DateTime now = rtc.now();                                       // time of this tap
  char d[11];                                                     // date text
  char t[9];                                                      // time text
  fmtDate(now, d, sizeof(d));                                     // fill the date text
  fmtTime(now, t, sizeof(t));                                     // fill the time text
  char line[112];                                                 // one line of the CSV file
  snprintf(line, sizeof(line), "%s,%s,%s,%s,%s", uidStr, st ? st->name : "UNKNOWN", d, t, st ? "PRESENT" : "UNKNOWN"); // build it
  if (!appendLine(sessionPath, line)) {                           // write the line to the card
    Serial.println("SD write failed. Check the card, then type INIT."); // explain
    sdOk = false;                                                 // mark the card as not working
    startPattern(P_ERROR);                                        // signal the error
    return;                                                       // the tap was NOT saved
  }                                                               // end of "write failed"
  seen.push_back(id);                                             // remember the card so a second tap is a duplicate
  if (st) {                                                       // a known student
    presentCount++;                                               // count him or her
    snprintf(lastLine, sizeof(lastLine), "%s", st->name);         // show the name on the OLED
    startPattern(P_OK);                                           // green LED + one beep
  } else {                                                        // an unknown card
    unknownCount++;                                               // count it separately
    snprintf(lastLine, sizeof(lastLine), "? %s", uidStr);         // show "? UID" on the OLED
    startPattern(P_UNKNOWN);                                      // long red LED + long beep
  }                                                               // end of known/unknown
  Serial.printf("TAP %s | %s | %s %s\n", uidStr, st ? st->name : "UNKNOWN", d, t); // report on the PC
}                                                                 // end of handleTap

// ------------------------------ I2C HELPER ---------------------------------
bool i2cPresent(uint8_t addr) {                                   // true if a device answers at this I2C address
  Wire.beginTransmission(addr);                                   // start talking to the address
  return Wire.endTransmission() == 0;                             // 0 = a device acknowledged, so it is really there
}                                                                 // end of i2cPresent

// ------------------------------ RESTART ------------------------------------
void rebootNow() {                                                // restarts the ESP32 (this is also how drive mode is left)
  Serial.println("Restarting...");                                // tell the PC
  Serial.flush();                                                 // wait until the text has really been sent
  delay(200);                                                     // short pause so the message is not cut
  ESP.restart();                                                  // software reset: the ESP32 starts again from setup()
}                                                                 // end of rebootNow

// ------------------------------ USB DRIVE MODE -----------------------------
#if USE_DRIVE_MODE                                                // real drive mode code, only if enabled
uint32_t mscSectorSize = 512;                                     // bytes per SD sector (read from the card when drive mode starts)

// The PC asks for data: read sectors from the SD card and hand them over.
static int32_t onMscRead(uint32_t lba, uint32_t offset, void* buffer, uint32_t bufsize) { // lba = first sector number
  uint32_t first = lba + offset / mscSectorSize;                  // first sector to read (offset is normally 0)
  uint32_t count = bufsize / mscSectorSize;                       // how many whole sectors the PC wants
  uint8_t* out = (uint8_t*)buffer;                                // where to put the data
  for (uint32_t i = 0; i < count; i++) {                          // one sector at a time
    if (!SD.readRAW(out + i * mscSectorSize, first + i)) return -1; // raw read failed: tell the PC it is an error
  }                                                               // end of the loop
  return (int32_t)(count * mscSectorSize);                        // number of bytes delivered
}                                                                 // end of onMscRead

// The PC sends data (copy, delete, edit a file): write the sectors to the SD card.
static int32_t onMscWrite(uint32_t lba, uint32_t offset, uint8_t* buffer, uint32_t bufsize) { // lba = first sector number
  uint32_t first = lba + offset / mscSectorSize;                  // first sector to write
  uint32_t count = bufsize / mscSectorSize;                       // how many whole sectors
  for (uint32_t i = 0; i < count; i++) {                          // one sector at a time
    if (!SD.writeRAW(buffer + i * mscSectorSize, first + i)) return -1; // raw write failed: tell the PC
  }                                                               // end of the loop
  return (int32_t)(count * mscSectorSize);                        // number of bytes written
}                                                                 // end of onMscWrite

// The PC sends start/stop/eject commands (for example when you click "Eject").
static bool onMscStartStop(uint8_t power_condition, bool start, bool load_eject) { // called by the USB task
  (void)power_condition;                                          // not needed here
  if (load_eject && !start) mscEjected = true;                    // the PC ejected the drive: it is safe to leave drive mode
  if (load_eject && start) mscEjected = false;                    // the drive was loaded again
  return true;                                                    // accept the command
}                                                                 // end of onMscStartStop

bool startDriveMode() {                                           // makes the SD card appear as a USB drive on the PC
  if (driveMode) return true;                                     // already in drive mode
  if (sessionActive) {                                            // never interrupt a running lecture by accident
    Serial.println("Stop the session first (hold button 1), then enter drive mode."); // explain
    startPattern(P_ERROR);                                        // signal the error
    return false;                                                 // failed
  }                                                               // end of the session check
  if (!sdOk) {                                                    // no card, nothing to show
    Serial.println("No SD card: nothing to show as a drive.");    // explain
    startPattern(P_ERROR);                                        // signal the error
    return false;                                                 // failed
  }                                                               // end of the card check
  size_t sectors = SD.numSectors();                               // how many sectors the card has
  mscSectorSize = (uint32_t)SD.sectorSize();                      // how big one sector is (normally 512 bytes)
  if (sectors == 0 || mscSectorSize == 0) {                       // the card did not report its size
    Serial.println("Cannot read the card size.");                 // explain
    startPattern(P_ERROR);                                        // signal the error
    return false;                                                 // failed
  }                                                               // end of the size check
  mscEjected = false;                                             // not ejected yet
  USB.manufacturerName("ice");                                    // name shown by the PC for the USB device
  USB.productName("Smart Attendance");                            // product name shown by the PC
  msc.vendorID("ATTEND");                                         // short vendor text of the drive (max 8 characters)
  msc.productID("SD card");                                       // product text of the drive (max 16 characters)
  msc.productRevision("1.0");                                     // version text (max 4 characters)
  msc.onRead(onMscRead);                                          // tell the USB driver how to read the card
  msc.onWrite(onMscWrite);                                        // ... how to write the card
  msc.onStartStop(onMscStartStop);                                // ... what to do on eject
  msc.mediaPresent(true);                                         // the "disk" is inserted
  if (!msc.begin((uint32_t)sectors, (uint16_t)mscSectorSize)) {   // create the drive with the size of the SD card
    Serial.println("USB drive could not be created.");            // explain
    startPattern(P_ERROR);                                        // signal the error
    return false;                                                 // failed
  }                                                               // end of the create check
  USB.begin();                                                    // switch the native USB-C port on: the PC now sees the drive
  driveMode = true;                                               // from now on the firmware leaves the SD card alone
  Serial.println("DRIVE MODE: plug a USB cable into the NATIVE USB-C port. Eject the drive on the PC, then hold button 2 to leave."); // instructions
  startPattern(P_DRIVE);                                          // blink and beep
  return true;                                                    // success
}                                                                 // end of startDriveMode
#else                                                             // drive mode disabled in config.h or platformio.ini
bool startDriveMode() {                                           // placeholder so the rest of the code still compiles
  Serial.println("Drive mode is not built in (USE_DRIVE_MODE is 0)."); // explain
  startPattern(P_ERROR);                                          // signal
  return false;                                                   // failed
}                                                                 // end of placeholder
#endif                                                            // end of the drive mode block

// ------------------------------ OLED SCREEN --------------------------------
#if USE_OLED                                                      // all OLED drawing code exists only if enabled
void drawDriveScreen() {                                          // OLED text shown during drive mode
  oled.clearDisplay();                                            // erase the screen buffer
  oled.setTextSize(1);                                            // smallest text: 21 characters per line
  oled.setTextColor(SSD1306_WHITE);                               // white pixels on black
  oled.setCursor(0, 0);                                           // top line
  oled.print("USB DRIVE MODE");                                   // title
  oled.setCursor(0, 12);                                          // second line
  oled.print("Use the native USB-C");                             // tell the user which port
  oled.setCursor(0, 22);                                          // third line
  oled.print("port to see the files");                            // continued
  oled.setCursor(0, 36);                                          // fifth line
  oled.print(mscEjected ? "Ejected: safe to exit" : "Eject on the PC first"); // safety hint, changes after the eject
  oled.setCursor(0, 50);                                          // last line
  oled.print("Hold button 2 to exit");                            // how to leave
  oled.display();                                                 // send the buffer to the screen
}                                                                 // end of drawDriveScreen
uint32_t lastDraw = 0;                                            // time of the last screen refresh
void drawScreen() {                                               // redraws the OLED twice per second
  if (!oledOk || millis() - lastDraw < 500) return;               // no OLED, or it was refreshed less than 0.5 s ago
  lastDraw = millis();                                            // remember this refresh
  if (driveMode) { drawDriveScreen(); return; }                   // drive mode has its own screen
  char d[11] = "----------";                                      // date text (dashes if the clock is not ready)
  char t[9] = "--:--:--";                                         // time text (dashes if the clock is not ready)
  if (rtcOk) {                                                    // the clock works
    DateTime now = rtc.now();                                     // read it
    fmtDate(now, d, sizeof(d));                                   // fill the date text
    fmtTime(now, t, sizeof(t));                                   // fill the time text
  }                                                               // end of "clock works"
  char buf[32];                                                   // buffer for lines with numbers
  oled.clearDisplay();                                            // erase the screen buffer
  oled.setTextSize(1);                                            // smallest text: 21 characters per line
  oled.setTextColor(SSD1306_WHITE);                               // white pixels on black
  oled.setCursor(0, 0);                                           // top line
  oled.print("SMART ATTENDANCE");                                 // title
  oled.setCursor(0, 10);                                          // second line
  oled.print(sessionActive ? "SESSION: ACTIVE" : "READY: btn1=start"); // state
  oled.setCursor(0, 20);                                          // third line
  snprintf(buf, sizeof(buf), "%s %s", d, t);                      // date and time in one text
  oled.print(buf);                                                // show it
  oled.setCursor(0, 30);                                          // fourth line
  snprintf(buf, sizeof(buf), "Present:%u Unk:%u", (unsigned)presentCount, (unsigned)unknownCount); // counters
  oled.print(buf);                                                // show them
  oled.setCursor(0, 40);                                          // fifth line
  oled.print(lastLine);                                           // name (or UID) of the last tap
  oled.setCursor(0, 50);                                          // sixth line
  snprintf(buf, sizeof(buf), "SD:%s RTC:%s%s", sdOk ? "OK" : "ERR", rtcOk ? "OK" : "ERR", muted ? " MUTE" : ""); // health flags
  oled.print(buf);                                                // show them
  oled.display();                                                 // send the buffer to the screen
}                                                                 // end of drawScreen
#else                                                             // OLED disabled: provide an empty function
void drawScreen() {}                                              // so the rest of the code can still call it
#endif                                                            // end of the OLED block

// ------------------------- SERIAL COMMANDS (PC) -----------------------------
void printHelp() {                                                // lists the commands on the serial monitor
  Serial.println("Commands (type then press Enter):");            // heading
  Serial.println("  HELP                         this list");     // each line explains one command
  Serial.println("  STATUS                       clock, SD card, students, session");
  Serial.println("  TIME                         show the clock");
  Serial.println("  SETTIME YYYY-MM-DD HH:MM:SS  set the clock");
  Serial.println("  START / STOP                 start or stop a session");
  Serial.println("  LIST                         list attendance files on the card");
  Serial.println("  DUMP <file>                  print one attendance file (name from LIST)");
  Serial.println("  STUDENTS                     show the first students loaded");
  Serial.println("  RELOAD                       read /students.csv again");
  Serial.println("  INIT                         restart the SD card after a problem");
  Serial.println("  MUTE                         mute or unmute the buzzer");
  Serial.println("  DRIVE                        show the SD card as a USB drive (native USB-C port)");
  Serial.println("  REBOOT                       restart (also leaves drive mode)");
}                                                                 // end of printHelp

void printStatus() {                                              // prints the health of the system
  Serial.printf("Clock: %s | SD card: %s | Students: %u | Session: %s | Buzzer: %s\n", // one summary line
                rtcOk ? "OK" : "NOT READY", sdOk ? "OK" : "NOT READY", (unsigned)students.size(), // values
                sessionActive ? "ACTIVE" : "stopped", muted ? "muted" : "on"); // more values
  Serial.printf("Drive mode: %s\n", driveMode ? "ON" : "off"); // also show whether the SD card belongs to the PC
}                                                                 // end of printStatus

void printTime() {                                                // prints the clock
  if (!rtcOk) { Serial.println("Clock not ready. Use SETTIME YYYY-MM-DD HH:MM:SS"); return; } // clock missing or lost power
  DateTime now = rtc.now();                                       // read the clock
  char d[11];                                                     // date text
  char t[9];                                                      // time text
  fmtDate(now, d, sizeof(d));                                     // fill the date text
  fmtTime(now, t, sizeof(t));                                     // fill the time text
  Serial.printf("%s %s\n", d, t);                                 // print them
}                                                                 // end of printTime

void cmdSetTime(const char* arg) {                                // sets the DS3231 from "YYYY-MM-DD HH:MM:SS"
  int y, mo, d, h, mi, s;                                         // the six numbers we read
  if (!arg || sscanf(arg, "%d-%d-%d %d:%d:%d", &y, &mo, &d, &h, &mi, &s) != 6) { // must find exactly six numbers
    Serial.println("Usage: SETTIME 2026-10-25 14:30:00");         // show the right form
    return;                                                       // stop
  }                                                               // end of the format check
  if (y < 2024 || y > 2099 || mo < 1 || mo > 12 || d < 1 || d > 31 || h < 0 || h > 23 || mi < 0 || mi > 59 || s < 0 || s > 59) { // sanity check
    Serial.println("Those numbers are not a valid date and time."); // explain
    return;                                                       // stop
  }                                                               // end of the range check
  rtc.adjust(DateTime(y, mo, d, h, mi, s));                       // write the new time into the DS3231
  rtcOk = true;                                                   // the clock is valid again
  Serial.print("Clock set to ");                                  // confirm
  printTime();                                                    // by printing the clock
}                                                                 // end of cmdSetTime

void listFiles() {                                                // lists the session files on the card
  if (!sdOk) { Serial.println("SD card not ready."); return; }    // nothing to list without a card
  File dir = SD.open(DIR_ATTENDANCE);                             // open the attendance folder
  if (!dir || !dir.isDirectory()) { Serial.println("No sessions yet."); return; } // folder does not exist yet
  int count = 0;                                                  // number of files shown
  File f = dir.openNextFile();                                    // first entry of the folder
  while (f) {                                                     // until there are no more entries
    if (!f.isDirectory()) {                                       // only real files, not sub-folders
      Serial.printf("%s  (%u bytes)\n", f.name(), (unsigned)f.size()); // name and size
      count++;                                                    // count it
    }                                                             // end of "real file"
    f = dir.openNextFile();                                       // next entry
  }                                                               // end of the loop
  dir.close();                                                    // close the folder
  Serial.printf("%d file(s)\n", count);                           // summary
}                                                                 // end of listFiles

void dumpFile(const char* name) {                                 // prints one session file to the serial monitor
  if (!sdOk) { Serial.println("SD card not ready."); return; }    // need a working card
  if (!name || !*name || strchr(name, '/') || strstr(name, "..")) { // refuse empty names and attempts to leave the folder
    Serial.println("Usage: DUMP <file name shown by LIST>");      // show the right form
    return;                                                       // stop
  }                                                               // end of the name check
  char path[96];                                                  // full path buffer
  snprintf(path, sizeof(path), "%s/%s", DIR_ATTENDANCE, name);    // /attendance/<name>
  File f = SD.open(path, FILE_READ);                              // open it for reading
  if (!f) { Serial.println("File not found."); return; }          // wrong name
  Serial.printf("----- %s -----\n", name);                        // start marker (copy the lines below it)
  uint8_t buf[128];                                               // read 128 bytes at a time
  while (f.available()) {                                         // until the end of the file
    int n = f.read(buf, sizeof(buf));                             // read a block
    if (n <= 0) break;                                            // nothing more
    Serial.write(buf, (size_t)n);                                 // send the block to the PC
  }                                                               // end of the loop
  f.close();                                                      // close the file
  Serial.println("----- end -----");                              // end marker
}                                                                 // end of dumpFile

void showStudents() {                                             // prints the first 20 students
  Serial.printf("%u students loaded\n", (unsigned)students.size()); // how many
  size_t shown = students.size() < 20 ? students.size() : 20;     // show at most 20
  for (size_t i = 0; i < shown; i++) {                            // for each of them
    char uid[11];                                                 // card text
    uint64_t v = students[i].id;                                  // card number
    for (int k = 9; k >= 0; k--) {                                // convert the number back to 10 hex characters
      uid[k] = "0123456789ABCDEF"[v & 0xF];                       // lowest 4 bits -> one hex character
      v >>= 4;                                                    // move to the next 4 bits
    }                                                             // end of the conversion
    uid[10] = 0;                                                  // close the text
    Serial.printf("  %s  %s\n", uid, students[i].name);           // print card and name
  }                                                               // end of the loop
}                                                                 // end of showStudents

void toggleMute() {                                               // switches the buzzer on or off
  muted = !muted;                                                 // flip the flag
  Serial.println(muted ? "Buzzer muted" : "Buzzer on");           // tell the PC user
  startPattern(P_MUTE);                                           // both LEDs light briefly as confirmation
}                                                                 // end of toggleMute

void handleCommand(char* line) {                                  // runs one typed command line
  char* arg = strchr(line, ' ');                                  // find the first space: the argument starts after it
  if (arg) {                                                      // there is an argument
    *arg++ = 0;                                                   // end the command word and step to the argument
    while (*arg == ' ') arg++;                                    // skip extra spaces
  }                                                               // end of "there is an argument"
  for (char* p = line; *p; p++) *p = (char)toupper((unsigned char)*p); // commands work in any letter case
  if (driveMode && (!strcmp(line, "START") || !strcmp(line, "STOP") || !strcmp(line, "LIST") || !strcmp(line, "DUMP") || !strcmp(line, "RELOAD") || !strcmp(line, "INIT"))) { // commands that need the SD card
    Serial.println("Not available in drive mode (the PC owns the SD card). Type REBOOT to leave drive mode."); // explain
    return;                                                       // do nothing else
  }                                                               // end of the drive-mode guard
  if (!strcmp(line, "HELP")) printHelp();                         // each branch compares the command word
  else if (!strcmp(line, "STATUS")) printStatus();                // show system health
  else if (!strcmp(line, "TIME")) printTime();                    // show the clock
  else if (!strcmp(line, "SETTIME")) cmdSetTime(arg);             // set the clock
  else if (!strcmp(line, "START")) startSession();                // same as button 1 short press
  else if (!strcmp(line, "STOP")) stopSession();                  // same as button 1 long press
  else if (!strcmp(line, "LIST")) listFiles();                    // list session files
  else if (!strcmp(line, "DUMP")) dumpFile(arg);                  // print one session file
  else if (!strcmp(line, "STUDENTS")) showStudents();             // show the student list
  else if (!strcmp(line, "RELOAD")) { Serial.printf("%u students loaded\n", (unsigned)(sdOk ? loadStudents() : 0)); } // re-read the list
  else if (!strcmp(line, "INIT")) { Serial.println(mountSd() ? "SD card OK" : "SD card FAILED"); } // restart the card
  else if (!strcmp(line, "MUTE")) toggleMute();                   // same as button 2
  else if (!strcmp(line, "DRIVE")) startDriveMode();              // same as a long press of button 2
  else if (!strcmp(line, "REBOOT")) rebootNow();                  // restart the ESP32
  else Serial.println("Unknown command. Type HELP.");             // anything else
}                                                                 // end of handleCommand

char cmdBuf[96];                                                  // the line being typed
size_t cmdLen = 0;                                                // how many characters it has so far

void serialUpdate() {                                             // collects typed characters; runs a command at Enter
  while (Serial.available()) {                                    // while characters are waiting
    char c = (char)Serial.read();                                 // take one
    if (c == '\r' || c == '\n') {                                 // Enter was pressed
      if (cmdLen > 0) {                                           // the line is not empty
        cmdBuf[cmdLen] = 0;                                       // close the text
        cmdLen = 0;                                               // get ready for the next line
        handleCommand(cmdBuf);                                    // run it
      }                                                           // end of "not empty"
    } else if (cmdLen < sizeof(cmdBuf) - 1) {                     // a normal character and there is room
      cmdBuf[cmdLen++] = c;                                       // add it to the line
    }                                                             // end of the if/else
  }                                                               // end of the loop
}                                                                 // end of serialUpdate

// ------------------------------ SETUP (runs once) ---------------------------
void setup() {                                                    // runs once after power-up or reset
  pinMode(PIN_LED_GREEN, OUTPUT);                                 // green LED pin is an output
  pinMode(PIN_LED_RED, OUTPUT);                                   // red LED pin is an output
  pinMode(PIN_BUZZER, OUTPUT);                                    // buzzer transistor pin is an output
  pinMode(PIN_LED_POWER, OUTPUT);                                 // power LED pin is an output
  digitalWrite(PIN_BUZZER, LOW);                                  // buzzer silent at start
  btnSession.begin(PIN_BTN_SESSION);                              // prepare button 1
  btnMute.begin(PIN_BTN_MUTE);                                    // prepare button 2
  Serial.begin(115200);                                           // start the USB serial link to the PC (speed must match platformio.ini)
  delay(1200);                                                    // give the PC time to open the serial monitor
  Serial.println();                                               // empty line
  Serial.println("=== Smart Attendance System ===");              // banner
  Wire.begin(PIN_SDA, PIN_SCL);                                   // start the I2C bus on our two pins
  rtcOk = rtc.begin(&Wire);                                       // look for the DS3231 clock
  if (!rtcOk) {                                                   // not found
    Serial.println("RTC not found: check SDA=GPIO9, SCL=GPIO8 and the 3V3 wire."); // hint
  } else if (rtc.lostPower()) {                                   // found, but its battery was empty or removed
    rtcOk = false;                                                // its time cannot be trusted
    Serial.println("RTC lost power: set it with SETTIME YYYY-MM-DD HH:MM:SS"); // hint
  }                                                               // end of the clock checks
#if USE_OLED                                                      // OLED start-up only if enabled
  uint8_t oledAddr = 0;                                           // 0 = OLED not found yet
  if (i2cPresent(OLED_ADDR)) oledAddr = OLED_ADDR;                // does a device answer at the configured address?
  else if (i2cPresent(OLED_ADDR ^ 0x01)) oledAddr = OLED_ADDR ^ 0x01; // 0x3C <-> 0x3D: many modules use the other address
  if (oledAddr) {                                                 // something answered
    oledOk = oled.begin(SSD1306_SWITCHCAPVCC, oledAddr, true, false); // start the display driver (false = we already started I2C)
    Serial.printf("OLED found at 0x%02X, init %s\n", oledAddr, oledOk ? "OK" : "FAILED"); // report
  } else {                                                        // nothing answered on either address
    Serial.println("OLED not found at 0x3C or 0x3D: check VCC, GND, SDA=GPIO9, SCL=GPIO8."); // hint
  }                                                               // end of the OLED search
  if (oledOk) {                                                   // show a start-up screen so you can see the OLED works
    oled.clearDisplay();                                          // erase the screen buffer
    oled.setTextSize(1);                                          // smallest text
    oled.setTextColor(SSD1306_WHITE);                             // white on black
    oled.setCursor(0, 0);                                         // top line
    oled.print("SMART ATTENDANCE");                               // title
    oled.setCursor(0, 12);                                        // second line
    oled.print("Starting...");                                    // message
    oled.display();                                               // send it to the screen
  }                                                               // end of the start-up screen
#endif                                                            // end of the OLED start-up
  if (mountSd()) {                                                // try the microSD card
    size_t n = loadStudents();                                    // read the student list
    Serial.printf("SD card OK, %u students loaded\n", (unsigned)n); // report
    if (n == 0) Serial.println("Warning: /students.csv is missing or empty."); // hint
  } else {                                                        // card not working
    Serial.println("SD card not found: check wiring and that it is FAT32."); // hint
  }                                                               // end of the card check
  RFID.begin(9600, SERIAL_8N1, PIN_RFID_RX, -1);                  // UART1: 9600 baud, receive on GPIO18, no transmit pin
  printStatus();                                                  // one-line summary of everything
  Serial.println("Type HELP for the list of commands.");          // hint
  startPattern((sdOk && rtcOk) ? P_BOOT : P_ERROR);               // happy beeps if all is fine, error pattern otherwise
}                                                                 // end of setup

// ------------------------------ LOOP (runs forever) ------------------------
void loop() {                                                     // runs again and again, thousands of times per second
  patternUpdate();                                                // keep the LED/buzzer patterns moving
  idleLedUpdate();                                                // show the device state when no pattern plays
  powerLedUpdate();                                               // double blink of the power LED every 3 seconds

  BtnEvent e1 = btnSession.poll();                                // check button 1
  if (e1 == BTN_SHORT) {                                          // short press
    if (!sessionActive) startSession();                           // no session yet: start one
    else Serial.println("Session running. Hold button 1 for 1.5 s to stop it."); // protect against accidental stops
  } else if (e1 == BTN_LONG && sessionActive) {                   // long press while a session runs
    stopSession();                                                // stop it
  }                                                               // end of button 1

  BtnEvent e2 = btnMute.poll();                                   // check button 2
  if (e2 == BTN_SHORT) toggleMute();                              // short press: mute or unmute the buzzer
  else if (e2 == BTN_LONG) {                                      // long press (1.5 s): drive mode on or off
    if (driveMode) rebootNow();                                   // already in drive mode: restart to leave it
    else startDriveMode();                                        // otherwise show the SD card as a USB drive
  }                                                               // end of button 2

  while (RFID.available()) {                                      // while bytes are waiting from the reader
    char uid[11];                                                 // receives the card text
    uint8_t b = (uint8_t)RFID.read();                             // take one byte from the reader
    if (driveMode) continue;                                      // drive mode: ignore cards, the SD card belongs to the PC
    if (rdm.feed(b, uid)) {                                       // feed the byte to the parser; true when a full valid frame arrived
      uint64_t id;                                                // the card as a number
      if (!parseUid10(uid, id)) continue;                         // should not fail; skip if it does
      uint32_t now = millis();                                    // current time
      if (id == lastUid && now - lastSeenMs < SAME_CARD_IGNORE_MS) { // the same card is still on the reader
        lastSeenMs = now;                                         // keep extending the "still there" time
        continue;                                                 // do not count it again
      }                                                           // end of "same card"
      lastUid = id;                                               // remember this card
      lastSeenMs = now;                                           // and when we saw it
      handleTap(uid, id);                                         // process the tap
    }                                                             // end of "valid frame"
  }                                                               // end of the reader loop

  serialUpdate();                                                 // handle commands typed on the PC
  drawScreen();                                                   // refresh the OLED
}                                                                 // end of loop
```


---

## 7. data/students.csv (goes on the microSD card)

One student per line: the 10-character card number, a comma, the name. Lines starting with `#` and the header line are ignored.


```csv
# students.csv - copy this file to the ROOT of the microSD card.
# One student per line:  UID,Name   (the UID is the 10 hex characters that the reader sends)
# Lines that start with # and the header line below are ignored.
uid,name
0A00B2C3D4,Tendai Moyo
0A00B2C3D5,Amina Benali
0A00B2C3D6,Example Student
```


---

## 8. Test sketches D1 to D9

To use one, replace the whole content of `src/main.cpp` with the sketch (keep the full firmware somewhere safe). D1 to D5 and D8 work as they are; D6 and D7 still use the older button pin numbers, so swap them if needed.


### D1: Hello: checks upload, serial link and flash size (should print 16 MB)


```cpp
// D1 - Hello: checks that the ESP32-S3 works, that uploading works and that the flash size is right.
#include <Arduino.h>                                                  // core Arduino functions and Serial

void setup() {                                                        // runs once at power-up
  Serial.begin(115200);                                               // start the USB serial link at 115200 baud
}                                                                     // end of setup

void loop() {                                                         // runs again and again
  Serial.printf("ESP32-S3 OK, flash %u MB\n", (unsigned)(ESP.getFlashChipSize() / (1024 * 1024))); // print the flash size in MB (should be 16)
  delay(1000);                                                        // wait one second between messages
}                                                                     // end of loop
```



### D2: I2C scanner: should find 0x68 (clock) and 0x3C (OLED)


```cpp
// D2 - I2C scanner: lists every device that answers on the I2C bus (SDA = GPIO9, SCL = GPIO8).
#include <Arduino.h>                                                  // core Arduino functions and Serial
#include <Wire.h>                                                     // I2C bus driver

void setup() {                                                        // runs once at power-up
  Serial.begin(115200);                                               // start the USB serial link
  Wire.begin(9, 8);                                                   // start I2C: first number = SDA pin, second = SCL pin
  delay(1500);                                                        // give the serial monitor time to open
}                                                                     // end of setup

void loop() {                                                         // runs again and again
  for (byte a = 1; a < 127; a++) {                                    // try every possible I2C address
    Wire.beginTransmission(a);                                        // start talking to address a
    if (Wire.endTransmission() == 0) Serial.printf("Found 0x%02X\n", a); // 0 means a device answered: print its address
  }                                                                   // end of the address loop
  Serial.println("---");                                              // separator between scans
  delay(3000);                                                        // wait three seconds, then scan again
}                                                                     // end of loop
```



### D3: Set and read the DS3231 clock (delete the adjust line after the first upload)


```cpp
// D3 - Set and read the DS3231 clock. Upload once to set the time, then delete the adjust line.
#include <Arduino.h>                                                  // core Arduino functions and Serial
#include <Wire.h>                                                     // I2C bus driver
#include <RTClib.h>                                                   // DS3231 library

RTC_DS3231 rtc;                                                       // the clock chip object

void setup() {                                                        // runs once at power-up
  Serial.begin(115200);                                               // start the USB serial link
  Wire.begin(9, 8);                                                   // start I2C: SDA = GPIO9, SCL = GPIO8
  if (!rtc.begin(&Wire)) {                                            // look for the clock on the I2C bus
    Serial.println("RTC not found");                                  // report that it did not answer
    while (1) delay(1000);                                            // stop here forever
  }                                                                   // end of "not found"
  rtc.adjust(DateTime(F(__DATE__), F(__TIME__)));                     // set the clock to the moment this sketch was compiled (delete this line after the first upload)
}                                                                     // end of setup

void loop() {                                                         // runs again and again
  DateTime now = rtc.now();                                           // read the clock
  Serial.printf("%04d-%02d-%02d %02d:%02d:%02d\n", now.year(), now.month(), now.day(), now.hour(), now.minute(), now.second()); // print the date and time
  delay(1000);                                                        // once per second
}                                                                     // end of loop
```



### D4: microSD test: writes /test.txt


```cpp
// D4 - microSD test: CS = GPIO10, SCK = GPIO11, MOSI = GPIO12, MISO = GPIO13.
#include <Arduino.h>                                                  // core Arduino functions and Serial
#include <SPI.h>                                                      // SPI bus driver
#include <SD.h>                                                       // microSD library

void setup() {                                                        // runs once at power-up
  Serial.begin(115200);                                               // start the USB serial link
  delay(1500);                                                        // give the serial monitor time to open
  SPI.begin(11, 13, 12, 10);                                          // SPI pins in this order: SCK, MISO, MOSI, CS
  if (!SD.begin(10, SPI)) {                                           // try to mount the card (CS = GPIO10)
    Serial.println("SD FAIL");                                        // report failure
    return;                                                           // nothing more to do
  }                                                                   // end of "mount failed"
  Serial.printf("SD OK, size %llu MB\n", (unsigned long long)(SD.cardSize() / (1024ULL * 1024ULL))); // card size in MB
  File f = SD.open("/test.txt", FILE_WRITE);                          // create (or overwrite) a test file
  f.println("hello");                                                 // write one line into it
  f.close();                                                          // close it so the data is saved
  Serial.println("write done");                                       // report success
}                                                                     // end of setup

void loop() {}                                                        // nothing to repeat
```



### D5: RDM6300 raw bytes: one 14-byte line per tap


```cpp
// D5 - RDM6300 raw test: prints the bytes the reader sends (reader TX -> GPIO18, 9600 baud).
#include <Arduino.h>                                                  // core Arduino functions and Serial

HardwareSerial RFID(1);                                               // use hardware UART number 1 for the reader

void setup() {                                                        // runs once at power-up
  Serial.begin(115200);                                               // USB serial link to the PC
  RFID.begin(9600, SERIAL_8N1, 18, -1);                               // reader link: 9600 baud, receive on GPIO18, no transmit pin
}                                                                     // end of setup

void loop() {                                                         // runs again and again
  while (RFID.available()) {                                          // while bytes are waiting from the reader
    int c = RFID.read();                                              // take one byte
    Serial.printf("%02X ", c);                                        // print it as two hex digits
    if (c == 0x03) Serial.println();                                  // 0x03 ends a frame: start a new line
  }                                                                   // end of the loop
}                                                                     // end of loop
```



### D6: LEDs, buzzer and buttons (uses the older pins: GPIO41 = button 1, GPIO40 = button 2, so swap them if you keep your new numbering)


```cpp
// D6 - LEDs, buzzer and buttons test (green = GPIO1, red = GPIO2, buzzer = GPIO42, buttons = GPIO41 and GPIO40).
#include <Arduino.h>                                                  // core Arduino functions

const int GREEN = 1, RED = 2, BUZ = 42, B1 = 41, B2 = 40;             // pin numbers of the parts

void beep(int ms) {                                                   // sounds the buzzer for ms milliseconds
  digitalWrite(BUZ, HIGH);                                            // transistor on, buzzer sounds
  delay(ms);                                                          // wait
  digitalWrite(BUZ, LOW);                                             // transistor off, buzzer silent
}                                                                     // end of beep

void setup() {                                                        // runs once at power-up
  pinMode(GREEN, OUTPUT);                                             // green LED pin is an output
  pinMode(RED, OUTPUT);                                               // red LED pin is an output
  pinMode(BUZ, OUTPUT);                                               // buzzer pin is an output
  pinMode(B1, INPUT_PULLUP);                                          // button 1 pin is an input with pull-up
  pinMode(B2, INPUT_PULLUP);                                          // button 2 pin is an input with pull-up
}                                                                     // end of setup

void loop() {                                                         // runs again and again
  if (digitalRead(B1) == LOW) {                                       // button 1 pressed (pulled to GND)
    digitalWrite(GREEN, HIGH);                                        // green LED stays on
    beep(150);                                                        // one beep
    delay(200);                                                       // small pause
    return;                                                           // start the loop again
  }                                                                   // end of button 1
  if (digitalRead(B2) == LOW) {                                       // button 2 pressed
    digitalWrite(RED, HIGH);                                          // red LED stays on
    beep(100);                                                        // first beep
    delay(100);                                                       // pause
    beep(100);                                                        // second beep
    delay(200);                                                       // small pause
    return;                                                           // start the loop again
  }                                                                   // end of button 2
  digitalWrite(GREEN, HIGH);                                          // no button: green LED on
  delay(300);                                                         // for 0.3 s
  digitalWrite(GREEN, LOW);                                           // green LED off
  digitalWrite(RED, HIGH);                                            // red LED on
  delay(300);                                                         // for 0.3 s
  digitalWrite(RED, LOW);                                             // red LED off
}                                                                     // end of loop
```



### D7: Card read with LED and buzzer feedback (no PC needed)


```cpp
// D7 - Card read with LED and buzzer feedback (works without the PC: GPIO1 green LED, GPIO42 buzzer).
#include <Arduino.h>                                                  // core Arduino functions

HardwareSerial RFID(1);                                               // UART1 for the reader
const int GREEN = 1, BUZ = 42;                                        // feedback pins

void setup() {                                                        // runs once at power-up
  pinMode(GREEN, OUTPUT);                                             // green LED pin is an output
  pinMode(BUZ, OUTPUT);                                               // buzzer pin is an output
  RFID.begin(9600, SERIAL_8N1, 18, -1);                               // reader on GPIO18, 9600 baud, no transmit pin
}                                                                     // end of setup

void loop() {                                                         // runs again and again
  if (RFID.available()) {                                             // the reader sent something: a card is on it
    while (RFID.available()) RFID.read();                             // empty the receive buffer
    digitalWrite(GREEN, HIGH);                                        // green LED on
    digitalWrite(BUZ, HIGH);                                          // buzzer on
    delay(150);                                                       // beep for 0.15 s
    digitalWrite(BUZ, LOW);                                           // buzzer off
    delay(350);                                                       // keep the LED on a little longer
    digitalWrite(GREEN, LOW);                                         // green LED off
    while (RFID.available()) RFID.read();                             // drop the repeats sent while the card stayed on the coil
  }                                                                   // end of "card present"
}                                                                     // end of loop
```



### D8: Measure the RDM6300 TX level through the divider


```cpp
// D8 - Measures the voltage at the divider joint (RDM6300 TX -> 2.2k -> joint -> 3.3k -> GND, joint -> GPIO18).
#include <Arduino.h>                                                  // core Arduino functions and Serial

void setup() {                                                        // runs once at power-up
  Serial.begin(115200);                                               // USB serial link
  delay(1500);                                                        // give the serial monitor time to open
  analogSetPinAttenuation(18, ADC_11db);                              // let the ADC measure up to about 3.1 V on GPIO18
}                                                                     // end of setup

void loop() {                                                         // runs again and again
  Serial.printf("GPIO18: %u mV\n", (unsigned)analogReadMilliVolts(18)); // ~3000 mV = 5 V TX, ~2000 mV = 3.3 V TX (keep cards away)
  delay(500);                                                         // twice per second
}                                                                     // end of loop
```



### D9: OLED test: finds the display and draws a frame and text


```cpp
// D9 - OLED test: finds the OLED on the I2C bus (0x3C or 0x3D), then draws a frame and some text.
#include <Arduino.h>                                                  // core Arduino functions and Serial
#include <Wire.h>                                                     // I2C bus driver
#include <Adafruit_GFX.h>                                             // graphics library used by the OLED driver
#include <Adafruit_SSD1306.h>                                         // driver of the SSD1306 OLED

Adafruit_SSD1306 oled(128, 64, &Wire, -1);                            // 128x64 OLED on the I2C bus, no reset pin (use 32 instead of 64 for a 128x32 OLED)

bool present(uint8_t addr) {                                          // true if a device answers at this address
  Wire.beginTransmission(addr);                                       // start talking to the address
  return Wire.endTransmission() == 0;                                 // 0 = a device acknowledged
}                                                                     // end of present

void setup() {                                                        // runs once at power-up
  Serial.begin(115200);                                               // serial link to the PC
  Wire.begin(9, 8);                                                   // start I2C: SDA = GPIO9, SCL = GPIO8
  delay(1500);                                                        // give the serial monitor time to open
  uint8_t addr = present(0x3C) ? 0x3C : (present(0x3D) ? 0x3D : 0);   // look for the OLED at its two possible addresses
  if (!addr) {                                                        // nothing answered
    Serial.println("No OLED at 0x3C or 0x3D. Check VCC (3V3), GND, SDA (GPIO9), SCL (GPIO8)."); // explain
    return;                                                           // nothing more to do
  }                                                                   // end of "not found"
  Serial.printf("OLED found at 0x%02X\n", addr);                      // report the address
  if (!oled.begin(SSD1306_SWITCHCAPVCC, addr, true, false)) {         // start the driver (false = I2C already started)
    Serial.println("OLED init failed");                               // report
    return;                                                           // nothing more to do
  }                                                                   // end of "init failed"
  oled.clearDisplay();                                                // erase the screen buffer
  oled.drawRect(0, 0, 128, 64, SSD1306_WHITE);                        // draw a frame around the whole screen: shows the real size
  oled.setTextSize(1);                                                // smallest text
  oled.setTextColor(SSD1306_WHITE);                                   // white on black
  oled.setCursor(8, 10);                                              // position of the first line
  oled.print("OLED works!");                                          // first line
  oled.setCursor(8, 28);                                              // position of the second line
  oled.printf("Address 0x%02X", addr);                                // second line: the I2C address
  oled.display();                                                     // send the buffer to the screen
}                                                                     // end of setup

void loop() {}                                                        // nothing to repeat
```



---

## 9. The PC test of the parsers: what it is and why

**What "parsers" are.** A parser turns raw input into something meaningful. This project has three, all in `parsers.h`:
- `Rdm6300Parser` takes the bytes coming from the reader and recognises a complete, correct card frame (start marker, 10 hex characters, checksum, end marker).
- `parseUid10` turns the text `0A00B2C3D4` into a number.
- `parseStudentLine` reads one line `UID,Name` of `students.csv`.

**Why they can be tested on a PC.** They contain only plain C++ (text, numbers, arrays). They never touch pins, the SD card, I2C or USB. So the same code compiles with `g++` on your computer, where it can be run in a fraction of a second.

**What `test_parsers.cpp` is.** A small program that feeds the parsers known inputs and checks the results, printing PASS or FAIL for each (a "unit test"). It is not part of the firmware: `pio run` ignores the `test` folder.

**What it checks (10 checks):**
1. A valid frame is accepted and the card number is decoded correctly.
2. A frame with a wrong checksum is rejected.
3. After noise and a broken start, the parser recovers and reads the next good frame.
4. `parseUid10` accepts exactly 10 hex digits, and rejects 9 digits or a non-hex character.
5. A normal student line is read (spaces and Windows line ends are handled).
6. The header line and `#` comment lines are skipped.
7. A comma inside a name is replaced by a space, so it cannot break the CSV file.

**Why bother.**
- A wrong decode would mean students are marked as someone else or as unknown. This is the part where a small mistake does the most harm, and it is easy to check with certainty.
- Testing on a PC needs no board, no wiring and no upload.
- If you change `parsers.h` later, run the test again and you immediately see whether you broke something.

**What it cannot test.** Anything that needs hardware: pins, I2C, the SD card, USB, timing. Those are checked on the board (the test sketches D1 to D9).

**Run it** from the project folder (needs `g++`):

```bash
g++ -std=c++17 -Iinclude test/host/test_parsers.cpp -o t && ./t
```

Expected last line: `ALL TESTS PASSED`.

---

## 10. What happens when a new card is scanned

1. **The card is energised.** The coil of the RDM6300 makes a 125 kHz field. The card has no battery: the field powers its chip, which sends back its 40-bit number.
2. **The reader sends a frame.** The RDM6300 turns that number into a 14-byte text frame (`0x02`, 10 hex characters, 2 checksum characters, `0x03`) and sends it on its TX wire at 9600 baud. It keeps repeating it while the card stays on the coil.
3. **The ESP32 receives bytes.** UART1 listens on GPIO18. In `loop()` every byte is read and given to `rdm.feed()`.
4. **The parser checks the frame.** It waits for the start marker, collects 14 bytes, checks the end marker, checks that all characters are hex digits, and checks that the checksum matches. A damaged frame is silently thrown away. A good one gives the card number, for example `0A00B2C3D4`.
5. **Same card still on the reader?** If it is the same card as a moment ago (within 1.5 s), it is ignored, so one tap is never counted twice just because the card stays on the reader.
6. **`handleTap()` decides what the tap means,** in this order:
   - **No session running:** tell the student with the red LED and two beeps, write nothing.
   - **Card already tapped in this session:** duplicate, red LED and two beeps, write nothing.
   - **Otherwise:** look the card up in the student list loaded from `/students.csv` (known student, or UNKNOWN).
7. **Time stamp.** The date and time are read from the DS3231.
8. **Write to the SD card.** One line (`uid,name,date,time,result`) is added to the session file `/attendance/YYYYMMDD_HHMMSS.csv`. The file is opened, written and closed each time, so a power cut loses at most the current tap.
9. **Remember and count.** The card is added to the list of cards seen in this session. A known student raises the present counter, an unknown card raises the unknown counter.
10. **Feedback.** Known student: green LED and one beep. Unknown card: long red LED and long beep. The serial monitor prints a `TAP` line, and the OLED shows the counters and the last name within half a second.
11. **If the SD write fails,** the red LED and the beeps signal the error, the card is marked not working, and the tap is not counted. Type `INIT` after checking the card.

---

## 11. USB drive mode

**What it does.** The SD card appears on your computer as a normal USB drive. You can copy the attendance files off it, and you can even edit `students.csv` there.

**How to use it:**
1. Stop any running session (hold button 1). Drive mode refuses to start during a session, so a lecture is never interrupted by accident.
2. **Hold button 2 for 1.5 s** (or type `DRIVE`). Both LEDs flash and the OLED shows "USB DRIVE MODE".
3. Plug a USB cable into the **native USB port** and your computer. The drive appears.
4. Copy what you need. When finished, **eject the drive** on your computer (the OLED then says "Ejected: safe to exit").
5. **Hold button 2 for 1.5 s again** (or type `REBOOT`, or press RST). The board restarts in normal mode.

**What the firmware does and does not do in drive mode.**
- The computer owns the SD card. The firmware does not touch the card's files, ignores card taps, and refuses `START`, `LIST`, `DUMP`, `RELOAD` and `INIT`.
- Leaving drive mode restarts the board, so the firmware always reads the card fresh. That is why changes you made to `students.csv` are used afterwards.
- Never unplug the SD card or the cable while files are being copied.

**How it works inside (short).** The ESP32-S3's native USB port is switched into USB device mode (TinyUSB) and a "mass storage" device is registered. When the computer asks for sector number N, the callback `onMscRead` reads that sector from the card with `SD.readRAW`; `onMscWrite` does the reverse. The computer's own file system driver does the rest.

---

## 12. Reference: buttons, lights, commands, files

### Buttons (pins from your config.h)
| Button | Press | Action |
|---|---|---|
| Button 1 (GPIO40) | Short | Start a session (if none is running) |
| Button 1 | Hold 1.5 s | Stop the session |
| Button 2 (GPIO41) | Short | Mute or unmute the buzzer |
| Button 2 | Hold 1.5 s | Drive mode on (no session running), or off (restart) |

### Lights and sounds
| Situation | Green LED | Red LED | Buzzer |
|---|---|---|---|
| **Power LED (GPIO5), always** | Two fast blinks every 3 s | , | , |
| Ready, no session | Short blink every 2 s | off | off |
| Session running | Steady | off | off |
| Known student counted | On briefly | off | One short beep |
| Same card tapped again (duplicate) | off | Two blinks | Two short beeps |
| Unknown card (logged as UNKNOWN) | off | One long | One long beep |
| Card tapped, no session | off | Two blinks | Two short beeps |
| Session started | Three blinks | off | Three beeps |
| Session stopped | off | Two long | Two long beeps |
| Drive mode on | Both LEDs flash, then they take turns | | Two beeps |
| Fault (no clock or no SD card) | off | Short blink every second | error pattern at start-up |

### Serial commands (115200 baud, UART port)
| Command | What it does |
|---|---|
| `HELP` | List the commands |
| `STATUS` | Clock, SD card, students, session, drive mode |
| `TIME` / `SETTIME YYYY-MM-DD HH:MM:SS` | Show or set the clock |
| `START` / `STOP` | Start or stop a session (same as button 1) |
| `LIST` / `DUMP <file>` | List the session files / print one |
| `STUDENTS` / `RELOAD` | Show the student list / read `/students.csv` again |
| `INIT` | Restart the SD card after a problem |
| `MUTE` | Mute or unmute the buzzer |
| `DRIVE` | Drive mode on (same as holding button 2) |
| `REBOOT` | Restart the board (also leaves drive mode) |

### Files on the microSD card
- `/students.csv`: your student list.
- `/attendance/YYYYMMDD_HHMMSS.csv`: one file per session:

```csv
uid,name,date,time,result
0A00B2C3D4,Tendai Moyo,2026-10-25,14:30:03,PRESENT
0A00FFFFFF,UNKNOWN,2026-10-25,14:30:08,UNKNOWN
# end,2026-10-25,14:30:13,present=1,unknown=1
```

---

## 13. What was tested

On a computer, not on your board:
- The parser checks (section 9) pass, using your own `test_parsers.cpp`.
- The firmware compiles with no warnings in all eight combinations of drive mode on/off, OLED on/off and C++11/C++17, against stand-in libraries. The USB mass-storage part was checked against the function signatures of Espressif's Arduino core 2.0.17 (`USBMSC.h`, `SD.h`, and the official USBMSC example).
- A simulation with a fake reader, clock, SD card and buttons showed: the power LED makes two blinks per 3 s (on at 0 to 80 ms and 160 to 240 ms); sessions, duplicates and unknown cards behave as before; drive mode is refused during a session; in drive mode the read and write callbacks return correct sectors (and an error past the end of the card); cards and SD commands are ignored; the eject is noticed; a long press of button 2 restarts the board.
- `platformio.ini` is read correctly by PlatformIO's parser, and the build stops with a clear message if the USB mode flag is wrong.

**Not tested:** a real PlatformIO build with the real Arduino core, and everything on the real hardware (the USB drive appearing on your computer, SD timing, OLED, buzzer). Drive mode is the part most likely to need a small adjustment on the first try.

---

## 14. Troubleshooting

| Problem | Check |
|---|---|
| Upload fails on `/dev/ttyUSB0` | Run `pio device list` and fix `upload_port` and `monitor_port`; hold BOOT while it says "Connecting"; or use `pio run -e native-serial -t upload` |
| Build stops with "USE_DRIVE_MODE needs -DARDUINO_USB_MODE=0" | The flags in `platformio.ini` were not applied; check the `build_unflags` and `build_flags` lines of the main environment |
| Drive does not appear on the computer | Cable in the **native** USB port (data cable)? Drive mode started (OLED shows USB DRIVE MODE, serial prints DRIVE MODE)? Try another cable or port |
| Drive appears but is empty or asks to format | Do not format. Eject, hold button 2 to restart, and check the card in the computer with the board removed |
| `Stop the session first` | Hold button 1 to stop the session, then try again |
| OLED blank | Upload D9: it prints whether the display answers at 0x3C or 0x3D. A new OLED stays black until code runs. If it says not found: VCC to 3V3, GND, SDA to GPIO9, SCL to GPIO8, and check the pin order printed on the module |
| OLED shows only half or garbage | Set `OLED_H` to 32 in `config.h` for a 128x32 display |
| Power LED does nothing | GPIO5 to a 220 ohm resistor to the long leg of the LED; short leg to GND |
| Nothing in the serial monitor | Monitor on the UART port at 115200; in the `native-serial` build use the native port |
| `RTC lost power` | Type `SETTIME ...` or run D3 once |
| `SD card not found` | FAT32 card; CS 10, SCK 11, MOSI 12, MISO 13; then `INIT` |
| Student shows as UNKNOWN | The printed UID must match `students.csv` exactly (10 characters) |

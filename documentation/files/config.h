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
constexpr int PIN_BTN_INFO    = 41;             // short press = show time + last file count, hold 3 s = USB drive mode (backup)

// ============================== OPTIONS ======================================
#define USE_OLED 1                              // 1 = use the OLED, 0 = build without it
#ifndef USE_DRIVE_MODE                          // platformio.ini can set this; if it does not, use the default below
#define USE_DRIVE_MODE 1                        // 1 = long press of button 2 shows the SD card as a USB drive, 0 = build without it
#endif                                          // end of the USE_DRIVE_MODE default
#ifndef AUTO_DRIVE_MODE                         // platformio.ini can set this; if it does not, use the default below
#define AUTO_DRIVE_MODE 1                       // 1 = the SD card appears as a drive by itself when a computer is plugged into the native USB port
#endif                                          // end of the AUTO_DRIVE_MODE default
#if !USE_DRIVE_MODE                             // automatic drive mode cannot work without drive mode
#undef AUTO_DRIVE_MODE                          // so remove the setting
#define AUTO_DRIVE_MODE 0                       // and switch it off
#endif                                          // end of the consistency check
constexpr uint8_t OLED_ADDR = 0x3C;             // I2C address of the OLED (try 0x3D if not found)
constexpr int OLED_W = 128;                     // OLED width in pixels
constexpr int OLED_H = 64;                      // OLED height in pixels (use 32 for a 128x32 OLED)

constexpr uint32_t SAME_CARD_IGNORE_MS = 1500;  // a card left on the reader is counted only once
constexpr uint32_t DEBOUNCE_MS   = 40;          // ignore button contact bounce shorter than this
constexpr uint32_t LONG_PRESS_MS = 1500;        // holding a button this long counts as a long press
constexpr uint32_t HEARTBEAT_PERIOD_MS = 3000;  // the power LED repeats its double blink every 3 seconds
constexpr uint32_t HEARTBEAT_BLINK_MS  = 80;    // each of the two blinks, and the gap between them, lasts 80 ms (fast)
constexpr uint32_t DRIVE_LONG_PRESS_MS = 3000;  // holding button 2 this long switches USB drive mode on or off (backup for the automatic mode)
constexpr uint32_t INFO_SHOW_MS = 5000;         // how long the time and last-file screen stays on the OLED after a short press of button 2
constexpr uint32_t DRIVE_EXIT_DELAY_MS = 2000;  // the computer must be gone this long before drive mode ends by itself
constexpr uint32_t AUTO_BLOCK_MS = 60000;       // after an eject and restart, the drive does not reopen by itself for this long
constexpr size_t   MAX_STUDENTS  = 1000;        // maximum number of students loaded from the card
constexpr size_t   MAX_SEEN      = 1000;        // maximum number of taps remembered in one session

// ---- Names of files and folders on the microSD card ----
constexpr char FILE_STUDENTS[]  = "/students.csv"; // list of students: one "UID,Name" per line
constexpr char DIR_ATTENDANCE[] = "/attendance";   // folder where one file per session is saved

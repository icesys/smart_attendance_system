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

// ---- Buttons (other leg to GND, internal pull-up resistor is used) ----
constexpr int PIN_BTN_SESSION = 41;             // short press = start session, long press = stop session
constexpr int PIN_BTN_MUTE    = 40;             // short press = mute / unmute the buzzer

// ============================== OPTIONS ======================================
#define USE_OLED 1                              // 1 = use the OLED, 0 = build without it
constexpr uint8_t OLED_ADDR = 0x3C;             // I2C address of the OLED (try 0x3D if not found)
constexpr int OLED_W = 128;                     // OLED width in pixels
constexpr int OLED_H = 64;                      // OLED height in pixels (use 32 for a 128x32 OLED)

constexpr uint32_t SAME_CARD_IGNORE_MS = 1500;  // a card left on the reader is counted only once
constexpr uint32_t DEBOUNCE_MS   = 40;          // ignore button contact bounce shorter than this
constexpr uint32_t LONG_PRESS_MS = 1500;        // holding a button this long counts as a long press
constexpr size_t   MAX_STUDENTS  = 2000;        // maximum number of students loaded from the card
constexpr size_t   MAX_SEEN      = 2000;        // maximum number of taps remembered in one session

// ---- Names of files and folders on the microSD card ----
constexpr char FILE_STUDENTS[]  = "/students.csv"; // list of students: one "UID,Name" per line
constexpr char DIR_ATTENDANCE[] = "/attendance";   // folder where one file per session is saved
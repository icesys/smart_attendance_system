// config.h - every pin number and option of the project in ONE place.
#pragma once
#include <stddef.h>
#include <stdint.h>

// ======================= PINS (see the assembly guide) =======================
// ---- I2C bus: DS3231 clock (address 0x68) and OLED (address 0x3C) ----
constexpr int PIN_SDA = 9;
constexpr int PIN_SCL = 8;

// ---- microSD module on the SPI bus ----
constexpr int PIN_SD_CS   = 10;
constexpr int PIN_SD_SCK  = 11;
constexpr int PIN_SD_MOSI = 12;
constexpr int PIN_SD_MISO = 13;

// ---- RDM6300 125 kHz reader ----
constexpr int PIN_RFID_RX = 18;   // RDM6300 TX, 9600 baud

// ---- Feedback parts (J3 row of the ESP32-S3) ----
constexpr int PIN_LED_GREEN = 1;
constexpr int PIN_LED_RED   = 2;
constexpr int PIN_BUZZER    = 42;
constexpr int PIN_LED_POWER = 5;   // blue: 2 blinks every 3 s = the system is on

// ---- Buttons (other leg to GND, internal pull-up resistor is used) ----
constexpr int PIN_BTN_SESSION = 40;   // short = start session, long = stop
constexpr int PIN_BTN_INFO    = 41;   // short = info, hold 3 s = USB drive mode

// ============================== OPTIONS ======================================
#define USE_OLED 1   // 0 = build without the OLED
#ifndef USE_DRIVE_MODE
#define USE_DRIVE_MODE 1   // long press of button 2 shows the SD card as a USB drive
#endif
#ifndef AUTO_DRIVE_MODE
#define AUTO_DRIVE_MODE 1   // the drive opens by itself when a PC is plugged into the native port
#endif
#if !USE_DRIVE_MODE
#undef AUTO_DRIVE_MODE
#define AUTO_DRIVE_MODE 0
#endif
constexpr uint8_t OLED_ADDR = 0x3C;   // try 0x3D if not found
constexpr int OLED_W = 128;
constexpr int OLED_H = 64;   // 32 for a 128x32 OLED

constexpr uint32_t SAME_CARD_IGNORE_MS = 1500;   // a card left on the reader is counted once
constexpr uint32_t DEBOUNCE_MS   = 40;
constexpr uint32_t LONG_PRESS_MS = 1500;
constexpr uint32_t HEARTBEAT_PERIOD_MS = 3000;
constexpr uint32_t HEARTBEAT_BLINK_MS  = 80;
constexpr uint32_t DRIVE_LONG_PRESS_MS = 3000;
constexpr uint32_t INFO_SHOW_MS = 5000;
constexpr uint32_t DRIVE_EXIT_DELAY_MS = 2000;   // PC gone this long: drive mode ends
constexpr uint32_t AUTO_BLOCK_MS = 60000;   // after an eject, the drive does not reopen by itself for this long
constexpr size_t   MAX_STUDENTS  = 1000;
constexpr size_t   MAX_SEEN      = 1000;

// ---- Names of files and folders on the microSD card ----
constexpr char FILE_STUDENTS[]  = "/students.csv";   // one "UID,Surname,Names,Matricule" per line
constexpr char DIR_ATTENDANCE[] = "/attendance";
constexpr char DIR_FINAL[]      = "/final";   // sorted final list of each session, tab-separated

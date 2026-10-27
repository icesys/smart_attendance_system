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
#include "esp_attr.h"           // RTC_NOINIT_ATTR: a variable that survives a software restart
#include "esp_system.h"         // esp_reset_reason(): tells us why the board restarted
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
bool driveHostSeen = false;     // true once a computer has been seen while drive mode is on
bool usbWaiting = false;        // true when a computer is plugged in but a session is still running
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
const Step P_INFO[] = {         // button 2 short press: the info screen is shown
  {LED_G, false, 150}, {0, false, 0}            // one short green blink, no sound
};                              // end of P_INFO

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

  BtnEvent poll(uint32_t longMs) {                                // call this often; longMs = how long a press must last to be a long press
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
    if (r && down && !longFired && now - tDown >= longMs) {             // still held for long enough
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
Button btnInfo;                                                   // button 2: short = info screen, long (3 s) = USB drive mode

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
    Serial.println("Drive mode is on: unplug the USB cable or hold button 2 for 3 s to leave it first."); // explain
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
uint32_t mscSectorSize = 512;                                     // bytes per SD sector (read from the card when USB is set up)
bool usbStarted = false;                                          // true once USB.begin() was called (it can only be called once per power-up)
volatile bool usbMounted = false;                                 // true while a computer has set our USB device up (set by the USB event task)
volatile bool usbSuspended = false;                               // true while the USB bus is idle (cable pulled out, or the computer sleeps)
uint32_t autoBlockUntilMs = 0;                                    // until this time the drive does not open by itself (see leaveDriveMode)
uint32_t driveLastHostMs = 0;                                     // last time a computer was seen while in drive mode
RTC_NOINIT_ATTR uint32_t autoBlockMagic;                          // survives a software restart; holds AUTO_BLOCK_MAGIC after an eject
constexpr uint32_t AUTO_BLOCK_MAGIC = 0xA17E0001;                 // a value that random memory is very unlikely to contain

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
  if (load_eject && !start) mscEjected = true;                    // the PC ejected the drive: it is safe to unplug
  if (load_eject && start) mscEjected = false;                    // the drive was loaded again
  return true;                                                    // accept the command
}                                                                 // end of onMscStartStop

// The USB driver tells us when a computer connects or leaves.
static void onUsbEvent(void* arg, esp_event_base_t base, int32_t id, void* data) { // runs in the USB event task
  (void)arg;                                                      // not needed here
  (void)data;                                                     // not needed here
  if (base != ARDUINO_USB_EVENTS) return;                         // only USB events interest us
  switch (id) {                                                   // which event happened?
    case ARDUINO_USB_STARTED_EVENT: usbMounted = true; usbSuspended = false; break; // a computer set our USB device up
    case ARDUINO_USB_STOPPED_EVENT: usbMounted = false; break;   // the computer let go of our USB device
    case ARDUINO_USB_SUSPEND_EVENT: usbSuspended = true; break;   // the bus went quiet: cable pulled out or computer asleep
    case ARDUINO_USB_RESUME_EVENT: usbSuspended = false; break;  // the bus is active again
    default: break;                                               // other events are not needed
  }                                                               // end of the switch
}                                                                 // end of onUsbEvent

bool usbHostPresent() {                                           // true while a computer is really connected and awake
  return usbMounted && !usbSuspended;                             // set up by the computer and the bus is not idle
}                                                                 // end of usbHostPresent

// Prepares the USB drive object and switches the native USB-C port on (only once per power-up).
bool usbSetup() {                                                 // returns true when USB is running
  if (usbStarted) return true;                                    // already done
  if (!sdOk) return false;                                        // without a working card there is nothing to show
  size_t sectors = SD.numSectors();                               // how many sectors the card has
  mscSectorSize = (uint32_t)SD.sectorSize();                      // how big one sector is (normally 512 bytes)
  if (sectors == 0 || mscSectorSize == 0) return false;           // the card did not report its size
  USB.manufacturerName("ice");                                    // name shown by the PC for the USB device
  USB.productName("Smart Attendance");                            // product name shown by the PC
  msc.vendorID("ATTEND");                                         // short vendor text of the drive (max 8 characters)
  msc.productID("SD card");                                       // product text of the drive (max 16 characters)
  msc.productRevision("1.0");                                     // version text (max 4 characters)
  msc.onRead(onMscRead);                                          // tell the USB driver how to read the card
  msc.onWrite(onMscWrite);                                        // ... how to write the card
  msc.onStartStop(onMscStartStop);                                // ... what to do on eject
  msc.mediaPresent(false);                                        // no card shown to the PC yet: it sees an empty drive slot
  if (!msc.begin((uint32_t)sectors, (uint16_t)mscSectorSize)) return false; // create the drive with the size of the SD card
  USB.onEvent(onUsbEvent);                                        // be told when a computer connects or leaves
  USB.begin();                                                    // switch the native USB-C port on
  usbStarted = true;                                              // remember that USB runs now
  return true;                                                    // success
}                                                                 // end of usbSetup

// Gives the SD card to the computer. automatic = true when a computer was detected, false when a button/command asked for it.
bool enterDriveMode(bool automatic) {                             // returns true if drive mode is on afterwards
  if (driveMode) return true;                                     // already in drive mode
  if (sessionActive) {                                            // never interrupt a running lecture
    if (!automatic) {                                             // a person asked for it, so tell them why not
      Serial.println("Stop the session first (hold button 1), then enter drive mode."); // explain
      startPattern(P_ERROR);                                      // signal the error
    }                                                             // end of the message
    return false;                                                 // not now
  }                                                               // end of the session check
  if (!sdOk) {                                                    // no card, nothing to show
    if (!automatic) {                                             // a person asked for it
      Serial.println("No SD card: nothing to show as a drive.");  // explain
      startPattern(P_ERROR);                                      // signal the error
    }                                                             // end of the message
    return false;                                                 // not possible
  }                                                               // end of the card check
  if (!usbSetup()) {                                              // make sure the USB drive exists
    Serial.println("USB drive could not be created.");            // explain
    startPattern(P_ERROR);                                        // signal the error
    return false;                                                 // failed
  }                                                               // end of the setup check
  mscEjected = false;                                             // not ejected yet
  driveHostSeen = usbHostPresent();                               // is a computer already there?
  driveLastHostMs = millis();                                     // start the "computer last seen" clock
  msc.mediaPresent(true);                                         // the card now appears in the computer
  driveMode = true;                                               // from now on the firmware leaves the SD card alone
  Serial.println(automatic ? "DRIVE MODE (automatic): the SD card is now a drive on the computer. Eject it, then unplug." // message for the automatic case
                           : "DRIVE MODE: plug the native USB-C port into a computer. Eject the drive, then unplug or hold button 2 for 3 s."); // message for the manual case
  startPattern(P_DRIVE);                                          // blink and beep
  return true;                                                    // success
}                                                                 // end of enterDriveMode

// Leaves drive mode by restarting, so the firmware reads the card fresh.
void leaveDriveMode() {                                           // called by the button, the command or the "computer gone" check
  if (mscEjected) autoBlockMagic = AUTO_BLOCK_MAGIC;              // after an eject, do not reopen the drive on its own right after the restart
  Serial.println(mscEjected ? "Leaving drive mode (the drive was ejected)." : "Leaving drive mode. Tip: eject the drive on the computer first."); // explain
  rebootNow();                                                    // restart the ESP32
}                                                                 // end of leaveDriveMode

// Called from loop(): opens the drive by itself when a computer appears, and closes it when the computer is gone.
void usbUpdate() {                                                // never waits, so it is safe to call every loop
  if (!usbStarted) return;                                        // USB is not running: nothing to watch
  bool present = usbHostPresent();                                // is a computer connected and awake right now?
  uint32_t now = millis();                                        // current time
  if (!driveMode) {                                               // normal attendance mode
#if AUTO_DRIVE_MODE                                               // automatic opening is switched on in config.h
    static bool noticePrinted = false;                            // so the hint below is printed only once per plug-in
    usbWaiting = present && sessionActive;                        // a computer waits while a session still runs
    if (usbWaiting && !noticePrinted) {                           // first time we notice it
      Serial.println("A computer is connected: stop the session and the SD card will appear as a drive."); // explain
      noticePrinted = true;                                       // do not repeat it
    }                                                             // end of the hint
    if (!usbWaiting) noticePrinted = false;                       // ready to print the hint again next time
    if (present && !sessionActive && now >= autoBlockUntilMs) enterDriveMode(true); // computer there, no session, not blocked: open the drive
#endif                                                            // end of the automatic block
  } else {                                                        // drive mode is on
    if (present) {                                                // a computer is there
      driveHostSeen = true;                                       // remember that we have seen it
      driveLastHostMs = now;                                      // and when
    } else if (driveHostSeen && now - driveLastHostMs >= DRIVE_EXIT_DELAY_MS) { // it was there, and has been gone long enough
      leaveDriveMode();                                           // go back to attendance mode
    }                                                             // end of the "gone" check
  }                                                               // end of the mode check
}                                                                 // end of usbUpdate
#else                                                             // drive mode disabled in config.h or platformio.ini
bool usbHostPresent() { return false; }                           // there is no USB device, so no computer is ever seen
bool enterDriveMode(bool automatic) {                             // placeholder so the rest of the code still compiles
  (void)automatic;                                                // not used here
  Serial.println("Drive mode is not built in (USE_DRIVE_MODE is 0)."); // explain
  startPattern(P_ERROR);                                          // signal
  return false;                                                   // failed
}                                                                 // end of placeholder
void leaveDriveMode() { rebootNow(); }                            // placeholder: just restart
void usbUpdate() {}                                               // placeholder: nothing to watch
#endif                                                            // end of the drive mode block

// ------------------------------ INFO (button 2, short press) ----------------
struct LastFileInfo {                                             // what we know about the newest attendance file
  char name[64];                                                  // its file name
  uint16_t present;                                               // known students counted in it
  uint16_t unknown;                                               // unknown cards counted in it
  bool found;                                                     // true if there is any file at all
  bool live;                                                      // true if it is the session that is running now
};                                                                // end of LastFileInfo

LastFileInfo lastInfo = LastFileInfo();                           // the latest result (all zero at start)
uint32_t infoUntilMs = 0;                                         // the OLED shows the info screen until this time

void countLine(const char* line, uint16_t& present, uint16_t& unknown) { // looks at one line of a session file
  size_t len = strlen(line);                                      // length of the line
  if (len < 8 || line[0] == '#') return;                          // too short to end in PRESENT or UNKNOWN, or a comment line
  if (!strcmp(line + len - 8, ",PRESENT")) present++;             // the line ends with ,PRESENT: a known student
  else if (!strcmp(line + len - 8, ",UNKNOWN")) unknown++;        // the line ends with ,UNKNOWN: an unknown card
}                                                                 // end of countLine

void scanLastFile() {                                             // fills lastInfo with the newest file and its counts
  lastInfo = LastFileInfo();                                      // start empty
  if (sessionActive) {                                            // a session is running: use its live numbers
    const char* base = strrchr(sessionPath, '/');                 // find the file name part of the path
    snprintf(lastInfo.name, sizeof(lastInfo.name), "%s", base ? base + 1 : sessionPath); // copy the file name
    lastInfo.present = presentCount;                              // live counter
    lastInfo.unknown = unknownCount;                              // live counter
    lastInfo.found = true;                                        // there is a file
    lastInfo.live = true;                                         // and it is the running session
    return;                                                       // done
  }                                                               // end of the live case
  if (!sdOk) return;                                              // no card: nothing to look at
  File dir = SD.open(DIR_ATTENDANCE);                             // open the attendance folder
  if (!dir || !dir.isDirectory()) return;                         // no folder yet: no files
  char best[64] = "";                                             // the newest file name found so far
  File f = dir.openNextFile();                                    // first entry of the folder
  while (f) {                                                     // until there are no more entries
    if (!f.isDirectory()) {                                       // only real files
      const char* nm = f.name();                                  // its name
      const char* slash = strrchr(nm, '/');                       // some library versions include the folder
      if (slash) nm = slash + 1;                                  // keep only the file name
      if (strcmp(nm, best) > 0) snprintf(best, sizeof(best), "%s", nm); // names start with the date, so the largest name is the newest
    }                                                             // end of "real file"
    f = dir.openNextFile();                                       // next entry
  }                                                               // end of the loop
  dir.close();                                                    // close the folder
  if (!best[0]) return;                                           // the folder is empty
  char path[96];                                                  // full path buffer
  snprintf(path, sizeof(path), "%s/%s", DIR_ATTENDANCE, best);    // /attendance/<newest>
  File g = SD.open(path, FILE_READ);                              // open it for reading
  if (!g) return;                                                 // could not open
  char line[112];                                                 // buffer for one line
  size_t n = 0;                                                   // characters in the buffer
  while (g.available()) {                                         // until the end of the file
    int ch = g.read();                                            // read one character
    if (ch < 0) break;                                            // read error: stop
    if (ch == '\r') continue;                                     // ignore the carriage return of Windows line ends
    if (ch == '\n' || n >= sizeof(line) - 1) {                    // end of a line (or the line is too long)
      line[n] = 0;                                                // close the text
      n = 0;                                                      // start a new line
      countLine(line, lastInfo.present, lastInfo.unknown);        // count it if it is a PRESENT or UNKNOWN line
      if (ch != '\n') {                                           // the line was too long
        while (g.available()) {                                   // skip the rest of it
          int d = g.read();                                       // next character
          if (d == '\n' || d < 0) break;                          // stop at the line end
        }                                                         // end of skipping
      }                                                           // end of "too long"
    } else {                                                      // a normal character
      line[n++] = (char)ch;                                       // add it to the buffer
    }                                                             // end of the if/else
  }                                                               // end of the file loop
  if (n > 0) {                                                    // the last line had no line break
    line[n] = 0;                                                  // close the text
    countLine(line, lastInfo.present, lastInfo.unknown);          // count it
  }                                                               // end of "last line"
  g.close();                                                      // close the file
  snprintf(lastInfo.name, sizeof(lastInfo.name), "%s", best);     // remember the file name
  lastInfo.found = true;                                          // we have a result
}                                                                 // end of scanLastFile

void showInfo() {                                                 // short press of button 2 (or the INFO command)
  if (driveMode) {                                                // the computer owns the SD card now
    Serial.println("Info is not available in drive mode.");       // explain
    return;                                                       // nothing to do
  }                                                               // end of the drive-mode check
  scanLastFile();                                                 // find the newest file and its counts
  infoUntilMs = millis() + INFO_SHOW_MS;                          // show the info screen for a few seconds
  char d[11] = "----------";                                      // date text (dashes if the clock is not ready)
  char t[9] = "--:--:--";                                         // time text (dashes if the clock is not ready)
  if (rtcOk) {                                                    // the clock works
    DateTime now = rtc.now();                                     // read it
    fmtDate(now, d, sizeof(d));                                   // fill the date text
    fmtTime(now, t, sizeof(t));                                   // fill the time text
  }                                                               // end of "clock works"
  if (lastInfo.found) {                                           // there is a file to report
    Serial.printf("INFO %s %s | %s %s | present=%u unknown=%u\n", d, t, lastInfo.live ? "session" : "last file", lastInfo.name, (unsigned)lastInfo.present, (unsigned)lastInfo.unknown); // report on the PC
  } else {                                                        // no attendance file yet
    Serial.printf("INFO %s %s | no attendance files yet\n", d, t); // report on the PC
  }                                                               // end of the report
  startPattern(P_INFO);                                           // one short green blink as confirmation
}                                                                 // end of showInfo

// ------------------------------ OLED SCREEN --------------------------------
#if USE_OLED                                                      // all OLED drawing code exists only if enabled
void drawDriveScreen() {                                          // OLED text shown during drive mode
  oled.clearDisplay();                                            // erase the screen buffer
  oled.setTextSize(1);                                            // smallest text: 21 characters per line
  oled.setTextColor(SSD1306_WHITE);                               // white pixels on black
  oled.setCursor(0, 0);                                           // top line
  oled.print("USB DRIVE MODE");                                   // title
  oled.setCursor(0, 12);                                          // second line
  oled.print(driveHostSeen ? "The SD card is now a" : "Plug the native USB"); // depends on whether a computer is there yet
  oled.setCursor(0, 22);                                          // third line
  oled.print(driveHostSeen ? "drive on the computer" : "cable into a computer"); // continued
  oled.setCursor(0, 36);                                          // fifth line
  oled.print(mscEjected ? "Ejected: safe to exit" : "Eject on the PC first"); // safety hint, changes after the eject
  oled.setCursor(0, 50);                                          // last line
  oled.print("Hold btn2 3s to exit");                             // how to leave by hand
  oled.display();                                                 // send the buffer to the screen
}                                                                 // end of drawDriveScreen

void drawInfoScreen() {                                           // OLED text shown after a short press of button 2
  char d[11] = "----------";                                      // date text (dashes if the clock is not ready)
  char t[9] = "--:--:--";                                         // time text (dashes if the clock is not ready)
  if (rtcOk) {                                                    // the clock works
    DateTime now = rtc.now();                                     // read it
    fmtDate(now, d, sizeof(d));                                   // fill the date text
    fmtTime(now, t, sizeof(t));                                   // fill the time text
  }                                                               // end of "clock works"
  char buf[32];                                                   // buffer for lines with numbers
  oled.clearDisplay();                                            // erase the screen buffer
  oled.setTextSize(1);                                            // smallest text
  oled.setTextColor(SSD1306_WHITE);                               // white pixels on black
  oled.setCursor(0, 0);                                           // top line
  snprintf(buf, sizeof(buf), "TIME %s", t);                       // "TIME hh:mm:ss"
  oled.print(buf);                                                // show it
  oled.setCursor(0, 10);                                          // second line
  oled.print(d);                                                  // the date
  oled.setCursor(0, 24);                                          // fourth line
  oled.print(lastInfo.found ? (lastInfo.live ? "Session running:" : "Last file:") : "No files yet"); // what the numbers below belong to
  oled.setCursor(0, 34);                                          // fifth line
  oled.print(lastInfo.name);                                      // the file name (empty if none)
  oled.setCursor(0, 46);                                          // sixth line
  if (lastInfo.found) {                                           // only if there is a file
    snprintf(buf, sizeof(buf), "Present:%u Unk:%u", (unsigned)lastInfo.present, (unsigned)lastInfo.unknown); // the counters
    oled.print(buf);                                              // show them
  }                                                               // end of the counters
  oled.display();                                                 // send the buffer to the screen
}                                                                 // end of drawInfoScreen
uint32_t lastDraw = 0;                                            // time of the last screen refresh
void drawScreen() {                                               // redraws the OLED twice per second
  if (!oledOk || millis() - lastDraw < 500) return;               // no OLED, or it was refreshed less than 0.5 s ago
  lastDraw = millis();                                            // remember this refresh
  if (driveMode) { drawDriveScreen(); return; }                   // drive mode has its own screen
  if (millis() < infoUntilMs) { drawInfoScreen(); return; }       // the info screen is shown for a few seconds after button 2
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
  if (usbWaiting) snprintf(buf, sizeof(buf), "USB PC: stop session"); // a computer waits: tell the lecturer what to do
  else snprintf(buf, sizeof(buf), "SD:%s RTC:%s%s", sdOk ? "OK" : "ERR", rtcOk ? "OK" : "ERR", muted ? " MUTE" : ""); // health flags
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
  Serial.println("  DRIVE                        show the SD card as a USB drive now (also automatic when a computer is plugged in)");
  Serial.println("  INFO                         show time and the count of the last file (same as button 2)");
  Serial.println("  REBOOT                       restart (also leaves drive mode)");
}                                                                 // end of printHelp

void printStatus() {                                              // prints the health of the system
  Serial.printf("Clock: %s | SD card: %s | Students: %u | Session: %s | Buzzer: %s\n", // one summary line
                rtcOk ? "OK" : "NOT READY", sdOk ? "OK" : "NOT READY", (unsigned)students.size(), // values
                sessionActive ? "ACTIVE" : "stopped", muted ? "muted" : "on"); // more values
  Serial.printf("Drive mode: %s\n", driveMode ? "ON" : "off"); // also show whether the SD card belongs to the PC
  Serial.printf("USB computer: %s | automatic drive mode: %s\n", usbHostPresent() ? "connected" : "no", AUTO_DRIVE_MODE ? "on" : "off"); // USB state
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
  else if (!strcmp(line, "DRIVE")) enterDriveMode(false);          // same as holding button 2 for 3 seconds
  else if (!strcmp(line, "INFO")) showInfo();                     // same as a short press of button 2
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
  btnInfo.begin(PIN_BTN_INFO);                                    // prepare button 2
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
#if USE_DRIVE_MODE                                                // USB drive start-up (only if drive mode is built in)
  if (esp_reset_reason() == ESP_RST_SW && autoBlockMagic == AUTO_BLOCK_MAGIC) autoBlockUntilMs = millis() + AUTO_BLOCK_MS; // restarted after an eject: do not reopen the drive right away
  autoBlockMagic = 0;                                             // forget the marker so it is used only once
#if AUTO_DRIVE_MODE                                               // automatic mode: be ready for a computer from the start
  if (sdOk) {                                                     // only possible with a working SD card
    Serial.println(usbSetup() ? "USB ready: plug a computer into the native USB-C port to see the SD card." : "USB drive setup failed."); // report
  }                                                               // end of the card check
#endif                                                            // end of the automatic block
#endif                                                            // end of the USB drive start-up
  printStatus();                                                  // one-line summary of everything
  Serial.println("Type HELP for the list of commands.");          // hint
  startPattern((sdOk && rtcOk) ? P_BOOT : P_ERROR);               // happy beeps if all is fine, error pattern otherwise
}                                                                 // end of setup

// ------------------------------ LOOP (runs forever) ------------------------
void loop() {                                                     // runs again and again, thousands of times per second
  patternUpdate();                                                // keep the LED/buzzer patterns moving
  idleLedUpdate();                                                // show the device state when no pattern plays
  powerLedUpdate();                                               // double blink of the power LED every 3 seconds

  BtnEvent e1 = btnSession.poll(LONG_PRESS_MS);                   // check button 1 (long press = 1.5 s)
  if (e1 == BTN_SHORT) {                                          // short press
    if (!sessionActive) startSession();                           // no session yet: start one
    else Serial.println("Session running. Hold button 1 for 1.5 s to stop it."); // protect against accidental stops
  } else if (e1 == BTN_LONG && sessionActive) {                   // long press while a session runs
    stopSession();                                                // stop it
  }                                                               // end of button 1

  BtnEvent e2 = btnInfo.poll(DRIVE_LONG_PRESS_MS);                // check button 2 (long press = 3 s)
  if (e2 == BTN_SHORT) showInfo();                                // short press: show the time and the count of the last file
  else if (e2 == BTN_LONG) {                                      // long press (3 s): USB drive mode on or off
    if (driveMode) leaveDriveMode();                              // already in drive mode: restart to leave it
    else enterDriveMode(false);                                   // otherwise give the SD card to the computer
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

  usbUpdate();                                                    // open the USB drive by itself when a computer appears
  serialUpdate();                                                 // handle commands typed on the PC
  drawScreen();                                                   // refresh the OLED
}                                                                 // end of loop
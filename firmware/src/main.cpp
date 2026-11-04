/**********************************************************************************/
/*                                                         / - ice.               */
/*   SMART ATTENDANCE SYSTEM                              /                       */
/*   ----------------------------               :+:   .:#/ #:.   .:#/#:.          */
/*   Code By : ice.                                  +:         #:   ##           */
/*   GitHub : https://github.com/icesys       #+#   +:         #+::##"            */
/*   Created : 20-10-2026                    #+#   #+         #+                  */
/*   Updated : 03-11-2026                   #+#   ##    ##   ##    ##             */
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

#include <Arduino.h>
#include <SPI.h>
#include <SD.h>
#include <Wire.h>
#include <RTClib.h>
#include <ctype.h>
#include <stdio.h>
#include <string.h>
#include <vector>
#include <algorithm>
#include "config.h"
#include "parsers.h"
#if USE_DRIVE_MODE && ARDUINO_USB_MODE   // drive mode needs TinyUSB (ARDUINO_USB_MODE=0)
#error "USE_DRIVE_MODE needs -DARDUINO_USB_MODE=0 in platformio.ini (see the comments there)"
#endif
#if USE_DRIVE_MODE
#include "USB.h"
#include "USBMSC.h"
#include "esp_attr.h"
#include "esp_system.h"
#endif
#if USE_OLED
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#endif

// ------------------------------ GLOBAL OBJECTS -----------------------------
HardwareSerial RFID(1);   // UART1 talks to the RDM6300
RTC_DS3231 rtc;
Rdm6300Parser rdm;
#if USE_OLED
Adafruit_SSD1306 oled(OLED_W, OLED_H, &Wire, -1);
bool oledOk = false;
#endif

// ------------------------------ GLOBAL STATE -------------------------------
bool rtcOk = false;
bool sdOk = false;
bool muted = false;
bool driveMode = false;
volatile bool mscEjected = false;
bool driveHostSeen = false;
bool usbWaiting = false;
#if USE_DRIVE_MODE
USBMSC msc;
#endif
std::vector<StudentRec> students;
std::vector<uint64_t> seen;
bool sessionActive = false;
char sessionPath[64] = "";
uint32_t sessionStartMs = 0;
uint16_t presentCount = 0;
uint16_t unknownCount = 0;
char lastSurname[32] = "";
char lastNames[32] = "";
char lastMat[16] = "";
uint64_t lastUid = 0;
uint32_t lastSeenMs = 0;

// ------------------- FEEDBACK PATTERNS (LEDs + BUZZER) ---------------------
struct Step {
  uint8_t leds;   // bit 0 = green, bit 1 = red
  bool buzz;
  uint16_t ms;   // 0 marks the end of the pattern
};

enum : uint8_t { LED_G = 1, LED_R = 2 };

const Step P_BOOT[] = {
  {LED_G, true, 80}, {0, false, 80},
  {LED_G, true, 80}, {0, false, 80},
  {LED_G, true, 200}, {0, false, 0}
};
const Step P_OK[] = {
  {LED_G, true, 120}, {LED_G, false, 250},
  {0, false, 0}
};
const Step P_DUP[] = {
  {LED_R, true, 80}, {0, false, 80},
  {LED_R, true, 80}, {LED_R, false, 200},
  {0, false, 0}
};
const Step P_UNKNOWN[] = {
  {LED_R, true, 600}, {LED_R, false, 200},
  {0, false, 0}
};
const Step P_NOSESSION[] = {
  {LED_R, true, 150}, {0, false, 150},
  {LED_R, true, 150}, {0, false, 0}
};
const Step P_START[] = {
  {LED_G, true, 100}, {0, false, 100},
  {LED_G, true, 100}, {0, false, 100},
  {LED_G, true, 300}, {0, false, 0}
};
const Step P_STOP[] = {
  {LED_R, true, 300}, {0, false, 100},
  {LED_R, true, 300}, {0, false, 0}
};
const Step P_ERROR[] = {
  {LED_R, true, 300}, {LED_R, false, 300},
  {LED_R, true, 300}, {LED_R, false, 300},
  {LED_R, true, 300}, {0, false, 0}
};
const Step P_MUTE[] = {
  {LED_G | LED_R, false, 150}, {0, false, 0}
};
const Step P_DRIVE[] = {
  {LED_G | LED_R, true, 200}, {0, false, 100},
  {LED_G | LED_R, true, 200}, {0, false, 0}
};
const Step P_INFO[] = {
  {LED_G, false, 150}, {0, false, 0}
};

const Step* patCur = nullptr;
uint32_t patT0 = 0;

// Switches the LEDs and the buzzer to what one step asks for.
void applyStep(const Step& s) {
  digitalWrite(PIN_LED_GREEN, (s.leds & LED_G) ? HIGH : LOW);
  digitalWrite(PIN_LED_RED, (s.leds & LED_R) ? HIGH : LOW);
  digitalWrite(PIN_BUZZER, (s.buzz && !muted) ? HIGH : LOW);
}

// Starts playing a pattern. It plays in the background: loop() keeps running.
void startPattern(const Step* p) {
  patCur = p;
  patT0 = millis();
  applyStep(*patCur);
}

// Called from loop(): moves to the next step when the current one has lasted long enough.
void patternUpdate() {
  if (!patCur) return;
  if (millis() - patT0 >= patCur->ms) {
    patCur++;
    patT0 = millis();
    if (patCur->ms == 0) {
      patCur = nullptr;
      digitalWrite(PIN_BUZZER, LOW);
      digitalWrite(PIN_LED_GREEN, LOW);
      digitalWrite(PIN_LED_RED, LOW);
      return;
    }
    applyStep(*patCur);
  }
}

// When no pattern is playing, the LEDs show the state of the device.
void idleLedUpdate() {
  if (patCur) return;
  uint32_t t = millis();
  bool fault = !sdOk;
  bool g = false;
  bool r = false;
  if (driveMode) { g = (t % 1000) < 500; r = !g; }
  else if (fault) r = (t % 1000) < 100;
  else if (sessionActive) g = true;
  else g = (t % 2000) < 80;
  digitalWrite(PIN_LED_GREEN, g ? HIGH : LOW);
  digitalWrite(PIN_LED_RED, r ? HIGH : LOW);
}

// The power LED: two fast blinks every 3 seconds, so you can see that the system is on.
void powerLedUpdate() {
  uint32_t p = millis() % HEARTBEAT_PERIOD_MS;
  bool on = (p < HEARTBEAT_BLINK_MS) ||
            (p >= 2 * HEARTBEAT_BLINK_MS && p < 3 * HEARTBEAT_BLINK_MS);
  digitalWrite(PIN_LED_POWER, on ? HIGH : LOW);
}

// ------------------------------ PUSH BUTTONS -------------------------------
enum BtnEvent : uint8_t { BTN_NONE, BTN_SHORT, BTN_LONG };

struct Button {
  int pin = 0;
  bool raw = false;
  bool down = false;
  bool longFired = false;
  uint32_t tChange = 0;
  uint32_t tDown = 0;

  void begin(int p) {
    pin = p;
    pinMode(pin, INPUT_PULLUP);   // pressed = LOW
  }

  BtnEvent poll(uint32_t longMs) {
    bool r = (digitalRead(pin) == LOW);
    uint32_t now = millis();
    if (r != raw) {
      raw = r;
      tChange = now;
    }
    if (now - tChange < DEBOUNCE_MS) return BTN_NONE;   // still bouncing
    if (r && !down) {
      down = true;
      longFired = false;
      tDown = now;
      return BTN_NONE;
    }
    if (r && down && !longFired && now - tDown >= longMs) {
      longFired = true;
      return BTN_LONG;
    }
    if (!r && down) {
      down = false;
      if (!longFired) return BTN_SHORT;
    }
    return BTN_NONE;
  }
};

Button btnSession;
Button btnInfo;

// Prints a message, plays the error pattern and returns false (the common "failed" path).
bool fail(const char* msg) {
  Serial.println(msg);
  startPattern(P_ERROR);
  return false;
}

// ------------------------------ TIME HELPERS -------------------------------
void fmtDate(const DateTime& d, char* out, size_t n) {
  snprintf(out, n, "%04d-%02d-%02d", d.year(), d.month(), d.day());
}

void fmtTime(const DateTime& d, char* out, size_t n) {
  snprintf(out, n, "%02d:%02d:%02d", d.hour(), d.minute(), d.second());
}

// Date and time texts for display: the clock, or dashes when the clock is not ready.
void clockText(char* d, size_t dn, char* t, size_t tn) {
  if (!rtcOk) {
    snprintf(d, dn, "----------");
    snprintf(t, tn, "--:--:--");
    return;
  }
  DateTime now = rtc.now();
  fmtDate(now, d, dn);
  fmtTime(now, t, tn);
}

// Fills the date and time texts of a record. With a working clock: "YYYY-MM-DD" and "HH:MM:SS".
// Without the clock (not found or lost power): "NO-CLOCK" and the time since the session started, "+HH:MM:SS",
// so the taps are still saved in the order they happened.
void stampNow(char* d, size_t dn, char* t, size_t tn) {
  if (rtcOk) {
    DateTime now = rtc.now();
    fmtDate(now, d, dn);
    fmtTime(now, t, tn);
    return;
  }
  uint32_t s = (millis() - sessionStartMs) / 1000;
  snprintf(d, dn, "NO-CLOCK");
  snprintf(t, tn, "+%02lu:%02lu:%02lu", (unsigned long)(s / 3600), (unsigned long)(s / 60 % 60), (unsigned long)(s % 60));
}

// ------------------------------ MICROSD CARD -------------------------------
bool mountSd() {
  SPI.begin(PIN_SD_SCK, PIN_SD_MISO, PIN_SD_MOSI, PIN_SD_CS);
  sdOk = SD.begin(PIN_SD_CS, SPI);
  return sdOk;
}

// Calls fn(line) for every line of a file. Reads in 512-byte blocks; '\r' is dropped and a line longer
// than the buffer is cut (the rest of it is skipped).
template <typename Fn>
void forEachLine(File& f, char* line, size_t cap, Fn fn) {
  uint8_t block[512];
  size_t n = 0;
  bool skipping = false;
  int got;
  while ((got = f.read(block, sizeof(block))) > 0) {
    for (int i = 0; i < got; i++) {
      char c = (char)block[i];
      if (c == '\r') continue;
      if (c == '\n') {
        if (!skipping) {
          line[n] = 0;
          fn(line);
        }
        n = 0;
        skipping = false;
      } else if (!skipping) {
        if (n < cap - 1) {
          line[n++] = c;
        } else {
          line[n] = 0;
          fn(line);
          n = 0;
          skipping = true;
        }
      }
    }
  }
  if (n > 0 && !skipping) {
    line[n] = 0;
    fn(line);
  }
}

// Name of the current session file, without the folder.
const char* sessionName() {
  const char* slash = strrchr(sessionPath, '/');
  return slash ? slash + 1 : sessionPath;
}

// Adds one line of text at the end of a file (creates the file if it does not exist).
bool appendLine(const char* path, const char* text) {
  File f = SD.open(path, FILE_APPEND);
  if (!f) return false;
  size_t w = f.println(text);
  f.close();
  return w > 0;
}

// Reads /students.csv into the "students" list. Returns how many students were loaded.
size_t loadStudents() {
  students.clear();
  File f = SD.open(FILE_STUDENTS, FILE_READ);
  if (!f) return 0;
  char line[96];
  forEachLine(f, line, sizeof(line), [](char* l) {
    StudentRec s;
    if (students.size() < MAX_STUDENTS && parseStudentLine(l, s)) students.push_back(s);
  });
  f.close();
  return students.size();
}

const StudentRec* findStudent(uint64_t id) {
  for (const StudentRec& s : students) {
    if (s.id == id) return &s;
  }
  return nullptr;
}

// A card added automatically keeps "UNKNOWN" as its surname until the lecturer fills in the names:
// it still counts as an unknown card until then.
constexpr char PLACEHOLDER[] = "UNKNOWN";

bool isPlaceholder(const StudentRec* s) {
  return s && !strcmp(s->surname, PLACEHOLDER);
}

// Adds a card that is not in the list yet to /students.csv as "UID,UNKNOWN,UNKNOWN,UNKNOWN",
// so the lecturer only has to type the names. Each card is added once.
bool registerNewCard(const char* uidStr, uint64_t id) {
  if (!sdOk || driveMode || students.size() >= MAX_STUDENTS) return false;
  bool needNewline = false;
  File r = SD.open(FILE_STUDENTS, FILE_READ);
  if (r) {
    size_t size = r.size();
    if (size > 0 && r.seek(size - 1)) needNewline = (r.read() != '\n');   // never glue the new line onto the last student
    r.close();
  }
  File f = SD.open(FILE_STUDENTS, FILE_APPEND);
  if (!f) return false;
  size_t w = f.printf("%s%s,%s,%s,%s\n", needNewline ? "\n" : "", uidStr, PLACEHOLDER, PLACEHOLDER, PLACEHOLDER);
  f.close();
  if (w == 0) return false;
  StudentRec s;
  s.id = id;
  snprintf(s.surname, sizeof(s.surname), "%s", PLACEHOLDER);
  snprintf(s.names, sizeof(s.names), "%s", PLACEHOLDER);
  snprintf(s.matricule, sizeof(s.matricule), "%s", PLACEHOLDER);
  students.push_back(s);
  return true;
}

bool alreadySeen(uint64_t id) {
  for (uint64_t v : seen) {
    if (v == id) return true;
  }
  return false;
}

// ------------------------------ FINAL LIST ---------------------------------
// Finds the newest session file in /attendance: dated names (YYYYMMDD_hhmmss) sort by time; NOCLOCK_nnnn files are numbered.
bool findNewestSession(char* out, size_t n) {
  if (!sdOk) return false;
  File dir = SD.open(DIR_ATTENDANCE);
  if (!dir || !dir.isDirectory()) return false;
  char best[64] = "";
  File f = dir.openNextFile();
  while (f) {
    if (!f.isDirectory()) {
      const char* nm = f.name();
      const char* slash = strrchr(nm, '/');
      if (slash) nm = slash + 1;
      bool nc = !strncmp(nm, "NOCLOCK_", 8);
      bool bestNc = !strncmp(best, "NOCLOCK_", 8);
      bool better;
      if (!best[0]) better = true;
      else if (nc != bestNc) better = (nc == !rtcOk);   // prefer NOCLOCK files only while the clock is not ready
      else better = strcmp(nm, best) > 0;
      if (better) snprintf(best, sizeof(best), "%s", nm);
    }
    f = dir.openNextFile();
  }
  dir.close();
  if (!best[0]) return false;
  snprintf(out, n, "%s", best);
  return true;
}

// Reads one session file and writes the final list of it: the students in alphabetical order of surname,
// as a tab-separated table (UID, Surname, Name(s), Matricule) that can be copied straight into Excel.
// Unknown cards come last. The list is saved in /final with the same name as the session file (.txt).
bool buildFinalList(const char* name, bool printToSerial) {
  if (!sdOk) return false;
  char inPath[96];
  snprintf(inPath, sizeof(inPath), "%s/%s", DIR_ATTENDANCE, name);
  File in = SD.open(inPath, FILE_READ);
  if (!in) return false;
  std::vector<ListRow> rows;
  char line[160];
  forEachLine(in, line, sizeof(line), [&rows](char* l) {
    ListRow r;
    if (rows.size() < MAX_SEEN && parseSessionLine(l, r, (uint16_t)rows.size())) rows.push_back(r);
  });
  in.close();
  std::sort(rows.begin(), rows.end(), rowLess);
  if (!SD.exists(DIR_FINAL) && !SD.mkdir(DIR_FINAL)) return false;
  char baseName[64];
  snprintf(baseName, sizeof(baseName), "%s", name);
  char* dot = strrchr(baseName, '.');
  if (dot) *dot = 0;
  char outPath[96];
  snprintf(outPath, sizeof(outPath), "%s/%s.txt", DIR_FINAL, baseName);
  File out = SD.open(outPath, FILE_WRITE);
  if (!out) return false;
  out.println(LIST_HEADER);
  if (printToSerial) Serial.println(LIST_HEADER);
  char row[128];
  for (const ListRow& r : rows) {
    formatListRow(r, row, sizeof(row));
    out.println(row);
    if (printToSerial) Serial.println(row);
  }
  out.close();
  Serial.printf("FINAL LIST saved: %s (%u rows, sorted by surname)\n", outPath, (unsigned)rows.size());
  return true;
}

// ------------------------------ SESSIONS -----------------------------------
bool startSession() {
  if (sessionActive) return true;
  if (driveMode) return fail("Drive mode is on: unplug the USB cable or hold button 2 for 3 s to leave it first.");
  if (!sdOk) return fail("Cannot start: SD card not ready. Type STATUS.");
  if (!SD.exists(DIR_ATTENDANCE) && !SD.mkdir(DIR_ATTENDANCE)) return fail("Cannot create the /attendance folder.");
  if (rtcOk) {
    DateTime now = rtc.now();
    snprintf(sessionPath, sizeof(sessionPath), "%s/%04d%02d%02d_%02d%02d%02d.csv", DIR_ATTENDANCE,
             now.year(), now.month(), now.day(), now.hour(), now.minute(), now.second());
  } else {
    int k = 1;
    do {
      snprintf(sessionPath, sizeof(sessionPath), "%s/NOCLOCK_%04d.csv", DIR_ATTENDANCE, k++);
    } while (SD.exists(sessionPath) && k < 10000);
    Serial.println("Warning: clock not ready, taps are saved with the time since the session started. Use SETTIME to fix it.");
  }
  sessionStartMs = millis();
  if (!appendLine(sessionPath, "uid,surname,names,matricule,date,time,result")) {
    sdOk = false;
    return fail("Cannot create the session file.");
  }
  seen.clear();
  presentCount = 0;
  unknownCount = 0;
  lastUid = 0;   // the first tap of a session is never ignored
  lastSurname[0] = 0;
  lastNames[0] = 0;
  lastMat[0] = 0;
  sessionActive = true;
  Serial.printf("SESSION START -> %s\n", sessionPath);
  startPattern(P_START);
  return true;
}

void stopSession() {
  if (!sessionActive) return;
  char d[11];
  char t[16];
  stampNow(d, sizeof(d), t, sizeof(t));
  char line[96];
  snprintf(line, sizeof(line), "# end,%s,%s,present=%u,unknown=%u", d, t, (unsigned)presentCount, (unsigned)unknownCount);   // starts with # so the parsers skip it
  appendLine(sessionPath, line);
  sessionActive = false;
  Serial.printf("SESSION STOP: present=%u unknown=%u file=%s\n", (unsigned)presentCount, (unsigned)unknownCount, sessionPath);
  bool listOk = buildFinalList(sessionName(), false);
  if (!listOk) Serial.println("The final list could not be written. Check the SD card, then type FINAL.");
  startPattern(listOk ? P_STOP : P_ERROR);
}

// Called every time a NEW card is read by the reader.
void handleTap(const char* uidStr, uint64_t id) {
  if (!sessionActive) {
    Serial.printf("TAP %s ignored: no session (press button 1 or type START)\n", uidStr);
    startPattern(P_NOSESSION);
    return;
  }
  if (!findStudent(id) && registerNewCard(uidStr, id)) {
    Serial.printf("NEW CARD %s added to %s: fill in the names on the PC (USB drive), then RELOAD\n", uidStr, FILE_STUDENTS);
  }
  if (alreadySeen(id)) {
    Serial.printf("TAP %s DUPLICATE\n", uidStr);
    startPattern(P_DUP);
    return;
  }
  if (seen.size() >= MAX_SEEN) {
    fail("Session is full.");
    return;
  }
  const StudentRec* st = findStudent(id);
  if (isPlaceholder(st)) st = nullptr;
  const char* surname = st ? st->surname : "UNKNOWN";
  const char* names = st ? st->names : "";
  const char* mat = st ? st->matricule : "";
  char d[11];
  char t[16];
  stampNow(d, sizeof(d), t, sizeof(t));
  char line[160];
  snprintf(line, sizeof(line), "%s,%s,%s,%s,%s,%s,%s", uidStr, surname, names, mat, d, t, st ? "PRESENT" : "UNKNOWN");
  if (!appendLine(sessionPath, line)) {
    sdOk = false;
    fail("SD write failed. Check the card, then type INIT.");
    return;
  }
  seen.push_back(id);
  if (st) presentCount++;
  else unknownCount++;
  snprintf(lastSurname, sizeof(lastSurname), "%s", surname);
  snprintf(lastNames, sizeof(lastNames), "%s", st ? names : uidStr);
  snprintf(lastMat, sizeof(lastMat), "%s", mat);
  startPattern(st ? P_OK : P_UNKNOWN);
  Serial.printf("TAP %s | %s %s | %s | %s %s\n", uidStr, surname, names, mat, d, t);
}

// ------------------------------ I2C HELPER ---------------------------------
bool i2cPresent(uint8_t addr) {
  Wire.beginTransmission(addr);
  return Wire.endTransmission() == 0;
}

// ------------------------------ RESTART ------------------------------------
void rebootNow() {
  Serial.println("Restarting...");
  Serial.flush();
  delay(200);
  ESP.restart();
}

// ------------------------------ USB DRIVE MODE -----------------------------
#if USE_DRIVE_MODE
uint32_t mscSectorSize = 512;
bool usbStarted = false;
volatile bool usbMounted = false;
volatile bool usbSuspended = false;
uint32_t autoBlockUntilMs = 0;
uint32_t driveLastHostMs = 0;
RTC_NOINIT_ATTR uint32_t autoBlockMagic;   // survives a software restart
constexpr uint32_t AUTO_BLOCK_MAGIC = 0xA17E0001;

// The PC asks for data: read sectors from the SD card and hand them over.
static int32_t onMscRead(uint32_t lba, uint32_t offset, void* buffer, uint32_t bufsize) {
  uint32_t first = lba + offset / mscSectorSize;
  uint32_t count = bufsize / mscSectorSize;
  uint8_t* out = (uint8_t*)buffer;
  for (uint32_t i = 0; i < count; i++) {
    if (!SD.readRAW(out + i * mscSectorSize, first + i)) return -1;
  }
  return (int32_t)(count * mscSectorSize);
}

// The PC sends data (copy, delete, edit a file): write the sectors to the SD card.
static int32_t onMscWrite(uint32_t lba, uint32_t offset, uint8_t* buffer, uint32_t bufsize) {
  uint32_t first = lba + offset / mscSectorSize;
  uint32_t count = bufsize / mscSectorSize;
  for (uint32_t i = 0; i < count; i++) {
    if (!SD.writeRAW(buffer + i * mscSectorSize, first + i)) return -1;
  }
  return (int32_t)(count * mscSectorSize);
}

// The PC sends start/stop/eject commands (for example when you click "Eject").
static bool onMscStartStop(uint8_t power_condition, bool start, bool load_eject) {
  (void)power_condition;
  if (load_eject && !start) mscEjected = true;   // the PC ejected the drive
  if (load_eject && start) mscEjected = false;
  return true;
}

// The USB driver tells us when a computer connects or leaves.
static void onUsbEvent(void* arg, esp_event_base_t base, int32_t id, void* data) {
  (void)arg;
  (void)data;
  if (base != ARDUINO_USB_EVENTS) return;
  switch (id) {
    case ARDUINO_USB_STARTED_EVENT: usbMounted = true; usbSuspended = false; break;
    case ARDUINO_USB_STOPPED_EVENT: usbMounted = false; break;
    case ARDUINO_USB_SUSPEND_EVENT: usbSuspended = true; break;
    case ARDUINO_USB_RESUME_EVENT: usbSuspended = false; break;
    default: break;
  }
}

bool usbHostPresent() {
  return usbMounted && !usbSuspended;
}

// Prepares the USB drive object and switches the native USB-C port on (only once per power-up).
bool usbSetup() {
  if (usbStarted) return true;
  if (!sdOk) return false;
  size_t sectors = SD.numSectors();
  mscSectorSize = (uint32_t)SD.sectorSize();
  if (sectors == 0 || mscSectorSize == 0) return false;
  USB.manufacturerName("ice");
  USB.productName("Smart Attendance");
  msc.vendorID("ATTEND");
  msc.productID("SD card");
  msc.productRevision("1.0");
  msc.onRead(onMscRead);
  msc.onWrite(onMscWrite);
  msc.onStartStop(onMscStartStop);
  msc.mediaPresent(false);   // the PC sees an empty slot until drive mode starts
  if (!msc.begin((uint32_t)sectors, (uint16_t)mscSectorSize)) return false;
  USB.onEvent(onUsbEvent);
  USB.begin();   // can only be called once per power-up
  usbStarted = true;
  return true;
}

// Gives the SD card to the computer. automatic = true when a computer was detected, false when a button/command asked for it.
bool enterDriveMode(bool automatic) {
  if (driveMode) return true;
  if (sessionActive) return automatic ? false : fail("Stop the session first (hold button 1), then enter drive mode.");
  if (!sdOk) return automatic ? false : fail("No SD card: nothing to show as a drive.");
  if (!usbSetup()) return fail("USB drive could not be created.");
  mscEjected = false;
  driveHostSeen = usbHostPresent();
  driveLastHostMs = millis();
  msc.mediaPresent(true);
  driveMode = true;
  Serial.println(automatic ? "DRIVE MODE (automatic): the SD card is now a drive on the computer. Eject it, then unplug."
                           : "DRIVE MODE: connect the USB-C port marked USB (the native one, not COM) to a computer. Eject the drive, then unplug or hold button 2 for 3 s.");
  startPattern(P_DRIVE);
  return true;
}

// Leaves drive mode by restarting, so the firmware reads the card fresh.
void leaveDriveMode() {
  if (mscEjected) autoBlockMagic = AUTO_BLOCK_MAGIC;
  Serial.println(mscEjected ? "Leaving drive mode (the drive was ejected)." : "Leaving drive mode. Tip: eject the drive on the computer first.");
  rebootNow();
}

// Called from loop(): opens the drive by itself when a computer appears, and closes it when the computer is gone.
void usbUpdate() {
  if (!usbStarted) return;
  bool present = usbHostPresent();
  uint32_t now = millis();
  if (!driveMode) {
#if AUTO_DRIVE_MODE
    static bool noticePrinted = false;
    usbWaiting = present && sessionActive;
    if (usbWaiting && !noticePrinted) {
      Serial.println("A computer is connected: stop the session and the SD card will appear as a drive.");
      noticePrinted = true;
    }
    if (!usbWaiting) noticePrinted = false;
    if (present && !sessionActive && now >= autoBlockUntilMs) enterDriveMode(true);
#endif
  } else {
    if (present) {
      driveHostSeen = true;
      driveLastHostMs = now;
    } else if (driveHostSeen && now - driveLastHostMs >= DRIVE_EXIT_DELAY_MS) {
      leaveDriveMode();
    }
  }
}
#else
bool usbHostPresent() { return false; }
bool enterDriveMode(bool automatic) {
  (void)automatic;
  return fail("Drive mode is not built in (USE_DRIVE_MODE is 0).");
}
void leaveDriveMode() { rebootNow(); }
void usbUpdate() {}
#endif

// ------------------------------ INFO (button 2, short press) ----------------
struct LastFileInfo {
  char name[64];
  uint16_t present;
  uint16_t unknown;
  bool found;
  bool live;
};

LastFileInfo lastInfo = LastFileInfo();
uint32_t infoUntilMs = 0;

void countLine(const char* line, uint16_t& present, uint16_t& unknown) {
  size_t len = strlen(line);
  if (len < 8 || line[0] == '#') return;
  if (!strcmp(line + len - 8, ",PRESENT")) present++;
  else if (!strcmp(line + len - 8, ",UNKNOWN")) unknown++;
}

void scanLastFile() {
  lastInfo = LastFileInfo();
  if (sessionActive) {
    snprintf(lastInfo.name, sizeof(lastInfo.name), "%s", sessionName());
    lastInfo.present = presentCount;
    lastInfo.unknown = unknownCount;
    lastInfo.found = true;
    lastInfo.live = true;
    return;
  }
  if (!sdOk) return;
  char best[64] = "";
  if (!findNewestSession(best, sizeof(best))) return;
  char path[96];
  snprintf(path, sizeof(path), "%s/%s", DIR_ATTENDANCE, best);
  File g = SD.open(path, FILE_READ);
  if (!g) return;
  char line[112];
  forEachLine(g, line, sizeof(line), [](char* l) { countLine(l, lastInfo.present, lastInfo.unknown); });
  g.close();
  snprintf(lastInfo.name, sizeof(lastInfo.name), "%s", best);
  lastInfo.found = true;
}

void showInfo() {
  if (driveMode) {
    Serial.println("Info is not available in drive mode.");
    return;
  }
  scanLastFile();
  infoUntilMs = millis() + INFO_SHOW_MS;
  char d[11];
  char t[9];
  clockText(d, sizeof(d), t, sizeof(t));
  if (lastInfo.found) {
    Serial.printf("INFO %s %s | %s %s | present=%u unknown=%u\n", d, t, lastInfo.live ? "session" : "last file", lastInfo.name, (unsigned)lastInfo.present, (unsigned)lastInfo.unknown);
  } else {
    Serial.printf("INFO %s %s | no attendance files yet\n", d, t);
  }
  startPattern(P_INFO);
}

// ------------------------------ OLED SCREEN --------------------------------
#if USE_OLED
// One screen = up to 6 lines of text at given heights. The OLED is only rewritten when the text changes,
// because sending the 1 KB screen over I2C blocks the loop for a while.
struct Screen {
  char line[6][22];
  uint8_t y[6];
  uint8_t n;
  void add(uint8_t row, const char* text) {
    if (n >= 6) return;
    y[n] = row;
    snprintf(line[n++], sizeof(line[0]), "%s", text);
  }
};

Screen shown = Screen();

void render(const Screen& s) {
  if (s.n == shown.n && !memcmp(&s, &shown, sizeof(Screen))) return;
  shown = s;
  oled.clearDisplay();
  for (uint8_t i = 0; i < s.n; i++) {
    oled.setCursor(0, s.y[i]);
    oled.print(s.line[i]);
  }
  oled.display();
}

void drawDriveScreen(Screen& s) {
  s.add(0, "USB DRIVE MODE");
  s.add(12, driveHostSeen ? "The SD card is now a" : "Waiting for a PC on");
  s.add(22, driveHostSeen ? "drive on the computer" : "port USB (not COM)");
  if (driveHostSeen) s.add(36, mscEjected ? "Ejected: safe to exit" : "Eject on the PC first");
  s.add(50, "Hold btn2 3s to exit");
}

void drawInfoScreen(Screen& s, const char* d, const char* t) {
  char buf[32];
  snprintf(buf, sizeof(buf), "TIME %s", t);
  s.add(0, buf);
  s.add(10, d);
  s.add(24, lastInfo.found ? (lastInfo.live ? "Session running:" : "Last file:") : "No files yet");
  s.add(34, lastInfo.name);
  if (lastInfo.found) {
    snprintf(buf, sizeof(buf), "Present:%u Unk:%u", (unsigned)lastInfo.present, (unsigned)lastInfo.unknown);
    s.add(46, buf);
  }
}

void drawMainScreen(Screen& s, const char* d, const char* t) {
  char buf[32];
  if (usbWaiting) s.add(0, "USB PC: stop session");
  else if (!sdOk) s.add(0, "ERROR: SD CARD");
  else s.add(0, sessionActive ? "SESSION: ACTIVE" : "READY: btn1=start");
  if (rtcOk) snprintf(buf, sizeof(buf), "%s %s", d, t);
  else if (sessionActive) {
    char e[16];
    char dd[11];
    stampNow(dd, sizeof(dd), e, sizeof(e));
    snprintf(buf, sizeof(buf), "NO CLOCK %s", e);
  } else snprintf(buf, sizeof(buf), "NO CLOCK (SETTIME)");
  s.add(10, buf);
  snprintf(buf, sizeof(buf), "Present:%u Unk:%u%s", (unsigned)presentCount, (unsigned)unknownCount, muted ? " M" : "");
  s.add(20, buf);
  s.add(32, lastSurname);
  s.add(42, lastNames);
  s.add(52, lastMat);
}

uint32_t lastDraw = 0;
void drawScreen() {
  if (!oledOk || millis() - lastDraw < 500) return;
  lastDraw = millis();
  Screen s = Screen();
  if (driveMode) {
    drawDriveScreen(s);
  } else {
    char d[11];
    char t[9];
    clockText(d, sizeof(d), t, sizeof(t));
    if (millis() < infoUntilMs) drawInfoScreen(s, d, t);
    else drawMainScreen(s, d, t);
  }
  render(s);
}
#else
void drawScreen() {}
#endif

// ------------------------- SERIAL COMMANDS (PC) -----------------------------
void printHelp() {
  Serial.println("Commands (type then press Enter):");
  Serial.println("  HELP                         this list");
  Serial.println("  STATUS                       clock, SD card, students, session");
  Serial.println("  TIME                         show the clock");
  Serial.println("  SETTIME YYYY-MM-DD HH:MM:SS  set the clock");
  Serial.println("  START / STOP                 start or stop a session");
  Serial.println("  LIST                         list the session files and the final lists on the card");
  Serial.println("  DUMP <file>                  print one file (name from LIST)");
  Serial.println("  FINAL [file]                 build and show the sorted final list (newest session, or the named file)");
  Serial.println("  STUDENTS                     show the first students loaded");
  Serial.println("  RELOAD                       read /students.csv again");
  Serial.println("  INIT                         restart the SD card after a problem");
  Serial.println("  MUTE                         mute or unmute the buzzer");
  Serial.println("  DRIVE                        show the SD card as a USB drive now (also automatic when a computer is plugged in)");
  Serial.println("  INFO                         show time and the count of the last file (same as button 2)");
  Serial.println("  REBOOT                       restart (also leaves drive mode)");
}

void printStatus() {
  Serial.printf("Clock: %s | SD card: %s | Students: %u | Session: %s | Buzzer: %s\n",
                rtcOk ? "OK" : "NOT READY", sdOk ? "OK" : "NOT READY", (unsigned)students.size(),
                sessionActive ? "ACTIVE" : "stopped", muted ? "muted" : "on");
  Serial.printf("Drive mode: %s\n", driveMode ? "ON" : "off");
  Serial.printf("USB computer: %s | automatic drive mode: %s\n", usbHostPresent() ? "connected" : "no", AUTO_DRIVE_MODE ? "on" : "off");
}

void printTime() {
  if (!rtcOk) { Serial.println("Clock not ready. Use SETTIME YYYY-MM-DD HH:MM:SS"); return; }
  char d[11];
  char t[9];
  clockText(d, sizeof(d), t, sizeof(t));
  Serial.printf("%s %s\n", d, t);
}

void cmdSetTime(const char* arg) {
  int y, mo, d, h, mi, s;
  if (!arg || sscanf(arg, "%d-%d-%d %d:%d:%d", &y, &mo, &d, &h, &mi, &s) != 6) {
    Serial.println("Usage: SETTIME 2026-10-25 14:30:00");
    return;
  }
  if (y < 2024 || y > 2099 || mo < 1 || mo > 12 || d < 1 || d > 31 || h < 0 || h > 23 || mi < 0 || mi > 59 || s < 0 || s > 59) {
    Serial.println("Those numbers are not a valid date and time.");
    return;
  }
  rtc.adjust(DateTime(y, mo, d, h, mi, s));
  rtcOk = true;
  Serial.print("Clock set to ");
  printTime();
}

void listFolder(const char* folder, const char* title) {
  Serial.printf("%s (%s):\n", title, folder);
  File dir = SD.open(folder);
  if (!dir || !dir.isDirectory()) { Serial.println("  none yet"); return; }
  int count = 0;
  File f = dir.openNextFile();
  while (f) {
    if (!f.isDirectory()) {
      Serial.printf("  %s  (%u bytes)\n", f.name(), (unsigned)f.size());
      count++;
    }
    f = dir.openNextFile();
  }
  dir.close();
  Serial.printf("  %d file(s)\n", count);
}

void listFiles() {
  if (!sdOk) { Serial.println("SD card not ready."); return; }
  listFolder(DIR_ATTENDANCE, "Session files");
  listFolder(DIR_FINAL, "Final lists");
}

void dumpFile(const char* name) {
  if (!sdOk) { Serial.println("SD card not ready."); return; }
  if (!name || !*name || strchr(name, '/') || strstr(name, "..")) {
    Serial.println("Usage: DUMP <file name shown by LIST>");
    return;
  }
  char path[96];
  snprintf(path, sizeof(path), "%s/%s", DIR_ATTENDANCE, name);
  File f = SD.open(path, FILE_READ);
  if (!f) {
    snprintf(path, sizeof(path), "%s/%s", DIR_FINAL, name);
    f = SD.open(path, FILE_READ);
  }
  if (!f) { Serial.println("File not found."); return; }
  Serial.printf("----- %s -----\n", name);
  uint8_t buf[128];
  while (f.available()) {
    int n = f.read(buf, sizeof(buf));
    if (n <= 0) break;
    Serial.write(buf, (size_t)n);
  }
  f.close();
  Serial.println("----- end -----");
}

void showStudents() {
  Serial.printf("%u students loaded\n", (unsigned)students.size());
  size_t shown = students.size() < 20 ? students.size() : 20;
  for (size_t i = 0; i < shown; i++) {
    char uid[11];
    uint64_t v = students[i].id;
    for (int k = 9; k >= 0; k--) {
      uid[k] = "0123456789ABCDEF"[v & 0xF];
      v >>= 4;
    }
    uid[10] = 0;
    Serial.printf("  %s  %s  %s  %s\n", uid, students[i].surname, students[i].names, students[i].matricule);
  }
}

void cmdFinal(const char* arg) {
  if (!sdOk) { Serial.println("SD card not ready."); return; }
  char name[64];
  if (arg && *arg) {
    if (strchr(arg, '/') || strstr(arg, "..")) { Serial.println("Usage: FINAL [session file name from LIST]"); return; }
    snprintf(name, sizeof(name), "%s", arg);
  } else if (!findNewestSession(name, sizeof(name))) {
    Serial.println("No session files yet.");
    return;
  }
  if (!buildFinalList(name, true)) Serial.println("The final list could not be built. Check the file name with LIST.");
}

void toggleMute() {
  muted = !muted;
  Serial.println(muted ? "Buzzer muted" : "Buzzer on");
  startPattern(P_MUTE);
}

struct Command {
  const char* name;
  void (*run)(const char* arg);
  bool usesSd;   // not allowed in drive mode: the PC owns the SD card
};

const Command COMMANDS[] = {
  {"HELP", [](const char*) { printHelp(); }, false},
  {"STATUS", [](const char*) { printStatus(); }, false},
  {"TIME", [](const char*) { printTime(); }, false},
  {"SETTIME", cmdSetTime, false},
  {"START", [](const char*) { startSession(); }, true},
  {"STOP", [](const char*) { stopSession(); }, true},
  {"LIST", [](const char*) { listFiles(); }, true},
  {"DUMP", dumpFile, true},
  {"FINAL", cmdFinal, true},
  {"STUDENTS", [](const char*) { showStudents(); }, false},
  {"RELOAD", [](const char*) { Serial.printf("%u students loaded\n", (unsigned)(sdOk ? loadStudents() : 0)); }, true},
  {"INIT", [](const char*) { Serial.println(mountSd() ? "SD card OK" : "SD card FAILED"); }, true},
  {"MUTE", [](const char*) { toggleMute(); }, false},
  {"DRIVE", [](const char*) { enterDriveMode(false); }, false},
  {"INFO", [](const char*) { showInfo(); }, false},
  {"REBOOT", [](const char*) { rebootNow(); }, false},
};

void handleCommand(char* line) {
  char* arg = strchr(line, ' ');
  if (arg) {
    *arg++ = 0;
    while (*arg == ' ') arg++;
  }
  for (char* p = line; *p; p++) *p = (char)toupper((unsigned char)*p);
  for (const Command& c : COMMANDS) {
    if (strcmp(line, c.name)) continue;
    if (driveMode && c.usesSd) Serial.println("Not available in drive mode (the PC owns the SD card). Type REBOOT to leave drive mode.");
    else c.run(arg);
    return;
  }
  Serial.println("Unknown command. Type HELP.");
}

char cmdBuf[96];
size_t cmdLen = 0;

void serialUpdate() {
  while (Serial.available()) {
    char c = (char)Serial.read();
    if (c == '\r' || c == '\n') {
      if (cmdLen > 0) {
        cmdBuf[cmdLen] = 0;
        cmdLen = 0;
        handleCommand(cmdBuf);
      }
    } else if (cmdLen < sizeof(cmdBuf) - 1) {
      cmdBuf[cmdLen++] = c;
    }
  }
}

// ------------------------------ SETUP (runs once) ---------------------------
void setup() {
  pinMode(PIN_LED_GREEN, OUTPUT);
  pinMode(PIN_LED_RED, OUTPUT);
  pinMode(PIN_BUZZER, OUTPUT);
  pinMode(PIN_LED_POWER, OUTPUT);
  digitalWrite(PIN_BUZZER, LOW);
  btnSession.begin(PIN_BTN_SESSION);
  btnInfo.begin(PIN_BTN_INFO);
  Serial.begin(115200);
  delay(1200);   // time for the PC to open the serial monitor
  Serial.println();
  Serial.println("=== Smart Attendance System ===");
  Wire.begin(PIN_SDA, PIN_SCL);
  Wire.setClock(400000);   // DS3231 and SSD1306 both support 400 kHz: the screen updates 4x faster
  rtcOk = rtc.begin(&Wire);
  if (!rtcOk) {
    Serial.println("RTC not found: check SDA=GPIO9, SCL=GPIO8 and the 3V3 wire.");
  } else if (rtc.lostPower()) {   // the DS3231 stop flag is set: its time cannot be trusted
    rtcOk = false;
    Serial.println("RTC lost power: set it with SETTIME YYYY-MM-DD HH:MM:SS (the system still works, without dates)");
  }
#if USE_OLED
  uint8_t oledAddr = 0;
  if (i2cPresent(OLED_ADDR)) oledAddr = OLED_ADDR;
  else if (i2cPresent(OLED_ADDR ^ 0x01)) oledAddr = OLED_ADDR ^ 0x01;   // many modules use 0x3D instead of 0x3C
  if (oledAddr) {
    oledOk = oled.begin(SSD1306_SWITCHCAPVCC, oledAddr, true, false);   // false: I2C is already started
    Serial.printf("OLED found at 0x%02X, init %s\n", oledAddr, oledOk ? "OK" : "FAILED");
  } else {
    Serial.println("OLED not found at 0x3C or 0x3D: check VCC, GND, SDA=GPIO9, SCL=GPIO8.");
  }
  if (oledOk) {
    oled.setTextSize(1);
    oled.setTextColor(SSD1306_WHITE);
    oled.setTextWrap(false);
    oled.clearDisplay();
    oled.setCursor(0, 0);
    oled.print("SMART ATTENDANCE");
    oled.setCursor(0, 12);
    oled.print("Starting...");
    oled.display();
  }
#endif
  if (mountSd()) {
    size_t n = loadStudents();
    Serial.printf("SD card OK, %u students loaded\n", (unsigned)n);
    if (n == 0) Serial.println("Warning: /students.csv is missing or empty.");
  } else {
    Serial.println("SD card not found: check wiring and that it is FAT32.");
  }
  RFID.begin(9600, SERIAL_8N1, PIN_RFID_RX, -1);   // receive only
#if USE_DRIVE_MODE
  if (esp_reset_reason() == ESP_RST_SW && autoBlockMagic == AUTO_BLOCK_MAGIC) autoBlockUntilMs = millis() + AUTO_BLOCK_MS;   // restarted after an eject: do not reopen the drive at once
  autoBlockMagic = 0;
#if AUTO_DRIVE_MODE
  if (sdOk) {
    Serial.println(usbSetup() ? "USB ready: plug a computer into the native USB-C port to see the SD card." : "USB drive setup failed.");
  }
#endif
#endif
  printStatus();
  Serial.println("Type HELP for the list of commands.");
  startPattern(sdOk ? P_BOOT : P_ERROR);
}

// ------------------------------ LOOP (runs forever) ------------------------
void loop() {
  patternUpdate();
  idleLedUpdate();
  powerLedUpdate();

  BtnEvent e1 = btnSession.poll(LONG_PRESS_MS);   // button 1: short = start, long (1.5 s) = stop
  if (e1 == BTN_SHORT) {
    if (!sessionActive) startSession();
    else Serial.println("Session running. Hold button 1 for 1.5 s to stop it.");
  } else if (e1 == BTN_LONG && sessionActive) {
    stopSession();
  }

  BtnEvent e2 = btnInfo.poll(DRIVE_LONG_PRESS_MS);   // button 2: short = info, long (3 s) = USB drive mode
  if (e2 == BTN_SHORT) showInfo();
  else if (e2 == BTN_LONG) {
    if (driveMode) leaveDriveMode();
    else enterDriveMode(false);
  }

  while (RFID.available()) {
    char uid[11];
    uint8_t b = (uint8_t)RFID.read();
    if (driveMode) continue;   // in drive mode the SD card belongs to the PC
    if (rdm.feed(b, uid)) {   // true when a full, valid 14-byte frame arrived
      uint64_t id;
      if (!parseUid10(uid, id)) continue;
      uint32_t now = millis();
      if (id == lastUid && now - lastSeenMs < SAME_CARD_IGNORE_MS) {   // same card still on the reader
        lastSeenMs = now;
        continue;
      }
      lastUid = id;
      lastSeenMs = now;
      handleTap(uid, id);
    }
  }

  usbUpdate();
  serialUpdate();
  drawScreen();
}
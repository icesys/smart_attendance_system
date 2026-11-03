// parsers.h - plain C++ helpers with NO Arduino code, so they can be tested on a PC too.
#pragma once
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// Converts one hex character ('0'-'9', 'A'-'F', 'a'-'f') to its value 0-15; returns -1 if it is not hex.
inline int hexVal(int c) {
  if (c >= '0' && c <= '9') return c - '0';
  if (c >= 'A' && c <= 'F') return c - 'A' + 10;
  if (c >= 'a' && c <= 'f') return c - 'a' + 10;
  return -1;
}

// Reads the bytes sent by the RDM6300 and recognises one complete, correct frame.
// A frame has 14 bytes: 0x02, 10 ASCII hex characters (the card), 2 ASCII hex characters
// (checksum = XOR of the 5 card bytes), and 0x03.
class Rdm6300Parser {
 public:
  bool feed(uint8_t c, char uid10[11]) {
    if (n_ == 0) {
      if (c == 0x02) buf_[n_++] = c;
      return false;
    }
    if (c == 0x02) {
      n_ = 0;
      buf_[n_++] = c;
      return false;
    }
    buf_[n_++] = c;
    if (n_ < 14) return false;
    n_ = 0;
    if (buf_[13] != 0x03) return false;
    uint8_t x = 0;
    for (int i = 0; i < 5; i++) {
      int h = hexVal(buf_[1 + 2 * i]);
      int l = hexVal(buf_[2 + 2 * i]);
      if (h < 0 || l < 0) return false;
      x ^= (uint8_t)((h << 4) | l);
    }
    int ch = hexVal(buf_[11]);
    int cl = hexVal(buf_[12]);
    if (ch < 0 || cl < 0) return false;
    if (x != (uint8_t)((ch << 4) | cl)) return false;
    for (int i = 0; i < 10; i++) {
      char k = (char)buf_[1 + i];
      if (k >= 'a' && k <= 'f') k = (char)(k - 32);
      uid10[i] = k;
    }
    uid10[10] = 0;
    return true;
  }

 private:
  uint8_t buf_[14] = {0};
  uint8_t n_ = 0;
};

// Turns the text "0A00B2C3D4" into a 40-bit number. Returns false if it is not exactly 10 hex digits.
inline bool parseUid10(const char* s, uint64_t& out) {
  if (strlen(s) != 10) return false;
  uint64_t v = 0;
  for (int i = 0; i < 10; i++) {
    int h = hexVal(s[i]);
    if (h < 0) return false;
    v = (v << 4) | (uint64_t)h;
  }
  out = v;
  return true;
}

// ---- text helpers used by the student list and the final list ----

// Copies one text field into a fixed-size buffer. It trims spaces and line ends, replaces the characters
// that would break the CSV and tab-separated files (comma, semicolon, quote, tab) by a space, and cuts the text to fit.
inline void copyField(char* dst, size_t n, const char* src) {
  while (*src == ' ' || *src == '\t') src++;
  size_t len = strlen(src);
  while (len && (src[len - 1] == ' ' || src[len - 1] == '\t' || src[len - 1] == '\r' || src[len - 1] == '\n')) len--;
  size_t j = 0;
  for (size_t i = 0; i < len && j + 1 < n; i++) {
    char c = src[i];
    if (c == ',' || c == ';' || c == '"' || c == '\t') c = ' ';
    dst[j++] = c;
  }
  dst[j] = 0;
}

// One student of the list: card number, surname, first name(s) and matricule (registration number).
struct StudentRec {
  uint64_t id;
  char surname[32];
  char names[32];
  char matricule[16];
};

// Reads one line "UID,Surname,Names,Matricule" of students.csv. The line text is modified while reading.
// Also accepts shorter lines (UID,Surname or UID,Surname,Names). Returns false for empty lines,
// comment lines (starting with #), the header line and bad lines.
inline bool parseStudentLine(char* line, StudentRec& out) {
  while (*line == ' ' || *line == '\t') line++;
  if (*line == 0 || *line == '#' || *line == '\r' || *line == '\n') return false;
  char* f[4];
  int n = 0;
  f[n++] = line;
  for (char* p = line; *p && n < 4; p++) {
    if (*p == ',') {
      *p = 0;
      f[n++] = p + 1;
    }
  }
  char uid[16];
  copyField(uid, sizeof(uid), f[0]);
  uint64_t id;
  if (!parseUid10(uid, id)) return false;
  if (n < 2) return false;
  copyField(out.surname, sizeof(out.surname), f[1]);
  if (n >= 3) copyField(out.names, sizeof(out.names), f[2]); else out.names[0] = 0;
  if (n >= 4) copyField(out.matricule, sizeof(out.matricule), f[3]); else out.matricule[0] = 0;
  if (out.surname[0] == 0) strcpy(out.surname, "(no name)");
  out.id = id;
  return true;
}

// ---- sorting (for the final list) ----

// Makes a sort key: capital letters, and the common accented letters (UTF-8) turned into their plain letter.
inline void foldKey(const char* s, char* out, size_t n) {
  static const char T1[] = "AAAAAAACEEEEIIIIDNOOOOO*OUUUUYTS";
  static const char T2[] = "AAAAAAACEEEEIIIIDNOOOOO/OUUUUYTY";
  size_t j = 0;
  for (size_t i = 0; s[i] && j + 1 < n; i++) {
    unsigned char c = (unsigned char)s[i];
    if (c == 0xC3 && s[i + 1]) {
      unsigned char d = (unsigned char)s[i + 1];
      if (d >= 0x80 && d <= 0xBF) {
        out[j++] = (d < 0xA0) ? T1[d - 0x80] : T2[d - 0xA0];
        i++;
        continue;
      }
    }
    if (c >= 'a' && c <= 'z') c = (unsigned char)(c - 32);
    out[j++] = (char)c;
  }
  out[j] = 0;
}

// Compares two texts the way a dictionary does: capitals and accents ignored. Returns <0, 0 or >0.
inline int cmpFolded(const char* a, const char* b) {
  char ka[48];
  char kb[48];
  foldKey(a, ka, sizeof(ka));
  foldKey(b, kb, sizeof(kb));
  return strcmp(ka, kb);
}

// ---- one row of the final list ----
struct ListRow {
  char uid[11];
  char surname[32];
  char names[32];
  char matricule[16];
  bool unknown;
  uint16_t seq;
};

// Reads one line of a session file: uid,surname,names,matricule,date,time,result.
// Returns true only for PRESENT and UNKNOWN lines (the header and the # lines are rejected).
inline bool parseSessionLine(char* line, ListRow& out, uint16_t seq) {
  char* f[7];
  int n = 0;
  f[n++] = line;
  for (char* p = line; *p; p++) {
    if (*p == ',') {
      if (n >= 7) return false;
      *p = 0;
      f[n++] = p + 1;
    }
  }
  if (n != 7) return false;
  char res[12];
  copyField(res, sizeof(res), f[6]);
  bool unknown;
  if (!strcmp(res, "PRESENT")) unknown = false;
  else if (!strcmp(res, "UNKNOWN")) unknown = true;
  else return false;
  copyField(out.uid, sizeof(out.uid), f[0]);
  copyField(out.surname, sizeof(out.surname), f[1]);
  copyField(out.names, sizeof(out.names), f[2]);
  copyField(out.matricule, sizeof(out.matricule), f[3]);
  out.unknown = unknown;
  out.seq = seq;
  return true;
}

// Sort order of the final list: students alphabetically by surname, then first name(s), then card number.
// Unknown cards come last, in the order they were tapped.
inline bool rowLess(const ListRow& a, const ListRow& b) {
  if (a.unknown != b.unknown) return !a.unknown;
  if (!a.unknown) {
    int c = cmpFolded(a.surname, b.surname);
    if (c != 0) return c < 0;
    c = cmpFolded(a.names, b.names);
    if (c != 0) return c < 0;
    c = strcmp(a.uid, b.uid);
    if (c != 0) return c < 0;
  }
  return a.seq < b.seq;
}

constexpr char LIST_HEADER[] = "UID\tSurname\tName(s)\tMatricule";

// Builds one tab-separated row: UID <tab> Surname <tab> Name(s) <tab> Matricule.
inline void formatListRow(const ListRow& r, char* out, size_t n) {
  snprintf(out, n, "%s\t%s\t%s\t%s", r.uid, r.surname, r.names, r.matricule);
}

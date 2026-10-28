// parsers.h - plain C++ helpers with NO Arduino code, so they can be tested on a PC too.
#pragma once                                      // include this file only once per build
#include <stddef.h>                               // size_t
#include <stdint.h>                               // uint8_t, uint64_t
#include <stdio.h>                                // snprintf
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

// ---- text helpers used by the student list and the final list ----

// Copies one text field into a fixed-size buffer. It trims spaces and line ends, replaces the characters
// that would break the CSV and tab-separated files (comma, semicolon, quote, tab) by a space, and cuts the text to fit.
inline void copyField(char* dst, size_t n, const char* src) {     // dst has room for n characters including the closing '\0'
  while (*src == ' ' || *src == '\t') src++;                      // skip spaces before the text
  size_t len = strlen(src);                                       // length of the rest of the text
  while (len && (src[len - 1] == ' ' || src[len - 1] == '\t' || src[len - 1] == '\r' || src[len - 1] == '\n')) len--; // ignore spaces and line ends at the end
  size_t j = 0;                                                   // how many characters we copied
  for (size_t i = 0; i < len && j + 1 < n; i++) {                 // copy, leaving room for the closing '\0'
    char c = src[i];                                              // the character to copy
    if (c == ',' || c == ';' || c == '"' || c == '\t') c = ' ';   // these would break the files, so use a space
    dst[j++] = c;                                                 // store it
  }                                                               // end of the copy loop
  dst[j] = 0;                                                     // close the text
}                                                                 // end of copyField

// One student of the list: card number, surname, first name(s) and matricule (registration number).
struct StudentRec {                               // a small record type
  uint64_t id;                                    // card number as a 40-bit number (fast to compare)
  char surname[32];                               // surname, up to 31 characters
  char names[32];                                 // first name(s), up to 31 characters
  char matricule[16];                             // registration number, up to 15 characters
};                                                // end of StudentRec

// Reads one line "UID,Surname,Names,Matricule" of students.csv. The line text is modified while reading.
// Also accepts shorter lines (UID,Surname or UID,Surname,Names). Returns false for empty lines,
// comment lines (starting with #), the header line and bad lines.
inline bool parseStudentLine(char* line, StudentRec& out) {       // "out" receives the result
  while (*line == ' ' || *line == '\t') line++;                   // skip spaces at the start of the line
  if (*line == 0 || *line == '#' || *line == '\r' || *line == '\n') return false; // empty line or comment: nothing to read
  char* f[4];                                                     // pointers to the four fields
  int n = 0;                                                      // how many fields we found
  f[n++] = line;                                                  // the first field starts at the beginning of the line
  for (char* p = line; *p && n < 4; p++) {                        // look for the commas that separate the fields
    if (*p == ',') {                                              // a separator
      *p = 0;                                                     // end the previous field here
      f[n++] = p + 1;                                             // the next field starts after the comma
    }                                                             // end of "separator"
  }                                                               // end of the search (the last field keeps any extra commas)
  char uid[16];                                                   // the card number as text
  copyField(uid, sizeof(uid), f[0]);                              // trim it
  uint64_t id;                                                    // will hold the UID as a number
  if (!parseUid10(uid, id)) return false;                         // the header line "uid,surname,..." fails here and is skipped
  if (n < 2) return false;                                        // a student needs at least a surname
  copyField(out.surname, sizeof(out.surname), f[1]);              // surname
  if (n >= 3) copyField(out.names, sizeof(out.names), f[2]); else out.names[0] = 0; // first names, or empty
  if (n >= 4) copyField(out.matricule, sizeof(out.matricule), f[3]); else out.matricule[0] = 0; // matricule (cut to 15 characters), or empty
  if (out.surname[0] == 0) strcpy(out.surname, "(no name)");      // use a placeholder if the surname is empty
  out.id = id;                                                    // store the card number in the record
  return true;                                                    // the line was valid
}                                                                 // end of parseStudentLine

// ---- sorting (for the final list) ----

// Makes a sort key: capital letters, and the common accented letters (UTF-8) turned into their plain letter.
inline void foldKey(const char* s, char* out, size_t n) {         // out has room for n characters
  static const char T1[] = "AAAAAAACEEEEIIIIDNOOOOO*OUUUUYTS";    // letters U+00C0 to U+00DF  (second UTF-8 byte 0x80 to 0x9F)
  static const char T2[] = "AAAAAAACEEEEIIIIDNOOOOO/OUUUUYTY";    // letters U+00E0 to U+00FF  (second UTF-8 byte 0xA0 to 0xBF)
  size_t j = 0;                                                   // how many characters we wrote
  for (size_t i = 0; s[i] && j + 1 < n; i++) {                    // go through the text
    unsigned char c = (unsigned char)s[i];                        // the current byte
    if (c == 0xC3 && s[i + 1]) {                                  // the first byte of an accented Latin letter
      unsigned char d = (unsigned char)s[i + 1];                  // its second byte
      if (d >= 0x80 && d <= 0xBF) {                               // inside the Latin-1 range
        out[j++] = (d < 0xA0) ? T1[d - 0x80] : T2[d - 0xA0];      // use the plain letter
        i++;                                                      // skip the second byte
        continue;                                                 // next character
      }                                                           // end of the range check
    }                                                             // end of the accent check
    if (c >= 'a' && c <= 'z') c = (unsigned char)(c - 32);        // small letter to capital letter
    out[j++] = (char)c;                                           // store the byte
  }                                                               // end of the loop
  out[j] = 0;                                                     // close the text
}                                                                 // end of foldKey

// Compares two texts the way a dictionary does: capitals and accents ignored. Returns <0, 0 or >0.
inline int cmpFolded(const char* a, const char* b) {              // like strcmp, but friendlier
  char ka[48];                                                    // sort key of a
  char kb[48];                                                    // sort key of b
  foldKey(a, ka, sizeof(ka));                                     // build the first key
  foldKey(b, kb, sizeof(kb));                                     // build the second key
  return strcmp(ka, kb);                                          // compare the keys
}                                                                 // end of cmpFolded

// ---- one row of the final list ----
struct ListRow {                                  // one student (or unknown card) of a session
  char uid[11];                                   // card number as text
  char surname[32];                               // surname
  char names[32];                                 // first name(s)
  char matricule[16];                             // registration number
  bool unknown;                                   // true for a card that is not in the student list
  uint16_t seq;                                   // position in the session file (keeps the tap order of unknown cards)
};                                                // end of ListRow

// Reads one line of a session file: uid,surname,names,matricule,date,time,result.
// Returns true only for PRESENT and UNKNOWN lines (the header and the # lines are rejected).
inline bool parseSessionLine(char* line, ListRow& out, uint16_t seq) { // "out" receives the row
  char* f[7];                                                     // pointers to the seven fields
  int n = 0;                                                      // how many fields we found
  f[n++] = line;                                                  // the first field starts at the beginning
  for (char* p = line; *p; p++) {                                 // look for the commas
    if (*p == ',') {                                              // a separator
      if (n >= 7) return false;                                   // too many fields: not one of our lines
      *p = 0;                                                     // end the previous field
      f[n++] = p + 1;                                             // the next field starts after the comma
    }                                                             // end of "separator"
  }                                                               // end of the search
  if (n != 7) return false;                                       // we need exactly seven fields
  char res[12];                                                   // the result field as text
  copyField(res, sizeof(res), f[6]);                              // trim it
  bool unknown;                                                   // PRESENT or UNKNOWN
  if (!strcmp(res, "PRESENT")) unknown = false;                   // a known student
  else if (!strcmp(res, "UNKNOWN")) unknown = true;               // an unknown card
  else return false;                                              // the header line ("result") and others are skipped
  copyField(out.uid, sizeof(out.uid), f[0]);                      // card number
  copyField(out.surname, sizeof(out.surname), f[1]);              // surname
  copyField(out.names, sizeof(out.names), f[2]);                  // first name(s)
  copyField(out.matricule, sizeof(out.matricule), f[3]);          // matricule
  out.unknown = unknown;                                          // remember the kind
  out.seq = seq;                                                  // remember the position
  return true;                                                    // a valid row
}                                                                 // end of parseSessionLine

// Sort order of the final list: students alphabetically by surname, then first name(s), then card number.
// Unknown cards come last, in the order they were tapped.
inline bool rowLess(const ListRow& a, const ListRow& b) {         // true if a must come before b
  if (a.unknown != b.unknown) return !a.unknown;                  // known students before unknown cards
  if (!a.unknown) {                                               // both are known students
    int c = cmpFolded(a.surname, b.surname);                      // compare the surnames
    if (c != 0) return c < 0;                                     // different surnames: alphabetical order
    c = cmpFolded(a.names, b.names);                              // same surname: compare the first names
    if (c != 0) return c < 0;                                     // alphabetical order
    c = strcmp(a.uid, b.uid);                                     // still equal: compare the card numbers
    if (c != 0) return c < 0;                                     // so the order is always the same
  }                                                               // end of "both known"
  return a.seq < b.seq;                                           // otherwise keep the tap order
}                                                                 // end of rowLess

// The heading line of the final list (tab-separated, so it pastes into Excel columns).
constexpr char LIST_HEADER[] = "UID\tSurname\tName(s)\tMatricule"; // the four column headings

// Builds one tab-separated row: UID <tab> Surname <tab> Name(s) <tab> Matricule.
inline void formatListRow(const ListRow& r, char* out, size_t n) { // out has room for n characters
  snprintf(out, n, "%s\t%s\t%s\t%s", r.uid, r.surname, r.names, r.matricule); // join the four columns with tabs
}                                                                 // end of formatListRow

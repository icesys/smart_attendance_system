// g++ -std=c++17 -Iinclude test/host/test_parsers.cpp -o t && ./t

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
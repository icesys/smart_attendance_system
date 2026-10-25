// g++ -std=c++17 -Iinclude test/host/test_parsers.cpp -o t && ./t

// test_parsers.cpp - runs on a PC (not on the ESP32) to check the parsers.
// Build and run:  g++ -std=c++17 -Iinclude test/host/test_parsers.cpp -o t && ./t
#include <stdio.h>                                                    // printf
#include <string.h>                                                   // strcmp, strcpy
#include "parsers.h"                                                  // the code we test

static int failures = 0;                                              // counts failed checks

static void check(bool ok, const char* what) {                        // prints PASS or FAIL for one check
  printf("%s  %s\n", ok ? "PASS" : "FAIL", what);                     // show the result
  if (!ok) failures++;                                                // count failures
}                                                                     // end of check

int main() {                                                          // test program
  // A valid frame for card 0A00B2C3D4: checksum = 0A ^ 00 ^ B2 ^ C3 ^ D4 = AF
  const uint8_t good[14] = {0x02, '0','A','0','0','B','2','C','3','D','4', 'A','F', 0x03}; // the 14 bytes
  Rdm6300Parser p;                                                    // a parser
  char uid[11] = "";                                                  // result text
  bool got = false;                                                   // did a frame complete?
  for (int i = 0; i < 14; i++) got = p.feed(good[i], uid);            // feed the bytes one by one
  check(got && !strcmp(uid, "0A00B2C3D4"), "valid frame is accepted and decoded");

  uint8_t bad[14];                                                    // a frame with a wrong checksum
  memcpy(bad, good, 14);                                              // copy the good frame
  bad[12] = 'E';                                                      // damage the checksum (AE instead of AF)
  got = false;                                                        // reset the flag
  for (int i = 0; i < 14; i++) got = p.feed(bad[i], uid);             // feed the damaged frame
  check(!got, "wrong checksum is rejected");

  got = false;                                                        // reset the flag
  const uint8_t junk[5] = {0x55, 0x10, 0x7F, 0x02, 0x00};             // noise, ends with a start byte and a stray byte
  for (int i = 0; i < 5; i++) p.feed(junk[i], uid);                   // feed noise (parser must not crash)
  for (int i = 0; i < 14; i++) got = p.feed(good[i], uid);            // a good frame right after the noise
  check(got && !strcmp(uid, "0A00B2C3D4"), "parser resynchronises after noise");

  uint64_t v = 0;                                                     // result of parseUid10
  check(parseUid10("0A00B2C3D4", v) && v == 0x0A00B2C3D4ULL, "parseUid10 reads 10 hex digits");
  check(!parseUid10("0A00B2C3D", v), "parseUid10 rejects 9 digits");
  check(!parseUid10("0A00B2C3DZ", v), "parseUid10 rejects a non-hex character");

  StudentRec s;                                                       // result of parseStudentLine
  char l1[] = "0A00B2C3D4, Tendai Moyo\r\n";                          // a normal line with spaces and a Windows line end
  check(parseStudentLine(l1, s) && s.id == 0x0A00B2C3D4ULL && !strcmp(s.name, "Tendai Moyo"), "student line is parsed");
  char l2[] = "uid,name";                                             // the header line
  check(!parseStudentLine(l2, s), "header line is skipped");
  char l3[] = "# comment";                                            // a comment line
  check(!parseStudentLine(l3, s), "comment line is skipped");
  char l4[] = "0A00B2C3D5,Smith, John";                               // a name with a comma
  check(parseStudentLine(l4, s) && !strcmp(s.name, "Smith  John"), "comma inside a name is replaced by a space");

  printf("%s\n", failures ? "SOME TESTS FAILED" : "ALL TESTS PASSED"); // summary
  return failures ? 1 : 0;                                            // exit code for scripts
}                                                                     // end of main
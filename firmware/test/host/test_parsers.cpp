// g++ -std=c++17 -Iinclude test/host/test_parsers.cpp -o t && ./t

// test_parsers.cpp - runs on a PC (not on the ESP32) to check the parsers.
// Build and run:  g++ -std=c++17 -Iinclude test/host/test_parsers.cpp -o t && ./t
#include <stdio.h>
#include <string.h>
#include <algorithm>
#include <vector>
#include "parsers.h"

static int failures = 0;

static void check(bool ok, const char* what) {
  printf("%s  %s\n", ok ? "PASS" : "FAIL", what);
  if (!ok) failures++;
}

int main() {
  const uint8_t good[14] = {0x02, '0','A','0','0','B','2','C','3','D','4', 'A','F', 0x03};
  Rdm6300Parser p;
  char uid[11] = "";
  bool got = false;
  for (int i = 0; i < 14; i++) got = p.feed(good[i], uid);
  check(got && !strcmp(uid, "0A00B2C3D4"), "valid frame is accepted and decoded");

  uint8_t bad[14];
  memcpy(bad, good, 14);
  bad[12] = 'E';
  got = false;
  for (int i = 0; i < 14; i++) got = p.feed(bad[i], uid);
  check(!got, "wrong checksum is rejected");

  got = false;
  const uint8_t junk[5] = {0x55, 0x10, 0x7F, 0x02, 0x00};
  for (int i = 0; i < 5; i++) p.feed(junk[i], uid);
  for (int i = 0; i < 14; i++) got = p.feed(good[i], uid);
  check(got && !strcmp(uid, "0A00B2C3D4"), "parser resynchronises after noise");

  uint64_t v = 0;
  check(parseUid10("0A00B2C3D4", v) && v == 0x0A00B2C3D4ULL, "parseUid10 reads 10 hex digits");
  check(!parseUid10("0A00B2C3D", v), "parseUid10 rejects 9 digits");
  check(!parseUid10("0A00B2C3DZ", v), "parseUid10 rejects a non-hex character");

  StudentRec s;
  char l1[] = "0A00B2C3D4, Moyo , Tendai Simba, 2023-EE-0145\r\n";
  check(parseStudentLine(l1, s) && s.id == 0x0A00B2C3D4ULL && !strcmp(s.surname, "Moyo") && !strcmp(s.names, "Tendai Simba") && !strcmp(s.matricule, "2023-EE-0145"),
        "student line with surname, names and matricule is parsed");
  char l2[] = "uid,surname,names,matricule";
  check(!parseStudentLine(l2, s), "header line is skipped");
  char l3[] = "# comment";
  check(!parseStudentLine(l3, s), "comment line is skipped");
  char l4[] = "0A00B2C3D5,Smith,John,AB,CD";
  check(parseStudentLine(l4, s) && !strcmp(s.matricule, "AB CD"), "comma inside the last field is replaced by a space");
  char l5[] = "0A00B2C3D6,Benali,Amina,1234567890ABCDEFGHIJ";
  check(parseStudentLine(l5, s) && strlen(s.matricule) == 15 && !strcmp(s.matricule, "1234567890ABCDE"), "matricule is cut to 15 characters");
  char l6[] = "0A00B2C3D7,Old Format Name";
  check(parseStudentLine(l6, s) && !strcmp(s.surname, "Old Format Name") && s.names[0] == 0 && s.matricule[0] == 0, "old UID,Name lines still load");
  char l7[] = "0A00B2C3D8,Diallo,Fatou";
  check(parseStudentLine(l7, s) && !strcmp(s.names, "Fatou") && s.matricule[0] == 0, "missing matricule is left empty");
  char l8[] = "NOTAUID123,Diallo,Fatou,1";
  check(!parseStudentLine(l8, s), "line with a bad card number is rejected");
  char l9[] = "0A00B2C3D9,Ka\tmara,Ibr;ahim,7";
  check(parseStudentLine(l9, s) && !strcmp(s.surname, "Ka mara") && !strcmp(s.names, "Ibr ahim"), "tabs and semicolons inside fields become spaces");

  // ---- sorting ----
  char k1[48], k2[48];
  foldKey("\xC3\x89" "b\xC3\xA8ne", k1, sizeof(k1));
  check(!strcmp(k1, "EBENE"), "accents are folded in the sort key (Ébène -> EBENE)");
  foldKey("dupont", k2, sizeof(k2));
  check(!strcmp(k2, "DUPONT"), "sort key ignores capitals");
  check(cmpFolded("Dupont", "\xC3\x89" "b\xC3\xA8ne") < 0 && cmpFolded("\xC3\x89" "b\xC3\xA8ne", "Fabre") < 0, "Dupont < Ébène < Fabre");

  // ---- reading session lines ----
  ListRow r;
  char s1[] = "0A00B2C3D4,Moyo,Tendai,2023-EE-0145,2026-10-27,14:30:03,PRESENT\r\n";
  check(parseSessionLine(s1, r, 0) && !r.unknown && !strcmp(r.uid, "0A00B2C3D4") && !strcmp(r.surname, "Moyo"), "PRESENT line is read");
  char s2[] = "0A00FFFFFF,UNKNOWN,,,2026-10-27,14:30:08,UNKNOWN";
  check(parseSessionLine(s2, r, 1) && r.unknown && !strcmp(r.surname, "UNKNOWN") && r.names[0] == 0, "UNKNOWN line is read");
  char s3[] = "uid,surname,names,matricule,date,time,result";
  check(!parseSessionLine(s3, r, 2), "session header line is skipped");
  char s4[] = "# end,2026-10-27,14:35:00,present=1,unknown=1";
  check(!parseSessionLine(s4, r, 3), "summary line is skipped");

  // ---- the final list order ----
  std::vector<ListRow> rows;
  const char* src[] = {
    "0A00000001,Moyo,Tendai,M1,d,t,PRESENT", "0A00000002,Benali,Amina,M2,d,t,PRESENT", "0A00000003,UNKNOWN,,,d,t,UNKNOWN",
    "0A00000004,Dupont,Jean Pierre,M4,d,t,PRESENT", "0A00000005,\xC3\x89" "b\xC3\xA8ne,Marie,M5,d,t,PRESENT", "0A00000006,Benali,Aicha,M6,d,t,PRESENT",
    "0A00000007,UNKNOWN,,,d,t,UNKNOWN"};
  for (size_t i = 0; i < sizeof(src) / sizeof(src[0]); i++) {
    char buf[160]; snprintf(buf, sizeof(buf), "%s", src[i]);
    ListRow row; if (parseSessionLine(buf, row, (uint16_t)rows.size())) rows.push_back(row);
  }
  std::sort(rows.begin(), rows.end(), rowLess);
  const char* expect[] = {"0A00000006", "0A00000002", "0A00000004", "0A00000005", "0A00000001", "0A00000003", "0A00000007"};
  bool order = rows.size() == 7;
  for (size_t i = 0; order && i < 7; i++) order = !strcmp(rows[i].uid, expect[i]);
  check(order, "final list: surname order (Benali Aicha, Benali Amina, Dupont, Ébène, Moyo), unknown cards last in tap order");
  char out[128]; formatListRow(rows[0], out, sizeof(out));
  check(!strcmp(out, "0A00000006\tBenali\tAicha\tM6"), "a row is tab-separated: UID, Surname, Name(s), Matricule");
  check(!strcmp(LIST_HEADER, "UID\tSurname\tName(s)\tMatricule"), "the heading line has the four requested columns");

  printf("%s\n", failures ? "SOME TESTS FAILED" : "ALL TESTS PASSED");
  return failures ? 1 : 0;
}

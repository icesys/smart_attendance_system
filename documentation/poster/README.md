# Poster (one poster on 2 × A0)

One poster of **1667 × 1189 mm**, printed on two A0 sheets (841 × 1189 mm) that are glued together. The right sheet overlaps the last **15 mm** of the left sheet.

| File | Use |
|---|---|
| `Poster_Smart_Attendance_System_A0_1_left.pdf` | Left sheet: print at 100 % on A0 |
| `Poster_Smart_Attendance_System_A0_2_right.pdf` | Right sheet: print at 100 % on A0 |
| `Poster_Smart_Attendance_System_full.pdf` | The whole poster on one page (to check it, or to print on one 1.7 m wide roll) |
| `preview.png` | Small preview |
| `poster.html` | Editable source; figures are in `img/`, photos go in `photos/` |

## Printing and gluing
1. Print both sheets at **100 % / actual size**. Do not use "fit to page".
2. If the printer leaves a white border, cut it off along the **left edge of the right sheet**. The other white borders can stay or be trimmed as you like.
3. Lay the left sheet flat. Its last 15 mm on the right are duplicated on the right sheet, so put the glue on that strip.
4. Place the right sheet on top, overlapping by 15 mm. Line up the blue line under the header and the letters of the title, then press it down.

The seam falls in the white space between the two halves, so only the header crosses it.

## Adding the photos
Create `photos/` here with `prototype.jpg` (breadboard prototype) and `cartes.jpg` (assembled boards). They appear by themselves in "Réalisation et tests". Fill in the "Résultat obtenu" column of the test table in `poster.html` at the same time.

## Exporting again after a change
```bash
google-chrome-stable --headless=new --no-pdf-header-footer --virtual-time-budget=6000 \
  --print-to-pdf=Poster_Smart_Attendance_System_full.pdf "file://$PWD/poster.html"
# left sheet: x 0-841 mm, right sheet: x 826-1667 mm (1 mm = 2.8346 pt)
gs -q -o Poster_Smart_Attendance_System_A0_1_left.pdf  -sDEVICE=pdfwrite -dDEVICEWIDTHPOINTS=2383.94 -dDEVICEHEIGHTPOINTS=3370.39 -dFIXEDMEDIA -c "<</PageOffset [0 0]>> setpagedevice" -f Poster_Smart_Attendance_System_full.pdf
gs -q -o Poster_Smart_Attendance_System_A0_2_right.pdf -sDEVICE=pdfwrite -dDEVICEWIDTHPOINTS=2383.94 -dDEVICEHEIGHTPOINTS=3370.39 -dFIXEDMEDIA -c "<</PageOffset [-2341.42 0]>> setpagedevice" -f Poster_Smart_Attendance_System_full.pdf
```

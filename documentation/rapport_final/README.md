# Rapport final : Smart Attendance System

- `Rapport_Smart_Attendance_System_FR.docx` / `.pdf`: French version.
- `Report_Smart_Attendance_System_EN.docx` / `.pdf`: English version.

The cover has the same details as the USTHB mini-project cover (`../cover.jpeg`) in a flat, print-safe design: logo, institution lines, faculty and programme (Électronique, Licence 3 LMD), "Mini-projet", title, authors (TSONGODZA Evidence, MANDEBVU Langelihle Sasha), supervisor (Mr BOUCHEFRA), picture, academic year. Colours: blue and gray only. To change these, edit the lines at the top of `tools/build_report.py` and rerun it.

It follows the outline of `../contenu du rapport.pptx`: **13 pages before the annex** (cover, contents, introduction, objectives and cahier des charges, hardware ×2, electrical diagram, block diagram, flowcharts ×2, PCB design, fabrication and tests, conclusion). Page 7 shows the complete schematic drawn as one circuit (`hardware/schematics/kicad/sas_complete`), then explains why it was split into three stacked boards. Then **3 pages of appendix**: A = the schematic split into three boards with the ribbon cables (`sas_full_system`); B = ESP32-S3 pin table, both cable pinouts and the microSD file formats; C = key code excerpts (`handleTap()`, `loop()`) with only the essential comments, plus a link to the full code on GitHub.

**Still to fill in** (dashed boxes in the document): section 5.2 (photos and assembly notes); section 5.3 (test results); and the "Bilan des objectifs" box in the conclusion.

## Regenerating
```
pip install kiutils matplotlib pillow python-docx      # graphviz (dot) also needed
python3 tools/fig_kicad.py       # schematic and PCB figures, from the KiCad files
python3 tools/fig_diagrams.py    # block diagram and flowcharts
python3 tools/build_report.py    # both .docx files
soffice --headless --convert-to pdf Rapport_Smart_Attendance_System_FR.docx Report_Smart_Attendance_System_EN.docx
```
If you edit the .docx by hand, rerunning `build_report.py` overwrites your changes.

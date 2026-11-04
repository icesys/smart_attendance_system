# hardware

| Folder | Content |
|---|---|
| [`schematics/kicad/sas_complete/`](schematics/kicad/sas_complete/) | The whole system drawn as one circuit (A3), no board connectors |
| [`schematics/kicad/sas_full_system/`](schematics/kicad/sas_full_system/) | The three boards and both ribbon cables on one A1 sheet |
| [`schematics/kicad/sas_schematics/`](schematics/kicad/sas_schematics/) | One sheet per board (hierarchical), shared symbol and footprint libraries |
| [`schematics/kicad/sas_pcb/`](schematics/kicad/sas_pcb/) | The three routed PCBs, BOM, connector table, power notes, 1:1 printouts |
| [`gerbers/`](gerbers/) | Gerber and drill files of the three boards, one folder per board |
| [`datasheets/`](datasheets/) | Datasheets of the chips and modules |

KiCad 10 (the PCB files are saved in KiCad 10 format). All projects use relative library paths (`${KIPRJMOD}`), so the folder can be moved or cloned anywhere.

## Ordering the PCBs
Zip each folder in `gerbers/` (for example `pcb_top_gerbers_&_drills.zip`) and upload one zip per board. All three boards: 95 × 60 mm, 2 layers, 1.6 mm, HASL, any colour.

Enclosure (FreeCAD): planned, will go in `enclosure/`.

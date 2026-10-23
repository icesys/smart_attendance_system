# Overview

## Problem
Taking attendance by hand at the end of a lecture is slow and error-prone. Students already carry a card that is used at the university restaurant, where they place it on a small reader that shows their details and ticks that they ate. The same interaction can be used for lecture attendance.

## Concept
1. The lecturer stands at the door at the end of the lecture.
2. Each student places their card flat on the device.
3. The device reads the card, timestamps the event and stores it.
4. Later, the lecturer plugs the device into a PC and retrieves the attendance files.

## Design constraints
- **Wireless in use:** battery powered, nothing plugged in at the door.
- **Tap interaction:** card placed on the reader, no pointing, no laser, no camera.
- **Data access:** the files are accessed from a PC after the lecture.
- **Own PCB:** designed and built by the author in KiCad.
- **Deadline:** complete project by February 2027.

## Architecture at a glance
```
 Student card ──► 125 kHz reader ──► ESP32-S3 ──► Storage ──► PC (after lecture)
                                        ▲
                       2 × 18650 ──► Power management
```
Details: [`documentation/system_architecture.md`](documentation/system_architecture.md)

## Current status
- Prototype parts purchased.
- Card technology: a 125 kHz reader was bought first; the card frequency is not yet confirmed. If the reader does not read the card, the choice will be reassessed (see `documentation/decisions_log.md`).
- Next: breadboard assembly, then firmware, then schematic and PCB.

## Where to go next
- Requirements: `documentation/requirements.md`
- Planning: `documentation/project_plan.md`
- Everything else: `smart_attendance_system_index.md`

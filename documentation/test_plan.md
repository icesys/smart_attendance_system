# Test Plan

| ID | Test | Expected result | Result | Date |
|---|---|---|---|---|
| T1 | Reader detects the student card | Identifier is output | | |
| T2 | Reader read range and orientation | Reliable read when the card is placed flat | | |
| T3 | Repeated tap of the same card | Counted once | | |
| T4 | File persists after power-off | Data intact | | |
| T5 | Retrieve the file from a PC | File opens correctly | | |
| T6 | Battery life | Meets target (to define) | | |
| T7 | Full lecture simulation (many cards in sequence) | No missed taps | | |

## Notes
- T1 is the critical first test: it confirms whether the 125 kHz reader matches the student card.

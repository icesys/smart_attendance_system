#!/usr/bin/env python3
"""Writes smart_attendance.pretty (custom module footprints). Units: mm, KiCad footprint axes (x right, y down),
as seen from the TOP of the board. Header-mounted modules plug in pin-down, so they are the MIRROR of the hand drawings
(which were made looking at the face the pin tips point to). Run: python3 gen_footprints.py <project dir>"""
import os, sys

def f(v):
    return ('%.4f' % v).rstrip('0').rstrip('.')

def rect(x1, y1, x2, y2, layer='F.SilkS', w=0.12):
    return f'  (fp_rect (start {f(x1)} {f(y1)}) (end {f(x2)} {f(y2)}) (stroke (width {w}) (type solid)) (fill none) (layer "{layer}"))'

def circle(cx, cy, r, layer='F.SilkS', w=0.12):
    return f'  (fp_circle (center {f(cx)} {f(cy)}) (end {f(cx + r)} {f(cy)}) (stroke (width {w}) (type solid)) (fill none) (layer "{layer}"))'

def text(t, x, y, size=0.8, layer='F.SilkS', ang=0, th=0.15):
    return (f'  (fp_text user "{t}" (at {f(x)} {f(y)} {ang}) (layer "{layer}") '
            f'(effects (font (size {size} {size}) (thickness {th}))))')

def pad(num, x, y, d=1.0, s=1.8):
    shape = 'rect' if num == 1 else 'circle'
    return (f'  (pad "{num}" thru_hole {shape} (at {f(x)} {f(y)}) (size {f(s)} {f(s)}) (drill {f(d)}) '
            f'(layers "*.Cu" "*.Mask"))')

def module(name, descr, pads, outline, label_dy=-2.0, extra=(), d=1.0, s=1.8, ls=0.8, above=(), outline_layer='F.Fab'):
    """pads: list of (number, name, x, y). outline: (x1, y1, x2, y2) of the real module (drawn on F.Fab).
    Pin names are written vertically (0.8 mm) inside the module: below the pad, or above it for the pads in `above`."""
    x1, y1, x2, y2 = outline
    items = [pad(n, x, y, d, s) for n, _, x, y in pads]
    for n, nm, x, y in pads:
        half = 0.34 * len(nm) + 0.3 + s / 2
        items.append(text(nm, x, y - half if n in above else y + half, 0.8, 'F.SilkS', 90, 0.12))
    items += [rect(x1, y1, x2, y2, outline_layer)] + list(extra)
    body = [f'(footprint "{name}" (version 20221018) (generator pcbnew)', '  (layer "F.Cu")', f'  (descr "{descr}")',
            '  (attr through_hole)',
            f'  (fp_text reference "REF**" (at {f((x1 + x2) / 2)} {f(y1 - 1.5)}) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15))))',
            f'  (fp_text value "{name}" (at {f((x1 + x2) / 2)} {f(y2 + 1.5)}) (layer "F.Fab") (effects (font (size 1 1) (thickness 0.15))))']
    body += items
    body.append(rect(x1 - 0.25, y1 - 0.25, x2 + 0.25, y2 + 0.25, 'F.CrtYd', 0.05))
    body.append(')')
    return '\n'.join(body) + '\n'

FPS = {}

# Buzzer 12 mm, pins 8 mm apart (measured). Pad 1 = + (assumption: check the + mark on your buzzer).
FPS['Buzzer_12mm_P8mm'] = module('Buzzer_12mm_P8mm', 'Buzzer 12 mm, pins 8 mm apart (measured). Pad 1 = + (check your buzzer).',
    [(1, '+', 0, 0), (2, '-', 8, 0)], (-2, -6, 10, 6), extra=[circle(4, 0, 6)], outline_layer='F.Fab')

# Slide switch, 2 rows x 3 pins, 2 mm grid both ways, body 8.5 x 6.5 (measured). Pins 1-3 = pole A, 4-6 = pole B.
FPS['SW_Slide_6pin_2mm'] = module('SW_Slide_6pin_2mm', 'Mini slide switch DPDT 2 x 3 pins, 2 mm grid, body 8.5 x 6.5 mm (measured). Commons are pins 2 and 5.',
    [(1, '1', 0, 0), (2, '2', 2, 0), (3, '3', 4, 0), (4, '4', 0, 2), (5, '5', 2, 2), (6, '6', 4, 2)],
    (-2.25, -2.25, 6.25, 4.25), label_dy=-3.2, d=0.9, s=1.5, outline_layer='F.SilkS')

# TP4056 HW-373 (his drawing, USB-C at the TOP edge): 17.5 x 28 mm. Pads along the bottom edge, left to right:
# OUT-, B-, B+, OUT+ at 3.5 / 7.2 / 3.5 mm apart, OUT+ 1.5 mm from the right edge. Origin = OUT+ (pad 1).
# Only the distance from the pad row to the bottom edge (2.0 mm) is assumed; it affects the outline only.
FPS['MOD_TP4056'] = module('MOD_TP4056',
    'TP4056 HW-373 protected charger 17.5 x 28 mm, USB-C at the top edge. Pads left to right: 4 OUT-, 3 B-, 2 B+, 1 OUT+ (spacings 3.5, 7.2, 3.5 measured; 1.5 mm to the right edge). Pad row 2.0 mm from the bottom edge is an assumption.',
    [(1, 'OUT+', 0, 0), (2, 'B+', -3.5, 0), (3, 'B-', -10.7, 0), (4, 'OUT-', -14.2, 0)], (-16.0, -26.0, 1.5, 2.0),
    extra=[text('USB-C', -7.25, -24.0, 1.0, 'F.SilkS', 0, 0.15)], d=1.0, s=2.0, above=(1, 2, 3, 4))

# MT3608 (his drawing, component side up): 17 x 37 mm. Top pads VIN+ (left), VIN- (right); bottom pads VOUT+ (left),
# VOUT- (right); 7 mm apart in each pair, rows 30.5 mm apart, bottom row 3.5 mm from the bottom edge, 5 mm from the sides.
FPS['MOD_MT3608'] = module('MOD_MT3608',
    'MT3608 boost module 17 x 37 mm. Top row: 1 VIN+ (left), 2 VIN- (right); bottom row: 3 VOUT+ (left), 4 VOUT- (right). All spacings measured.',
    [(1, 'VIN+', 0, 0), (2, 'VIN-', 7, 0), (3, 'VOUT+', 0, 30.5), (4, 'VOUT-', 7, 30.5)], (-5.0, -3.0, 12.0, 34.0),
    d=1.2, s=2.2, above=(3, 4))

# OLED 0.96" (25 x 27 mm). Header GND VCC SCL SDA as printed on the screen face; header 8.5 mm from the side edges.
# Seen from the top of the board (module plugged in pin-down, screen up), GND is on the left. Header 1.5 mm from the top edge (measured).
FPS['MOD_OLED096'] = module('MOD_OLED096',
    'OLED 0.96 inch I2C 25 x 27 mm, screen up: pads left to right 1 GND, 2 VCC, 3 SCL, 4 SDA. Header 8.5 mm from the side edges (measured). Header 1.5 mm from the top edge (measured).',
    [(i + 1, n, i * 2.54, 0) for i, n in enumerate(['GND', 'VCC', 'SCL', 'SDA'])], (-8.5, -1.5, 16.5, 25.5))

# microSD module 24.5 x 42 mm. Sketch (pin tips toward the viewer): CS SCK MOSI MISO VCC GND, GND 6 mm from the right edge.
# Plugged pin-down the order is mirrored: left to right GND VCC MISO MOSI SCK CS, GND 6 mm from the left edge.
FPS['MOD_SD_6PIN'] = module('MOD_SD_6PIN',
    'microSD module 24.5 x 42 mm, plugged pin-down: pads left to right 1 GND, 2 VCC, 3 MISO, 4 MOSI, 5 SCK, 6 CS (mirror of the hand drawing). 6 mm to the side edge measured. Header 2.0 mm from the top edge is an assumption.',
    [(i + 1, n, i * 2.54, 0) for i, n in enumerate(['GND', 'VCC', 'MISO', 'MOSI', 'SCK', 'CS'])], (-6.0, -2.0, 18.5, 40.0))

# DS3231 module 21.5 x 37 mm. Sketch (pin tips toward the viewer): GND VCC SDA SCL SQW 32K, 32K 5 mm from the right edge.
# Plugged pin-down the order is mirrored: left to right 32K SQW SCL SDA VCC GND, 32K 5 mm from the left edge.
FPS['MOD_DS3231_6PIN'] = module('MOD_DS3231_6PIN',
    'DS3231 module 21.5 x 37 mm, plugged pin-down: pads left to right 1 32K, 2 SQW, 3 SCL, 4 SDA, 5 VCC, 6 GND (mirror of the hand drawing). 5 mm to the side edge measured. Header 2.0 mm from the top edge is an assumption.',
    [(i + 1, n, i * 2.54, 0) for i, n in enumerate(['32K', 'SQW', 'SCL', 'SDA', 'VCC', 'GND'])], (-5.0, -2.0, 16.5, 35.0))

# RDM6300 38 x 17.5 mm. Sketch (pin tips toward the viewer): 5-pin header on the top edge, first pin (TX) 2 mm from the left
# edge; 2-pin antenna header on the bottom edge, last pin 2.5 mm from the right edge; rows 15.5 mm apart.
# Plugged pin-down the drawing is mirrored left-right. Origin = TX (pad 1). Rows assumed 1.0 mm from the long edges.
FPS['MOD_RDM6300'] = module('MOD_RDM6300',
    'RDM6300 125 kHz reader 38 x 17.5 mm, plugged pin-down (mirror of the hand drawing): top row pads 1 TX, 2 RX, 3 nc, 4 GND, 5 5V (TX 2 mm from the right edge); bottom row pads 6 ANT1, 7 ANT2 (2.5 mm from the left edge); rows 15.5 mm apart. Rows 1.0 mm from the long edges is an assumption.',
    [(1, 'TX', 0, 0), (2, 'RX', -2.54, 0), (3, 'nc', -5.08, 0), (4, 'GND', -7.62, 0), (5, '5V', -10.16, 0),
     (6, 'ANT1', -33.5, 15.5), (7, 'ANT2', -30.96, 15.5)], (-36.0, -1.0, 2.0, 16.5), above=(6, 7))

if __name__ == '__main__':
    out = os.path.join(sys.argv[1], 'smart_attendance.pretty')
    os.makedirs(out, exist_ok=True)
    for old in os.listdir(out):
        os.remove(os.path.join(out, old))
    for name, body in FPS.items():
        open(os.path.join(out, name + '.kicad_mod'), 'w').write(body)
    print('wrote', len(FPS), 'footprints to', out)

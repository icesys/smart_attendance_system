#!/usr/bin/env python3
"""Writes smart_attendance.pretty (custom module footprints). Units: mm, KiCad footprint axes (x right, y down).
Anything marked ESTIMATE in a footprint description is a guess to be replaced by a real measurement."""
import os, sys

def f(v):
    return ('%.4f' % v).rstrip('0').rstrip('.')

def line(x1, y1, x2, y2, layer='F.SilkS', w=0.12):
    return f'  (fp_line (start {f(x1)} {f(y1)}) (end {f(x2)} {f(y2)}) (stroke (width {w}) (type solid)) (layer "{layer}"))'

def rect(x1, y1, x2, y2, layer='F.SilkS', w=0.12):
    return f'  (fp_rect (start {f(x1)} {f(y1)}) (end {f(x2)} {f(y2)}) (stroke (width {w}) (type solid)) (fill none) (layer "{layer}"))'

def circle(cx, cy, r, layer='F.SilkS', w=0.12):
    return f'  (fp_circle (center {f(cx)} {f(cy)}) (end {f(cx + r)} {f(cy)}) (stroke (width {w}) (type solid)) (fill none) (layer "{layer}"))'

def text(t, x, y, layer='F.SilkS', size=1.0):
    return (f'  (fp_text user "{t}" (at {f(x)} {f(y)}) (layer "{layer}") '
            f'(effects (font (size {size} {size}) (thickness 0.15))))')

def pad(num, x, y, d=1.0, s=1.8, shape='circle'):
    if num == 1 and shape == 'circle':
        shape = 'rect'
    return (f'  (pad "{num}" thru_hole {shape} (at {f(x)} {f(y)}) (size {f(s)} {f(s)}) (drill {f(d)}) '
            f'(layers "*.Cu" "*.Mask"))')

def hole(x, y, d):
    return f'  (pad "" np_thru_hole circle (at {f(x)} {f(y)}) (size {f(d)} {f(d)}) (drill {f(d)}) (layers "*.Cu" "*.Mask"))'

def fp(name, descr, items, ref_at, val_at, crt):
    x1, y1, x2, y2 = crt
    body = [f'(footprint "{name}" (version 20221018) (generator pcbnew)', '  (layer "F.Cu")', f'  (descr "{descr}")',
            '  (attr through_hole)',
            f'  (fp_text reference "REF**" (at {f(ref_at[0])} {f(ref_at[1])}) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15))))',
            f'  (fp_text value "{name}" (at {f(val_at[0])} {f(val_at[1])}) (layer "F.Fab") (effects (font (size 1 1) (thickness 0.15))))']
    body += items
    body.append(rect(x1, y1, x2, y2, 'F.CrtYd', 0.05))
    body.append(')')
    return '\n'.join(body) + '\n'

def hdr(n, x0=0.0, y0=0.0, pitch=2.54):
    return [pad(i + 1, x0 + i * pitch, y0) for i in range(n)]

FPS = {}

# Buzzer 12 mm, pins 8 mm apart (measured). Pin 1 = + (ESTIMATE: which side is +).
FPS['Buzzer_12mm_P8mm'] = fp('Buzzer_12mm_P8mm', 'Buzzer 12 mm round, pins 8 mm apart (measured). ESTIMATE: pad 1 is the + pin.',
    [pad(1, 0, 0), pad(2, 8, 0), circle(4, 0, 6), text('+', -2.2, 0)], (4, -8), (4, 8), (-6.5, -6.5, 14.5, 6.5))

# Slide switch 6 pins, 2 x 3, 2 mm grid both ways (measured), body 6.5 x 8.5 (measured; orientation ESTIMATE).
sw_items = [pad(n, x, y, 0.9, 1.5) for n, x, y in [(1, 0, 0), (2, 2, 0), (3, 4, 0), (4, 0, 2), (5, 2, 2), (6, 4, 2)]]
sw_items.append(rect(-2.25, -2.25, 6.25, 4.25))
FPS['SW_Slide_6pin_2mm'] = fp('SW_Slide_6pin_2mm',
    'Mini slide switch DPDT, 2 rows x 3 pins, 2 mm grid, body 8.5 x 6.5 mm (measured). ESTIMATE: body orientation and offset. Pins 1-3 = pole A, 4-6 = pole B, 2 and 5 are the commons.',
    sw_items, (2, -4), (2, 6), (-2.5, -2.5, 6.5, 4.5))

# TP4056 HW-373: 28 x 17.5 mm; pads on the right edge: OUT+ B+ B- OUT- (OUT+/OUT- 14 mm apart, B+/B- 7.2 mm apart).
# ESTIMATE: pads 2.5 mm from the right end, centred across the width. USB-C at the left end.
FPS['MOD_TP4056'] = fp('MOD_TP4056',
    'TP4056 HW-373 protected charger module 28 x 17.5 mm; pads: 1 OUT+, 2 B+, 3 B-, 4 OUT- (spacings measured). ESTIMATE: pad inset 2.5 mm from the right end and centred vertically. USB-C at the LEFT end.',
    [pad(1, 0, -7, 1.0, 2.0), pad(2, 0, -3.6, 1.0, 2.0), pad(3, 0, 3.6, 1.0, 2.0), pad(4, 0, 7, 1.0, 2.0),
     rect(-25.5, -8.75, 2.5, 8.75), text('USB-C', -22, 0), text('OUT+', 3.5, -7, size=0.8), text('B+', 3.0, -3.6, size=0.8),
     text('B-', 3.0, 3.6, size=0.8), text('OUT-', 3.5, 7, size=0.8)], (-12, -10.5), (-12, 10.5), (-25.75, -9, 2.75, 9))

# MT3608 module: 37 x 16.5 mm; VIN pair 7 mm apart, VOUT pair 7 mm apart, 30.5 mm from VIN- to VOUT- (measured).
# Seen from the component side: VIN- top-left, VIN+ bottom-left, VOUT- top-right, VOUT+ bottom-right. ESTIMATE: pads 3.25 mm from each end.
FPS['MOD_MT3608'] = fp('MOD_MT3608',
    'MT3608 boost module 37 x 16.5 mm; pads 1 VIN+, 2 VIN-, 3 VOUT+, 4 VOUT- (spacings measured). ESTIMATE: pads 3.25 mm from each end, centred. Keep the trimmer reachable.',
    [pad(1, 0, 3.5, 1.2, 2.2), pad(2, 0, -3.5, 1.2, 2.2), pad(3, 30.5, 3.5, 1.2, 2.2), pad(4, 30.5, -3.5, 1.2, 2.2),
     rect(-3.25, -8.25, 33.75, 8.25), text('VIN-', 0, -5.6, size=0.8), text('VIN+', 0, 5.6, size=0.8),
     text('VOUT-', 30.5, -5.6, size=0.8), text('VOUT+', 30.5, 5.6, size=0.8)], (15, -10), (15, 10), (-3.5, -8.5, 34, 8.5))

# OLED 0.96": header GND VCC SCL SDA at 2.54 mm. ESTIMATE: module 27.3 x 27.8, mounting holes 23.5 x 23.8 mm, 2.0 mm drill.
FPS['MOD_OLED096'] = fp('MOD_OLED096',
    'OLED 0.96 inch I2C module; header pins 1 GND, 2 VCC, 3 SCL, 4 SDA at 2.54 mm. ESTIMATE: module 27.3 x 27.8 mm and mounting holes 23.5 x 23.8 mm (replace with measurements).',
    hdr(4) + [hole(3.81 - 11.75, 0, 2.0), hole(3.81 + 11.75, 0, 2.0), hole(3.81 - 11.75, 23.8, 2.0), hole(3.81 + 11.75, 23.8, 2.0),
              rect(3.81 - 13.65, -2.0, 3.81 + 13.65, 25.8), text('OLED', 3.81, 12)],
    (3.81, -4), (3.81, 28), (3.81 - 13.9, -2.25, 3.81 + 13.9, 26.05))

# SD module, 6 pins GND VCC MISO MOSI SCK CS. ESTIMATE: 42 x 24 mm, header centred on the short edge.
FPS['MOD_SD_6PIN'] = fp('MOD_SD_6PIN',
    'microSD module with 6-pin header: 1 GND, 2 VCC(5V), 3 MISO, 4 MOSI, 5 SCK, 6 CS. ESTIMATE: module 42 x 24 mm, header centred on the short edge (replace with measurements).',
    hdr(6) + [rect(6.35 - 12, -2.0, 6.35 + 12, 40.0), text('microSD', 6.35, 20)], (6.35, -4), (6.35, 42), (6.35 - 12.25, -2.25, 6.35 + 12.25, 40.25))

# DS3231 module, 6 pins 32K SQW SCL SDA VCC GND. ESTIMATE: 38 x 22 mm, header centred on the short edge.
FPS['MOD_DS3231_6PIN'] = fp('MOD_DS3231_6PIN',
    'DS3231 module with 6-pin header: 1 32K, 2 SQW, 3 SCL, 4 SDA, 5 VCC, 6 GND. ESTIMATE: module 38 x 22 mm, header centred on the short edge (replace with measurements).',
    hdr(6) + [rect(6.35 - 11, -2.0, 6.35 + 11, 36.0), text('DS3231', 6.35, 18)], (6.35, -4), (6.35, 38), (6.35 - 11.25, -2.25, 6.35 + 11.25, 36.25))

if __name__ == '__main__':
    out = os.path.join(sys.argv[1], 'smart_attendance.pretty')
    os.makedirs(out, exist_ok=True)
    for name, body in FPS.items():
        open(os.path.join(out, name + '.kicad_mod'), 'w').write(body)
    print('wrote', len(FPS), 'footprints to', out)

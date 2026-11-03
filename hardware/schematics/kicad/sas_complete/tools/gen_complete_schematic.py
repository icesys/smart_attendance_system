#!/usr/bin/env python3
"""Complete electrical schematic of the Smart Attendance System drawn AS ONE CIRCUIT (as if it were a single PCB):
no TOP / MIDDLE / BOTTOM sections, no board-to-board connectors (J1, J105, J106, J201), no ribbon cables, no mounting holes.
The ESP32-S3 dev board and the modules are drawn as blocks with named pins. References are renumbered for one design
(see README.md for the table against the three-board references).
Needs kiutils. Reuses the router of ../../sas_schematics/tools/gen_schematics.py.
Run:  python3 gen_complete_schematic.py
"""
import json, math, os, sys, uuid

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ_DIR = os.path.dirname(HERE)
SAS = os.path.join(os.path.dirname(PROJ_DIR), 'sas_schematics')
sys.path.insert(0, os.path.join(SAS, 'tools'))
import gen_schematics as gs   # noqa: E402
from kiutils.symbol import SymbolLib   # noqa: E402
from kiutils.items.common import Position, PageSettings, TitleBlock, Stroke, Effects, Font   # noqa: E402
from kiutils.items.schitems import Connection, Junction, NoConnect, Text   # noqa: E402

PROJ = 'sas_complete'
W, H = 420.0, 297.0          # A3 landscape
G = gs.G


# ------------------------------------------------------------------------------------------- custom symbols
def _pin(num, name, x, y, ang, length=2.54):
    return (f'      (pin passive line (at {x:g} {y:g} {ang}) (length {length:g})\n'
            f'        (name "{name}" (effects (font (size 1.27 1.27))))\n'
            f'        (number "{num}" (effects (font (size 1.27 1.27))))\n      )\n')


def _head(name, ref, value, names_hidden=False, offset=0.762):
    return (f'  (symbol "{name}" (pin_names (offset {offset})' + (' hide' if names_hidden else '') + ') (in_bom yes) (on_board yes)\n'
            f'    (property "Reference" "{ref}" (at 0 0 0) (effects (font (size 1.27 1.27))))\n'
            f'    (property "Value" "{value}" (at 0 0 0) (effects (font (size 1.27 1.27))))\n'
            f'    (property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))\n'
            f'    (property "Datasheet" "~" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))\n')


def module(name, value, left, right, width):
    """A block with named pins: left = [(number, name)], right = [(number, name)] from top to bottom."""
    n = max(len(left), len(right))
    top = math.ceil((n - 1) / 2) * 2.54
    hw = width / 2
    s = _head(name, 'U', value) + f'    (symbol "{name}_1_1"\n'
    s += (f'      (rectangle (start {-hw:g} {top + 2.54:g}) (end {hw:g} {top - n * 2.54:g})\n'
          '        (stroke (width 0.254) (type default)) (fill (type background)))\n')
    for i, (num, nm) in enumerate(left):
        s += _pin(num, nm, -hw - 2.54, round(top - i * 2.54, 3), 0)
    for i, (num, nm) in enumerate(right):
        s += _pin(num, nm, hw + 2.54, round(top - i * 2.54, 3), 180)
    return s + '    )\n  )\n'


def battery():
    s = _head('Battery_Cell_18650', 'BT', '18650', names_hidden=True) + '    (symbol "Battery_Cell_18650_1_1"\n'
    s += ('      (polyline (pts (xy -2.54 1.27) (xy 2.54 1.27)) (stroke (width 0.254) (type default)) (fill (type none)))\n'
          '      (polyline (pts (xy -1.27 0.254) (xy 1.27 0.254)) (stroke (width 0.762) (type default)) (fill (type none)))\n'
          '      (polyline (pts (xy 0 0.254) (xy 0 -1.27)) (stroke (width 0.254) (type default)) (fill (type none)))\n'
          '      (polyline (pts (xy 1.016 2.794) (xy 2.032 2.794)) (stroke (width 0.254) (type default)) (fill (type none)))\n'
          '      (polyline (pts (xy 1.524 3.302) (xy 1.524 2.286)) (stroke (width 0.254) (type default)) (fill (type none)))\n')
    s += _pin('1', '+', 0, 3.81, 270, 2.54) + _pin('2', '-', 0, -3.81, 90, 2.54)
    return s + '    )\n  )\n'


def coil():
    s = _head('Antenna_Coil', 'L', 'coil', names_hidden=True) + '    (symbol "Antenna_Coil_1_1"\n'
    for k in range(4):
        y0 = 2.54 - k * 1.27
        s += (f'      (arc (start 0 {y0:g}) (mid 0.635 {y0 - 0.635:g}) (end 0 {y0 - 1.27:g})\n'
              '        (stroke (width 0.254) (type default)) (fill (type none)))\n')
    s += _pin('1', '1', 0, 3.81, 270, 1.27) + _pin('2', '2', 0, -3.81, 90, 1.27)
    return s + '    )\n  )\n'


ESP_L = gs.ESP_L          # row 1 (pins 1-22), USB end first
ESP_R = gs.ESP_R          # row 2 (pins 23-44)
CUSTOM = (
    module('ESP32-S3-DevKitC-1', 'ESP32-S3 N16R8 dev board', [(str(i), n) for i, n in enumerate(ESP_L, 1)],
           [(str(22 + i), n) for i, n in enumerate(ESP_R, 1)], 20.32)
    + module('RDM6300', 'RDM6300 125 kHz reader', [('5', '+5V'), ('4', 'GND'), ('1', 'TX'), ('2', 'RX'), ('3', 'NC')],
             [('6', 'ANT1'), ('7', 'ANT2')], 15.24)
    + module('DS3231_Module', 'DS3231 RTC (CR2032)', [('5', 'VCC'), ('6', 'GND'), ('3', 'SCL'), ('4', 'SDA'), ('1', '32K'), ('2', 'SQW')], [], 15.24)
    + module('MicroSD_Module', 'microSD module (SPI)', [('2', 'VCC'), ('1', 'GND'), ('6', 'CS'), ('5', 'SCK'), ('4', 'MOSI'), ('3', 'MISO')], [], 15.24)
    + module('OLED_SSD1306', 'OLED 0.96in SSD1306 (I2C)', [('2', 'VCC'), ('1', 'GND'), ('3', 'SCL'), ('4', 'SDA')], [], 15.24)
    + module('TP4056_Module', 'TP4056 charger, protected, USB-C', [('2', 'B+'), ('3', 'B-')], [('1', 'OUT+'), ('4', 'OUT-')], 15.24)
    + module('MT3608_Module', 'MT3608 boost (set 5.0 V)', [('1', 'VIN+'), ('2', 'VIN-')], [('3', 'VOUT+'), ('4', 'VOUT-')], 15.24)
    + battery() + coil())

os.makedirs(PROJ_DIR, exist_ok=True)
_custom_path = os.path.join(HERE, '_custom.kicad_sym')
open(_custom_path, 'w').write('(kicad_symbol_lib (version 20211014) (generator kiutils)\n' + CUSTOM + ')\n')
_LOCAL = {s.entryName: s for s in SymbolLib.from_file(os.path.join(SAS, 'sas_symbols.kicad_sym')).symbols}
_LOCAL.update({s.entryName: s for s in SymbolLib.from_file(_custom_path).symbols})
os.remove(_custom_path)
gs.libsym = lambda lib, name: _LOCAL[name]
gs.CUR['proj'], gs.CUR['file'] = PROJ, PROJ

RES = 'smart_attendance:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal'
CER = 'smart_attendance:C_Disc_D5.0mm_W2.5mm_P5.00mm'


def esp_nets():
    nets, nc = {}, []
    for i, n in enumerate(ESP_L + ESP_R, 1):
        (nets.__setitem__(i, gs.ESP_USED[n]) if n in gs.ESP_USED else nc.append(i))
    return nets, nc


def build():
    sh = gs.Sheet(PROJ, 'SAS - Smart Attendance System: complete electrical schematic (one circuit)', '', None, None)
    sh.sch.paper = PageSettings(paperSize='A3')
    sh.sch.titleBlock = TitleBlock(title='Smart Attendance System - complete electrical schematic', date='2026-11-03', revision='1.0',
                                   company='Smart Attendance System - TSONGODZA Evidence, MANDEBVU Langelihle Sasha',
                                   comments={1: 'Whole system drawn as one circuit (no board-to-board connectors)',
                                             2: 'Generated by tools/gen_complete_schematic.py'})
    P = sh.place
    sh.text('SMART ATTENDANCE SYSTEM - complete electrical schematic (whole system as one circuit)', 20, 17, 2.8)

    # ---- power supply (top row, left to right)
    sh.text('POWER SUPPLY', 20, 30, 2.0)
    P('SAS', 'Battery_Cell_18650', 'BT1', '18650 Li-ion 3.7 V', 28, 58, nets={1: 'BAT+', 2: 'BAT-'})
    P('SAS', 'TP4056_Module', 'U6', 'TP4056 charger, protected, USB-C', 62, 58, fp='smart_attendance:MOD_TP4056',
      nets={1: 'CHG_OUT+', 2: 'BAT+', 3: 'BAT-', 4: 'GND'})
    P('SAS', 'SW_DPDT_x2', 'SW1', 'Slide switch (on/off)', 100, 45, unit=1, fp='smart_attendance:SW_Slide_6pin_2mm',
      nets={1: 'SW_OUT', 2: 'CHG_OUT+'}, nc=[3])
    P('SAS', 'SW_DPDT_x2', 'SW1', 'Slide switch (on/off)', 100, 70, unit=2, fp='smart_attendance:SW_Slide_6pin_2mm',
      nets={4: 'SW_OUT', 5: 'CHG_OUT+'}, nc=[6])
    P('SAS', 'MT3608_Module', 'U7', 'MT3608 boost (set 5.0 V)', 138, 58, fp='smart_attendance:MOD_MT3608',
      nets={1: 'SW_OUT', 2: 'GND', 3: '5V_BOOST', 4: 'GND'})
    P('SAS', 'C_Polarized', 'C1', '470u 10V', 168, 75, fp='smart_attendance:CP_Radial_D10.0mm_P5.00mm', nets={1: '5V_BOOST', 2: 'GND'})
    P('SAS', 'C', 'C2', '100n', 181, 75, fp=CER, nets={1: '5V_BOOST', 2: 'GND'})
    P('SAS', 'D_Schottky', 'D5', '1N5819', 200, 45, fp='smart_attendance:D_DO-41_SOD81_P10.16mm_Horizontal',
      nets={'A': '5V_BOOST', 'K': '5V_SYS'})
    P('SAS', 'C', 'C3', '10u', 222, 75, fp=CER, nets={1: '5V_SYS', 2: 'GND'})
    P('SAS', 'C', 'C4', '100n', 235, 75, fp=CER, nets={1: '5V_SYS', 2: 'GND'})

    # ---- microcontroller (centre)
    sh.text('MICROCONTROLLER', 200, 112, 2.0)
    nets, nc = esp_nets()
    P('SAS', 'ESP32-S3-DevKitC-1', 'U1', 'ESP32-S3 N16R8 dev board', 213, 160, nets=nets, nc=nc)
    for k, (c, v) in enumerate((('C5', '100n'), ('C6', '100n'), ('C7', '10u'), ('C8', '100n'))):
        P('SAS', 'C', c, v, 196 + 13 * k, 222, fp=CER, nets={1: '3V3', 2: 'GND'})

    # ---- RFID, storage, clock, display (right column, pins facing the ESP32)
    sh.text('RFID 125 kHz', 300, 30, 2.0)
    P('SAS', 'RDM6300', 'U2', 'RDM6300 125 kHz reader', 318, 58, fp='smart_attendance:MOD_RDM6300',
      nets={1: 'GPIO18', 4: 'GND', 5: '5V_SYS', 6: 'COIL_A', 7: 'COIL_B'}, nc=[2, 3])
    P('SAS', 'Antenna_Coil', 'L1', 'Antenna coil 35 x 46 mm', 355, 58, fp='smart_attendance:PinHeader_1x02_P2.54mm_Vertical',
      nets={1: 'COIL_A', 2: 'COIL_B'})
    sh.text('STORAGE, CLOCK AND DISPLAY', 300, 100, 2.0)
    P('SAS', 'MicroSD_Module', 'U4', 'microSD module (SPI)', 318, 125, fp='smart_attendance:MOD_SD_6PIN',
      nets={1: 'GND', 2: '5V_SYS', 3: 'SD_MISO', 4: 'SD_MOSI', 5: 'SD_SCK', 6: 'SD_CS'})
    P('SAS', 'DS3231_Module', 'U3', 'DS3231 RTC (CR2032)', 318, 168, fp='smart_attendance:MOD_DS3231_6PIN',
      nets={3: 'SCL', 4: 'SDA', 5: '3V3', 6: 'GND'}, nc=[1, 2])
    P('SAS', 'OLED_SSD1306', 'U5', 'OLED 0.96in SSD1306 (I2C)', 318, 208, fp='smart_attendance:MOD_OLED096',
      nets={1: 'GND', 2: '3V3', 3: 'SCL', 4: 'SDA'})

    # ---- user interface (left, facing the ESP32 pins GPIO1/2/40/41/42)
    sh.text('USER INTERFACE: LEDS, BUTTONS, BUZZER', 20, 112, 2.0)
    for i, (d, r, gpio, net, col) in enumerate([('D1', 'R1', 'GPIO5', 'LED_BLUE', 'blue (power)'),
                                                 ('D2', 'R2', 'GPIO1', 'LED_GRN', 'green'),
                                                 ('D3', 'R3', 'GPIO2', 'LED_RED', 'red')]):
        y = 130 + 14 * i
        P('SAS', 'R', r, '220', 120, y, rot=90, fp=RES, nets={1: gpio, 2: net})
        P('SAS', 'LED', d, col, 85, y, rot=0, fp='smart_attendance:LED_D5.0mm', nets={'A': net, 'K': 'GND'})
    P('SAS', 'SW_Push', 'SW2', 'Button 1 (session)', 120, 182, fp='smart_attendance:SW_PUSH_6mm', nets={1: 'GPIO40', 2: 'GND'})
    P('SAS', 'SW_Push', 'SW3', 'Button 2 (info)', 120, 197, fp='smart_attendance:SW_PUSH_6mm', nets={1: 'GPIO41', 2: 'GND'})
    P('SAS', 'R', 'R4', '1k', 130, 232, rot=90, fp=RES, nets={1: 'GPIO42', 2: 'BUZ_B'})
    P('SAS', 'R', 'R5', '100k', 112, 252, fp=RES, nets={1: 'BUZ_B', 2: 'GND'})
    P('SAS', 'Q_NPN_EBC', 'Q1', '2N2222A', 92, 232, rot=180, fp='smart_attendance:TO-92_Inline', nets={'B': 'BUZ_B', 'C': 'BUZ_N', 'E': 'GND'})
    P('SAS', 'Buzzer', 'BZ1', 'Buzzer 12 mm', 55, 215, fp='smart_attendance:Buzzer_12mm_P8mm', nets={1: 'BUZ_VCC', 2: 'BUZ_N'})
    P('SAS', 'D', 'D4', '1N4148', 33, 222, rot=90, fp='smart_attendance:D_DO-35_SOD27_P7.62mm_Horizontal', nets={'K': 'BUZ_VCC', 'A': 'BUZ_N'})
    P('SAS', 'SolderJumper_3_Bridged12', 'JP1', 'Buzzer supply (1-2 = 3V3)', 55, 190,
      fp='smart_attendance:SolderJumper-3_P1.3mm_Bridged12_RoundedPad1.0x1.5mm', nets={1: '3V3', 3: '5V_SYS', 2: 'BUZ_VCC'})

    sh.text('Power path: 18650 -> TP4056 (charge + protection) -> switch -> MT3608 (5.0 V) -> Schottky D5 -> 5V_SYS. '
            '3V3 comes from the ESP32-S3 board regulator.', 20, 268, 1.6)
    sh.text('BAT- is not ground: OUT- of the TP4056 is the system ground. LED_BLUE blinks twice every 3 s while the system is on.', 20, 273, 1.6)
    return sh


def route(sh):
    sch = sh.sch
    groups = {}
    for it in sh.items:
        for pp in it['pins']:
            if pp['net'] is None:
                sch.noConnects.append(NoConnect(position=Position(*pp['end'], 0), uuid=str(uuid.uuid4())))
                continue
            groups.setdefault(pp['net'], []).append(pp)
            if it['ref'].startswith('U') and not pp['net'].startswith(('LED_', 'BUZ_')):
                sh.label(pp['net'], *pp['end'], pp['out'])
    R = gs.Router(xmax=W, ymax=H)
    R.block_rect(-5, -5, W + 5, 10)
    R.block_rect(-5, -5, 10, H + 5)
    R.block_rect(W - 10, -5, W + 5, H + 5)
    R.block_rect(-5, H - 10, W + 5, H + 5)
    R.block_rect(300, 250, W + 5, H + 5)       # title block
    R.block_rect(15, 264, 300, 276)             # notes
    for it in sh.items:
        R.block_rect(*it['bbox'])
        for pp in it['pins']:
            c = R.cell(*pp['end'])
            R.pin_net[c] = pp['net'] or '__nc__'
            for k in range(1, int(round(pp['length'] / G)) + 1):
                R.blocked.add((c[0] - pp['out'][0] * k, c[1] - pp['out'][1] * k))
    for it in sh.items:
        for pp in it['pins']:
            c = R.cell(*pp['end'])
            R.blocked.discard(c)
            R.blocked.discard((c[0] + pp['out'][0], c[1] + pp['out'][1]))
    rails = ('GND', '3V3', '5V_SYS', '5V_BOOST')
    for net in sorted(groups, key=lambda n: (rails.index(n) if n in rails else 9, len(groups[n]), n)):
        plist = groups[net]
        cells = [R.cell(*pp['end']) for pp in plist]
        tree = {cells[0]}
        R.occ.setdefault(cells[0], {}).setdefault(net, set()).add('n')
        todo = list(range(1, len(plist)))
        while todo:
            j = min(todo, key=lambda k: min(abs(cells[k][0] - t[0]) + abs(cells[k][1] - t[1]) for t in tree))
            todo.remove(j)
            hint = min(tree, key=lambda t: abs(cells[j][0] - t[0]) + abs(cells[j][1] - t[1]))
            path = R.path(net, cells[j], plist[j]['out'], tree, hint, tree)
            if path is None:
                sh.failed.append((net, plist[j]['end']))
                sh.label(net, *plist[j]['end'], plist[j]['out'])
                sh.label(net, *plist[0]['end'], plist[0]['out'])
                continue
            R.commit(net, path, True)
            tree.update(path)
    nodes = {}
    for net, a, b in R.segments:
        nodes.setdefault(net, set()).update([a, b])
    for c in R.junctions:
        for net in R.occ.get(c, {}):
            nodes.setdefault(net, set()).add(c)
    for net, a, b in R.segments:
        inner = sorted([c for c in nodes[net] if c not in (a, b) and
                        ((a[0] == b[0] == c[0] and min(a[1], b[1]) < c[1] < max(a[1], b[1])) or
                         (a[1] == b[1] == c[1] and min(a[0], b[0]) < c[0] < max(a[0], b[0])))],
                       key=lambda c: abs(c[0] - a[0]) + abs(c[1] - a[1]))
        pts = [a] + inner + [b]
        for i in range(len(pts) - 1):
            sch.graphicalItems.append(Connection(type='wire', points=[
                Position(round(pts[i][0] * G, 3), round(pts[i][1] * G, 3)),
                Position(round(pts[i + 1][0] * G, 3), round(pts[i + 1][1] * G, 3))],
                stroke=Stroke(width=0, type='default'), uuid=str(uuid.uuid4())))
    ends = {}
    for gi in sch.graphicalItems:
        for p in gi.points:
            ends[(p.X, p.Y)] = ends.get((p.X, p.Y), 0) + 1
    pin_pts = {pp['end'] for it in sh.items for pp in it['pins']}
    for (x, y), n in ends.items():
        if n + ((x, y) in pin_pts) >= 3:
            sch.junctions.append(Junction(position=Position(x, y), diameter=0, uuid=str(uuid.uuid4())))


def main():
    sh = build()
    route(sh)
    sh.sch.to_file(os.path.join(PROJ_DIR, f'{PROJ}.kicad_sch'))
    exp = {}
    for it in sh.items:
        for pp in it['pins']:
            if pp['net']:
                exp.setdefault(pp['net'], []).append(f"{it['ref']}.{pp['num']}")
    json.dump(exp, open(os.path.join(HERE, 'expected_nets.json'), 'w'), indent=1, sort_keys=True)
    # project library = the shared symbols + the module blocks, so the project opens anywhere
    lib = SymbolLib.from_file(os.path.join(SAS, 'sas_symbols.kicad_sym'))
    names = {s.entryName for s in lib.symbols}
    for n in ('ESP32-S3-DevKitC-1', 'RDM6300', 'DS3231_Module', 'MicroSD_Module', 'OLED_SSD1306', 'TP4056_Module',
              'MT3608_Module', 'Battery_Cell_18650', 'Antenna_Coil'):
        if n not in names:
            lib.symbols.append(_LOCAL[n])
    lib.to_file(os.path.join(PROJ_DIR, 'sas_complete_symbols.kicad_sym'))
    with open(os.path.join(PROJ_DIR, 'sym-lib-table'), 'w') as f:
        f.write('(sym_lib_table\n  (version 7)\n  (lib (name "SAS")(type "KiCad")(uri "${KIPRJMOD}/sas_complete_symbols.kicad_sym")'
                '(options "")(descr "Smart Attendance System symbols + module blocks"))\n)\n')
    with open(os.path.join(PROJ_DIR, 'fp-lib-table'), 'w') as f:
        f.write('(fp_lib_table\n  (version 7)\n  (lib (name "smart_attendance")(type "KiCad")(uri "${KIPRJMOD}/../sas_schematics/smart_attendance.pretty")'
                '(options "")(descr "Module footprints + copies of the standard ones"))\n)\n')
    with open(os.path.join(PROJ_DIR, f'{PROJ}.kicad_pro'), 'w') as f:
        json.dump({'meta': {'filename': f'{PROJ}.kicad_pro', 'version': 1}}, f, indent=2)
    print('written', os.path.join(PROJ_DIR, f'{PROJ}.kicad_sch'))
    print('drawn with labels instead of wires:', sh.failed) if sh.failed else print('every connection drawn as a wire')


if __name__ == '__main__':
    main()

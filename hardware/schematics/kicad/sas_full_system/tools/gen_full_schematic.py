#!/usr/bin/env python3
"""Generates the FULL electrical schematic of the Smart Attendance System: the three boards on ONE flat A1 sheet,
with both 16-conductor ribbon cables drawn wire by wire between their connectors.

It reuses the board descriptions of ../../sas_schematics/tools/gen_schematics.py (same parts, references, values,
footprints and nets as the per-board schematics and the PCBs), places each board in its own frame and routes:
  - every connection inside a board as real wires (same router as the per-board schematics),
  - every cable conductor as a wire from pin k of one connector to pin k of the other.
Needs kiutils (pip install kiutils). Symbols come from ../sas_schematics/sas_symbols.kicad_sym (no KiCad install needed).
Run:  python3 gen_full_schematic.py
"""
import json, os, sys, uuid

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ_DIR = os.path.dirname(HERE)
SAS = os.path.join(os.path.dirname(PROJ_DIR), 'sas_schematics')
sys.path.insert(0, os.path.join(SAS, 'tools'))
import gen_schematics as gs   # noqa: E402
from kiutils.symbol import SymbolLib   # noqa: E402
from kiutils.items.common import Position, PageSettings, TitleBlock, Stroke, Effects, Font   # noqa: E402
from kiutils.items.schitems import (Connection, Junction, NoConnect, Rectangle, Text)   # noqa: E402

PROJ = 'sas_full_system'
W, H = 841.0, 594.0            # A1 landscape
G = gs.G

# the board libraries are copies of the standard KiCad symbols: read them from the project library
_LOCAL = {s.entryName: s for s in SymbolLib.from_file(os.path.join(SAS, 'sas_symbols.kicad_sym')).symbols}
gs.libsym = lambda lib, name: _LOCAL[name]
gs.CUR['proj'], gs.CUR['file'] = PROJ, PROJ

# where each board's A3-sized drawing goes on the A1 sheet (offsets are whole multiples of 2.54 mm)
#   MIDDLE | BOTTOM      cable 2 runs between them (MIDDLE J106 on its right, BOTTOM J201 on its left)
#   TOP    | notes       cable 1 runs down the left margin (MIDDLE J105 and TOP J1 are both on the left)
OFFS = {'MIDDLE': (0.0, 0.0), 'BOTTOM': (416.56, 0.0), 'TOP': (0.0, 289.56)}
FRAMES = {'MIDDLE': (27.94, 13.97, 402.59, 259.08), 'BOTTOM': (444.5, 13.97, 828.04, 259.08),
          'TOP': (27.94, 303.53, 402.59, 548.64)}
CABLES = [('CABLE 1', 'J105', 'J1', gs.J_TM), ('CABLE 2', 'J106', 'J201', gs.J_MB)]


class FullSheet(gs.Sheet):
    """One sheet collecting the three boards; the build_* functions of gen_schematics draw into it."""

    def __init__(self):
        super().__init__(PROJ, 'SAS - Smart Attendance System: complete electrical schematic (3 boards + 2 cables)',
                         'All three boards on one sheet; the ribbon cables are drawn conductor by conductor', None, None)
        self.sch.paper = PageSettings(paperSize='A1')
        self.board, self.ox, self.oy = None, 0.0, 0.0

    def start(self, board):
        self.board = board
        self.ox, self.oy = OFFS[board]

    def text(self, t, x, y, h=1.8):
        super().text(t, x + self.ox, y + self.oy, h)

    def place(self, lib, name, ref, value, x, y, **kw):
        super().place(lib, name, ref, value, x + self.ox, y + self.oy, **kw)
        self.items[-1]['board'] = self.board

    def finish(self, outdir):   # called by each build_*: routing is done once, at the end
        pass

    def gtext(self, t, x, y, h=1.8, bold=False):
        self.sch.texts.append(Text(text=t, position=Position(x, y, 0),
                                   effects=Effects(font=Font(height=h, width=h, bold=bold)), uuid=str(uuid.uuid4())))

    # ------------------------------------------------------------------------------------------- routing
    def route(self):
        sch = self.sch
        pins_by = {}                      # (ref, pin) -> pin dict
        groups = {}                       # (board, net) -> [pin dicts]
        for it in self.items:
            for pp in it['pins']:
                pins_by[(it['ref'], pp['num'])] = pp
                if pp['net'] is None:
                    sch.noConnects.append(NoConnect(position=Position(*pp['end'], 0), uuid=str(uuid.uuid4())))
                    continue
                groups.setdefault((it['board'], pp['net']), []).append(pp)
                if it['ref'].startswith('J'):
                    self.label(pp['net'], *pp['end'], pp['out'])
        R = gs.Router(xmax=W, ymax=H)
        R.block_rect(-5, -5, W + 5, 10)             # sheet border
        R.block_rect(-5, -5, 10, H + 5)
        R.block_rect(W - 10, -5, W + 5, H + 5)
        R.block_rect(-5, H - 10, W + 5, H + 5)
        R.block_rect(416, 262, W + 5, H + 5)        # notes and title block (bottom right quarter)
        for it in self.items:
            R.block_rect(*it['bbox'])
            for pp in it['pins']:
                c = R.cell(*pp['end'])
                R.pin_net[c] = pp['net'] or '__nc__'
                for k in range(1, int(round(pp['length'] / G)) + 1):
                    R.blocked.add((c[0] - pp['out'][0] * k, c[1] - pp['out'][1] * k))
        for it in self.items:
            for pp in it['pins']:
                c = R.cell(*pp['end'])
                R.blocked.discard(c)
                R.blocked.discard((c[0] + pp['out'][0], c[1] + pp['out'][1]))

        jobs = []
        for _name, a, b, pinmap in CABLES:      # cables first: they get clean parallel channels
            for k in range(1, 17):
                jobs.append((pinmap[k], [pins_by[(a, str(k))], pins_by[(b, str(k))]], f'{a}.{k}-{b}.{k}'))
        rails = ('GND', '3V3', '5V_SYS', '5V_BOOST')
        for (board, net) in sorted(groups, key=lambda g: (rails.index(g[1]) if g[1] in rails else 9, len(groups[g]), g)):
            jobs.append((net, groups[(board, net)], f'{board}/{net}'))

        for net, plist, tag in jobs:
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
                    self.failed.append((tag, plist[j]['end']))
                    self.label(net, *plist[j]['end'], plist[j]['out'])
                    self.label(net, *plist[0]['end'], plist[0]['out'])
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
        # a junction dot only where 3 or more wire ends / pins meet (KiCad's own rule)
        ends = {}
        for gi in sch.graphicalItems:
            for p in gi.points:
                ends[(p.X, p.Y)] = ends.get((p.X, p.Y), 0) + 1
        pin_pts = {pp['end'] for it in self.items for pp in it['pins']}
        for (x, y), n in ends.items():
            if n + ((x, y) in pin_pts) >= 3:
                sch.junctions.append(Junction(position=Position(x, y), diameter=0, uuid=str(uuid.uuid4())))


def frames_and_notes(sh):
    sch = sh.sch
    for board, (x0, y0, x1, y1) in FRAMES.items():
        sch.shapes.append(Rectangle(start=Position(x0, y0), end=Position(x1, y1),
                                    stroke=Stroke(width=0.5, type='dash'), uuid=str(uuid.uuid4())))
        sh.gtext(f'{board} BOARD', x0 + 2, y0 + 3.5, 3.0, bold=True)
    sh.gtext('CABLE 1: 16-wire ribbon, MIDDLE J105 <-> TOP J1 (same pin number at both ends)', 100, 282, 1.8, bold=True)
    sh.gtext('CABLE 2\n16 wires\nJ106 <-> J201', 406, 185, 1.8, bold=True)

    x, y = 425, 272
    sh.gtext('SMART ATTENDANCE SYSTEM: complete electrical schematic', x, y, 3.2, bold=True)
    sh.gtext('Three boards stacked TOP / MIDDLE / BOTTOM (95 x 60 mm each), joined by two 16-conductor ribbon cables.\n'
             'Every connection is a wire; net names are also written on the connector pins.', x, y + 8, 1.8)
    y += 20
    sh.gtext('CABLE 1 (MIDDLE J105 <-> TOP J1)', x, y, 2.0, bold=True)
    sh.gtext('CABLE 2 (MIDDLE J106 <-> BOTTOM J201)', x + 135, y, 2.0, bold=True)
    for k in range(1, 17):
        r = y + 6 + ((k - 1) % 8) * 5
        sh.gtext(f'{k:2d}  {gs.J_TM[k]}', x + ((k - 1) // 8) * 55, r, 1.8)
        sh.gtext(f'{k:2d}  {gs.J_MB[k]}', x + 135 + ((k - 1) // 8) * 55, r, 1.8)
    y += 52
    sh.gtext('POWER PATH', x, y, 2.0, bold=True)
    sh.gtext('18650 (J202) -> TP4056 charger, protected, USB-C (J203) -> slide switch SW201 -> MT3608 boost set to 5.0 V (J204)\n'
             '-> 5V_BOOST, cable 2 pins 1 and 3 -> Schottky D101 on MIDDLE -> 5V_SYS (ESP32 5V pin, RDM6300, SD module,\n'
             'buzzer option via JP1). 3V3 comes from the ESP32-S3 board regulator and goes to OLED, DS3231, LEDs/buzzer side.\n'
             'USB on the ESP32 (about 5 V) wins against the battery path (about 4.7 V after the diode).\n'
             'BAT- is NOT ground: it sits behind the TP4056 protection chip; OUT- (J203 pin 4) is the system ground.', x, y + 6, 1.8)
    y += 38
    sh.gtext('ESP32-S3 GPIO MAP', x, y, 2.0, bold=True)
    sh.gtext('GPIO1 green LED, GPIO2 red LED, GPIO5 power LED (220 ohm each), GPIO42 buzzer transistor (1 k)\n'
             'GPIO8 SCL / GPIO9 SDA: OLED + DS3231 (I2C)    GPIO10 CS, 11 SCK, 12 MOSI, 13 MISO: microSD (SPI)\n'
             'GPIO18 <- RDM6300 TX (9600 baud, 3.2 V level)    GPIO40 button 1 (session), GPIO41 button 2 (info)', x, y + 6, 1.8)
    y += 26
    sh.gtext('REFERENCES', x, y, 2.0, bold=True)
    sh.gtext('TOP 1-99, MIDDLE 101-199, BOTTOM 201-299: identical to the per-board schematics (sas_schematics)\n'
             'and to the three PCBs (sas_pcb). H* are the M3 mounting holes of each board.', x, y + 6, 1.8)


def main():
    sh = FullSheet()
    sh.sch.titleBlock = TitleBlock(title='SAS - Smart Attendance System: complete electrical schematic', date='2026-11-03',
                                   revision='1.0', company='Smart Attendance System - by Ice',
                                   comments={1: 'TOP + MIDDLE + BOTTOM boards and both ribbon cables on one sheet',
                                             2: 'Generated by tools/gen_full_schematic.py from the sas_schematics board data'})
    gs.Sheet = lambda *a, **k: sh       # the build_* functions now draw into the one full sheet
    for board, fn in (('MIDDLE', gs.build_middle), ('BOTTOM', gs.build_bottom), ('TOP', gs.build_top)):
        sh.start(board)
        fn(PROJ_DIR, None, None)
    sh.board = None
    frames_and_notes(sh)
    sh.route()
    sh.sch.to_file(os.path.join(PROJ_DIR, f'{PROJ}.kicad_sch'))

    # expected netlist (named nets, all boards merged) for the checker
    exp = {}
    for it in sh.items:
        for pp in it['pins']:
            if pp['net']:
                exp.setdefault(pp['net'], []).append(f"{it['ref']}.{pp['num']}")
    json.dump(exp, open(os.path.join(HERE, 'expected_nets.json'), 'w'), indent=1, sort_keys=True)

    with open(os.path.join(PROJ_DIR, 'sym-lib-table'), 'w') as f:
        f.write('(sym_lib_table\n  (version 7)\n  (lib (name "SAS")(type "KiCad")(uri "${KIPRJMOD}/../sas_schematics/sas_symbols.kicad_sym")'
                '(options "")(descr "Symbols used by the Smart Attendance System"))\n)\n')
    with open(os.path.join(PROJ_DIR, 'fp-lib-table'), 'w') as f:
        f.write('(fp_lib_table\n  (version 7)\n  (lib (name "smart_attendance")(type "KiCad")(uri "${KIPRJMOD}/../sas_schematics/smart_attendance.pretty")'
                '(options "")(descr "Custom module footprints + copies of the standard ones"))\n)\n')
    with open(os.path.join(PROJ_DIR, f'{PROJ}.kicad_pro'), 'w') as f:
        json.dump({'meta': {'filename': f'{PROJ}.kicad_pro', 'version': 1}}, f, indent=2)
    print('written', os.path.join(PROJ_DIR, f'{PROJ}.kicad_sch'))
    if sh.failed:
        print('drawn with labels instead of wires:', sh.failed)
    else:
        print('every connection drawn as a wire')


if __name__ == '__main__':
    main()

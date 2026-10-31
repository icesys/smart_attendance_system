#!/usr/bin/env python3
"""Generates the KiCad 7 schematics of the Smart Attendance System with REAL WIRES between the pins.

Parts are placed roughly where they sit on the real boards; every connection is drawn as an orthogonal wire found by a
small router (wires never overlap other nets; crossings are allowed only where two wires go straight through each other).
Pins of connectors/modules also carry the net name as a label, so you can read it on the wire.
If the router cannot draw a wire, that pin gets a label instead and is reported on screen.
Run:  python3 gen_schematics.py <output dir>
"""
import heapq, itertools, json, math, os, sys, uuid, copy
from kiutils.schematic import Schematic
from kiutils.symbol import SymbolLib
from kiutils.items.common import Position, Property, Effects, Font, Justify, PageSettings, TitleBlock, Stroke, ColorRGBA
from kiutils.items.schitems import (SchematicSymbol, LocalLabel, NoConnect, Text, Connection, Junction,
                                    SymbolProjectInstance, SymbolProjectPath, HierarchicalSheet,
                                    HierarchicalSheetProjectInstance, HierarchicalSheetProjectPath, HierarchicalSheetInstance)

LIBDIR = '/usr/share/kicad/symbols'
G = 1.27
PROJ = 'sas_schematics'
CUR = {'proj': PROJ, 'file': None}   # overridden when a board is written as its own project
_libs = {}
LOCAL = {}   # symbols copied into the project's own library sas_symbols.kicad_sym


def libsym(lib, name):
    if lib not in _libs:
        _libs[lib] = {s.entryName: s for s in SymbolLib.from_file(f'{LIBDIR}/{lib}.kicad_sym').symbols}
    return _libs[lib][name]


def fx(hide=False, h=1.27, just=None):
    e = Effects(font=Font(height=h, width=h), hide=hide)
    if just:
        e.justify = Justify(horizontally=just)
    return e


def snap(v):
    return round(round(v / 2.54) * 2.54, 3)


def tf(px, py, x, y, rot):
    r = math.radians(rot)
    return (x + px * math.cos(r) - py * math.sin(r), y - (px * math.sin(r) + py * math.cos(r)))


# ------------------------------------------------------------------------------------------------ router
class Router:
    def __init__(self, xmax=412, ymax=287):
        self.nx, self.ny = int(xmax / G) + 1, int(ymax / G) + 1
        self.blocked, self.pin_net, self.occ = set(), {}, {}
        self.segments, self.junctions = [], []

    def cell(self, x, y):
        return (round(x / G), round(y / G))

    def block_rect(self, x0, y0, x1, y1, m=0.6):
        for ix in range(math.ceil((x0 - m) / G), math.floor((x1 + m) / G) + 1):
            for iy in range(math.ceil((y0 - m) / G), math.floor((y1 + m) / G) + 1):
                self.blocked.add((ix, iy))

    def others(self, c, net):
        return {m: f for m, f in self.occ.get(c, {}).items() if m != net}

    def path(self, net, start, out, goal_cells, hint, tree):
        """A* from a pin end cell (first move must go outward) to any cell of the net's tree."""
        ctr = itertools.count()
        h = lambda c: abs(c[0] - hint[0]) + abs(c[1] - hint[1])
        a0 = 0 if out[0] != 0 else 1
        heap = [(h(start), next(ctr), 0, start, a0, None)]
        best = {}
        parent = {}
        n = 0
        while heap and n < 300000:
            f, _, cost, c, axis, par = heapq.heappop(heap)
            if (c, axis) in best:
                continue
            best[(c, axis)] = cost
            parent[(c, axis)] = par
            n += 1
            if c != start and c in goal_cells and not self.others(c, net):
                cells, key = [], (c, axis)
                while key is not None:
                    cells.append(key[0])
                    key = parent[key]
                return cells[::-1]
            for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                a2 = 0 if d[0] != 0 else 1
                if c == start and d != out:
                    continue
                if par is not None and (c[0] + d[0], c[1] + d[1]) == par[0]:
                    continue
                turn = (a2 != axis) and c != start
                if turn and self.others(c, net):
                    continue
                c2 = (c[0] + d[0], c[1] + d[1])
                if not (0 <= c2[0] < self.nx and 0 <= c2[1] < self.ny) or c2 in self.blocked:
                    continue
                pn = self.pin_net.get(c2)
                if pn is not None and (pn != net or c2 not in goal_cells):
                    continue
                cross = False
                ok = True
                for m, fl in self.others(c2, net).items():
                    if 'n' in fl or ('h' if a2 == 0 else 'v') in fl:
                        ok = False
                        break
                    cross = True
                if not ok:
                    continue
                nc = cost + 1 + (2 if turn else 0) + (8 if cross else 0)
                if (c2, a2) not in best:
                    heapq.heappush(heap, (nc + h(c2), next(ctr), nc, c2, a2, (c, axis)))
        return None

    def commit(self, net, cells, join):
        flags = lambda c: self.occ.setdefault(c, {}).setdefault(net, set())
        flags(cells[0]).add('n')
        flags(cells[-1]).add('n')
        if join:
            self.junctions.append(cells[-1])
        seg_start = cells[0]
        for i in range(1, len(cells)):
            d = (cells[i][0] - cells[i - 1][0], cells[i][1] - cells[i - 1][1])
            ax = 'h' if d[0] != 0 else 'v'
            flags(cells[i - 1]).add(ax)
            flags(cells[i]).add(ax)
            if i + 1 < len(cells):
                d2 = (cells[i + 1][0] - cells[i][0], cells[i + 1][1] - cells[i][1])
                if d2 != d:
                    flags(cells[i]).add('n')
                    self.segments.append((net, seg_start, cells[i]))
                    seg_start = cells[i]
        self.segments.append((net, seg_start, cells[-1]))


# ------------------------------------------------------------------------------------------------ sheet
class Sheet:
    def __init__(self, file, title, comment, root_uuid, sheet_uuid, labels_only=False):
        self.proj, self.file, self.labels_only = CUR['proj'], CUR['file'] or file, labels_only
        s = Schematic.create_new()
        s.version, s.generator, s.uuid = 20230121, 'eeschema', str(uuid.uuid4())
        self.root_uuid, self.sheet_uuid = (root_uuid or s.uuid), sheet_uuid
        s.paper = PageSettings(paperSize='A3')
        s.titleBlock = TitleBlock(title=title, date='2026-10-29', revision='0.7',
                                  company='Smart Attendance System - by Ice', comments={1: comment})
        self.sch, self.embedded, self.items, self.failed = s, set(), [], []

    def text(self, t, x, y, h=1.8):
        self.sch.texts.append(Text(text=t, position=Position(x, y, 0), effects=fx(h=h), uuid=str(uuid.uuid4())))

    def label(self, net, x, y, out):
        ang = {(1, 0): 0, (0, -1): 90, (-1, 0): 180, (0, 1): 270}[out]
        self.sch.labels.append(LocalLabel(text=net, position=Position(round(x, 3), round(y, 3), ang),
                                          effects=fx(just='right' if ang in (180, 270) else None), uuid=str(uuid.uuid4())))

    def place(self, lib, name, ref, value, x, y, rot=0, fp='', unit=1, nets=None, nc=(), dnp=False):
        x, y = snap(x), snap(y)
        sym = libsym(lib, name)
        if name not in LOCAL:
            LOCAL[name] = copy.deepcopy(sym)
        lib = 'SAS'
        if (lib, name) not in self.embedded:
            c = copy.deepcopy(sym)
            c.libraryNickname = lib
            self.sch.libSymbols.append(c)
            self.embedded.add((lib, name))
        nets = {str(k): v for k, v in (nets or {}).items()}
        nc = [str(n) for n in nc]
        pts, pins, used = [], [], set()
        for u in sym.units:
            if u.unitId not in (0, unit) or u.styleId not in (0, 1):
                continue
            for g in u.graphicItems:
                k = type(g).__name__
                if k == 'SyRect':
                    pts += [(g.start.X, g.start.Y), (g.end.X, g.end.Y)]
                elif k == 'SyPolyLine':
                    pts += [(q.X, q.Y) for q in g.points]
                elif k == 'SyCircle':
                    pts += [(g.center.X + dx * g.radius, g.center.Y + dy * g.radius) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))]
                elif k == 'SyArc':
                    pts += [(g.start.X, g.start.Y), (g.mid.X, g.mid.Y), (g.end.X, g.end.Y)]
            for p in u.pins:
                ex, ey = tf(p.position.X, p.position.Y, x, y, rot)
                a = math.radians(p.position.angle + rot)
                out = (round(-math.cos(a)), round(math.sin(a)))
                key = p.number if p.number in nets else (p.name if p.name in nets else None)
                net = nets[key] if key is not None else None
                if key is not None:
                    used.add(key)
                elif not (p.number in nc or p.name in nc):
                    raise SystemExit(f'{self.proj} {ref}: pin {p.number} ({p.name}) has no net')
                pins.append(dict(num=p.number, end=(round(ex, 3), round(ey, 3)), out=out, length=p.length, net=net))
        if set(nets) - used:
            raise SystemExit(f'{self.proj} {ref}: unknown pins {set(nets) - used}')
        spts = [tf(px, py, x, y, rot) for px, py in pts] or [pp['end'] for pp in pins]
        bb = (min(q[0] for q in spts), min(q[1] for q in spts), max(q[0] for q in spts), max(q[1] for q in spts))
        cx = (bb[0] + bb[2]) / 2
        s = SchematicSymbol()
        s.libraryNickname, s.entryName = lib, name
        s.position, s.unit, s.inBom, s.onBoard, s.dnp = Position(x, y, rot), unit, True, True, dnp
        s.uuid = str(uuid.uuid4())
        s.properties = [Property('Reference', ref, 0, Position(round(cx, 2), round(bb[1] - 2.0, 2), 0), fx()),
                        Property('Value', value, 1, Position(round(cx, 2), round(bb[3] + 2.0, 2), 0), fx()),
                        Property('Footprint', fp, 2, Position(x, y, 0), fx(hide=True)),
                        Property('Datasheet', '~', 3, Position(x, y, 0), fx(hide=True))]
        s.instances = [SymbolProjectInstance(name=self.proj, paths=[
            SymbolProjectPath(sheetInstancePath='/' + self.root_uuid + (('/' + self.sheet_uuid) if self.sheet_uuid else ''), reference=ref, unit=unit)])]
        for pp in pins:
            s.pins[pp['num']] = str(uuid.uuid4())
        self.sch.schematicSymbols.append(s)
        self.items.append(dict(ref=ref, bbox=bb, pins=pins))

    # ---------------------------------------------------------------------------------------- routing
    def finish(self, outdir):
        sch = self.sch
        net_pins = {}
        for it in self.items:
            for pp in it['pins']:
                if pp['net'] is None:
                    sch.noConnects.append(NoConnect(position=Position(*pp['end'], 0), uuid=str(uuid.uuid4())))
                else:
                    net_pins.setdefault(pp['net'], []).append((it['ref'], pp))
                    if it['ref'].startswith('J') or self.labels_only:
                        self.label(pp['net'], *pp['end'], pp['out'])
        if not self.labels_only:
            R = Router()
            R.block_rect(-5, -5, 420, 12)
            R.block_rect(-5, -5, 12, 300)
            R.block_rect(405, -5, 420, 300)
            R.block_rect(-5, 252, 420, 300) if False else None
            R.block_rect(236, 250, 420, 300)
            for it in self.items:
                R.block_rect(*it['bbox'])
                for pp in it['pins']:
                    c = R.cell(*pp['end'])
                    R.pin_net[c] = pp['net'] or '__nc__'
                    for k in range(1, int(round(pp['length'] / G)) + 1):
                        R.blocked.add((c[0] - pp['out'][0] * k, c[1] - pp['out'][1] * k))
            for it in self.items:   # a pin tip and the cell in front of it must always be free to leave the pin
                for pp in it['pins']:
                    c = R.cell(*pp['end'])
                    R.blocked.discard(c)
                    R.blocked.discard((c[0] + pp['out'][0], c[1] + pp['out'][1]))
            rails = ('GND', '3V3', '5V_SYS', '5V_BOOST')
            order = sorted(net_pins, key=lambda n: (rails.index(n) if n in rails else 9, len(net_pins[n])))
            for net in order:
                plist = [pp for _, pp in net_pins[net]]
                cells = [R.cell(*pp['end']) for pp in plist]
                tree = {cells[0]}
                R.occ.setdefault(cells[0], {}).setdefault(net, set()).add('n')
                todo = list(range(1, len(plist)))
                while todo:
                    # connect the unconnected pin that is nearest to the tree
                    j = min(todo, key=lambda k: min(abs(cells[k][0] - t[0]) + abs(cells[k][1] - t[1]) for t in tree))
                    todo.remove(j)
                    hint = min(tree, key=lambda t: abs(cells[j][0] - t[0]) + abs(cells[j][1] - t[1]))
                    path = R.path(net, cells[j], plist[j]['out'], tree, hint, tree)
                    if path is None:
                        self.failed.append((net, net_pins[net][j][0], plist[j]['num']))
                        self.label(net, *plist[j]['end'], plist[j]['out'])
                        self.label(net, *plist[0]['end'], plist[0]['out'])
                        continue
                    join = path[-1] not in {cells[0]} or len(path) > 0
                    R.commit(net, path, True)
                    tree.update(path)
            # split every wire at all points where another wire of the same net ends or joins, so that all
            # connections are end-to-end (no wire end sitting in the middle of another wire)
            nodes = {}
            for net, a, b in R.segments:
                nodes.setdefault(net, set()).update([a, b])
            for c in R.junctions:
                for net in R.occ.get(c, {}):
                    nodes.setdefault(net, set()).add(c)
            split = []
            for net, a, b in R.segments:
                inner = sorted([c for c in nodes[net] if c not in (a, b) and
                                ((a[0] == b[0] == c[0] and min(a[1], b[1]) < c[1] < max(a[1], b[1])) or
                                 (a[1] == b[1] == c[1] and min(a[0], b[0]) < c[0] < max(a[0], b[0])))],
                               key=lambda c: abs(c[0] - a[0]) + abs(c[1] - a[1]))
                pts_ = [a] + inner + [b]
                split += [(net, pts_[i], pts_[i + 1]) for i in range(len(pts_) - 1)]
            for net, a, b in split:
                sch.graphicalItems.append(Connection(type='wire', points=[Position(round(a[0] * G, 3), round(a[1] * G, 3)),
                                                                           Position(round(b[0] * G, 3), round(b[1] * G, 3))],
                                                     stroke=Stroke(width=0, type='default'), uuid=str(uuid.uuid4())))
            for c in R.junctions:
                sch.junctions.append(Junction(position=Position(round(c[0] * G, 3), round(c[1] * G, 3)), diameter=0, uuid=str(uuid.uuid4())))
        os.makedirs(outdir, exist_ok=True)
        sch.to_file(os.path.join(outdir, f'{self.file}.kicad_sch'))
        json.dump({n: [f"{r}.{pp['num']}" for r, pp in v] for n, v in net_pins.items()}, open(f'/tmp/expected_{self.file}.json', 'w'))
        self.expected = net_pins
        if self.failed:
            print(self.file, 'pins drawn with a label instead of a wire:', self.failed)


# ---------------- shared connector pin maps (same pinout at both ends of every cable) -------------
J_TM = {1: '3V3', 2: 'GND', 3: '5V_SYS', 4: 'GPIO42', 5: 'GPIO5', 6: 'GPIO1', 7: 'GPIO2', 8: 'GND',
        9: 'GPIO40', 10: 'GPIO41', 11: 'SCL', 12: 'SDA', 13: 'GND', 14: 'COIL_A', 15: 'COIL_B', 16: 'GND'}
J_MB = {1: '5V_BOOST', 2: 'GND', 3: '5V_BOOST', 4: 'GND', 5: '5V_SYS', 6: '3V3', 7: 'GND', 8: 'SDA',
        9: 'SCL', 10: 'GND', 11: 'SD_CS', 12: 'SD_SCK', 13: 'GND', 14: 'SD_MOSI', 15: 'SD_MISO', 16: 'GND'}
IDC = 'Connector_IDC:IDC-Header_2x08_P2.54mm_Vertical'
HDR = 'Connector_PinHeader_2.54mm:PinHeader_1x%02d_P2.54mm_Vertical'
RES = 'Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal'
CER = 'Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm'


def add_holes(sh, base):
    for i in range(4):
        sh.place('Mechanical', 'MountingHole', f'H{base + i}', 'M3', 40 + 22 * i, 245, fp='MountingHole:MountingHole_3.2mm_M3')


def conn2x8(sh, ref, x, y, nets, label, rot=0):
    sh.place('Connector_Generic', 'Conn_02x08_Odd_Even', ref, label, x, y, rot=rot, fp=IDC, nets=nets)


def build_top(out, ru, su):
    sh = Sheet('top', 'TOP board: LEDs, buzzer, buttons, OLED, RFID coil', 'J1 = J_TM cable to the MIDDLE board', ru, su)
    sh.text('TOP BOARD (95 x 60 mm): LEDs and decoupling on the left, buzzer on the right, OLED and coil below', 140, 22, 2.5)
    conn2x8(sh, 'J1', 70, 130, J_TM, 'J_TM (to MIDDLE)')
    for i, (d, r, gpio, net, col) in enumerate([('D1', 'R1', 'GPIO5', 'LED_BLUE', 'blue (power LED)'),
                                                 ('D2', 'R2', 'GPIO1', 'LED_GRN', 'green'),
                                                 ('D3', 'R3', 'GPIO2', 'LED_RED', 'red')]):
        y = 45 + 17 * i
        sh.place('Device', 'R', r, '220', 140, y, rot=90, fp=RES, nets={1: gpio, 2: net})
        sh.place('Device', 'LED', d, col, 185, y, rot=180, fp='LED_THT:LED_D5.0mm', nets={'A': net, 'K': 'GND'})
    for i, (c, v) in enumerate([('C1', '100n'), ('C2', '10u'), ('C3', '100n')]):
        sh.place('Device', 'C', c, v, 235 + 17 * i, 55, fp=CER, nets={1: '3V3', 2: 'GND'})
    sh.place('Jumper', 'SolderJumper_3_Bridged12', 'JP1', 'BUZ supply (1-2 = 3V3)', 305, 45,
             fp='Jumper:SolderJumper-3_P1.3mm_Bridged12_RoundedPad1.0x1.5mm', nets={1: '3V3', 3: '5V_SYS', 2: 'BUZ_VCC'})
    sh.place('Device', 'Buzzer', 'BZ1', 'Buzzer 12 mm (8 mm pins)', 350, 65, fp='smart_attendance:Buzzer_12mm_P8mm',
             nets={1: 'BUZ_VCC', 2: 'BUZ_N'})
    sh.place('Device', 'D', 'D4', '1N4148', 325, 95, rot=90, fp='Diode_THT:D_DO-35_SOD27_P7.62mm_Horizontal',
             nets={'K': 'BUZ_VCC', 'A': 'BUZ_N'})
    sh.place('Device', 'Q_NPN_EBC', 'Q1', '2N2222A', 350, 130, fp='Package_TO_SOT_THT:TO-92_Inline',
             nets={'B': 'BUZ_B', 'C': 'BUZ_N', 'E': 'GND'})
    sh.place('Device', 'R', 'R4', '1k', 285, 130, rot=90, fp=RES, nets={1: 'GPIO42', 2: 'BUZ_B'})
    sh.place('Device', 'R', 'R5', '100k', 305, 160, fp=RES, nets={1: 'BUZ_B', 2: 'GND'})
    sh.place('Switch', 'SW_Push', 'SW1', 'Button 1 (session)', 150, 195, fp='Button_Switch_THT:SW_PUSH_6mm',
             nets={1: 'GPIO40', 2: 'GND'})
    sh.place('Switch', 'SW_Push', 'SW2', 'Button 2 (info)', 150, 215, fp='Button_Switch_THT:SW_PUSH_6mm',
             nets={1: 'GPIO41', 2: 'GND'})
    sh.place('Connector_Generic', 'Conn_01x04', 'J2', 'OLED 0.96in (GND VCC SCL SDA)', 235, 180,
             fp='smart_attendance:MOD_OLED096', nets={1: 'GND', 2: '3V3', 3: 'SCL', 4: 'SDA'})
    sh.place('Connector_Generic', 'Conn_01x02', 'J3', 'RFID coil 35 x 46', 235, 220, fp=HDR % 2,
             nets={1: 'COIL_A', 2: 'COIL_B'})
    add_holes(sh, 1)
    sh.finish(out)
    return sh


ESP_L = ['GND', 'GND', 'GPIO19', 'GPIO20', 'GPIO21', 'GPIO47', 'GPIO48', 'GPIO45', 'GPIO0', 'GPIO35', 'GPIO36',
         'GPIO37', 'GPIO38', 'GPIO39', 'GPIO40', 'GPIO41', 'GPIO42', 'GPIO2', 'GPIO1', 'RX', 'TX', 'GND']
ESP_R = ['GND', '5V', 'GPIO14', 'GPIO13', 'GPIO12', 'GPIO11', 'GPIO10', 'GPIO9', 'GPIO46', 'GPIO3', 'GPIO8',
         'GPIO18', 'GPIO17', 'GPIO16', 'GPIO15', 'GPIO7', 'GPIO6', 'GPIO5', 'GPIO4', 'RST', '3V3', '3V3']
ESP_USED = {'GND': 'GND', '5V': '5V_SYS', '3V3': '3V3', 'GPIO40': 'GPIO40', 'GPIO41': 'GPIO41', 'GPIO42': 'GPIO42',
            'GPIO2': 'GPIO2', 'GPIO1': 'GPIO1', 'GPIO5': 'GPIO5', 'GPIO8': 'SCL', 'GPIO9': 'SDA',
            'GPIO10': 'SD_CS', 'GPIO11': 'SD_SCK', 'GPIO12': 'SD_MOSI', 'GPIO13': 'SD_MISO', 'GPIO18': 'GPIO18'}


def esp_nets(names):
    nets, nc = {}, []
    for i, n in enumerate(names, 1):
        (nets.__setitem__(i, ESP_USED[n]) if n in ESP_USED else nc.append(i))
    return nets, nc


def build_middle(out, ru, su):
    sh = Sheet('middle', 'MIDDLE board: ESP32-S3, RDM6300, 5V diode', 'ESP32 rows checked against the S3-N16R8 pin diagram', ru, su)
    sh.text('MIDDLE BOARD (95 x 60 mm): cable to TOP on the left, ESP32-S3 in the middle, cable to BOTTOM and power on the right', 150, 22, 2.5)
    conn2x8(sh, 'J105', 50, 100, J_TM, 'J_TM (to TOP)')
    nets, nc = esp_nets(ESP_L)
    sh.place('Connector_Generic', 'Conn_01x22', 'J101', 'ESP32-S3 row 1 (USB end at the top)', 140, 150,
             fp='Connector_PinSocket_2.54mm:PinSocket_1x22_P2.54mm_Vertical', nets=nets, nc=nc)
    nets, nc = esp_nets(ESP_R)
    sh.place('Connector_Generic', 'Conn_01x22', 'J102', 'ESP32-S3 row 2', 220, 150, rot=180,
             fp='Connector_PinSocket_2.54mm:PinSocket_1x22_P2.54mm_Vertical', nets=nets, nc=nc)
    sh.place('Device', 'D_Schottky', 'D101', 'Schottky 1A (1N5819)', 330, 45,
             fp='Diode_THT:D_DO-41_SOD81_P10.16mm_Horizontal', nets={'A': '5V_BOOST', 'K': '5V_SYS'})
    for i, (c, v, n) in enumerate([('C101', '10u', '5V_SYS'), ('C102', '100n', '5V_SYS'), ('C103', '100n', '3V3')]):
        sh.place('Device', 'C', c, v, 290 + 17 * i, 90, fp=CER, nets={1: n, 2: 'GND'})
    sh.place('Connector_Generic', 'Conn_01x07', 'J103', 'RDM6300 (TX RX nc GND 5V | ANT1 ANT2)', 290, 190,
             fp='smart_attendance:MOD_RDM6300', nets={1: 'GPIO18', 4: 'GND', 5: '5V_SYS', 6: 'COIL_A', 7: 'COIL_B'}, nc=[2, 3])
    conn2x8(sh, 'J106', 380, 130, J_MB, 'J_MB (to BOTTOM)')
    sh.text('RDM6300 TX is 3.2 V: it goes straight to GPIO18 (no resistor needed)', 290, 215)
    sh.text('GPIO map: 1 green LED, 2 red LED, 5 blue LED, 8 SCL, 9 SDA, 10-13 SD, 18 RFID TX, 40/41 buttons, 42 buzzer', 20, 270)
    add_holes(sh, 101)
    sh.finish(out)
    return sh


def build_bottom(out, ru, su):
    sh = Sheet('bottom', 'BOTTOM board: battery, charger, boost, switch, SD, RTC', 'MT3608: set 5.0 V with a multimeter first', ru, su)
    sh.text('BOTTOM BOARD (95 x 60 mm): the 18650 holder sits UNDER this board, its two wires come up to J2', 150, 22, 2.5)
    conn2x8(sh, 'J201', 60, 150, J_MB, 'J_MB (to MIDDLE)')
    sh.place('Connector_Generic', 'Conn_01x06', 'J205', 'microSD module (GND VCC MISO MOSI SCK CS)', 160, 50,
             fp='smart_attendance:MOD_SD_6PIN', nets={1: 'GND', 2: '5V_SYS', 3: 'SD_MISO', 4: 'SD_MOSI', 5: 'SD_SCK', 6: 'SD_CS'})
    sh.place('Connector_Generic', 'Conn_01x06', 'J206', 'DS3231 (32K SQW SCL SDA VCC GND)', 260, 50,
             fp='smart_attendance:MOD_DS3231_6PIN', nets={3: 'SCL', 4: 'SDA', 5: '3V3', 6: 'GND'}, nc=[1, 2])
    sh.place('Switch', 'SW_DPDT_x2', 'SW201', 'Slide switch 6-pin', 160, 110, unit=1, fp='smart_attendance:SW_Slide_6pin_2mm',
             nets={1: 'SW_OUT', 2: 'CHG_OUT+'}, nc=[3])
    sh.place('Switch', 'SW_DPDT_x2', 'SW201', 'Slide switch 6-pin', 160, 140, unit=2, fp='smart_attendance:SW_Slide_6pin_2mm',
             nets={4: 'SW_OUT', 5: 'CHG_OUT+'}, nc=[6])
    sh.place('Connector_Generic', 'Conn_01x04', 'J203', 'TP4056 (OUT+ B+ B- OUT-)', 160, 230,
             fp='smart_attendance:MOD_TP4056', nets={1: 'CHG_OUT+', 2: 'BAT+', 3: 'BAT-', 4: 'GND'})
    sh.place('Connector_Generic', 'Conn_01x02', 'J202', 'Battery 18650 (under the board)', 160, 190, fp=HDR % 2,
             nets={1: 'BAT+', 2: 'BAT-'})
    sh.place('Connector_Generic', 'Conn_01x04', 'J204', 'MT3608 (VIN+ VIN- VOUT+ VOUT-)', 270, 190,
             fp='smart_attendance:MOD_MT3608', nets={1: 'SW_OUT', 2: 'GND', 3: '5V_BOOST', 4: 'GND'})
    sh.place('Device', 'C_Polarized', 'C201', '470u 10V (10 mm, 5 mm pins)', 340, 120,
             fp='Capacitor_THT:CP_Radial_D10.0mm_P5.00mm', nets={1: '5V_BOOST', 2: 'GND'})
    sh.place('Device', 'C', 'C202', '100n', 365, 120, fp=CER, nets={1: '5V_BOOST', 2: 'GND'})
    sh.text('BAT- is NOT ground: it is behind the protection chip of the TP4056 (OUT- is the system ground)', 150, 255)
    add_holes(sh, 201)
    sh.finish(out)
    return sh




def build_root(out, ru, sheets):
    s = Schematic.create_new()
    s.version, s.generator, s.uuid = 20230121, 'eeschema', ru
    s.paper = PageSettings(paperSize='A3')
    s.titleBlock = TitleBlock(title='SAS - Smart Attendance System: root sheet', date='2026-10-29', revision='0.7',
                              company='Smart Attendance System - by Ice', comments={1: 'Open the three boards below with a double click'})
    def txt(t, x, y, h=1.8):
        s.texts.append(Text(text=t, position=Position(x, y, 0), effects=fx(h=h), uuid=str(uuid.uuid4())))
    txt('SMART ATTENDANCE SYSTEM: three boards stacked TOP / MIDDLE / BOTTOM, joined by two 16-conductor ribbon cables', 20, 22, 2.8)
    for i, (name, fname, su, desc) in enumerate(sheets):
        x = 30 + i * 125
        s.sheets.append(HierarchicalSheet(position=Position(x, 45, 0), width=100, height=30, fieldsAutoplaced=True,
                                          stroke=Stroke(width=0.1524, type='solid'), fill=ColorRGBA(0, 0, 0, 0), uuid=su,
                                          sheetName=Property('Sheetname', name, 0, Position(x, 43.5, 0), fx(just='left')),
                                          fileName=Property('Sheetfile', fname, 1, Position(x, 77, 0), fx(just='left')),
                                          instances=[HierarchicalSheetProjectInstance(name=PROJ, paths=[
                                              HierarchicalSheetProjectPath(sheetInstancePath='/' + ru, page=str(i + 2))])]))
        txt(desc, x + 2, 82, 1.5)
    txt('CABLE 1 (TOP J1 <-> MIDDLE J105), pin = same number at both ends:', 30, 105, 2.0)
    for k in range(1, 17):
        txt(f'{k:2d}  {J_TM[k]}', 30 + ((k - 1) // 8) * 60, 112 + ((k - 1) % 8) * 6, 1.8)
    txt('CABLE 2 (MIDDLE J106 <-> BOTTOM J201), pin = same number at both ends:', 30, 170, 2.0)
    for k in range(1, 17):
        txt(f'{k:2d}  {J_MB[k]}', 30 + ((k - 1) // 8) * 60, 177 + ((k - 1) % 8) * 6, 1.8)
    txt('POWER PATH: 18650 -> TP4056 (protected) -> slide switch -> MT3608 (set to 5.0 V) -> cable 2 pins 1,3 (5V_BOOST)', 200, 112, 1.8)
    txt('-> MIDDLE Schottky diode -> 5V_SYS (ESP32 5V pin, RDM6300, SD module, buzzer option). 3V3 comes from the ESP32 board.', 200, 119, 1.8)
    txt('USB wins when plugged (about 5 V against 4.7 V from the battery); the battery takes over when USB is unplugged.', 200, 126, 1.8)
    txt('BAT- is not ground: on the protected TP4056 it sits behind the protection chip (OUT- is the system ground).', 200, 133, 1.8)
    txt('References: TOP uses numbers 1-99, MIDDLE 101-199, BOTTOM 201-299 so they stay unique in this project.', 200, 140, 1.8)
    s.sheetInstances = [HierarchicalSheetInstance(instancePath='/', page='1')]
    os.makedirs(out, exist_ok=True)
    s.to_file(os.path.join(out, f'{PROJ}.kicad_sch'))


def write_libs(base, sym_uri, fp_uri, local):
    from kiutils.symbol import SymbolLib as _SL
    with open(os.path.join(base, 'sym-lib-table'), 'w') as f:
        f.write('(sym_lib_table\n  (version 7)\n  (lib (name "SAS")(type "KiCad")(uri "%s")(options "")(descr "Symbols used by the Smart Attendance System"))\n)\n' % sym_uri)
    with open(os.path.join(base, 'fp-lib-table'), 'w') as f:
        f.write('(fp_lib_table\n  (version 7)\n  (lib (name "smart_attendance")(type "KiCad")(uri "%s")(options "")(descr "Custom module footprints"))\n)\n' % fp_uri)
    with open(os.path.join(base, f'{local}.kicad_pro'), 'w') as f:
        json.dump({'meta': {'filename': f'{local}.kicad_pro', 'version': 1}}, f, indent=2)


def write_symbol_lib(path):
    from kiutils.symbol import SymbolLib as _SL
    lib = _SL(version='20211014', generator='kiutils')
    for n in sorted(LOCAL):
        c = copy.deepcopy(LOCAL[n])
        c.libraryNickname = None
        lib.symbols.append(c)
    lib.to_file(path)


if __name__ == '__main__':
    base = sys.argv[1]
    pcb = sys.argv[2] if len(sys.argv) > 2 else None
    ru = str(uuid.uuid4())
    sheets = [('TOP', 'top.kicad_sch', str(uuid.uuid4()), 'LEDs, buzzer driver, 2 buttons, OLED, RFID coil'),
              ('MIDDLE', 'middle.kicad_sch', str(uuid.uuid4()), 'ESP32-S3 sockets, RDM6300, 5 V Schottky, both cables'),
              ('BOTTOM', 'bottom.kicad_sch', str(uuid.uuid4()), 'Battery, TP4056, MT3608, switch, SD card, DS3231')]
    build_root(base, ru, sheets)
    build_top(base, ru, sheets[0][2])
    build_middle(base, ru, sheets[1][2])
    build_bottom(base, ru, sheets[2][2])
    write_symbol_lib(os.path.join(base, 'sas_symbols.kicad_sym'))
    write_libs(base, '${KIPRJMOD}/sas_symbols.kicad_sym', '${KIPRJMOD}/smart_attendance.pretty', PROJ)
    print('project written to', base)
    if pcb:   # one stand-alone project per board, sharing the libraries of the folder above
        for name, fn in (('top', build_top), ('middle', build_middle), ('bottom', build_bottom)):
            CUR['proj'], CUR['file'] = f'pcb_{name}', f'pcb_{name}'
            d = os.path.join(pcb, f'pcb_{name}')
            os.makedirs(d, exist_ok=True)
            fn(d, None, None)
            write_libs(d, '${KIPRJMOD}/../sas_symbols.kicad_sym', '${KIPRJMOD}/../smart_attendance.pretty', f'pcb_{name}')
        write_symbol_lib(os.path.join(pcb, 'sas_symbols.kicad_sym'))
        print('board projects written to', pcb)

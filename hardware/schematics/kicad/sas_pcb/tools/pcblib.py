"""Helpers to build a KiCad board file with kiutils: footprints placed (no tracks), nets assigned, outline and checks."""
import math, os, uuid, copy
import xml.etree.ElementTree as ET
from kiutils.board import Board
from kiutils.footprint import Footprint
from kiutils.items.common import Position, Net, PageSettings, TitleBlock, Effects, Font
from kiutils.items.gritems import GrRect, GrText
from kiutils.items.fpitems import FpText
from kiutils.items.zones import Zone, KeepoutSettings, ZonePolygon, Hatch

STD = '/usr/share/kicad/footprints'
W, H = 95.0, 60.0
OX, OY = 100.0, 100.0          # board corner on the KiCad sheet
HOLES = [(4, 4), (91, 4), (4, 56), (91, 56)]
HOLE_R = 3.5                   # keep-out radius around each M3 hole (screw head / standoff)


def rot(x, y, a):
    r = math.radians(a)
    return (x * math.cos(r) + y * math.sin(r), -x * math.sin(r) + y * math.cos(r))


def load_fp(libname, name, custom_dir):
    path = (os.path.join(custom_dir, f'{name}.kicad_mod') if libname == 'smart_attendance'
            else f'{STD}/{libname}.pretty/{name}.kicad_mod')
    return Footprint.from_file(path)


def local_bbox(fp):
    pts = []
    for g in fp.graphicItems:
        if getattr(g, 'layer', None) != 'F.CrtYd':
            continue
        k = type(g).__name__
        if k in ('FpLine', 'FpRect'):
            pts += [(g.start.X, g.start.Y), (g.end.X, g.end.Y)]
        elif k == 'FpCircle':
            r = math.hypot(g.end.X - g.center.X, g.end.Y - g.center.Y)
            pts += [(g.center.X - r, g.center.Y - r), (g.center.X + r, g.center.Y + r)]
        elif k == 'FpPoly':
            pts += [(p.X, p.Y) for p in g.coordinates]
    if not pts:
        pts = [(p.position.X + dx * p.size.X / 2, p.position.Y + dy * p.size.Y / 2) for p in fp.pads for dx in (-1, 1) for dy in (-1, 1)]
        pts = [(x - 0.5 * (1 if x < 0 else -1) * 0, y) for x, y in pts]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


def read_netlist(xml_path):
    r = ET.parse(xml_path).getroot()
    comps = {}
    for c in r.find('components'):
        ts = c.find('tstamps')
        comps[c.get('ref')] = dict(value=(c.find('value').text or ''), fp=(c.find('footprint').text or ''),
                                   uuid=(ts.text.split()[0] if ts is not None and ts.text else str(uuid.uuid4())))
    nets = []
    pad_net = {}
    for i, n in enumerate(r.find('nets'), 1):
        nets.append((i, n.get('name')))
        for x in n:
            pad_net[(x.get('ref'), x.get('pin'))] = (i, n.get('name'))
    return comps, nets, pad_net


class PCB:
    def __init__(self, title, xml, custom_dir):
        self.comps, self.nets, self.pad_net = read_netlist(xml)
        self.custom = custom_dir
        b = Board.create_new()
        b.version, b.generator = 20221018, 'pcbnew'
        b.paper = PageSettings(paperSize='A4')
        b.titleBlock = TitleBlock(title=title, date='2026-10-30', revision='0.1', company='Smart Attendance System - by Ice')
        b.nets = [Net(0, '')] + [Net(i, n) for i, n in self.nets]
        self.b, self.placed, self.info, self.rots = b, {}, {}, {}

    def put(self, ref, cx, cy, rot_deg=0):
        """Place footprint `ref` so that the centre of its courtyard is at board position (cx, cy) (mm from the board corner)."""
        c = self.comps[ref]
        lib, name = c['fp'].split(':')
        fp = load_fp(lib, name, self.custom)
        fp.libraryNickname = lib
        x1, y1, x2, y2 = local_bbox(fp)
        lx, ly = (x1 + x2) / 2, (y1 + y2) / 2
        ox, oy = rot(lx, ly, rot_deg)
        X, Y = cx - ox, cy - oy
        fp.position = Position(round(OX + X, 4), round(OY + Y, 4), rot_deg % 360 if rot_deg else None)
        fp.layer = 'F.Cu'
        fp.path = '/' + c['uuid']
        fp.tstamp = c['uuid']
        for g in fp.graphicItems:
            if isinstance(g, FpText):
                if g.type == 'reference':
                    g.text = ref
                elif g.type == 'value':
                    g.text = c['value']
                if rot_deg:
                    g.position.angle = ((g.position.angle or 0) + rot_deg) % 360
        for p in fp.pads:
            if rot_deg:
                p.position.angle = ((p.position.angle or 0) + rot_deg) % 360
            key = (ref, p.number)
            if key in self.pad_net:
                n, nm = self.pad_net[key]
                p.net = Net(n, nm)
        self.b.footprints.append(fp)
        self.rots[ref] = rot_deg % 360
        # world bounding box (board coordinates)
        pts = [rot(px, py, rot_deg) for px in (x1, x2) for py in (y1, y2)]
        wx0, wx1 = min(p[0] for p in pts) + X, max(p[0] for p in pts) + X
        wy0, wy1 = min(p[1] for p in pts) + Y, max(p[1] for p in pts) + Y
        self.placed[ref] = (wx0, wy0, wx1, wy1)
        self.info[ref] = (name, round(wx1 - wx0, 1), round(wy1 - wy0, 1))

    def place_refs(self):
        """Reference designators on the silkscreen only where there is free room inside the board; otherwise on F.Fab."""
        taken, moved = [], 0
        def hit(a, b, m=0.0):
            return a[0] < b[2] + m and a[2] > b[0] - m and a[1] < b[3] + m and a[3] > b[1] - m
        for fp in self.b.footprints:
            texts = [g for g in fp.graphicItems if isinstance(g, FpText) and g.type in ('reference', 'value')]
            ref = [g.text for g in texts if g.type == 'reference'][0]
            if ref.startswith('H'):
                for g in texts:
                    g.hide = True
                continue
            x0, y0, x1, y1 = self.placed[ref]
            n = len(ref)
            w, h = n * 0.85 + 0.5, 1.6
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            cands = [(cx, y0 - 0.4 - h / 2), (cx, y1 + 0.4 + h / 2), (x0 - 0.4 - w / 2, cy), (x1 + 0.4 + w / 2, cy)]
            ok = None
            for qx, qy in cands:
                bx = (qx - w / 2, qy - h / 2, qx + w / 2, qy + h / 2)
                if bx[0] < 0.8 or bx[1] < 0.8 or bx[2] > W - 0.8 or bx[3] > H - 0.8:
                    continue
                if any(hit(bx, bb, 0.3) for r2, bb in self.placed.items() if r2 != ref and not r2.startswith('H')):
                    continue
                if any(hit(bx, t_) for t_ in taken):
                    continue
                if any(math.hypot(max(bx[0] - hx, 0, hx - bx[2]), max(bx[1] - hy, 0, hy - bx[3])) < 3.6 for hx, hy in HOLES):
                    continue
                ok = (qx, qy, bx)
                break
            g = [g for g in texts if g.type == 'reference'][0]
            g.effects = Effects(font=Font(height=1.0, width=1.0, thickness=0.15))
            if ok:
                dx, dy = ok[0] - (fp.position.X - OX), ok[1] - (fp.position.Y - OY)
                lx, ly = rot(dx, dy, -(fp.position.angle or 0))
                g.position = Position(round(lx, 4), round(ly, 4), 0)
                g.layer = 'F.SilkS'
                taken.append(ok[2])
            else:
                g.layer = 'F.Fab'
                moved += 1
        return moved

    def outline(self):
        self.b.graphicItems.append(GrRect(start=Position(OX, OY), end=Position(OX + W, OY + H), layer='Edge.Cuts', width=0.1, fill='none'))

    def silk_rect(self, x0, y0, x1, y1, layer='Dwgs.User'):
        self.b.graphicItems.append(GrRect(start=Position(OX + x0, OY + y0), end=Position(OX + x1, OY + y1), layer=layer, width=0.15, fill='none'))

    def text(self, t, x, y, size=1.5, layer='Dwgs.User'):
        self.b.graphicItems.append(GrText(text=t, position=Position(OX + x, OY + y, 0), layer=layer,
                                          effects=Effects(font=Font(height=size, width=size, thickness=0.2))))

    def keepout(self, x0, y0, x1, y1, name):
        z = Zone(net=0, netName='', layers=['F.Cu', 'B.Cu'], tstamp=str(uuid.uuid4()), name=name,
                 hatch=Hatch(style='edge', pitch=0.5),
                 keepoutSettings=KeepoutSettings(tracks='not_allowed', vias='not_allowed', pads='allowed', copperpour='not_allowed', footprints='allowed'),
                 polygons=[ZonePolygon(coordinates=[Position(OX + a, OY + b) for a, b in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))])])
        self.b.zones.append(z)

    def check(self, keepouts=(), allow=()):
        """Overlaps, board edge and mounting-hole clearance. Returns a list of problems."""
        bad = []
        refs = [r for r in self.placed if not r.startswith('H')]
        for i, a in enumerate(refs):
            ax0, ay0, ax1, ay1 = self.placed[a]
            if ax0 < 0.3 or ay0 < 0.3 or ax1 > W - 0.3 or ay1 > H - 0.3:
                bad.append(f'{a} sticks out of / touches the board edge {tuple(round(v, 1) for v in self.placed[a])}')
            for hx, hy in HOLES:
                if ax0 < hx + HOLE_R and ax1 > hx - HOLE_R and ay0 < hy + HOLE_R and ay1 > hy - HOLE_R:
                    # exact test: distance from the hole centre to the rectangle
                    dx = max(ax0 - hx, 0, hx - ax1); dy = max(ay0 - hy, 0, hy - ay1)
                    if math.hypot(dx, dy) < HOLE_R:
                        bad.append(f'{a} too close to mounting hole ({hx},{hy})')
            for b_ in refs[i + 1:]:
                bx0, by0, bx1, by1 = self.placed[b_]
                if ax0 < bx1 - 0.05 and ax1 > bx0 + 0.05 and ay0 < by1 - 0.05 and ay1 > by0 + 0.05 and (a, b_) not in allow and (b_, a) not in allow:
                    bad.append(f'{a} overlaps {b_}')
            for k, (kx0, ky0, kx1, ky1) in enumerate(keepouts):
                if ax0 < kx1 and ax1 > kx0 and ay0 < ky1 and ay1 > ky0 and (a, k) not in allow:
                    bad.append(f'{a} inside keep-out {k}')
        return bad

    def save(self, path):
        self.b.to_file(path)

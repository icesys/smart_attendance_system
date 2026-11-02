#!/usr/bin/env python3
"""Builds pcb_top / pcb_middle / pcb_bottom .kicad_pcb: outline, M3 holes, footprints placed, nets assigned (ratsnest), NO tracks.
Fixed parts are placed by hand (connectors, ESP32 sockets, OLED ...); the others are placed by a greedy search
(no overlaps, away from the mounting holes, short connections). Run: python3 gen_pcb.py <sas_pcb dir>"""
import itertools, math, os, sys
sys.path.insert(0, os.path.dirname(__file__))
import pcblib as P

RAILS = {'GND', '3V3', '5V_SYS', '5V_BOOST'}
CX_J1, CX_J2, CY_J = 87.95, 75.95, 26.5          # cable connector positions shared by neighbouring boards

CFG = {
 'top': dict(
    title='TOP board 95 x 60 mm',
    fixed=[('J1', CX_J1, CY_J, 0), ('J2', 69.25, 19.75, 0), ('J3', 57.0, 41.0, 0)],
    keepouts=[(8, 22, 54, 57)], pull={'SW1': 3.0, 'SW2': 3.0},
    holes=['H1', 'H2', 'H3', 'H4']),
 'middle': dict(
    title='MIDDLE board 95 x 60 mm',
    fixed=[('J102', 37.17, 4.3, 90), ('J101', 37.17, 29.7, 90), ('J105', CX_J1, CY_J, 0), ('J106', CX_J2, CY_J, 0)],
    keepouts=[(9, 3, 66, 31), (0, 6, 8.6, 28)], pull={}, holes=['H101', 'H102', 'H103', 'H104']),
 'bottom': dict(
    title='BOTTOM board 95 x 60 mm',
    fixed=[], keepouts=[], pull={},
    edge={'J203': (2.6, (0, 90, 180, 270)), 'SW201': (6.0, (0, 90))},
    region={'J201': (3.0, 34.0, 40.0, 59.0)},   # the cable connector must sit where MIDDLE has room for its twin
    holes=['H201', 'H202', 'H203', 'H204']),
}


def greedy(pcb, cfg):
    cont = {}
    for net, pins in itertools.groupby(sorted(pcb.pad_net.items(), key=lambda kv: kv[1][1]), key=lambda kv: kv[1][1]):
        refs = sorted({k[0] for k, _ in pins})
        if net in RAILS or len(refs) > 6:
            continue
        for a, b in itertools.permutations(refs, 2):
            cont.setdefault(a, {}).setdefault(b, 0)
            cont[a][b] += 1
    auto = [r for r in pcb.comps if r not in pcb.placed and not r.startswith('H')]
    sizes = {}
    for r in auto:
        lib, name = pcb.comps[r]['fp'].split(':')
        fp = P.load_fp(lib, name, pcb.custom)
        x1, y1, x2, y2 = P.local_bbox(fp)
        sizes[r] = (x2 - x1, y2 - y1)
    auto.sort(key=lambda r: -sizes[r][0] * sizes[r][1])
    for r in auto:
        w0, h0 = sizes[r]
        best = None
        for rotd in (0, 90):
            w, h = (w0, h0) if rotd == 0 else (h0, w0)
            x = w / 2 + 0.8
            while x <= P.W - w / 2 - 0.8:
                y = h / 2 + 0.8
                while y <= P.H - h / 2 - 0.8:
                    box = (x - w / 2, y - h / 2, x + w / 2, y + h / 2)
                    ok = True
                    for hx, hy in P.HOLES:
                        dx = max(box[0] - hx, 0, hx - box[2]); dy = max(box[1] - hy, 0, hy - box[3])
                        if math.hypot(dx, dy) < P.HOLE_R + 0.3:
                            ok = False; break
                    if ok:
                        for kx0, ky0, kx1, ky1 in cfg['keepouts']:
                            if box[0] < kx1 and box[2] > kx0 and box[1] < ky1 and box[3] > ky0:
                                ok = False; break
                    if ok:
                        for q, (a0, b0, a1, b1) in pcb.placed.items():
                            if q.startswith('H'):
                                continue
                            if box[0] < a1 + 0.8 and box[2] > a0 - 0.8 and box[1] < b1 + 0.8 and box[3] > b0 - 0.8:
                                ok = False; break
                    if ok:
                        cost = 0.0
                        for q, wt in cont.get(r, {}).items():
                            if q in pcb.placed:
                                a0, b0, a1, b1 = pcb.placed[q]
                                cost += wt * (abs(x - (a0 + a1) / 2) + abs(y - (b0 + b1) / 2))
                        e = cfg['pull'].get(r, 0)
                        if e:
                            cost += e * min(x - w / 2, P.W - x - w / 2, y - h / 2, P.H - y - h / 2)
                        cost += 0.001 * (x + y)
                        if best is None or cost < best[0]:
                            best = (cost, x, y, rotd)
                    y += 1.0
                x += 1.0
        if best is None:
            raise SystemExit(f'no room for {r}')
        pcb.put(r, best[1], best[2], best[3])


def fit_first(pcb, cfg, tries=1500, seed=1):
    """Random-restart first-fit packing for a crowded board: returns True when every part found a place."""
    import random
    rnd = random.Random(seed)
    auto = [r for r in pcb.comps if r not in pcb.placed and not r.startswith('H')]
    sizes = {}
    for r in auto:
        lib, name = pcb.comps[r]['fp'].split(':')
        x1, y1, x2, y2 = P.local_bbox(P.load_fp(lib, name, pcb.custom))
        sizes[r] = (x2 - x1, y2 - y1)
    base_placed = dict(pcb.placed)
    for t in range(tries):
        pcb.placed = dict(base_placed)
        order = sorted(auto, key=lambda r: -sizes[r][0] * sizes[r][1] * rnd.uniform(0.5, 1.5))
        variant = rnd.randrange(4)
        ok_all, plan = True, []
        for r in order:
            w0, h0 = sizes[r]
            lim, rots = cfg.get('edge', {}).get(r, (None, (0, 90)))
            found = None
            xs = [0.8 + i for i in range(int(P.W))]
            ys = [0.8 + i for i in range(int(P.H))]
            pos = [(x, y) for x in xs for y in ys]
            pos.sort(key=lambda p: [(p[1], p[0]), (p[0], p[1]), (-p[1], p[0]), (-p[0], p[1])][variant])
            for rotd in rots:
                w, h = (w0, h0) if rotd in (0, 180) else (h0, w0)
                for cx0, cy0 in pos:
                    x, y = cx0 + w / 2, cy0 + h / 2
                    box = (x - w / 2, y - h / 2, x + w / 2, y + h / 2)
                    if box[2] > P.W - 0.8 or box[3] > P.H - 0.8:
                        continue
                    reg = cfg.get('region', {}).get(r)
                    if reg and (box[0] < reg[0] or box[1] < reg[1] or box[2] > reg[2] or box[3] > reg[3]):
                        continue
                    if r == 'J203':   # the USB-C end (top of the footprint) must point at the nearby edge
                        side = {0: box[1], 90: box[0], 180: P.H - box[3], 270: P.W - box[2]}[rotd]
                        if side > lim:
                            continue
                    elif lim is not None and min(box[0], P.W - box[2], box[1], P.H - box[3]) > lim:
                        continue
                    bad = False
                    for hx, hy in P.HOLES:
                        dx = max(box[0] - hx, 0, hx - box[2]); dy = max(box[1] - hy, 0, hy - box[3])
                        if math.hypot(dx, dy) < P.HOLE_R + 0.3:
                            bad = True; break
                    if not bad:
                        for q, (a0, b0, a1, b1) in pcb.placed.items():
                            if q.startswith('H'):
                                continue
                            if box[0] < a1 + 0.8 and box[2] > a0 - 0.8 and box[1] < b1 + 0.8 and box[3] > b0 - 0.8:
                                bad = True; break
                    if not bad:
                        found = (x, y, rotd); break
                if found:
                    break
            if not found:
                ok_all = False
                break
            pcb.placed[r] = (found[0] - 0, found[1] - 0, found[0], found[1])  # temporary marker, replaced below
            pcb.placed[r] = (found[0] - (w0 if found[2] in (0, 180) else h0) / 2, found[1] - (h0 if found[2] in (0, 180) else w0) / 2,
                             found[0] + (w0 if found[2] in (0, 180) else h0) / 2, found[1] + (h0 if found[2] in (0, 180) else w0) / 2)
            plan.append((r, found))
        if ok_all:
            pcb.placed = dict(base_placed)
            pcb.b.footprints = [f for f in pcb.b.footprints]
            for r, (x, y, rotd) in plan:
                pcb.put(r, x, y, rotd)
            return True
    pcb.placed = dict(base_placed)
    return False


def build(name, base, j106=None):
    cfg = CFG[name]
    d = os.path.join(base, f'pcb_{name}')
    pcb = P.PCB(cfg['title'], f'/tmp/pcb_{name}.xml', os.path.join(base, 'smart_attendance.pretty'))
    pcb.outline()
    for h, (hx, hy) in zip(cfg['holes'], P.HOLES):
        pcb.put(h, hx, hy, 0)
    for ref, cx, cy, r in cfg['fixed']:
        pcb.put(ref, cx, cy, r)
    if name == 'bottom':
        if not fit_first(pcb, cfg):
            raise SystemExit('bottom: no packing found')
    else:
        greedy(pcb, cfg)
    pcb.text(cfg['title'], 47.5, -2.5, 1.5)
    nfab = pcb.place_refs()
    if name == 'top':
        pcb.silk_rect(8, 22, 54, 57)
        pcb.text('RFID COIL 35 x 46 - NO COPPER', 31, 39.5, 1.2)
        pcb.keepout(8, 22, 54, 57, 'COIL_KEEPOUT')
    if name == 'middle':
        pcb.silk_rect(9, 3, 66, 31)
        pcb.text('ESP32-S3 (USB-C ports on the left edge)', 37.5, 17, 1.0)
    bad = pcb.check(cfg['keepouts'], allow={('J3', 0), ('J101', 0), ('J102', 0)})
    pcb.save(os.path.join(d, f'pcb_{name}.kicad_pcb'))
    print(f'== {name}: {len(pcb.placed)} footprints placed, {nfab} reference(s) moved to F.Fab,', 'OK, no overlaps' if not bad else bad)
    return pcb


if __name__ == '__main__':
    base = sys.argv[1]
    pb = build('bottom', base)
    x0, y0, x1, y1 = pb.placed['J201']
    CFG['middle']['fixed'][3] = ('J106', (x0 + x1) / 2, (y0 + y1) / 2, pb.rots['J201'])
    print('J_MB connector position taken from BOTTOM:', round((x0 + x1) / 2, 2), round((y0 + y1) / 2, 2))
    build('middle', base)
    build('top', base)

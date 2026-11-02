#!/usr/bin/env python3
"""Routes a placed board (2 layers, through-hole parts): orthogonal tracks on a 0.25 mm grid with vias, wide tracks for
power nets, GND by copper pours on both layers. Then checks the result with an independent geometry test.
Run: python3 route_pcb.py <pcb_xxx.kicad_pcb>"""
import heapq, math, sys, uuid, itertools, os
import numpy as np
from scipy import ndimage
from shapely.geometry import Point, LineString, box
from shapely.strtree import STRtree
sys.path.insert(0, os.path.dirname(__file__))
import pcblib as P
import check_pcb as C
from kiutils.board import Board
from kiutils.items.brditems import Segment, Via
from kiutils.items.common import Position
from kiutils.items.zones import Zone, ZonePolygon, Hatch, FillSettings

G, CLEAR, W_SIG = 0.25, 0.3, 0.3
VIA_D, VIA_DRILL = 0.8, 0.4
SLACK = 0.15                       # half of the thinnest track: obstacles are grown by CLEAR + SLACK
WIDTH = {'GND': 0.4, 'BAT+': 1.0, 'BAT-': 1.0, 'CHG_OUT+': 1.0, 'SW_OUT': 1.0, '5V_BOOST': 0.8, '5V_SYS': 0.6, '3V3': 0.5}
NX, NY = int(P.W / G) + 1, int(P.H / G) + 1
LAY = ['F.Cu', 'B.Cu']


def disk(r):
    k = np.arange(-r, r + 1)
    return (k[:, None] ** 2 + k[None, :] ** 2) <= r * r + 0.5


class Router:
    def __init__(self, bd, keepouts):
        self.bd = bd
        self.own = np.zeros((2, NX, NY), np.int32)
        self.pads = []
        self.viaban = np.zeros((NX, NY), bool)
        for fp in bd.footprints:
            ref = [t.text for t in fp.graphicItems if t.__class__.__name__ == 'FpText' and t.type == 'reference'][0]
            th = fp.position.angle or 0
            for p in fp.pads:
                if not p.number or p.net is None or p.net.number == 0:
                    continue
                dx, dy = P.rot(p.position.X, p.position.Y, th)
                sx, sy = p.size.X, p.size.Y
                if round(p.position.angle or 0) % 180 == 90:
                    sx, sy = sy, sx
                self.pads.append(dict(ref=ref, num=p.number, net=p.net.number, name=p.net.name, drill=((p.drill.diameter if p.drill else 0) or 0),
                                      x=fp.position.X + dx - P.OX, y=fp.position.Y + dy - P.OY, hx=sx / 2, hy=sy / 2,
                                      circle=(p.shape == 'circle')))
        for pd in self.pads:
            d = CLEAR + SLACK
            for l in (0, 1):
                self.claim_rect(l, pd['x'] - pd['hx'] - d, pd['y'] - pd['hy'] - d, pd['x'] + pd['hx'] + d, pd['y'] + pd['hy'] + d, pd['net'],
                                circle=(pd['x'], pd['y'], pd['hx'] + d) if pd['circle'] else None)
        for pd in self.pads:          # no via closer than 0.25 mm (hole to hole) to a pad hole
            self.ban(pd['x'], pd['y'], pd['drill'] / 2 + VIA_DRILL / 2 + 0.25 + 0.1)
        # fixed obstacles (only where nothing else claimed the cell)
        m = math.ceil(1.1 / G)
        for l in (0, 1):
            o = self.own[l]
            for sl in (o[:m, :], o[-m:, :], o[:, :m], o[:, -m:]):
                sl[sl == 0] = -1
            for hx, hy in P.HOLES:
                self.block_disk(l, hx, hy, 3.3)
            for kx0, ky0, kx1, ky1 in keepouts:
                self.block_rect(l, kx0, ky0, kx1, ky1)

    def ban(self, cx, cy, r):
        ix0, ix1, iy0, iy1 = self._slice(cx - r, cy - r, cx + r, cy + r)
        gx = (np.arange(ix0, ix1 + 1) * G - cx)[:, None]; gy = (np.arange(iy0, iy1 + 1) * G - cy)[None, :]
        self.viaban[ix0:ix1 + 1, iy0:iy1 + 1] |= (gx ** 2 + gy ** 2) <= r * r

    def _slice(self, x0, y0, x1, y1):
        ix0, ix1 = max(0, math.ceil(x0 / G - 1e-9)), min(NX - 1, math.floor(x1 / G + 1e-9))
        iy0, iy1 = max(0, math.ceil(y0 / G - 1e-9)), min(NY - 1, math.floor(y1 / G + 1e-9))
        return ix0, ix1, iy0, iy1

    def claim_rect(self, l, x0, y0, x1, y1, net, circle=None):
        ix0, ix1, iy0, iy1 = self._slice(x0, y0, x1, y1)
        if ix1 < ix0 or iy1 < iy0:
            return
        sub = self.own[l][ix0:ix1 + 1, iy0:iy1 + 1]
        m = np.ones(sub.shape, bool)
        if circle:
            cx, cy, r = circle
            gx = (np.arange(ix0, ix1 + 1) * G - cx)[:, None]; gy = (np.arange(iy0, iy1 + 1) * G - cy)[None, :]
            m = gx ** 2 + gy ** 2 <= r * r
        conf = m & (sub > 0) & (sub != net)
        free = m & (sub == 0)
        sub[conf] = -2
        sub[free] = net

    def block_rect(self, l, x0, y0, x1, y1):
        ix0, ix1, iy0, iy1 = self._slice(x0, y0, x1, y1)
        sub = self.own[l][ix0:ix1 + 1, iy0:iy1 + 1]
        sub[sub == 0] = -1

    def block_disk(self, l, cx, cy, r):
        ix0, ix1, iy0, iy1 = self._slice(cx - r, cy - r, cx + r, cy + r)
        sub = self.own[l][ix0:ix1 + 1, iy0:iy1 + 1]
        gx = (np.arange(ix0, ix1 + 1) * G - cx)[:, None]; gy = (np.arange(iy0, iy1 + 1) * G - cy)[None, :]
        sub[((gx ** 2 + gy ** 2) <= r * r) & (sub == 0)] = -1

    def stamp_disk(self, l, cx, cy, r, net):
        self.claim_rect(l, cx - r, cy - r, cx + r, cy + r, net, circle=(cx, cy, r))

    # ------------------------------------------------------------------------------------------------ search
    def search(self, net, w, starts, goals, hint):
        extra = max(0, math.ceil(((w - W_SIG) / 2) / G - 1e-9))
        vextra = max(0, math.ceil(((VIA_D - W_SIG) / 2) / G - 1e-9))
        base = [(self.own[l] != 0) & (self.own[l] != net) for l in (0, 1)]
        fw = [ndimage.binary_dilation(b, structure=disk(extra)) if extra else b for b in base]
        fv = [ndimage.binary_dilation(b, structure=disk(vextra)) for b in base]
        goalset = set(goals)
        hx, hy = hint
        ctr = itertools.count()
        heap, best, parent = [], {}, {}
        for (ix, iy) in starts:
            for l in (0, 1):
                heapq.heappush(heap, (abs(ix - hx) + abs(iy - hy), next(ctr), (0 if l == 0 else 2), (l, ix, iy, 4), None))
        n = 0
        dirs = ((1, 0), (-1, 0), (0, 1), (0, -1))
        while heap and n < 700000:
            f, _, cost, st, par = heapq.heappop(heap)
            if st in best:
                continue
            best[st] = cost; parent[st] = par; n += 1
            l, ix, iy, d = st
            if (l, ix, iy) in goalset:
                path, key = [], st
                while key is not None:
                    path.append(key[:3]); key = parent[key]
                return path[::-1]
            for k, (dx, dy) in enumerate(dirs):
                if d != 4 and (dirs[d][0] == -dx and dirs[d][1] == -dy):
                    continue
                jx, jy = ix + dx, iy + dy
                if not (0 <= jx < NX and 0 <= jy < NY) or fw[l][jx, jy]:
                    continue
                c = cost + (1.0 if l == 0 else 1.3) + (1.5 if (d != 4 and d != k) else 0)
                ns = (l, jx, jy, k)
                if ns not in best:
                    heapq.heappush(heap, (c + abs(jx - hx) + abs(jy - hy), next(ctr), c, ns, st))
            o = 1 - l
            if not fv[0][ix, iy] and not fv[1][ix, iy] and not self.viaban[ix, iy]:
                ns = (o, ix, iy, 4)
                if ns not in best:
                    c = cost + 14
                    heapq.heappush(heap, (c + abs(ix - hx) + abs(iy - hy), next(ctr), c, ns, st))
        return None

    def route_net(self, name, num, pads):
        w = WIDTH.get(name.lstrip('/'), W_SIG)
        cell = lambda p: (round(p['x'] / G), round(p['y'] / G))
        tree = {(l,) + cell(pads[0]) for l in (0, 1)}
        done, todo = [pads[0]], list(pads[1:])
        segs, vias = [], []
        fail = []
        while todo:
            def dist(p):
                c = cell(p); return min(abs(c[0] - t[1]) + abs(c[1] - t[2]) for t in tree)
            p = min(todo, key=dist); todo.remove(p)
            c = cell(p)
            hint = min(tree, key=lambda t: abs(c[0] - t[1]) + abs(c[1] - t[2]))[1:]
            path = self.search(num, w, [c], tree, hint)
            if path is None:
                fail.append(f"{p['ref']}.{p['num']}")
                continue
            self.commit(num, w, path, p, segs, vias, tree)
            done.append(p)
        return segs, vias, fail

    def commit(self, num, w, path, pad, segs, vias, tree):
        r = w / 2 + CLEAR + SLACK
        for (l, ix, iy) in path:
            self.stamp_disk(l, ix * G, iy * G, r, num)
            tree.add((l, ix, iy))
        # polyline pieces per layer
        cur = [path[0]]
        pieces = []
        for a, b in zip(path, path[1:]):
            if a[0] != b[0]:
                pieces.append(cur); cur = [b]
                vias.append((a[1] * G, a[2] * G))
                self.ban(a[1] * G, a[2] * G, VIA_DRILL + 0.25 + 0.3)
                for l in (0, 1):
                    self.stamp_disk(l, a[1] * G, a[2] * G, VIA_D / 2 + CLEAR + SLACK, num)
            else:
                cur.append(b)
        pieces.append(cur)
        for pc in pieces:
            pts = [(c[1] * G, c[2] * G) for c in pc]
            if pc[0][1:] == (round(pad['x'] / G), round(pad['y'] / G)) and pc is pieces[0]:
                pts[0] = (pad['x'], pad['y'])
            # merge collinear points
            out = [pts[0]]
            for i in range(1, len(pts) - 1):
                a, b, c = out[-1], pts[i], pts[i + 1]
                if (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0]) != 0 or True and abs((b[0]-a[0])*(c[1]-b[1])-(b[1]-a[1])*(c[0]-b[0])) > 1e-9:
                    out.append(b)
            out.append(pts[-1])
            for a, b in zip(out, out[1:]):
                if abs(a[0] - b[0]) > 1e-9 or abs(a[1] - b[1]) > 1e-9:
                    segs.append((a, b, pc[0][0]))
        return


def add_tracks(bd, num, w, segs, vias):
    for a, b, l in segs:
        bd.traceItems.append(Segment(start=Position(round(P.OX + a[0], 4), round(P.OY + a[1], 4)),
                                     end=Position(round(P.OX + b[0], 4), round(P.OY + b[1], 4)),
                                     width=w, layer=LAY[l], net=num, tstamp=str(uuid.uuid4())))
    for x, y in vias:
        bd.traceItems.append(Via(position=Position(round(P.OX + x, 4), round(P.OY + y, 4)), size=VIA_D, drill=VIA_DRILL,
                                 layers=['F.Cu', 'B.Cu'], net=num, tstamp=str(uuid.uuid4())))


def add_gnd_pours(bd, gnd):
    ins = 0.4
    poly = [Position(P.OX + a, P.OY + b) for a, b in ((ins, ins), (P.W - ins, ins), (P.W - ins, P.H - ins), (ins, P.H - ins))]
    for layer in LAY:
        bd.zones.append(Zone(net=gnd[0], netName=gnd[1], layers=[layer], tstamp=str(uuid.uuid4()), hatch=Hatch(style='edge', pitch=0.5),
                             connectPads='yes', clearance=CLEAR, minThickness=0.25,
                             fillSettings=FillSettings(yes=True, thermalGap=0.4, thermalBridgeWidth=0.5),
                             polygons=[ZonePolygon(coordinates=poly)]))


def verify(bd, routed_pads):
    """Independent geometry check: clearance between different nets, connectivity of every routed net, edge margin."""
    geoms = []   # (geometry, net, layer)
    for fp in bd.footprints:
        th = fp.position.angle or 0
        for p in fp.pads:
            if not p.number or p.net is None or p.net.number == 0:
                continue
            dx, dy = P.rot(p.position.X, p.position.Y, th)
            x, y = fp.position.X + dx, fp.position.Y + dy
            sx, sy = p.size.X, p.size.Y
            if round(p.position.angle or 0) % 180 == 90:
                sx, sy = sy, sx
            g = Point(x, y).buffer(sx / 2) if p.shape == 'circle' else box(x - sx / 2, y - sy / 2, x + sx / 2, y + sy / 2)
            for l in (0, 1):
                geoms.append((g, p.net.number, l, ('pad', fp, p.number)))
    for t in bd.traceItems:
        if isinstance(t, Segment):
            geoms.append((LineString([(t.start.X, t.start.Y), (t.end.X, t.end.Y)]).buffer(t.width / 2), t.net, LAY.index(t.layer), ('trk',)))
        else:
            for l in (0, 1):
                geoms.append((Point(t.position.X, t.position.Y).buffer(t.size / 2), t.net, l, ('via',)))
    bad = []
    for l in (0, 1):
        items = [g for g in geoms if g[2] == l]
        tree = STRtree([g[0] for g in items])
        for i, (g, n, _, _) in enumerate(items):
            for j in tree.query(g.buffer(CLEAR)):
                if j <= i:
                    continue
                g2, n2 = items[j][0], items[j][1]
                if n2 != n and g.distance(g2) < 0.2:
                    bad.append(f'clearance {LAY[l]}: net {n} vs {n2} = {g.distance(g2):.3f} mm')
    # connectivity
    nets = {}
    for g, n, l, meta in geoms:
        nets.setdefault(n, []).append((g, l, meta))
    unconnected = []
    for n, items in nets.items():
        if n not in routed_pads:
            continue
        parent = list(range(len(items)))
        def find(a):
            while parent[a] != a:
                parent[a] = parent[parent[a]]; a = parent[a]
            return a
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                gi, li, mi = items[i]; gj, lj, mj = items[j]
                if (li == lj and gi.intersects(gj)) or (mi[0] == 'via' and mj[0] == 'via' and gi.intersects(gj)) or \
                   (li != lj and gi.intersects(gj) and (mi[0] in ('via',) or mj[0] in ('via',) or (mi[0] == 'pad' and mj[0] == 'pad' and mi[2] == mj[2] and mi[1] is mj[1]))):
                    parent[find(i)] = find(j)
        pads = [i for i, it in enumerate(items) if it[2][0] == 'pad']
        if len({find(i) for i in pads}) > 1:
            unconnected.append(n)
    return bad, unconnected


def run_once(path, keepouts, prio):
    bd = Board.from_file(path)
    R = Router(bd, keepouts)
    byname = {}
    for p in R.pads:
        byname.setdefault((p['net'], p['name']), []).append(p)
    gnd = [k for k in byname if k[1].lstrip('/') == 'GND']
    order = sorted([k for k in byname if len(byname[k]) > 1 and not k[1].startswith('unconnected')],
                   key=lambda k: (k not in prio, k[1].lstrip('/') == 'GND', k[1].lstrip('/') not in WIDTH, len(byname[k]), k[1]))
    routed, failed = set(), []
    for key in order:
        num, name = key
        segs, vias, fail = R.route_net(name, num, byname[key])
        add_tracks(bd, num, WIDTH.get(name.lstrip('/'), W_SIG), segs, vias)
        if fail:
            failed.append((key, fail))
        routed.add(num)
    if gnd:
        gnum = gnd[0][0]
        for _ in range(12):      # stitch separate pour areas together with GND tracks
            systems, isolated = C.gnd_systems(bd, keepouts, gnum)
            groups = [s for s in systems] + [[p] for p in isolated]
            if len(groups) <= 1:
                break
            groups.sort(key=len)
            small = groups[0]
            rest = [p for g in groups[1:] for p in g]
            a, b = min(((p, q) for p in small for q in rest), key=lambda pq: math.dist(pq[0], pq[1]))
            cell = lambda q: (round((q[0] - P.OX) / G), round((q[1] - P.OY) / G))
            goals = {(l,) + cell(b) for l in (0, 1)}
            ca = cell(a)
            path = R.search(gnum, 0.5, [ca], goals, cell(b))
            if path is None:
                failed.append((gnd[0], [f'GND island at {a}']))
                break
            segs, vias = [], []
            padd = dict(x=a[0] - P.OX, y=a[1] - P.OY)
            R.commit(gnum, 0.5, path, padd, segs, vias, set())
            add_tracks(bd, gnum, 0.5, segs, vias)
        add_gnd_pours(bd, gnd[0])
    bad, unconn = verify(bd, routed)
    return bd, order, failed, bad, unconn


def main(path, keepouts, attempts=6):
    prio, best = set(), None
    for k in range(attempts):
        bd, order, failed, bad, unconn = run_once(path, keepouts, prio)
        score = (len(failed) + len(unconn) + len(bad), len(failed))
        print(f'  attempt {k + 1}: unrouted pins {sum(len(f) for _, f in failed)}, clearance problems {len(bad)}, unconnected nets {len(unconn)}', flush=True)
        if best is None or score < best[0]:
            best = (score, bd, order, failed, bad, unconn)
        if score[0] == 0:
            break
        prio |= {key for key, _ in failed}
        if not failed:
            break
    score, bd, order, failed, bad, unconn = best
    ntr = sum(1 for t in bd.traceItems if isinstance(t, Segment)); nv = sum(1 for t in bd.traceItems if isinstance(t, Via))
    length = sum(math.hypot(t.end.X - t.start.X, t.end.Y - t.start.Y) for t in bd.traceItems if isinstance(t, Segment))
    bd.to_file(path)
    print(f'{os.path.basename(path)}: nets to route {len(order)}, routed fully {len(order) - len(failed)}, segments {ntr}, vias {nv}, copper {length:.0f} mm')
    print('   not fully routed:', [(k[1], f) for k, f in failed] or 'none')
    print('   clearance violations below 0.2 mm (my own check):', len(bad), bad[:4])
    print('   nets whose pads are not connected by copper (my own check):', unconn or 'none')
    return failed, bad, unconn


if __name__ == '__main__':
    ko = {'pcb_top.kicad_pcb': [(8, 22, 54, 57)]}.get(os.path.basename(sys.argv[1]), [])
    main(sys.argv[1], ko)

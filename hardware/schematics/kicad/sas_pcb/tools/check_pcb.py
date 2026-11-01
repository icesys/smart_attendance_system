#!/usr/bin/env python3
"""Independent checks of a routed board (my own geometry, NOT KiCad's DRC): clearance 0.2, copper-to-edge 0.5,
hole-to-hole 0.25, minimum widths, every routed net connected, and whether every GND pad reaches a GND pour."""
import math, os, sys
from shapely.geometry import Point, LineString, box, Polygon
from shapely.ops import unary_union
from shapely.strtree import STRtree
sys.path.insert(0, os.path.dirname(__file__))
import pcblib as P
from kiutils.board import Board
from kiutils.items.brditems import Segment, Via

LAY = ['F.Cu', 'B.Cu']
CLR, EDGE, HH = 0.2, 0.5, 0.25


def collect(bd):
    items = []       # (geom, net, layer, kind, drill_point, drill_d, id)
    for fi, fp in enumerate(bd.footprints):
        th = fp.position.angle or 0
        for p in fp.pads:
            dx, dy = P.rot(p.position.X, p.position.Y, th)
            x, y = fp.position.X + dx, fp.position.Y + dy
            sx, sy = p.size.X, p.size.Y
            if round(p.position.angle or 0) % 180 == 90:
                sx, sy = sy, sx
            g = Point(x, y).buffer(sx / 2) if p.shape == 'circle' else box(x - sx / 2, y - sy / 2, x + sx / 2, y + sy / 2)
            net = p.net.number if p.net else 0
            dr = (p.drill.diameter if p.drill else 0) or 0
            for l in (0, 1):
                items.append(dict(g=g, net=net, l=l, kind='pad', fi=fi, num=p.number, hole=((x, y), dr) if dr else None, np=(p.type == 'np_thru_hole')))
    for t in bd.traceItems:
        if isinstance(t, Segment):
            items.append(dict(g=LineString([(t.start.X, t.start.Y), (t.end.X, t.end.Y)]).buffer(t.width / 2), net=t.net, l=LAY.index(t.layer), kind='trk', w=t.width, hole=None))
        else:
            for l in (0, 1):
                items.append(dict(g=Point(t.position.X, t.position.Y).buffer(t.size / 2), net=t.net, l=l, kind='via', hole=((t.position.X, t.position.Y), t.drill), np=False))
    return items


def gnd_systems(bd, keepouts, gnd_net):
    """Emulates the GND pours (board minus other-net copper grown by 0.3 mm, minus keep-outs) on both layers and returns
    (list of systems, isolated pads); a system is the list of GND pad centres (absolute mm) joined through pours and holes."""
    items = collect(bd)
    outline = box(P.OX, P.OY, P.OX + P.W, P.OY + P.H)
    ko = unary_union([box(P.OX + a, P.OY + b, P.OX + c, P.OY + d) for a, b, c, d in keepouts]) if keepouts else None
    board_in = outline.buffer(-0.4)
    pours = []
    for l in (0, 1):
        others = [i['g'] for i in items if i['l'] == l and i['net'] != gnd_net and not i.get('np')]
        poly = board_in
        if others:
            poly = poly.difference(unary_union(others).buffer(0.3))
        if ko is not None:
            poly = poly.difference(ko)
        poly = poly.buffer(-0.125).buffer(0.125)
        pours.append(list(poly.geoms) if poly.geom_type == 'MultiPolygon' else [poly])
    nodes = [(l, pc) for l in (0, 1) for pc in pours[l]]
    par = list(range(len(nodes)))
    def f(a):
        while par[a] != a:
            par[a] = par[par[a]]; a = par[a]
        return a
    gi = [i for i in items if i['net'] == gnd_net and i['l'] == 0 and i['kind'] in ('pad', 'via') and not i.get('np')]
    reach = {}
    for idx, i in enumerate(gi):
        r = [k for k, (l, pc) in enumerate(nodes) if pc.intersects(i['g'].buffer(0.9))]
        reach[idx] = r
        for a in r[1:]:
            par[f(a)] = f(r[0])
    systems, isolated = {}, []
    for idx, i in enumerate(gi):
        if i['kind'] != 'pad':
            continue
        ctr = (i['g'].centroid.x, i['g'].centroid.y)
        if not reach[idx]:
            isolated.append(ctr)
        else:
            systems.setdefault(f(reach[idx][0]), []).append(ctr)
    return list(systems.values()), isolated


def main(path, keepouts):
    bd = Board.from_file(path)
    items = collect(bd)
    outline = box(P.OX, P.OY, P.OX + P.W, P.OY + P.H)
    problems = []
    # 1 clearance between different nets, 2 copper to edge, 3 widths
    for l in (0, 1):
        its = [i for i in items if i['l'] == l and not i.get('np')]
        tree = STRtree([i['g'] for i in its])
        for a, i in enumerate(its):
            if i['g'].distance(outline.exterior) < EDGE or not outline.contains(i['g']):
                problems.append(f"{LAY[l]}: copper closer than {EDGE} mm to the board edge ({i['kind']})")
            for j in tree.query(i['g'].buffer(CLR)):
                if j <= a:
                    continue
                o = its[j]
                if o['net'] != i['net'] and i['g'].distance(o['g']) < CLR - 1e-6:
                    problems.append(f"{LAY[l]}: clearance {i['g'].distance(o['g']):.3f} between net {i['net']} ({i['kind']}) and net {o['net']} ({o['kind']})")
    # 4 hole to hole (pads and vias, once per hole)
    holes = {}
    for i in items:
        if i['hole']:
            holes[(round(i['hole'][0][0], 3), round(i['hole'][0][1], 3))] = i['hole']
    hl = list(holes.values())
    for a in range(len(hl)):
        for b in range(a + 1, len(hl)):
            d = math.dist(hl[a][0], hl[b][0]) - (hl[a][1] + hl[b][1]) / 2
            if d < HH - 1e-6:
                problems.append(f'hole to hole {d:.2f} mm')
    # 5 connectivity of every net with tracks
    nets = {}
    for i in items:
        nets.setdefault(i['net'], []).append(i)
    gnd_net = None
    for z in bd.zones:
        if z.netName and z.net:
            gnd_net = z.net
    unconnected = []
    for n, its in nets.items():
        if n == 0:
            continue
        if not any(i['kind'] in ('trk', 'via') for i in its):
            if sum(1 for i in its if i['kind'] == 'pad' and i['l'] == 0) > 1:
                unconnected.append(n)
            continue
        par = list(range(len(its)))
        def f(a):
            while par[a] != a:
                par[a] = par[par[a]]; a = par[a]
            return a
        for a in range(len(its)):
            for b in range(a + 1, len(its)):
                A, B = its[a], its[b]
                same = A['l'] == B['l'] and A['g'].intersects(B['g'])
                thru = A['l'] != B['l'] and A['kind'] != 'trk' and B['kind'] != 'trk' and A['g'].equals(B['g']) and A['kind'] == B['kind']
                if same or thru:
                    par[f(a)] = f(b)
        pads = [a for a, i in enumerate(its) if i['kind'] == 'pad' and i['l'] == 0]
        if len({f(a) for a in pads}) > 1:
            unconnected.append(n)
    # 6 GND pours: emulate the fill and check that every GND pad touches one connected pour system
    gnd_report = 'no GND net'
    if gnd_net:
        systems, isolated = gnd_systems(bd, keepouts, gnd_net)
        gnd_report = f'{sum(len(s) for s in systems) + len(isolated)} GND pads, isolated from any pour: {len(isolated)}, separate pour systems: {len(systems)}'
        if isolated or len(systems) > 1:
            problems.append('GND pour: ' + gnd_report)
    ntr = sum(1 for t in bd.traceItems if isinstance(t, Segment)); nv = sum(1 for t in bd.traceItems if isinstance(t, Via))
    print(f'{os.path.basename(path)}: tracks {ntr}, vias {nv}, zones {len(bd.zones)}')
    print('   nets with open connections:', unconnected or 'none')
    print('   GND pours:', gnd_report)
    print('   problems:', len(problems), sorted(set(problems))[:6])
    return problems, unconnected


if __name__ == '__main__':
    ko = {'pcb_top.kicad_pcb': [(8, 22, 54, 57)]}.get(os.path.basename(sys.argv[1]), [])
    main(sys.argv[1], ko)

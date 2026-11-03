#!/usr/bin/env python3
"""Independent check of sas_full_system.kicad_sch: rebuilds the connectivity from the saved file (pins, wires,
junctions, labels) and compares it with tools/expected_nets.json. Optionally also with a pad->net json of the PCBs.
Run:  python3 check_full_schematic.py [pcb_nets.json]
"""
import json, math, os, sys
from collections import defaultdict
from kiutils.schematic import Schematic

HERE = os.path.dirname(os.path.abspath(__file__))
sch = Schematic.from_file(os.path.join(os.path.dirname(HERE), 'sas_full_system.kicad_sch'))
R = lambda v: round(v, 2)
P = lambda x, y: (R(x), R(y))

parent = {}
def find(a):
    parent.setdefault(a, a)
    while parent[a] != a:
        parent[a] = parent[parent[a]]
        a = parent[a]
    return a
def union(a, b):
    parent[find(a)] = find(b)

lib = {f'{s.libraryNickname}:{s.entryName}': s for s in sch.libSymbols}
pins = {}          # point -> list of 'REF.pin'
problems = []
for s in sch.schematicSymbols:
    ref = next(p.value for p in s.properties if p.key == 'Reference')
    x, y, rot = s.position.X, s.position.Y, s.position.angle or 0
    if s.mirror:
        problems.append(f'{ref} is mirrored (not handled by this checker)')
    for u in lib[f'{s.libraryNickname}:{s.entryName}'].units:
        if u.unitId not in (0, s.unit) or u.styleId not in (0, 1):
            continue
        for p in u.pins:
            r = math.radians(rot)
            ex = x + p.position.X * math.cos(r) - p.position.Y * math.sin(r)
            ey = y - (p.position.X * math.sin(r) + p.position.Y * math.cos(r))
            pins.setdefault(P(ex, ey), []).append(f'{ref}.{p.number}')

wires = [(P(w.points[0].X, w.points[0].Y), P(w.points[1].X, w.points[1].Y)) for w in sch.graphicalItems if w.type == 'wire']
ends = defaultdict(int)
for a, b in wires:
    union(a, b)
    ends[a] += 1
    ends[b] += 1

def interior(pt, a, b):
    return ((a[0] == b[0] == pt[0] and min(a[1], b[1]) < pt[1] < max(a[1], b[1])) or
            (a[1] == b[1] == pt[1] and min(a[0], b[0]) < pt[0] < max(a[0], b[0])))

for a, b in wires:
    if a[0] != b[0] and a[1] != b[1]:
        problems.append(f'diagonal wire {a} {b}')
    for pt in list(ends) + list(pins):
        if interior(pt, a, b):
            problems.append(f'wire end or pin {pt} {pins.get(pt, "")} touches the middle of wire {a}-{b}')
juncs = [P(j.position.X, j.position.Y) for j in sch.junctions]
for j in juncs:
    if ends[j] + (j in pins) < 3:
        problems.append(f'junction at {j} joins fewer than 3 items')
    for a, b in wires:
        if interior(j, a, b):
            problems.append(f'junction {j} in the middle of a wire')
for pt in pins:
    find(pt)
by_label = defaultdict(list)
for l in sch.labels:
    pt = P(l.position.X, l.position.Y)
    if pt not in pins and pt not in ends:
        problems.append(f'label {l.text} at {pt} is not on a pin or wire end')
    by_label[l.text].append(pt)
for name, pts in by_label.items():
    for pt in pts[1:]:
        union(pt, pts[0])
nc_pts = {P(n.position.X, n.position.Y) for n in sch.noConnects}
pin_on_nothing = [pins[pt] for pt in pins if pt not in ends and pt not in nc_pts and
                  not any(P(l.position.X, l.position.Y) == pt for l in sch.labels)]
nets = defaultdict(set)
for pt, lst in pins.items():
    if pt in nc_pts:
        continue
    for pr in lst:
        nets[find(pt)].add(pr)
got = {frozenset(v) for v in nets.values() if not all(x.startswith('H') for x in v)}

exp = json.load(open(os.path.join(HERE, 'expected_nets.json')))
want = {frozenset(v) for v in exp.values()}
print(f'{len(sch.schematicSymbols)} symbol units, {len(wires)} wires, {len(juncs)} junctions, {len(sch.labels)} labels, '
      f'{len(nc_pts)} no-connect flags')
print('nets found:', len(got), ' expected:', len(want))
for s_ in want - got:
    print('MISSING/BROKEN net:', sorted(s_))
for s_ in got - want:
    print('UNEXPECTED net:', sorted(s_))
for p_ in pin_on_nothing:
    if not all(x.startswith('H') for x in p_):
        print('pin with no wire, label or no-connect:', p_)
for p_ in problems:
    print('PROBLEM:', p_)
if len(sys.argv) > 1:   # pad->net of the three PCBs (one name space; cables merge same-named nets)
    pcb = json.load(open(sys.argv[1]))
    pw = {frozenset(v) for k, v in pcb.items() if not k.startswith('unconnected')}
    print('PCB nets equal to schematic nets:', pw == got)
    for s_ in pw ^ got:
        print('  differs:', sorted(s_))
ok = want == got and not problems
print('RESULT:', 'OK' if ok else 'ERRORS')
sys.exit(0 if ok else 1)

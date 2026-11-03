#!/usr/bin/env python3
"""Draws the report figures that come from the KiCad files (no KiCad install needed, only kiutils + matplotlib):
  figures/schema_circuit_complet.png      the whole system as one circuit (sas_complete)
  figures/schema_electrique_complet.png   the three-board version with the cables (sas_full_system)
  figures/schema_<board>.png              one crop per board (annex)
  figures/pcb_<board>.png                 the routed layout of each board
Run:  python3 fig_kicad.py
"""
import math, os, sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle, FancyBboxPatch, Polygon
from kiutils.schematic import Schematic
from kiutils.utils.sexpr import parse_sexp

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
OUT = os.path.join(HERE, '..', 'figures')
KICAD = os.path.join(ROOT, 'hardware', 'schematics', 'kicad')
MM = 72 / 25.4            # points per millimetre when 1 figure millimetre = 1 sheet millimetre
SYM, WIRE, TXT, LBL = '#8B1A1A', '#1E7B34', '#24476B', '#111111'


def tf(px, py, x, y, rot):
    r = math.radians(rot)
    return (x + px * math.cos(r) - py * math.sin(r), y - (px * math.sin(r) + py * math.cos(r)))


def arc_pts(s, m, e, n=24):
    (x1, y1), (x2, y2), (x3, y3) = s, m, e
    d = 2 * (x1 * (y2 - y3) + x2 * (y3 - y1) + x3 * (y1 - y2))
    if abs(d) < 1e-9:
        return [s, e]
    ux = ((x1 ** 2 + y1 ** 2) * (y2 - y3) + (x2 ** 2 + y2 ** 2) * (y3 - y1) + (x3 ** 2 + y3 ** 2) * (y1 - y2)) / d
    uy = ((x1 ** 2 + y1 ** 2) * (x3 - x2) + (x2 ** 2 + y2 ** 2) * (x1 - x3) + (x3 ** 2 + y3 ** 2) * (x2 - x1)) / d
    a1, a2, a3 = (math.atan2(p[1] - uy, p[0] - ux) for p in (s, m, e))
    r = math.hypot(x1 - ux, y1 - uy)
    def norm(a):
        return a % (2 * math.pi)
    ccw = norm(a2 - a1) < norm(a3 - a1)
    span = norm(a3 - a1) if ccw else -norm(a1 - a3)
    return [(ux + r * math.cos(a1 + span * i / n), uy + r * math.sin(a1 + span * i / n)) for i in range(n + 1)]


def render_schematic(path, outfile, crop=None, dpi=200):
    sch = Schematic.from_file(path)
    x0, y0, x1, y1 = crop or (8, 8, 833, 552)
    fig = plt.figure(figsize=((x1 - x0) / 25.4, (y1 - y0) / 25.4))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(x0, x1)
    ax.set_ylim(y1, y0)
    ax.axis('off')
    fs = lambda h: h * MM / 0.72 * 0.8
    lib = {f'{s.libraryNickname}:{s.entryName}': s for s in sch.libSymbols}
    for s in sch.schematicSymbols:
        x, y, rot = s.position.X, s.position.Y, s.position.angle or 0
        ls = lib[f'{s.libraryNickname}:{s.entryName}']
        for u in ls.units:
            if u.unitId not in (0, s.unit) or u.styleId not in (0, 1):
                continue
            for g in u.graphicItems:
                k = type(g).__name__
                fill = getattr(getattr(g, 'fill', None), 'type', 'none')
                if k == 'SyRect':
                    pts = [(g.start.X, g.start.Y), (g.end.X, g.start.Y), (g.end.X, g.end.Y), (g.start.X, g.end.Y), (g.start.X, g.start.Y)]
                elif k == 'SyPolyLine':
                    pts = [(q.X, q.Y) for q in g.points]
                elif k == 'SyCircle':
                    pts = [(g.center.X + g.radius * math.cos(t * math.pi / 24), g.center.Y + g.radius * math.sin(t * math.pi / 24)) for t in range(49)]
                elif k == 'SyArc':
                    pts = arc_pts((g.start.X, g.start.Y), (g.mid.X, g.mid.Y), (g.end.X, g.end.Y))
                else:
                    continue
                q = [tf(a, b, x, y, rot) for a, b in pts]
                if fill == 'background':
                    ax.add_patch(Polygon(q, closed=True, fc='#FFFDE8', ec='none', zorder=1))
                elif fill == 'outline':
                    ax.add_patch(Polygon(q, closed=True, fc=SYM, ec='none', zorder=2))
                ax.plot([p[0] for p in q], [p[1] for p in q], color=SYM, lw=0.45, zorder=3, solid_capstyle='round')
            for p in u.pins:
                a = tf(p.position.X, p.position.Y, x, y, rot)
                ang = math.radians(p.position.angle + rot)
                b = (a[0] + p.length * math.cos(ang), a[1] - p.length * math.sin(ang))
                ax.plot([a[0], b[0]], [a[1], b[1]], color=SYM, lw=0.45, zorder=3)
                if not ls.hidePinNumbers:
                    mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
                    vert = abs(math.sin(ang)) > 0.5
                    ax.text(mx + (-0.5 if vert else 0), my - (0 if vert else 0.4), p.number, fontsize=fs(1.0), color=SYM,
                            ha='right' if vert else 'center', va='center' if vert else 'bottom', rotation=90 if vert else 0, zorder=4)
                if not ls.pinNamesHide and p.name not in ('~', '') and ls.entryName.startswith(('Conn', 'SW_DPDT')) is False:
                    off = (ls.pinNamesOffset or 0.508) + 0.2
                    c = (b[0] + off * math.cos(ang), b[1] - off * math.sin(ang))
                    ca = math.cos(ang)
                    ax.text(c[0], c[1], p.name, fontsize=fs(1.0), color='#0E6E6E', zorder=4,
                            ha='left' if ca > 0.5 else ('right' if ca < -0.5 else 'center'), va='center')
        for pr in s.properties:
            if pr.key in ('Reference', 'Value') and not (pr.effects and pr.effects.hide):
                ax.text(pr.position.X, pr.position.Y, pr.value, fontsize=fs(1.27 if pr.key == 'Reference' else 1.1),
                        color='#0B5C5C', ha='center', va='center', zorder=5, fontweight='bold' if pr.key == 'Reference' else 'normal')
    for w in sch.graphicalItems:
        if w.type == 'wire':
            ax.plot([w.points[0].X, w.points[1].X], [w.points[0].Y, w.points[1].Y], color=WIRE, lw=0.4, zorder=2, solid_capstyle='round')
    for j in sch.junctions:
        ax.add_patch(Circle((j.position.X, j.position.Y), 0.45, color=WIRE, zorder=3))
    for n in sch.noConnects:
        X, Y, d = n.position.X, n.position.Y, 0.6
        ax.plot([X - d, X + d], [Y - d, Y + d], color='#1F3FBF', lw=0.4)
        ax.plot([X - d, X + d], [Y + d, Y - d], color='#1F3FBF', lw=0.4)
    for l in sch.labels:
        a = l.position.angle or 0
        X, Y = l.position.X, l.position.Y
        if a in (0, 180):
            ax.text(X + (0.3 if a == 0 else -0.3), Y - 0.25, l.text, fontsize=fs(0.95), color=LBL, ha='left' if a == 0 else 'right', va='bottom', zorder=5)
        else:
            ax.text(X - 0.25, Y + (-0.3 if a == 90 else 0.3), l.text, fontsize=fs(0.95), color=LBL, rotation=90, ha='right', va='bottom' if a == 90 else 'top', zorder=5)
    for t in sch.texts:
        h = t.effects.font.height
        ax.text(t.position.X, t.position.Y, t.text, fontsize=fs(h), color=TXT, va='center' if '\n' not in t.text else 'top',
                fontweight='bold' if t.effects.font.bold else 'normal', zorder=5, linespacing=1.4)
    for r in sch.shapes:
        ax.add_patch(Rectangle((r.start.X, r.start.Y), r.end.X - r.start.X, r.end.Y - r.start.Y, fill=False, ec='#6B7680', lw=0.7, ls=(0, (6, 3))))
    fig.savefig(outfile, dpi=dpi, facecolor='white')
    plt.close(fig)
    print('written', outfile)


# ------------------------------------------------------------------------------------------------------ PCB
def node(e, key):
    return next((c for c in e[1:] if isinstance(c, list) and c and c[0] == key), None)


def nodes(e, key):
    return [c for c in e[1:] if isinstance(c, list) and c and c[0] == key]


def render_pcb(path, outfile, title, dpi=300):
    tree = parse_sexp(open(path).read())
    edges, segs, vias, pads, silk, refs = [], [], [], [], [], []
    for e in tree[1:]:
        if not isinstance(e, list):
            continue
        k = e[0]
        if k in ('gr_line', 'gr_rect') and node(e, 'layer')[1] == 'Edge.Cuts':
            s, t = node(e, 'start'), node(e, 'end')
            s, t = (float(s[1]), float(s[2])), (float(t[1]), float(t[2]))
            edges += [(s, t)] if k == 'gr_line' else [(s, (t[0], s[1])), ((t[0], s[1]), t), (t, (s[0], t[1])), ((s[0], t[1]), s)]
        elif k == 'segment':
            s, t = node(e, 'start'), node(e, 'end')
            segs.append(((float(s[1]), float(s[2])), (float(t[1]), float(t[2])), float(node(e, 'width')[1]), node(e, 'layer')[1]))
        elif k == 'via':
            a = node(e, 'at')
            vias.append((float(a[1]), float(a[2]), float(node(e, 'size')[1]), float(node(e, 'drill')[1])))
        elif k == 'footprint':
            a = node(e, 'at')
            fx_, fy_, fr = float(a[1]), float(a[2]), float(a[3]) if len(a) > 3 else 0.0
            r = math.radians(fr)
            T = lambda px, py: (fx_ + px * math.cos(r) + py * math.sin(r), fy_ - px * math.sin(r) + py * math.cos(r))
            ref = next((p[2] for p in nodes(e, 'property') if p[1] == 'Reference'), '')
            if not ref.startswith('H'):
                refs.append((fx_, fy_, ref))
            for p in nodes(e, 'pad'):
                pa = node(p, 'at')
                px, py = T(float(pa[1]), float(pa[2]))
                prot = float(pa[3]) if len(pa) > 3 else fr
                sz = node(p, 'size')
                dr = node(p, 'drill')
                drill = float(dr[1]) if dr and len(dr) > 1 and not isinstance(dr[1], str) or (dr and len(dr) > 1 and dr[1] not in ('oval',)) else 0
                try:
                    drill = float(dr[1]) if dr else 0
                except (ValueError, TypeError):
                    drill = float(dr[2]) if dr and len(dr) > 2 else 0
                pads.append((px, py, float(sz[1]), float(sz[2]), prot, p[3], p[2], drill))
            for g in nodes(e, 'fp_line'):
                if node(g, 'layer')[1] == 'F.SilkS':
                    s, t = node(g, 'start'), node(g, 'end')
                    silk.append((T(float(s[1]), float(s[2])), T(float(t[1]), float(t[2]))))
    xs = [p[0] for s in edges for p in s]
    ys = [p[1] for s in edges for p in s]
    bx0, by0, bx1, by1 = min(xs), min(ys), max(xs), max(ys)
    m = 2
    fig = plt.figure(figsize=((bx1 - bx0 + 2 * m) / 25.4 * 2, (by1 - by0 + 2 * m) / 25.4 * 2))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(bx0 - m, bx1 + m)
    ax.set_ylim(by1 + m, by0 - m)
    ax.axis('off')
    ax.add_patch(FancyBboxPatch((bx0, by0), bx1 - bx0, by1 - by0, boxstyle='round,pad=0,rounding_size=0.5', fc='#13233A', ec='none', zorder=0))
    for s, t, w, layer in segs:
        if layer == 'B.Cu':
            ax.plot([s[0], t[0]], [s[1], t[1]], color='#4D7FC4', lw=w * MM * 2, solid_capstyle='round', zorder=1, alpha=0.9)
    for s, t, w, layer in segs:
        if layer == 'F.Cu':
            ax.plot([s[0], t[0]], [s[1], t[1]], color='#C83434', lw=w * MM * 2, solid_capstyle='round', zorder=2, alpha=0.9)
    for px, py, w, h, rot, shape, ptype, drill in pads:
        r = math.radians(rot)
        if shape == 'circle':
            ax.add_patch(Circle((px, py), w / 2, color='#C9A227', zorder=3))
        else:
            cs = [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)]
            q = [(px + a * math.cos(r) + b * math.sin(r), py - a * math.sin(r) + b * math.cos(r)) for a, b in cs]
            if shape == 'oval':
                rr = min(w, h) / 2
                ax.add_patch(FancyBboxPatch((px - w / 2 + rr, py - h / 2 + rr), w - 2 * rr, h - 2 * rr,
                                            boxstyle=f'round,pad={rr}', color='#C9A227', zorder=3,
                                            transform=matplotlib.transforms.Affine2D().rotate_deg_around(px, py, -rot) + ax.transData))
            else:
                ax.add_patch(Polygon(q, closed=True, color='#C9A227', zorder=3))
        if drill:
            ax.add_patch(Circle((px, py), drill / 2, color='#13233A' if ptype != 'np_thru_hole' else '#E8E8E8', zorder=4))
    for x, y, size, drill in vias:
        ax.add_patch(Circle((x, y), size / 2, color='#B7B7B7', zorder=3))
        ax.add_patch(Circle((x, y), drill / 2, color='#13233A', zorder=4))
    for s, t in silk:
        ax.plot([s[0], t[0]], [s[1], t[1]], color='#E9E4D0', lw=0.5, zorder=5)
    for s, t in edges:
        ax.plot([s[0], t[0]], [s[1], t[1]], color='#E0C341', lw=1.2, zorder=6)
    for x, y, ref in refs:
        ax.text(x, y, ref, color='white', fontsize=7, ha='center', va='center', zorder=7, fontweight='bold',
                bbox=dict(fc='#13233A', ec='none', alpha=0.55, pad=0.4))
    fig.savefig(outfile, dpi=dpi, facecolor='white')
    plt.close(fig)
    print('written', outfile, f'({len(segs)} tracks, {len(vias)} vias, {len(pads)} pads)')


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    render_schematic(os.path.join(KICAD, 'sas_complete', 'sas_complete.kicad_sch'),
                     os.path.join(OUT, 'schema_circuit_complet.png'), crop=(8, 8, 412, 280), dpi=300)
    full = os.path.join(KICAD, 'sas_full_system', 'sas_full_system.kicad_sch')
    render_schematic(full, os.path.join(OUT, 'schema_electrique_complet.png'), dpi=220)
    for name, crop in (('middle', (24, 10, 410, 290)), ('bottom', (400, 10, 833, 262)), ('top', (8, 296, 410, 552))):
        render_schematic(full, os.path.join(OUT, f'schema_{name}.png'), crop=crop, dpi=220)
    for name, title in (('top', 'TOP'), ('middle', 'MIDDLE'), ('bottom', 'BOTTOM')):
        render_pcb(os.path.join(KICAD, 'sas_pcb', f'pcb_{name}', f'pcb_{name}.kicad_pcb'), os.path.join(OUT, f'pcb_{name}.png'), title)

#!/usr/bin/env python3
"""Builds the final report of the Smart Attendance System in French AND English (Word documents), following the outline
of documentation/contenu du rapport.pptx: 13 pages before the annex. Theme: gray, light blue, light cream.
The cover copies the USTHB mini-project cover (documentation/cover.jpeg): logo, institution lines, rounded boxes with
a blue shadow, authors / supervisor, picture, academic year.
Needs python-docx and pillow. Figures come from fig_kicad.py and fig_diagrams.py (run those first).
Run:  python3 build_report.py          (writes Rapport_Smart_Attendance_System_FR.docx and ..._EN.docx)
"""
import os
import re
from xml.sax.saxutils import escape
from docx import Document
from docx.enum.section import WD_ORIENT, WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT, WD_TAB_LEADER
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(HERE)
FIG = os.path.join(BASE, 'figures')
ROOT = os.path.abspath(os.path.join(BASE, '..', '..'))

GRAY_D, GRAY, GRAY_L = '4A5560', '8C969F', 'E4E7EA'
BLUE_L, BLUE, BLUE_D = 'D4E6F6', '6FA8DC', '2F78BD'
CREAM, CREAM_D = 'EEF1F4', 'C3CAD1'   # light gray fills and rules (theme: blue + gray only)
FONT, MONO, SERIF = 'Arial', 'Courier New', 'Times New Roman'
rgb = lambda h: RGBColor.from_string(h)

# ------------------------------------------------------------- cover data (edit here, then rerun) ------------
AUTHORS = ['TSONGODZA Evidence', 'MANDEBVU Langelihle Sasha']   # "SURNAME First name(s)", one per person
SUPERVISOR = 'Mr BOUCHEFRA'
REPO = 'github.com/icesys/smart_attendance_system'
YEAR = '2026/2027'

doc = None
LANG = 'fr'
_shape_id = [900]


def T(fr, en):
    return fr if LANG == 'fr' else en


def F(name):
    """Figure path; the diagrams exist in both languages, the KiCad drawings only once."""
    if LANG == 'en' and os.path.exists(os.path.join(FIG, name + '_en.png')):
        return os.path.join(FIG, name + '_en.png')
    return os.path.join(FIG, name + '.png')


# ------------------------------------------------------------------------------------------- low-level helpers
def shade(el, fill):
    pr = el.get_or_add_tcPr() if el.tag.endswith('}tc') else el.get_or_add_pPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), fill)
    pr.append(shd)


def p_border(p, side='bottom', color=BLUE, size=12, space=2):
    pPr = p._p.get_or_add_pPr()
    b = pPr.find(qn('w:pBdr'))
    if b is None:
        b = OxmlElement('w:pBdr')
        pPr.append(b)
    e = OxmlElement(f'w:{side}')
    for k, v in (('val', 'single'), ('sz', str(size)), ('space', str(space)), ('color', color)):
        e.set(qn(f'w:{k}'), v)
    b.append(e)


def table_borders(t, color=GRAY, size=4, inside=True, style='single'):
    b = OxmlElement('w:tblBorders')
    for side in ('top', 'left', 'bottom', 'right') + (('insideH', 'insideV') if inside else ()):
        e = OxmlElement(f'w:{side}')
        for k, v in (('val', style), ('sz', str(size)), ('space', '0'), ('color', color)):
            e.set(qn(f'w:{k}'), v)
        b.append(e)
    t._tbl.tblPr.append(b)


def no_borders(t):
    table_borders(t, 'FFFFFF', 0, style='nil')


def cell_margins(t, top=50, bottom=50, left=90, right=90):
    m = OxmlElement('w:tblCellMar')
    for side, v in (('top', top), ('bottom', bottom), ('left', left), ('right', right)):
        e = OxmlElement(f'w:{side}')
        e.set(qn('w:w'), str(v))
        e.set(qn('w:type'), 'dxa')
        m.append(e)
    t._tbl.tblPr.append(m)


def col_widths(t, widths):
    """Fixed column widths (Word reads the cell widths, LibreOffice the table grid: set both)."""
    t.autofit = False
    tblPr = t._tbl.tblPr
    lay = OxmlElement('w:tblLayout')
    lay.set(qn('w:type'), 'fixed')
    tblPr.append(lay)
    tw = tblPr.find(qn('w:tblW'))
    if tw is None:
        tw = OxmlElement('w:tblW')
        tblPr.append(tw)
    tw.set(qn('w:w'), str(int(sum(widths) / 2.54 * 1440)))
    tw.set(qn('w:type'), 'dxa')
    for gc, w in zip(t._tbl.tblGrid.findall(qn('w:gridCol')), widths):
        gc.set(qn('w:w'), str(int(w / 2.54 * 1440)))
    for row in t.rows:
        for c, w in zip(row.cells, widths):
            c.width = Cm(w)


def fix_grids(tables):
    """Tables whose widths were only set cell by cell get the same widths in their grid (for LibreOffice)."""
    for tb in tables:
        if tb._tbl.tblPr.find(qn('w:tblLayout')) is None:
            ws = [c.width for c in tb.rows[0].cells]
            if all(ws):
                col_widths(tb, [w / 360000 for w in ws])
        for row in tb.rows:
            for c in row.cells:
                fix_grids(c.tables)


def fmt(p, size=None, before=0, after=4, align=None, line=1.12, keep=False):
    pf = p.paragraph_format
    pf.space_before, pf.space_after, pf.line_spacing = Pt(before), Pt(after), line
    if align is not None:
        p.alignment = align
    if keep:
        pf.keep_with_next = True
    if size:
        for r in p.runs:
            r.font.size = Pt(size)
    return p


def run(p, text, bold=False, italic=False, size=None, color=None, font=None):
    r = p.add_run(text)
    r.bold, r.italic = bold, italic
    if size:
        r.font.size = Pt(size)
    if color:
        r.font.color.rgb = rgb(color)
    if font:
        r.font.name = font
        r._element.rPr.rFonts.set(qn('w:ascii'), font)
        r._element.rPr.rFonts.set(qn('w:hAnsi'), font)
    return r


def rich(p, text, size=None, color=None, font=None):
    """**bold** segments inside a text."""
    for i, s in enumerate(text.split('**')):
        if s:
            run(p, s, bold=bool(i % 2), size=size, color=color, font=font)
    return p


def para(text='', size=10.5, after=5, align=WD_ALIGN_PARAGRAPH.JUSTIFY, color=None, before=0, cont=None):
    p = (cont or doc).add_paragraph()
    rich(p, text, size, color)
    return fmt(p, before=before, after=after, align=align)


def bullets(items, size=10.5, after=2, cont=None, indent=0.55):
    for it in items:
        p = (cont or doc).add_paragraph()
        p.paragraph_format.left_indent = Cm(indent)
        p.paragraph_format.first_line_indent = Cm(-0.4)
        run(p, '•  ', bold=True, color=BLUE_D, size=size)
        rich(p, it, size)
        fmt(p, after=after, align=WD_ALIGN_PARAGRAPH.JUSTIFY)


def h1(num, text, new_page=True, size=16):
    p = doc.add_paragraph()
    if new_page:
        p.paragraph_format.page_break_before = True
    run(p, f'{num}   ' if num else '', bold=True, size=size, color=BLUE_D)
    run(p, text.upper(), bold=True, size=size, color=GRAY_D)
    shade(p._p, BLUE_L)
    p_border(p, 'left', BLUE_D, 36, 6)
    p.paragraph_format.left_indent = Cm(0.1)
    return fmt(p, before=0, after=10 if size == 16 else 4, line=1.3 if size == 16 else 1.2, keep=True)


def h2(text, before=8, new_page=False):
    p = doc.add_paragraph()
    if new_page:
        p.paragraph_format.page_break_before = True
    run(p, text, bold=True, size=12, color=BLUE_D)
    p_border(p, 'bottom', CREAM_D, 8, 1)
    return fmt(p, before=before, after=5, keep=True)


def table(header, rows, widths, size=9, header_fill=BLUE_L, zebra=True, bold_first=False, cont=None, align=None):
    t = (cont or doc).add_table(rows=1 + len(rows), cols=len(header))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    table_borders(t, GRAY, 4)
    cell_margins(t)
    for i, h in enumerate(header):
        c = t.rows[0].cells[i]
        shade(c._tc, header_fill)
        p = c.paragraphs[0]
        run(p, h, bold=True, size=size, color=GRAY_D)
        fmt(p, after=0, line=1.0)
    for r, row in enumerate(rows, 1):
        for i, v in enumerate(row):
            c = t.rows[r].cells[i]
            if zebra and r % 2 == 0:
                shade(c._tc, CREAM)
            c.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            p = c.paragraphs[0]
            rich(p, v, size)
            if bold_first and i == 0:
                for x in p.runs:
                    x.bold = True
            fmt(p, after=0, line=1.0, align=(align[i] if align else None))
    col_widths(t, widths)
    return t


def box(lines, fill=CREAM, border=CREAM_D, size=10, height=None, dashed=False, title=None, width=16.6, cont=None, center=False):
    t = (cont or doc).add_table(rows=1, cols=1)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    table_borders(t, border, 8 if dashed else 6, inside=False, style='dashed' if dashed else 'single')
    cell_margins(t, 90, 90, 140, 140)
    c = t.rows[0].cells[0]
    shade(c._tc, fill)
    if height:
        trPr = t.rows[0]._tr.get_or_add_trPr()
        h = OxmlElement('w:trHeight')
        h.set(qn('w:val'), str(int(height / 2.54 * 1440)))
        h.set(qn('w:hRule'), 'exact')
        trPr.append(h)
        c.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    p = c.paragraphs[0]
    if title:
        run(p, title, bold=True, size=size + 0.5, color=BLUE_D)
        fmt(p, after=3, line=1.05)
        p = c.add_paragraph()
    for i, ln in enumerate(lines):
        if i:
            p = c.add_paragraph()
        rich(p, ln, size, GRAY_D if not dashed else GRAY)
        if dashed:
            for x in p.runs:
                x.italic = True
        fmt(p, after=2, line=1.08, align=WD_ALIGN_PARAGRAPH.CENTER if center else WD_ALIGN_PARAGRAPH.JUSTIFY)
    col_widths(t, [width])
    return t


def placeholder(text, height, width=16.6, cont=None):
    return box([text], fill='F7F8FA', border=GRAY, size=9.5, height=height, dashed=True, width=width, cont=cont, center=True)


def picture(path, width=None, height=None, cont=None, after=3):
    p = (cont or doc).add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run().add_picture(path, width=Cm(width) if width else None, height=Cm(height) if height else None)
    return fmt(p, after=after, line=1.0)


def caption(text, cont=None, after=6):
    p = (cont or doc).add_paragraph()
    run(p, text, italic=True, size=9, color=GRAY)
    return fmt(p, after=after, align=WD_ALIGN_PARAGRAPH.CENTER, line=1.0)


def spacer(pt, cont=None):
    """An almost empty paragraph that only adds pt points of vertical space."""
    p = (cont or doc).add_paragraph()
    run(p, ' ', size=1)
    return fmt(p, after=pt, line=1.0)


def margins(s, landscape=False):
    s.top_margin, s.bottom_margin = Cm(1.9 if not landscape else 1.6), Cm(1.7 if not landscape else 1.4)
    s.left_margin = s.right_margin = Cm(2.2 if not landscape else 1.8)
    s.header_distance, s.footer_distance = Cm(0.8), Cm(0.7)


def new_section(landscape):
    s = doc.add_section(WD_SECTION.NEW_PAGE)
    w, h = Cm(21.0), Cm(29.7)
    s.orientation = WD_ORIENT.LANDSCAPE if landscape else WD_ORIENT.PORTRAIT
    s.page_width, s.page_height = (h, w) if landscape else (w, h)
    margins(s, landscape)
    s.different_first_page_header_footer = False
    return s


def add_field(p, instr):
    r = p.add_run()
    f1 = OxmlElement('w:fldChar')
    f1.set(qn('w:fldCharType'), 'begin')
    it = OxmlElement('w:instrText')
    it.set(qn('xml:space'), 'preserve')
    it.text = instr
    f2 = OxmlElement('w:fldChar')
    f2.set(qn('w:fldCharType'), 'separate')
    t = OxmlElement('w:t')
    t.text = '1'
    f3 = OxmlElement('w:fldChar')
    f3.set(qn('w:fldCharType'), 'end')
    for e in (f1, it, f2, t, f3):
        r._r.append(e)
    return r


# ------------------------------------------------------------------------------------------------ cover shapes
NS = ('xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
      'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" '
      'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
      'xmlns:wps="http://schemas.microsoft.com/office/word/2010/wordprocessingShape"')


def spaced(r, pts):
    """Letter spacing (in points) for a run: used for the small capital labels of the cover."""
    sp = OxmlElement('w:spacing')
    sp.set(qn('w:val'), str(int(pts * 20)))
    r._element.get_or_add_rPr().append(sp)
    return r


def cover_picture():
    """The three routed boards side by side (stand-in until a photo of the finished device exists)."""
    path = os.path.join(FIG, 'cover_pcbs.png')
    from PIL import Image
    ims = [Image.open(os.path.join(FIG, f'pcb_{n}.png')).convert('RGB') for n in ('top', 'middle', 'bottom')]
    h = min(i.size[1] for i in ims)
    ims = [i.resize((int(i.size[0] * h / i.size[1]), h)) for i in ims]
    gap = 60
    c = Image.new('RGB', (sum(i.size[0] for i in ims) + gap * 2, h), 'white')
    x = 0
    for i in ims:
        c.paste(i, (x, 0))
        x += i.size[0] + gap
    c.save(path)
    return path


def cover():
    """Flat, modern cover for A4 printing: no shadows, no full-bleed colour (everything stays inside the margins)."""
    # institution header: logo + the three official lines, then a thin blue rule
    t = doc.add_table(rows=1, cols=2)
    no_borders(t)
    cell_margins(t, 0, 0, 0, 120)
    lc, rc = t.rows[0].cells
    lc.vertical_alignment = rc.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    p = lc.paragraphs[0]
    p.add_run().add_picture(os.path.join(FIG, 'logo_usthb.png'), width=Cm(2.9))
    fmt(p, after=0, line=1.0)
    for i, (txt, b) in enumerate(((T('République Algérienne Démocratique et Populaire', "People's Democratic Republic of Algeria"), False),
                                  (T('Ministère de l\'Enseignement Supérieur et de la Recherche Scientifique',
                                     'Ministry of Higher Education and Scientific Research'), False),
                                  (T('Université des Sciences et de la Technologie Houari Boumediene',
                                     'University of Science and Technology Houari Boumediene'), True))):
        p = rc.paragraphs[0] if i == 0 else rc.add_paragraph()
        run(p, txt, bold=b, size=9.5, color=GRAY_D if b else GRAY)
        fmt(p, after=1, line=1.1)
    col_widths(t, [3.4, 13.2])
    p = doc.add_paragraph()
    p_border(p, 'bottom', BLUE, 12, 1)
    fmt(p, after=16, line=0.5)

    p = doc.add_paragraph()
    spaced(run(p, T('Faculté d\'Électronique et d\'Informatique', 'Faculty of Electronics and Computer Science').upper(),
               bold=True, size=13, color=GRAY_D), 1.0)
    fmt(p, after=3)
    p = doc.add_paragraph()
    run(p, T('Domaine Sciences et Technologie  ·  Filière Électronique  ·  Licence 3 (LMD)',
             'Science and Technology  ·  Electronics  ·  Third-year Bachelor (LMD)'), size=10, color=GRAY)
    fmt(p, after=64)

    # title panel: light blue, dark accent bar on the left, no shadow
    t = doc.add_table(rows=1, cols=1)
    table_borders(t, BLUE_L, 4, inside=False)
    c = t.rows[0].cells[0]
    shade(c._tc, BLUE_L)
    tcPr = c._tc.get_or_add_tcPr()
    bd = OxmlElement('w:tcBorders')
    lb = OxmlElement('w:left')
    for k, v in (('val', 'single'), ('sz', '48'), ('space', '0'), ('color', BLUE_D)):
        lb.set(qn(f'w:{k}'), v)
    bd.append(lb)
    tcPr.append(bd)
    cell_margins(t, 480, 480, 420, 300)
    p = c.paragraphs[0]
    spaced(run(p, T('Mini-projet', 'Mini-project').upper(), bold=True, size=10, color=BLUE_D), 2)
    fmt(p, after=10, line=1.0)
    p = c.add_paragraph()
    run(p, 'Smart Attendance System', bold=True, size=34, color=GRAY_D)
    fmt(p, after=6, line=1.0)
    p = c.add_paragraph()
    run(p, T('Système autonome de pointage des présences par carte étudiant RFID 125 kHz',
             'Stand-alone attendance system using 125 kHz RFID student cards'), size=14, color=BLUE_D)
    fmt(p, after=0, line=1.1)
    col_widths(t, [16.6])

    spacer(52)
    picture(cover_picture(), width=16.6, after=4)
    caption(T('Les trois circuits imprimés du dispositif (TOP, MIDDLE, BOTTOM), conçus sous KiCad',
              'The three printed circuit boards of the device (TOP, MIDDLE, BOTTOM), designed in KiCad'), after=50)

    # people: two cream cards
    t = doc.add_table(rows=1, cols=3)
    no_borders(t)
    cell_margins(t, 200, 200, 260, 260)
    left, gap, right = t.rows[0].cells
    for cc, head, names in ((left, T('Réalisé par', 'Carried out by'), AUTHORS), (right, T('Encadré par', 'Supervised by'), [SUPERVISOR])):
        shade(cc._tc, CREAM)
        p = cc.paragraphs[0]
        spaced(run(p, head.upper(), bold=True, size=8.5, color=BLUE_D), 1.5)
        fmt(p, after=6, line=1.0)
        for n in names:
            p = cc.add_paragraph()
            run(p, n, bold=True, size=12.5, color=GRAY_D)
            fmt(p, after=3, line=1.0)
    col_widths(t, [9.6, 0.6, 6.4])

    spacer(56)
    t = doc.add_table(rows=1, cols=1)
    table_borders(t, GRAY_D, 4, inside=False)
    c = t.rows[0].cells[0]
    shade(c._tc, GRAY_D)
    p = c.paragraphs[0]
    spaced(run(p, T(f'Année universitaire {YEAR}', f'Academic year {YEAR}').upper(), bold=True, size=11, color='FFFFFF'), 2)
    fmt(p, before=5, after=5, align=WD_ALIGN_PARAGRAPH.CENTER)
    col_widths(t, [16.6])


# ================================================================================================ the report
def build(lang):
    global doc, LANG
    LANG = lang
    _shape_id[0] = 900
    doc = Document()
    st = doc.styles['Normal']
    st.font.name, st.font.size = FONT, Pt(10.5)
    st.element.rPr.rFonts.set(qn('w:eastAsia'), FONT)
    st.font.color.rgb = rgb('2E3338')
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
    margins(sec)
    sec.different_first_page_header_footer = True

    hp = sec.header.paragraphs[0]
    run(hp, 'Smart Attendance System', bold=True, size=8.5, color=BLUE_D)
    run(hp, T('  ·  Rapport de mini-projet', '  ·  Mini-project report'), size=8.5, color=GRAY)
    run(hp, T(f'  ·  Année universitaire {YEAR}', f'  ·  Academic year {YEAR}'), size=8.5, color=GRAY)
    p_border(hp, 'bottom', BLUE, 6, 3)
    fp = sec.footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run(fp, '— ', size=9, color=GRAY)
    r = add_field(fp, 'PAGE')
    r.font.size, r.font.color.rgb, r.bold = Pt(9), rgb(BLUE_D), True
    run(fp, ' —', size=9, color=GRAY)

    # ============================================================================================ 1: cover
    cover()

    # ============================================================================================ 2: contents
    h1('', T('Sommaire', 'Contents'))
    toc = [(1, '1', T('Introduction générale', 'General introduction'), 3),
           (1, '2', T('Objectifs et cahier des charges', 'Objectives and specifications'), 4),
           (2, '2.1', T('Objectifs du projet', 'Project objectives'), 4),
           (2, '2.2', T('Cahier des charges', 'Specifications'), 4),
           (1, '3', T('Matériel et composants utilisés', 'Hardware and components'), 5),
           (2, '3.1', T('Liste du matériel', 'Bill of materials'), 5),
           (2, '3.2', T('Organisation en trois cartes', 'Three-board organisation'), 6),
           (2, '3.3', T('Chaîne d\'alimentation et choix techniques', 'Power chain and design choices'), 6),
           (1, '4', T('Fonctionnement du système', 'How the system works'), 7),
           (2, '4.1', T('Schéma électrique complet', 'Complete electrical schematic'), 7),
           (2, '4.2', T('Schéma synoptique', 'Block diagram'), 8),
           (2, '4.3', T('Organigramme du programme principal', 'Flowchart of the main program'), 9),
           (2, '4.4', T('Organigrammes de la lecture d\'une carte et des sessions', 'Flowcharts of card reading and sessions'), 10),
           (1, '5', T('Réalisation et tests du système', 'Build and testing'), 11),
           (2, '5.1', T('Conception des circuits imprimés', 'PCB design'), 11),
           (2, '5.2', T('Fabrication et assemblage', 'Manufacturing and assembly'), 12),
           (2, '5.3', T('Tests et validation', 'Testing and validation'), 12),
           (1, '6', T('Conclusion générale et perspectives', 'General conclusion and outlook'), 13),
           (1, 'A', T('Annexe A : schéma électrique découpé en trois cartes', 'Appendix A: schematic split into three boards'), 14),
           (1, 'B', T('Annexe B : brochage, nappes et formats de fichiers', 'Appendix B: pinout, cables and file formats'), 15),
           (1, 'C', T('Annexe C : extraits du programme', 'Appendix C: program excerpts'), 16)]
    for lvl, num, title, pg in toc:
        p = doc.add_paragraph()
        p.paragraph_format.tab_stops.add_tab_stop(Cm(16.4), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS)
        p.paragraph_format.left_indent = Cm(0 if lvl == 1 else 0.9)
        run(p, f'{num}   {title}', bold=(lvl == 1), size=11.5 if lvl == 1 else 10.5, color=GRAY_D if lvl == 1 else '2E3338')
        run(p, f'\t{pg}', bold=(lvl == 1), size=11 if lvl == 1 else 10.5, color=BLUE_D)
        fmt(p, before=(9 if lvl == 1 else 0), after=3)
    spacer(14)
    box([T('Le rapport suit le plan du document « Contenu du rapport » : introduction (1 page), objectifs et cahier des charges '
           '(1 page), matériel (2 pages), fonctionnement du système (4 pages), réalisation et tests (2 pages) et conclusion '
           '(1 page), soit **13 pages hors annexes**, suivies de 3 pages d\'annexes.',
           'The report follows the outline of the « Contenu du rapport » document: introduction (1 page), objectives and '
           'specifications (1 page), hardware (2 pages), how the system works (4 pages), build and testing (2 pages) and '
           'conclusion (1 page), i.e. **13 pages without the appendices**, followed by 3 pages of appendices.'),
         T('Les pages consacrées à la fabrication, à l\'assemblage et aux tests sur cartes réelles (sections 5.2 et 5.3) sont '
           'préparées et seront complétées après la réception des circuits imprimés.',
           'The pages on manufacturing, assembly and tests on the real boards (sections 5.2 and 5.3) are prepared and will be '
           'completed once the printed circuit boards have arrived.')],
        title=T('Note sur l\'organisation du rapport', 'Note on the structure of the report'), size=9.5)

    # ============================================================================================ 3: introduction
    h1('1', T('Introduction générale', 'General introduction'))
    para(T('Dans la plupart des établissements, la présence des étudiants est encore relevée sur une **feuille papier** qui circule '
           'dans l\'amphithéâtre. Cette méthode fait perdre du temps à chaque séance, elle est sujette aux erreurs de lecture et '
           'à la fraude (un étudiant signe à la place d\'un camarade absent), et elle oblige l\'enseignant ou l\'administration à '
           'ressaisir ensuite toutes les données à la main.',
           'In most institutions, student attendance is still taken on a **sheet of paper** passed around the lecture hall. '
           'This wastes time in every session, it is prone to reading mistakes and to fraud (a student signs for an absent '
           'friend), and it forces the lecturer or the administration to type all the data in again by hand.'))
    para(T('Pourtant, chaque étudiant possède déjà une **carte étudiant équipée d\'une puce RFID**. Elle est utilisée tous les '
           'jours au restaurant universitaire : on la pose à plat sur un petit lecteur, sans visée ni contact, et le passage est '
           'enregistré instantanément. L\'idée de ce mini-projet est d\'appliquer exactement la même interaction au pointage des '
           'cours : à la fin de la séance, l\'enseignant se place à la porte avec le dispositif et chaque étudiant pose sa carte '
           'en sortant.',
           'Yet every student already owns a **student card with an RFID chip**. It is used every day at the university '
           'restaurant: the card is laid flat on a small reader, without aiming or contact, and the visit is recorded at once. '
           'The idea of this mini-project is to bring exactly the same gesture to lecture attendance: at the end of the '
           'session, the lecturer stands at the door with the device and each student taps their card on the way out.'))
    para(T('Les **systèmes embarqués** à base de microcontrôleur se prêtent bien à ce type d\'application : ils sont peu coûteux, '
           'peu gourmands en énergie et capables de piloter à la fois des capteurs, une mémoire, un affichage et une liaison '
           'avec un ordinateur. Nous avons retenu une carte de développement **ESP32-S3**, associée à un lecteur RFID **RDM6300** '
           '(125 kHz), à une horloge temps réel **DS3231**, à une carte **microSD** et à une alimentation par batterie lithium '
           '**18650** rechargeable en USB-C. Le dispositif fonctionne ainsi entièrement sans fil pendant le cours ; ce n\'est '
           'qu\'après la séance que l\'enseignant le branche sur un PC, où la carte microSD apparaît comme une simple clé USB '
           'contenant les fichiers de présence au format CSV.',
           'Microcontroller-based **embedded systems** suit this kind of application well: they are cheap, use little energy '
           'and can drive sensors, memory, a display and a link to a computer at the same time. We chose an **ESP32-S3** '
           'development board, together with an **RDM6300** RFID reader (125 kHz), a **DS3231** real-time clock, a **microSD** '
           'card and a lithium **18650** battery that is charged over USB-C. The device therefore runs completely cable-free '
           'during the lecture; only afterwards does the lecturer plug it into a PC, where the microSD card shows up as an '
           'ordinary USB drive holding the attendance files in CSV format.'))
    para(T('Le projet a été mené de façon professionnelle : rédaction des exigences, journal des décisions techniques, '
           'prototype sur plaque d\'essai validé module par module, programme écrit en C/C++ sous PlatformIO et testé, puis '
           'conception sous **KiCad** d\'un ensemble de **trois circuits imprimés** superposés de 95 × 60 mm reliés par deux nappes.',
           'The project was run in a professional way: written requirements, a log of technical decisions, a breadboard '
           'prototype checked module by module, a program written and tested in C/C++ with PlatformIO, and finally the design '
           'in **KiCad** of a stack of **three printed circuit boards** of 95 × 60 mm joined by two ribbon cables.'))
    h2(T('Plan du rapport', 'Outline of the report'))
    bullets(T(['le **chapitre 2** fixe les objectifs et le cahier des charges ;',
               'le **chapitre 3** présente le matériel retenu, l\'organisation en trois cartes et la chaîne d\'alimentation ;',
               'le **chapitre 4** décrit le fonctionnement : schéma électrique, schéma synoptique et organigrammes du programme ;',
               'le **chapitre 5** traite de la réalisation des circuits imprimés, de leur fabrication et des tests ;',
               'le **chapitre 6** conclut et propose des perspectives d\'évolution ; les annexes donnent le schéma découpé en trois cartes, le brochage et des extraits du programme.'],
              ['**chapter 2** sets the objectives and the specifications;',
               '**chapter 3** presents the chosen hardware, the three-board organisation and the power chain;',
               '**chapter 4** explains how the system works: electrical schematic, block diagram and program flowcharts;',
               '**chapter 5** covers the design of the printed circuit boards, their manufacturing and the tests;',
               '**chapter 6** concludes and suggests future improvements; the appendices give the schematic split into three boards, the pinout and program excerpts.']))

    # ============================================================================================ 4: objectives
    h1('2', T('Objectifs et cahier des charges', 'Objectives and specifications'))
    h2(T('2.1  Objectifs du projet', '2.1  Project objectives'), before=0)
    t = doc.add_table(rows=1, cols=2)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell_margins(t, 60, 60, 120, 120)
    table_borders(t, 'FFFFFF', 4)
    blocks = ((T('Objectifs techniques (capacités du dispositif)', 'Technical objectives (what the device can do)'), BLUE_L,
               T(['**Identification sans contact** : lire la carte étudiant existante posée à plat.',
                  '**Horodatage fiable** de chaque passage, même après une coupure (horloge DS3231 sauvegardée par pile).',
                  '**Anti-doublon** : une carte passée deux fois n\'est comptée qu\'une fois par séance.',
                  '**Stockage persistant** dans des fichiers CSV sur carte microSD.',
                  '**Récupération simple** sur PC, sans logiciel : la microSD est vue comme une clé USB.',
                  '**Autonomie** : batterie rechargeable, aucun câble pendant le cours.',
                  '**Retour immédiat** à l\'étudiant : LED, buzzer et écran OLED.'],
                 ['**Contactless identification**: read the existing student card laid flat on the reader.',
                  '**Reliable time stamp** for each tap, even after a power cut (DS3231 clock with backup cell).',
                  '**No duplicates**: a card tapped twice is counted only once per session.',
                  '**Persistent storage** in CSV files on a microSD card.',
                  '**Easy retrieval** on a PC with no software: the microSD is seen as a USB drive.',
                  '**Autonomy**: rechargeable battery, no cable during the lecture.',
                  '**Immediate feedback** to the student: LEDs, buzzer and OLED display.'])),
              (T('Objectifs pédagogiques (apprentissage)', 'Learning objectives'), CREAM,
               T(['Programmer un microcontrôleur 32 bits en **C/C++** (PlatformIO, framework Arduino).',
                  'Maîtriser les bus de communication **UART, I2C, SPI et USB**.',
                  'Comprendre la **gestion d\'une batterie Li-ion** : charge, protection, conversion de tension.',
                  'Concevoir des **schémas électriques et des circuits imprimés** sous KiCad.',
                  'Suivre une **démarche de projet** : exigences, décisions argumentées, plan de test, documentation.'],
                 ['Program a 32-bit microcontroller in **C/C++** (PlatformIO, Arduino framework).',
                  'Master the **UART, I2C, SPI and USB** communication buses.',
                  'Understand **Li-ion battery management**: charging, protection, voltage conversion.',
                  'Design **electrical schematics and printed circuit boards** in KiCad.',
                  'Follow a **project method**: requirements, reasoned decisions, test plan, documentation.'])))
    for i, (title, fill, items) in enumerate(blocks):
        cc = t.rows[0].cells[i]
        shade(cc._tc, fill)
        cc.width = Cm(8.3)
        p = cc.paragraphs[0]
        run(p, title, bold=True, size=10.5, color=BLUE_D)
        fmt(p, after=4)
        bullets(items, size=9.5, after=2, cont=cc, indent=0.45)
    h2(T('2.2  Cahier des charges', '2.2  Specifications'))
    must, should, cons = T('Indispensable', 'Must'), T('Souhaitable', 'Should'), T('Contrainte', 'Constraint')
    table([T('Réf.', 'Ref.'), T('Exigence', 'Requirement'), T('Priorité', 'Priority')], [
        ['F1', T('Détecter une carte étudiant posée sur le lecteur et lire son identifiant (UID)',
                 'Detect a student card placed on the reader and read its identifier (UID)'), must],
        ['F2', T('Enregistrer chaque passage avec la date et l\'heure', 'Record each tap with the date and time'), must],
        ['F3', T('Ignorer les passages répétés d\'une même carte pendant une séance',
                 'Ignore repeated taps of the same card during a session'), must],
        ['F4', T('Conserver les données après une coupure d\'alimentation', 'Keep the data after a power cut'), must],
        ['F5', T('Permettre à l\'enseignant de récupérer les fichiers sur un PC après le cours',
                 'Let the lecturer retrieve the files on a PC after the lecture'), must],
        ['F6', T('Signaler le résultat de chaque passage (LED, buzzer, écran)',
                 'Show the result of each tap (LEDs, buzzer, display)'), should],
        ['F7', T('Associer l\'identifiant de la carte au nom et au matricule de l\'étudiant',
                 'Match the card identifier to the student\'s name and registration number'), should],
        ['C1', T('Fonctionnement autonome sur batterie Li-ion 18650, recharge par USB-C',
                 'Battery operation on an 18650 Li-ion cell, charged over USB-C'), cons],
        ['C2', T('Carte posée à plat, sans visée ; lecture en moins d\'une seconde',
                 'Card laid flat, no aiming; read in less than one second'), cons],
        ['C3', T('Circuits imprimés conçus sous KiCad ; carte ESP32-S3 montée sur supports (amovible)',
                 'PCBs designed in KiCad; ESP32-S3 board mounted on sockets (removable)'), cons],
        ['C4', T('Projet complet (matériel, logiciel, documentation) terminé en février 2027',
                 'Complete project (hardware, software, documentation) finished by February 2027'), cons],
    ], [1.2, 12.4, 3.0], size=9, bold_first=True)
    para(T('Les exigences « Indispensable » conditionnent la validation du projet ; elles sont reprises une à une dans le plan '
           'de test du chapitre 5.',
           'The "Must" requirements decide whether the project is validated; each one is checked by the test plan of chapter 5.'),
         size=9.5, before=5, after=0)

    # ============================================================================================ 5: hardware 1/2
    h1('3', T('Matériel et composants utilisés', 'Hardware and components'))
    h2(T('3.1  Liste du matériel', '3.1  Bill of materials'), before=0)
    table([T('Composant', 'Component'), T('Rôle', 'Role'), T('Caractéristiques principales', 'Main characteristics'), T('Qté', 'Qty')], [
        [T('ESP32-S3 N16R8 (carte de développement)', 'ESP32-S3 N16R8 (development board)'), T('Unité de traitement', 'Processing unit'),
         T('Double cœur Xtensa LX7 à 240 MHz, 16 Mo de flash, 8 Mo de PSRAM, Wi-Fi et Bluetooth LE, USB natif, régulateur 3,3 V intégré',
           'Dual-core Xtensa LX7 at 240 MHz, 16 MB flash, 8 MB PSRAM, Wi-Fi and Bluetooth LE, native USB, on-board 3.3 V regulator'), '1'],
        [T('Lecteur RDM6300 + bobine 35 × 46 mm', 'RDM6300 reader + 35 × 46 mm coil'), T('Lecture des cartes', 'Card reading'),
         T('125 kHz, protocole EM4100, trame série de 14 octets à 9600 bauds, alimentation 5 V',
           '125 kHz, EM4100 protocol, 14-byte serial frame at 9600 baud, 5 V supply'), '1'],
        [T('Horloge temps réel DS3231 + pile CR2032', 'DS3231 real-time clock + CR2032 cell'), T('Horodatage', 'Time stamping'),
         T('Oscillateur compensé en température (± 2 ppm), bus I2C (adresse 0x68), heure conservée sans alimentation',
           'Temperature-compensated oscillator (± 2 ppm), I2C bus (address 0x68), keeps time without power'), '1'],
        [T('Module carte microSD', 'microSD card module'), T('Stockage', 'Storage'),
         T('Bus SPI, système de fichiers FAT32, fichiers CSV lisibles sous Excel', 'SPI bus, FAT32 file system, CSV files readable in Excel'), '1'],
        [T('Écran OLED 0,96" SSD1306', '0.96" SSD1306 OLED display'), T('Affichage', 'Display'),
         T('128 × 64 pixels, bus I2C (adresse 0x3C), alimentation 3,3 V', '128 × 64 pixels, I2C bus (address 0x3C), 3.3 V supply'), '1'],
        [T('Batterie Li-ion 18650 + support', '18650 Li-ion cell + holder'), T('Source d\'énergie', 'Energy source'),
         T('3,7 V nominal, 4,2 V chargée ; support placé sous la carte BOTTOM', '3.7 V nominal, 4.2 V charged; holder under the BOTTOM board'), '1'],
        [T('Module TP4056 protégé (USB-C)', 'Protected TP4056 module (USB-C)'), T('Charge et protection', 'Charging and protection'),
         T('Charge 1 A à courant puis tension constants ; protection contre surcharge, décharge profonde et court-circuit',
           '1 A constant-current / constant-voltage charging; protection against overcharge, deep discharge and short circuit'), '1'],
        [T('Module élévateur MT3608', 'MT3608 boost module'), T('Conversion de tension', 'Voltage conversion'),
         T('Convertisseur DC-DC élévateur, sortie réglée à 5,0 V au multimètre', 'DC-DC boost converter, output set to 5.0 V with a multimeter'), '1'],
        [T('Interrupteur à glissière 6 broches', '6-pin slide switch'), T('Marche / arrêt', 'On / off'),
         T('Deux pôles câblés en parallèle pour le courant', 'Both poles wired in parallel for current'), '1'],
        [T('Diode Schottky 1N5819', '1N5819 Schottky diode'), T('Isolation USB / batterie', 'USB / battery isolation'),
         T('1 A, 40 V, chute de tension d\'environ 0,3 V', '1 A, 40 V, about 0.3 V forward drop'), '1'],
        [T('LED 5 mm bleue, verte, rouge + 3 × 220 Ω', '5 mm LEDs blue, green, red + 3 × 220 Ω'), T('Signalisation', 'Signalling'),
         T('Témoin de marche, passage accepté, passage refusé', 'Power-on indicator, tap accepted, tap refused'), '3'],
        [T('Buzzer 12 mm, 2N2222A, 1 kΩ, 100 kΩ, 1N4148', '12 mm buzzer, 2N2222A, 1 kΩ, 100 kΩ, 1N4148'), T('Signal sonore', 'Sound signal'),
         T('Transistor NPN en commutation, diode de roue libre, alimentation 3,3 V ou 5 V par cavalier',
           'NPN transistor switch, flyback diode, 3.3 V or 5 V supply selected by a jumper'), '1'],
        [T('Boutons poussoirs 6 × 6 mm', '6 × 6 mm push buttons'), T('Commandes', 'Controls'),
         T('Bouton 1 : session ; bouton 2 : informations / mode clé USB', 'Button 1: session; button 2: information / USB drive mode'), '2'],
        [T('Condensateurs 470 µF, 10 µF, 100 nF', 'Capacitors 470 µF, 10 µF, 100 nF'), T('Découplage', 'Decoupling'),
         T('Filtrage du 5 V de l\'élévateur et des rails 5V_SYS et 3V3', 'Filtering of the boost 5 V and of the 5V_SYS and 3V3 rails'), '8'],
        [T('Connecteurs IDC 2 × 8 + nappes 16 fils', '2 × 8 IDC headers + 16-wire ribbons'), T('Liaison entre cartes', 'Board-to-board link'),
         T('Pas de 2,54 mm, même brochage aux deux extrémités', '2.54 mm pitch, same pinout at both ends'), '4 + 2'],
        [T('Circuits imprimés 95 × 60 mm + entretoises M3', '95 × 60 mm PCBs + M3 spacers'), T('Support mécanique', 'Mechanical support'),
         T('Trois cartes double face superposées (TOP, MIDDLE, BOTTOM)', 'Three stacked double-sided boards (TOP, MIDDLE, BOTTOM)'), '3'],
    ], [4.6, 3.0, 8.0, 1.0], size=8.5, bold_first=True, align=[None, None, None, WD_ALIGN_PARAGRAPH.CENTER])
    para(T('Les modules du commerce (lecteur, horloge, microSD, écran, chargeur, élévateur) ont été préférés à des circuits '
           'intégrés soudés directement : ils sont disponibles localement, déjà testés et faciles à remplacer. Leurs empreintes '
           'ont été relevées à la main sur les modules réels puis vérifiées sur une impression à l\'échelle 1:1.',
           'Ready-made modules (reader, clock, microSD, display, charger, boost) were preferred to bare chips: they are '
           'available locally, already tested and easy to replace. Their footprints were measured by hand on the real modules '
           'and checked against a 1:1 printout.'), size=9.5, before=6, after=0)

    # ============================================================================================ 6: hardware 2/2
    h2(T('3.2  Organisation en trois cartes superposées', '3.2  Three stacked boards'), before=0, new_page=True)
    para(T('Pour garder un boîtier compact (environ la taille d\'une main), le circuit est réparti sur **trois cartes de '
           '95 × 60 mm** empilées et fixées par quatre entretoises M3. Deux nappes de 16 conducteurs relient les cartes ; '
           'chaque nappe porte plusieurs fils de masse pour limiter les perturbations.',
           'To keep the enclosure compact (about the size of a hand), the circuit is spread over **three 95 × 60 mm boards** '
           'stacked and held by four M3 spacers. Two 16-conductor ribbon cables join the boards; each cable carries several '
           'ground wires to limit interference.'), size=10)
    table([T('Carte', 'Board'), T('Fonction', 'Function'), T('Composants principaux', 'Main components')], [
        [T('**TOP** (dessus)', '**TOP**'), T('Interface utilisateur et antenne', 'User interface and antenna'),
         T('LED bleue, verte et rouge ; buzzer et son transistor ; 2 boutons ; écran OLED ; bobine RFID (zone sans cuivre)',
           'Blue, green and red LEDs; buzzer and its transistor; 2 buttons; OLED display; RFID coil (copper-free area)')],
        [T('**MIDDLE** (milieu)', '**MIDDLE**'), T('Traitement et lecture', 'Processing and reading'),
         T('ESP32-S3 sur deux barrettes femelles 1 × 22 ; lecteur RDM6300 ; diode Schottky ; découplage ; connecteurs J105 et J106',
           'ESP32-S3 on two 1 × 22 female headers; RDM6300 reader; Schottky diode; decoupling; connectors J105 and J106')],
        [T('**BOTTOM** (dessous)', '**BOTTOM**'), T('Énergie et stockage', 'Power and storage'),
         T('Batterie 18650 (sous la carte) ; TP4056 ; interrupteur ; MT3608 ; condensateur 470 µF ; microSD ; DS3231',
           '18650 cell (under the board); TP4056; switch; MT3608; 470 µF capacitor; microSD; DS3231')],
    ], [3.0, 4.0, 9.6], size=9)
    caption(T('Nappe 1 : TOP J1 ↔ MIDDLE J105 (LED, buzzer, boutons, I2C, bobine)    ·    Nappe 2 : MIDDLE J106 ↔ BOTTOM J201 (alimentation, I2C, SPI)',
              'Cable 1: TOP J1 ↔ MIDDLE J105 (LEDs, buzzer, buttons, I2C, coil)    ·    Cable 2: MIDDLE J106 ↔ BOTTOM J201 (power, I2C, SPI)'), after=4)
    h2(T('3.3  Chaîne d\'alimentation et choix techniques', '3.3  Power chain and design choices'))
    para(T('L\'énergie suit le chemin : **batterie 18650 → TP4056 → interrupteur → MT3608 (5,0 V) → diode Schottky → rail '
           '5V_SYS**. Le 3,3 V est fourni par le régulateur de la carte ESP32-S3.',
           'Energy follows the path: **18650 cell → TP4056 → switch → MT3608 (5.0 V) → Schottky diode → 5V_SYS rail**. '
           'The 3.3 V comes from the regulator of the ESP32-S3 board.'), size=10)
    table([T('Rail', 'Rail'), T('Tension', 'Voltage'), T('Alimente', 'Supplies')], [
        ['BAT+ / CHG_OUT+', T('3,0 à 4,2 V', '3.0 to 4.2 V'), T('Entrée de l\'élévateur MT3608 (via l\'interrupteur)', 'Input of the MT3608 boost (through the switch)')],
        ['5V_BOOST', T('5,0 V', '5.0 V'), T('Sortie de l\'élévateur, filtrée par 470 µF + 100 nF, envoyée par la nappe 2',
                                          'Boost output, filtered by 470 µF + 100 nF, sent over cable 2')],
        ['5V_SYS', T('≈ 4,7 V (batterie) / 5 V (USB)', '≈ 4.7 V (battery) / 5 V (USB)'),
         T('Broche 5V de l\'ESP32-S3, lecteur RDM6300, module microSD, option buzzer', 'ESP32-S3 5V pin, RDM6300 reader, microSD module, buzzer option')],
        ['3V3', T('3,3 V', '3.3 V'), T('Écran OLED, horloge DS3231, LED, buzzer (par défaut), logique de l\'ESP32',
                                     'OLED display, DS3231 clock, LEDs, buzzer (default), ESP32 logic')],
    ], [3.3, 4.5, 8.8], size=9, bold_first=True)
    spacer(4)
    bullets(T(['**Pourquoi 125 kHz ?** La fréquence de la carte n\'était pas documentée. Deux smartphones (iPhone avec NFC Tools, '
               'Android) n\'ont pas détecté la carte alors qu\'ils lisaient un passeport à 13,56 MHz : la carte est donc en basse '
               'fréquence (125 kHz), d\'où le choix du RDM6300.',
               '**Pourquoi l\'ESP32-S3 ?** Son port USB natif permet de présenter la microSD comme une clé USB au PC ; il offre '
               'assez de broches, de mémoire et de puissance. La carte de développement est montée sur supports plutôt que la puce '
               'seule, ce qui évite la conception délicate de l\'antenne, de la mémoire flash et du circuit de démarrage.',
               '**Diode Schottky** : quand l\'ESP32 est branché en USB (5 V), l\'USB alimente le système et la batterie ne peut pas '
               'refouler vers le PC ; dès que l\'USB est retiré, la batterie prend le relais sans coupure.',
               '**Attention** : sur le TP4056 protégé, la borne B− n\'est pas la masse (elle est derrière les transistors de '
               'protection) ; la masse du système est la sortie OUT−.'],
              ['**Why 125 kHz?** The card frequency was not documented. Two smartphones (iPhone with NFC Tools, Android) did not '
               'detect the card although they read a 13.56 MHz passport: the card is therefore low frequency (125 kHz), hence the '
               'RDM6300 reader.',
               '**Why the ESP32-S3?** Its native USB port lets the microSD appear as a USB drive on the PC; it has enough pins, '
               'memory and computing power. The development board is mounted on sockets instead of the bare chip, which avoids the '
               'tricky design of the antenna, the flash memory and the boot circuit.',
               '**Schottky diode**: when the ESP32 is plugged into USB (5 V), USB powers the system and the battery cannot push '
               'current back into the PC; as soon as USB is removed, the battery takes over without interruption.',
               '**Caution**: on the protected TP4056, the B− terminal is not ground (it sits behind the protection transistors); '
               'the system ground is the OUT− output.']), size=9.5)

    # ============================================================================================ 7: schematic (landscape)
    new_section(True)
    h1('4', T('Fonctionnement du système', 'How the system works'), new_page=False, size=14)
    h2(T('4.1  Schéma électrique complet du système', '4.1  Complete electrical schematic of the system'), before=0)
    picture(F('schema_circuit_complet'), height=13.0, after=1)
    caption(T('Figure 1 – Schéma électrique complet réalisé sous KiCad, dessiné comme un seul circuit (projet sas_complete). '
              'En haut : alimentation ; au centre : ESP32-S3 ; à droite : RFID, microSD, horloge et écran ; à gauche : LED, boutons et buzzer.',
              'Figure 1 – Complete electrical schematic drawn in KiCad as one circuit (project sas_complete). '
              'Top: power supply; centre: ESP32-S3; right: RFID, microSD, clock and display; left: LEDs, buttons and buzzer.'), after=2)
    para(T('**Lecture du schéma** : chaque liaison est un fil ; la carte ESP32-S3 et les modules sont représentés par des blocs dont les '
           'broches portent leur nom. GPIO1, 2, 5 → LED verte, rouge, bleue (220 Ω) ; GPIO42 → base du 2N2222A (1 kΩ) ; GPIO40/41 → boutons ; '
           'GPIO8/9 → SCL/SDA (OLED + DS3231) ; GPIO10 à 13 → microSD (SPI) ; GPIO18 ← TX du RDM6300.',
           '**Reading the schematic**: every connection is a wire; the ESP32-S3 board and the modules are drawn as blocks whose pins '
           'carry their names. GPIO1, 2, 5 → green, red, blue LED (220 Ω); GPIO42 → 2N2222A base (1 kΩ); GPIO40/41 → buttons; '
           'GPIO8/9 → SCL/SDA (OLED + DS3231); GPIO10 to 13 → microSD (SPI); GPIO18 ← RDM6300 TX.'), size=9, after=3)
    para(T('**Pourquoi trois cartes ?** Réalisé sur une seule carte, ce circuit donnerait un dispositif trop large pour être tenu '
           'facilement à la main à la porte de l\'amphithéâtre. Pour le rendre compact, il a été **réparti sur trois cartes de 95 × 60 mm '
           'superposées** (TOP, MIDDLE, BOTTOM, voir 3.2), reliées par deux nappes de 16 fils qui transportent les mêmes signaux. '
           'Le schéma découpé, avec ses connecteurs J1, J105, J106 et J201, est donné en **annexe A** ; les deux versions ont exactement '
           'les mêmes 29 équipotentielles, identiques à celles des trois circuits imprimés routés.',
           '**Why three boards?** Built on a single board, this circuit would make a device too wide to hold comfortably in one hand '
           'at the lecture-hall door. To keep it compact, it was **split over three stacked 95 × 60 mm boards** (TOP, MIDDLE, BOTTOM, '
           'see 3.2), joined by two 16-wire ribbon cables that carry the same signals. The split schematic, with its connectors J1, J105, '
           'J106 and J201, is given in **appendix A**; both versions have exactly the same 29 nets, identical to those of the three routed PCBs.'),
         size=9, after=0)

    # ============================================================================================ 8: block diagram (landscape)
    h2(T('4.2  Schéma synoptique', '4.2  Block diagram'), before=0, new_page=True)
    picture(F('schema_synoptique'), width=25.5, after=1)
    caption(T('Figure 2 – Schéma synoptique : les flèches indiquent le sens de circulation de l\'énergie et des données '
              '(double flèche = échange dans les deux sens)',
              'Figure 2 – Block diagram: the arrows show the direction in which energy and data flow (double arrow = both ways)'), after=4)
    t = doc.add_table(rows=1, cols=3)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell_margins(t, 60, 60, 120, 120)
    table_borders(t, 'FFFFFF', 4)
    cols = [(T('Bloc alimentation', 'Power supply block'), BLUE_L, T(
                ['La batterie 18650 est chargée par le TP4056 depuis une prise USB-C, qui la protège aussi.',
                 'L\'interrupteur met le système sous tension ; le MT3608 élève la tension à 5,0 V.',
                 'La diode Schottky forme le rail 5V_SYS et isole la batterie lorsque l\'ESP32 est branché au PC.'],
                ['The 18650 cell is charged by the TP4056 from a USB-C socket; the module also protects it.',
                 'The switch powers the system on; the MT3608 raises the voltage to 5.0 V.',
                 'The Schottky diode forms the 5V_SYS rail and isolates the battery when the ESP32 is plugged into the PC.'])),
            (T('Blocs acquisition et traitement', 'Acquisition and processing blocks'), CREAM, T(
                ['La bobine crée le champ 125 kHz qui alimente la puce de la carte ; le RDM6300 décode l\'identifiant et l\'envoie '
                 'par liaison série (UART, 9600 bauds).',
                 'L\'ESP32-S3 vérifie la trame, consulte la liste des étudiants, lit l\'heure du DS3231 (I2C) et prend les décisions.',
                 'Les boutons démarrent ou arrêtent la séance et affichent un bilan.'],
                ['The coil creates the 125 kHz field that powers the card chip; the RDM6300 decodes the identifier and sends it '
                 'over a serial link (UART, 9600 baud).',
                 'The ESP32-S3 checks the frame, looks up the student list, reads the time from the DS3231 (I2C) and decides.',
                 'The buttons start or stop the session and show a summary.'])),
            (T('Blocs stockage et interface', 'Storage and interface blocks'), BLUE_L, T(
                ['Chaque passage est ajouté à un fichier CSV sur la microSD (SPI) ; à la fin de la séance une liste triée par nom est créée.',
                 'LED, buzzer et écran OLED indiquent le résultat : présent, inconnu, doublon, erreur.',
                 'Branché au PC, le dispositif montre la microSD comme une clé USB ; le moniteur série permet aussi de régler l\'heure.'],
                ['Each tap is appended to a CSV file on the microSD (SPI); at the end of the session a list sorted by name is created.',
                 'LEDs, buzzer and OLED display show the result: present, unknown, duplicate, error.',
                 'Plugged into the PC, the device shows the microSD as a USB drive; the serial monitor can also set the clock.']))]
    for i, (title, fill, items) in enumerate(cols):
        cc = t.rows[0].cells[i]
        shade(cc._tc, fill)
        cc.width = Cm(8.6)
        p = cc.paragraphs[0]
        run(p, title, bold=True, size=10, color=BLUE_D)
        fmt(p, after=3)
        bullets(items, size=9, after=2, cont=cc, indent=0.4)

    # ============================================================================================ 9: main flowchart
    new_section(False)
    h2(T('4.3  Organigramme du programme principal', '4.3  Flowchart of the main program'), before=0)
    para(T('Le programme comporte deux parties : **setup()**, exécutée une seule fois à la mise sous tension pour initialiser les '
           'modules dans un ordre précis, puis **loop()**, répétée des milliers de fois par seconde. Aucune instruction ne bloque '
           'la boucle (pas d\'attente) : les boutons, le lecteur, les LED et la liaison PC restent toujours réactifs. Une anomalie '
           '(horloge non réglée, carte microSD absente) ne bloque pas le démarrage : elle est signalée et les séances sont refusées.',
           'The program has two parts: **setup()**, run once at power-on to initialise the modules in a fixed order, then '
           '**loop()**, repeated thousands of times per second. Nothing blocks the loop (no waiting): the buttons, the reader, '
           'the LEDs and the PC link always stay responsive. A fault (clock not set, microSD missing) does not stop the start-up: '
           'it is reported and sessions are refused.'), size=9.5, after=3)
    picture(F('organigramme_principal'), height=20.3, after=1)
    caption(T('Figure 3 – Organigramme du programme principal (setup puis boucle loop)',
              'Figure 3 – Flowchart of the main program (setup, then the loop)'), after=0)

    # ============================================================================================ 10: card + session flowcharts
    h2(T('4.4  Organigrammes de la lecture d\'une carte et des sessions', '4.4  Flowcharts of card reading and sessions'),
       before=0, new_page=True)
    t = doc.add_table(rows=1, cols=2)
    cell_margins(t, 0, 0, 60, 60)
    left, right = t.rows[0].cells
    left.width, right.width = Cm(8.6), Cm(8.0)
    p = left.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run().add_picture(F('organigramme_carte'), height=Cm(17.0))
    fmt(p, after=1, line=1.0)
    caption(T('Figure 4 – Traitement d\'une carte lue', 'Figure 4 – Processing a card that was read'), cont=left, after=0)
    p = right.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run().add_picture(F('organigramme_session'), width=Cm(7.9))
    fmt(p, after=1, line=1.0)
    caption(T('Figure 5 – Démarrage et arrêt d\'une séance', 'Figure 5 – Starting and stopping a session'), cont=right, after=6)
    para(T('Le RDM6300 envoie la même trame tant que la carte reste posée : un délai de 1,5 s évite de la compter plusieurs fois. '
           'Chaque trame de 14 octets est vérifiée (octets de début et de fin, somme de contrôle XOR) avant d\'être acceptée.',
           'The RDM6300 keeps sending the same frame while the card stays on it: a 1.5 s delay stops it from being counted several '
           'times. Each 14-byte frame is checked (start and end bytes, XOR checksum) before it is accepted.'),
         size=9, cont=right, after=5, align=WD_ALIGN_PARAGRAPH.LEFT)
    table([T('Événement', 'Event'), 'LED', 'Buzzer'], T([
        ['Démarrage correct', 'verte × 3', '3 bips'], ['Étudiant présent', 'verte', '1 bip court'],
        ['Carte inconnue', 'rouge', '1 bip long'], ['Doublon', 'rouge × 2', '2 bips'], ['Pas de séance', 'rouge × 2', '2 bips'],
        ['Début de séance', 'verte × 3', '3 bips'], ['Fin de séance', 'rouge × 2 (longs)', '2 bips longs'],
        ['Erreur (SD, horloge)', 'rouge × 3', '3 bips'], ['Système en marche', 'bleue : 2 éclats / 3 s', '—']], [
        ['Successful start-up', 'green × 3', '3 beeps'], ['Student present', 'green', '1 short beep'],
        ['Unknown card', 'red', '1 long beep'], ['Duplicate', 'red × 2', '2 beeps'], ['No session', 'red × 2', '2 beeps'],
        ['Session started', 'green × 3', '3 beeps'], ['Session ended', 'red × 2 (long)', '2 long beeps'],
        ['Error (SD, clock)', 'red × 3', '3 beeps'], ['System running', 'blue: 2 blinks / 3 s', '—']]),
        [3.3, 2.6, 2.0], size=8.5, cont=right, bold_first=True)
    fmt(right.add_paragraph(), after=4)
    para(T('Les fichiers produits : **/attendance/AAAAMMJJ_hhmmss.csv** (un passage par ligne : UID, nom, prénoms, matricule, date, '
           'heure, résultat) et **/final/…txt** (liste triée par nom, prête à coller dans Excel).',
           'Files produced: **/attendance/YYYYMMDD_hhmmss.csv** (one tap per line: UID, surname, first names, registration number, '
           'date, time, result) and **/final/…txt** (list sorted by name, ready to paste into Excel).'),
         size=9, cont=right, after=0, align=WD_ALIGN_PARAGRAPH.LEFT)

    # ============================================================================================ 11: PCB design
    h1('5', T('Réalisation et tests du système', 'Build and testing'))
    h2(T('5.1  Conception des circuits imprimés', '5.1  PCB design'), before=0)
    para(T('Après validation de chaque module sur plaque d\'essai (programmes de test D1 à D8 : liaison série, bus I2C, horloge, '
           'microSD, lecteur RFID, LED et buzzer, écran), les schémas ont été saisis sous **KiCad**. Les empreintes des modules ont '
           'été dessinées d\'après des relevés au pied à coulisse, puis contrôlées sur une impression 1:1 en y posant les modules réels. '
           'Le routage est fait sur **deux couches** (rouge : dessus, bleu : dessous), avec un plan de masse sur les deux faces.',
           'After each module had been validated on the breadboard (test programs D1 to D8: serial link, I2C bus, clock, microSD, '
           'RFID reader, LEDs and buzzer, display), the schematics were entered in **KiCad**. The module footprints were drawn '
           'from caliper measurements, then checked on a 1:1 printout by laying the real modules on it. Routing uses **two layers** '
           '(red: top, blue: bottom), with a ground plane on both sides.'), size=9.5)
    t = doc.add_table(rows=2, cols=2)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell_margins(t, 20, 20, 40, 40)
    for rr, cc_, name, lab in ((0, 0, 'top', T('Carte TOP : interface et bobine', 'TOP board: interface and coil')),
                               (0, 1, 'middle', T('Carte MIDDLE : ESP32-S3 et RDM6300', 'MIDDLE board: ESP32-S3 and RDM6300')),
                               (1, 0, 'bottom', T('Carte BOTTOM : énergie, microSD, horloge', 'BOTTOM board: power, microSD, clock'))):
        cc = t.rows[rr].cells[cc_]
        cc.width = Cm(8.3)
        p = cc.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.add_run().add_picture(os.path.join(FIG, f'pcb_{name}.png'), width=Cm(7.9))
        fmt(p, after=0, line=1.0)
        caption(lab, cont=cc, after=2)
    cc = t.rows[1].cells[1]
    cc.width = Cm(8.3)
    cp = cc.paragraphs[0]
    fmt(cp, after=2)
    run(cp, T('Règles de conception', 'Design rules'), bold=True, size=9.5, color=BLUE_D)
    bullets(T(['Isolement 0,3 mm ; pistes signal 0,3 mm, GND 0,4, 3V3 0,5, 5V_SYS 0,6, 5V_BOOST 0,8, batterie 1,0 mm.',
               'Vias 0,8 / 0,4 mm ; cuivre à plus de 0,55 mm du bord.',
               'Zone de la bobine RFID sans cuivre (x 8 à 54, y 22 à 57 mm) pour ne pas affaiblir le champ.',
               'Trous M3 aux mêmes coordonnées sur les trois cartes ; connecteurs des nappes alignés d\'une carte à l\'autre.'],
              ['Clearance 0.3 mm; tracks: signal 0.3 mm, GND 0.4, 3V3 0.5, 5V_SYS 0.6, 5V_BOOST 0.8, battery 1.0 mm.',
               'Vias 0.8 / 0.4 mm; copper more than 0.55 mm from the edge.',
               'No copper in the RFID coil area (x 8 to 54, y 22 to 57 mm) so the field is not weakened.',
               'M3 holes at the same coordinates on all three boards; ribbon connectors aligned from one board to the next.']),
            size=8.5, after=1, cont=cc, indent=0.4)
    caption(T('Figure 6 – Circuits imprimés routés (vue de dessus, d\'après les fichiers KiCad)',
              'Figure 6 – Routed printed circuit boards (top view, from the KiCad files)'), after=4)
    ok = T('Netlist conforme au schéma', 'Netlist matches the schematic')
    holes = T('trous', 'holes')
    table([T('Carte', 'Board'), 'Dimensions', T('Composants', 'Parts'), T('Segments de piste', 'Track segments'), 'Vias',
           T('Vérifications', 'Checks')], [
        ['TOP', '95 × 60 mm', f'20 + 4 {holes}', '245', '21', ok],
        ['MIDDLE', '95 × 60 mm', f'9 + 4 {holes}', '343', '45', ok],
        ['BOTTOM', '95 × 60 mm', f'9 + 4 {holes}', '180', '23', ok],
    ], [2.0, 2.4, 2.6, 3.0, 1.4, 5.2], size=8.5, bold_first=True)
    para(T('Les fichiers de fabrication (Gerber et perçage) des trois cartes ont été générés depuis KiCad pour la commande des circuits.',
           'The manufacturing files (Gerber and drill) of the three boards were generated from KiCad to order the PCBs.'),
         size=9, before=4, after=0)

    # ============================================================================================ 12: manufacturing + tests (blank)
    h2(T('5.2  Fabrication et assemblage', '5.2  Manufacturing and assembly'), before=0, new_page=True)
    para(T('À compléter après la réception des circuits imprimés : fabricant, délai, contrôle visuel, ordre de soudure, réglage du '
           'MT3608 à 5,0 V avant tout branchement, montage des trois cartes et des nappes.',
           'To be completed when the PCBs arrive: manufacturer, lead time, visual inspection, soldering order, setting the MT3608 '
           'to 5.0 V before connecting anything, assembly of the three boards and the cables.'), size=9.5, color=GRAY)
    t = doc.add_table(rows=1, cols=2)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell_margins(t, 0, 0, 50, 50)
    for i, txt in enumerate((T('Photo : circuits imprimés reçus (nus)', 'Photo: bare PCBs as received'),
                             T('Photo : cartes assemblées et empilées', 'Photo: assembled and stacked boards'))):
        cc = t.rows[0].cells[i]
        cc.width = Cm(8.3)
        placeholder(txt, 4.0, width=8.0, cont=cc)
        caption(T(f'Figure {7 + i} – à insérer', f'Figure {7 + i} – to be inserted'), cont=cc, after=0)
    spacer(4)
    placeholder(T('Texte à compléter : déroulement de l\'assemblage, problèmes rencontrés et corrections apportées.',
                  'Text to complete: how the assembly went, problems met and corrections made.'), 1.6)
    h2(T('5.3  Tests et validation', '5.3  Testing and validation'))
    table([T('N°', 'No.'), 'Test', T('Résultat attendu', 'Expected result'), T('Résultat obtenu', 'Result obtained'), T('Validé', 'Passed')], T([
        ['T1', 'Tensions à vide : 5V_BOOST, 5V_SYS, 3V3', '5,0 V / ≈ 4,7 V / 3,3 V', '', ''],
        ['T2', 'Lecture d\'une carte étudiant posée à plat', 'UID affiché, LED verte, bip', '', ''],
        ['T3', 'Même carte passée deux fois dans une séance', 'Comptée une seule fois (doublon)', '', ''],
        ['T4', 'Carte absente de students.csv', 'Enregistrée « UNKNOWN », LED rouge', '', ''],
        ['T5', 'Coupure d\'alimentation pendant une séance', 'Fichier intact, heure conservée', '', ''],
        ['T6', 'Branchement au PC', 'microSD visible comme clé USB', '', ''],
        ['T7', 'Séance complète (nombreux étudiants à la suite)', 'Aucun passage manqué', '', ''],
        ['T8', 'Autonomie sur batterie', 'Au moins une journée de cours', '', '']], [
        ['T1', 'No-load voltages: 5V_BOOST, 5V_SYS, 3V3', '5.0 V / ≈ 4.7 V / 3.3 V', '', ''],
        ['T2', 'Reading a student card laid flat', 'UID shown, green LED, beep', '', ''],
        ['T3', 'Same card tapped twice in one session', 'Counted only once (duplicate)', '', ''],
        ['T4', 'Card not in students.csv', 'Recorded as "UNKNOWN", red LED', '', ''],
        ['T5', 'Power cut during a session', 'File intact, time kept', '', ''],
        ['T6', 'Plugging into the PC', 'microSD visible as a USB drive', '', ''],
        ['T7', 'Full session (many students in a row)', 'No tap missed', '', ''],
        ['T8', 'Battery life', 'At least one day of lectures', '', '']]),
        [1.0, 5.4, 4.6, 3.8, 1.6], size=8.5, bold_first=True)
    spacer(4)
    placeholder(T('Mesures et observations à compléter (distance de lecture, temps de réponse, consommation, autonomie).',
                  'Measurements and observations to complete (read distance, response time, current draw, battery life).'), 1.8)
    spacer(3)
    placeholder(T('Photo : dispositif en fonctionnement (lecture d\'une carte)', 'Photo: device in use (reading a card)'), 3.0, width=10)

    # ============================================================================================ 13: conclusion
    h1('6', T('Conclusion générale et perspectives', 'General conclusion and outlook'))
    h2(T('Bilan des objectifs', 'Objectives achieved'), before=0)
    para(T('Ce mini-projet répondait à un besoin concret : remplacer la feuille de présence par un dispositif autonome qui utilise la '
           'carte étudiant existante. Le prototype, le programme et les trois circuits imprimés couvrent toutes les exigences '
           'indispensables du cahier des charges.',
           'This mini-project answered a real need: replacing the attendance sheet with a stand-alone device that uses the existing '
           'student card. The prototype, the program and the three PCBs cover every "Must" requirement of the specifications.'), size=10)
    placeholder(T('À compléter après les tests : exigences validées, résultats obtenus, écarts éventuels.',
                  'To complete after testing: requirements met, results obtained, any differences.'), 2.6)
    h2(T('Synthèse technique et apprentissages', 'Technical summary and what we learned'))
    para(T('Le système associe un ESP32-S3 programmé en C/C++ sous PlatformIO, un lecteur RFID 125 kHz, une horloge temps réel, une '
           'carte microSD, un écran OLED et une alimentation Li-ion complète (charge, protection, élévation de tension). Le projet a '
           'permis de mettre en œuvre les bus UART, I2C, SPI et USB, d\'écrire un programme non bloquant organisé en machines à états, '
           'de tester sur PC la partie logique (26 tests unitaires réussis) et de concevoir sous KiCad des schémas et des circuits '
           'imprimés double face vérifiés.',
           'The system combines an ESP32-S3 programmed in C/C++ with PlatformIO, a 125 kHz RFID reader, a real-time clock, a microSD '
           'card, an OLED display and a complete Li-ion power supply (charging, protection, boost). The project put the UART, I2C, SPI '
           'and USB buses into practice, produced a non-blocking program organised as state machines, tested the logic on a PC '
           '(26 unit tests passed) and led to checked schematics and double-sided PCBs designed in KiCad.'), size=10)
    h2(T('Difficultés rencontrées et solutions', 'Difficulties and solutions'))
    bullets(T(['**Fréquence de la carte inconnue** : identifiée par élimination avec deux smartphones NFC, puis confirmée par le lecteur.',
               '**Alimentation** : partage USB / batterie résolu par une diode Schottky ; la borne B− du TP4056 n\'est pas la masse.',
               '**Empreintes des modules** : dessinées à la main, puis vérifiées par impression 1:1 avant la commande.',
               '**Mode clé USB** : le PC et le programme ne doivent jamais écrire en même temps sur la microSD ; le programme cède la carte '
               'au PC et redémarre ensuite pour la relire proprement.'],
              ['**Unknown card frequency**: found by elimination with two NFC smartphones, then confirmed by the reader.',
               '**Power supply**: USB / battery sharing solved with a Schottky diode; the TP4056 B− terminal is not ground.',
               '**Module footprints**: drawn by hand, then checked on a 1:1 printout before ordering.',
               '**USB drive mode**: the PC and the program must never write to the microSD at the same time; the program hands the '
               'card to the PC and restarts afterwards to read it again cleanly.']), size=10)
    h2(T('Perspectives d\'évolution', 'Future improvements'))
    bullets(T(['Envoi automatique des présences par **Wi-Fi** vers un serveur ou l\'espace numérique de l\'établissement.',
               '**Application** web ou mobile pour consulter les listes et les statistiques d\'assiduité.',
               '**Boîtier** conçu sous FreeCAD et imprimé en 3D ; mesure et affichage du niveau de batterie.',
               'Lecteur **bi-fréquence** (125 kHz et 13,56 MHz) pour accepter d\'autres cartes.',
               '**Miniaturisation** : une seule carte avec le module ESP32-S3 soudé directement et des composants CMS.'],
              ['Automatic upload of attendance over **Wi-Fi** to a server or to the institution\'s online platform.',
               'Web or mobile **application** to browse the lists and attendance statistics.',
               '**Enclosure** designed in FreeCAD and 3D-printed; battery level measured and displayed.',
               '**Dual-frequency** reader (125 kHz and 13.56 MHz) to accept other cards.',
               '**Miniaturisation**: a single board with the ESP32-S3 module soldered directly and SMD components.']), size=10)
    spacer(6)
    box([T('En définitive, ce mini-projet nous a fait parcourir toute la chaîne de développement d\'un produit embarqué : '
           'de l\'expression du besoin au cahier des charges, du prototype sur plaque d\'essai au programme testé, puis des '
           'schémas aux circuits imprimés prêts à fabriquer. Nous espérons que ce dispositif pourra servir de base à un système '
           'de gestion de l\'assiduité utilisé à l\'échelle de l\'établissement.',
           'In the end, this mini-project took us through the whole development chain of an embedded product: from the need to '
           'the specifications, from the breadboard prototype to the tested program, then from the schematics to PCBs ready for '
           'manufacturing. We hope this device can become the basis of an attendance system used across the institution.')],
        size=10)

    # ============================================================================================ appendices (3 pages)
    new_section(True)
    h1('', T('Annexe A   Schéma électrique découpé en trois cartes', 'Appendix A   Schematic split into three boards'), new_page=False, size=14)
    picture(F('schema_electrique_complet'), height=14.6, after=1)
    caption(T('Le même circuit réparti sur les trois cartes (projet KiCad sas_full_system). En haut à gauche : MIDDLE ; en haut à droite : '
              'BOTTOM ; en bas à gauche : TOP. Les deux nappes (J105 ↔ J1 et J106 ↔ J201) sont dessinées fil par fil ; brochage en annexe B.',
              'The same circuit split over the three boards (KiCad project sas_full_system). Top left: MIDDLE; top right: BOTTOM; '
              'bottom left: TOP. Both ribbon cables (J105 ↔ J1 and J106 ↔ J201) are drawn wire by wire; pinout in appendix B.'), after=0)

    new_section(False)
    h1('', T('Annexe B   Brochage, nappes et fichiers', 'Appendix B   Pinout, cables and files'), new_page=False, size=14)
    h2(T('B.1  Broches utilisées sur l\'ESP32-S3', 'B.1  ESP32-S3 pins used'), before=0)
    table(['GPIO', T('Signal', 'Signal'), T('Relié à', 'Connected to'), 'Bus / ' + T('mode', 'mode')], [
        ['1 / 2 / 5', 'LED_GRN / LED_RED / LED_BLUE', T('LED verte, rouge, bleue via 220 Ω (carte TOP)', 'Green, red, blue LED via 220 Ω (TOP board)'), T('Sortie', 'Output')],
        ['42', 'BUZ', T('Base du 2N2222A via 1 kΩ (buzzer, carte TOP)', '2N2222A base via 1 kΩ (buzzer, TOP board)'), T('Sortie', 'Output')],
        ['40 / 41', 'BTN1 / BTN2', T('Boutons session / info, autre patte à la masse', 'Session / info buttons, other leg to ground'), T('Entrée pull-up', 'Input pull-up')],
        ['8 / 9', 'SCL / SDA', T('OLED 0x3C (TOP) et DS3231 0x68 (BOTTOM)', 'OLED 0x3C (TOP) and DS3231 0x68 (BOTTOM)'), 'I2C'],
        ['10 / 11 / 12 / 13', 'CS / SCK / MOSI / MISO', T('Module microSD (BOTTOM)', 'microSD module (BOTTOM)'), 'SPI'],
        ['18', 'RFID_RX', T('Sortie TX du RDM6300 (MIDDLE)', 'RDM6300 TX output (MIDDLE)'), 'UART1 9600'],
        ['5V / 3V3 / GND', T('Alimentation', 'Power'), T('5V_SYS (après diode), régulateur 3,3 V de la carte, masse', '5V_SYS (after the diode), board 3.3 V regulator, ground'), '—'],
    ], [3.0, 4.4, 7.0, 2.2], size=8.5, bold_first=True)
    h2(T('B.2  Brochage des nappes (même numéro de broche aux deux extrémités)',
         'B.2  Ribbon cable pinout (same pin number at both ends)'))
    t = doc.add_table(rows=1, cols=2)
    cell_margins(t, 0, 0, 40, 40)
    for k, (title, pins) in enumerate(((T('Nappe 1 : MIDDLE J105 ↔ TOP J1', 'Cable 1: MIDDLE J105 ↔ TOP J1'),
                                        ['3V3', 'GND', '5V_SYS', 'GPIO42', 'GPIO5', 'GPIO1', 'GPIO2', 'GND',
                                         'GPIO40', 'GPIO41', 'SCL', 'SDA', 'GND', 'COIL_A', 'COIL_B', 'GND']),
                                       (T('Nappe 2 : MIDDLE J106 ↔ BOTTOM J201', 'Cable 2: MIDDLE J106 ↔ BOTTOM J201'),
                                        ['5V_BOOST', 'GND', '5V_BOOST', 'GND', '5V_SYS', '3V3', 'GND', 'SDA',
                                         'SCL', 'GND', 'SD_CS', 'SD_SCK', 'GND', 'SD_MOSI', 'SD_MISO', 'GND']))):
        cc = t.rows[0].cells[k]
        p = cc.paragraphs[0]
        run(p, title, bold=True, size=9, color=GRAY_D)
        fmt(p, after=3)
        table([T('Broche', 'Pin'), 'Signal', T('Broche', 'Pin'), 'Signal'],
              [[str(i), pins[i - 1], str(i + 1), pins[i]] for i in range(1, 17, 2)], [1.65, 2.2, 1.65, 2.2], size=8.5, cont=cc)
    col_widths(t, [8.3, 8.3])
    h2(T('B.3  Fichiers sur la carte microSD', 'B.3  Files on the microSD card'))
    para(T('**/students.csv** (préparé par l\'enseignant) : une ligne par étudiant, UID,Nom,Prénoms,Matricule. '
           '**/attendance/AAAAMMJJ_hhmmss.csv** : un fichier par séance, une ligne par passage. '
           '**/final/…txt** : la liste finale de la séance, triée par nom, colonnes séparées par des tabulations (Excel).',
           '**/students.csv** (prepared by the lecturer): one line per student, UID,Surname,Names,ID number. '
           '**/attendance/YYYYMMDD_hhmmss.csv**: one file per session, one line per tap. '
           '**/final/…txt**: the final list of the session, sorted by name, tab-separated columns (Excel).'), size=9.5, after=4)
    for i, ln in enumerate(['# /students.csv', '0A00B2C3D4,BENALI,Amina,202131012345',
                            '# /attendance/20261125_101500.csv', 'uid,surname,names,matricule,date,time,result',
                            '0A00B2C3D4,BENALI,Amina,202131012345,2026-11-25,10:15:42,PRESENT',
                            '0A00FF1122,UNKNOWN,0A00FF1122,,2026-11-25,10:15:47,UNKNOWN',
                            '# end,2026-11-25,10:58:03,present=1,unknown=1']):
        p = doc.add_paragraph()
        run(p, ln, size=8, color=GRAY if ln.startswith('# /') else '2E3338', font=MONO)
        shade(p._p, CREAM)
        p.paragraph_format.left_indent = Cm(0.3)
        fmt(p, after=0, line=1.0)
    caption(T('Exemple (données fictives)', 'Example (made-up data)'), after=0)

    # ---- program excerpts (2 pages)
    h1('', T('Annexe C   Extraits du programme', 'Appendix C   Program excerpts'), new_page=True, size=14)
    para(T(f'Programme C/C++ (PlatformIO, Arduino), environ 1 500 lignes ; seuls les passages essentiels sont reproduits '
           f'(broches : tableau B.1). Code complet : **{REPO}** (dossier firmware/).',
           f'C/C++ program (PlatformIO, Arduino), about 1,500 lines; only the key parts are reproduced (pins: table B.1). '
           f'Full code: **{REPO}** (firmware/ folder).'), size=9, after=2)
    fw = os.path.join(ROOT, 'firmware')
    KEEP = [('PIN_RFID_RX =', "RDM6300 TX wire, 9600 baud"),
            ('OLED_ADDR =', 'try 0x3D if the screen is not found'),
            ('SAME_CARD_IGNORE_MS =', 'a card left on the reader is counted once'),
            ('if (alreadySeen(id))', 'already counted in this session'),
            ('seen.push_back(id)', 'a second tap will be a duplicate'),
            ('const StudentRec* st = findStudent', 'look the card up in students.csv'),
            ('btnSession.poll(', 'button 1: short = start, long (1.5 s) = stop'),
            ('btnInfo.poll(', 'button 2: short = info, long (3 s) = USB drive'),
            ('if (rdm.feed(b, uid))', 'true when a full, valid 14-byte frame arrived'),
            ('if (id == lastUid && now - lastSeenMs', 'same card still on the reader'),
            ('if (driveMode) continue;', 'the SD card belongs to the PC')]

    def extract(rel, start, end=None, first=None, last=None):
        lines = open(os.path.join(fw, rel), encoding='utf-8').read().split('\n')
        a = next(i for i, l in enumerate(lines) if l.startswith(start)) if start else 0
        b = next(i for i in range(a + 1, len(lines)) if lines[i].startswith(end)) if end else len(lines) - 1
        return a + 1, [x for x in (clean(l) for l in lines[a:b + 1]) if x is not None]

    def code_part(s):
        """The text before a // comment that is not inside a string."""
        q = False
        for k in range(len(s) - 1):
            if s[k] == '"' and (k == 0 or s[k - 1] != '\\'):
                q = not q
            if not q and s[k:k + 2] == '//':
                return s[:k]
        return s

    def clean(line):
        """Removes the explanatory comments; keeps section titles and the few comments needed to follow the logic."""
        s = line.replace('\t', '    ').rstrip()
        body = code_part(s).rstrip()
        if not body.strip():                                   # comment-only line
            c = s.strip()
            if c.startswith('// ----') or c.startswith('// ===='):
                return re.sub(r'[-=]{3,}', '', c).replace('//', '//').rstrip() .replace('  ', ' ').strip()
            return None if c else ''
        for key, note in KEEP:
            if key in body:
                return body + '   // ' + note
        return body

    def code(title, rel, start, end):
        h2(title, before=3)
        n0, lines = extract(rel, start, end)
        for i, ln in enumerate(x for x in lines if x.strip()):
            p = doc.add_paragraph()
            run(p, ln, size=6.4, color='2E3338', font=MONO)
            shade(p._p, CREAM if i % 2 else 'FFFFFF')
            p.paragraph_format.left_indent = Cm(0.7)
            p.paragraph_format.first_line_indent = Cm(-0.4)
            fmt(p, after=0, line=Pt(7.2))

    code(T('C.1  src/main.cpp : traitement d\'une carte (handleTap)', 'C.1  src/main.cpp: processing a card (handleTap)'),
         'src/main.cpp', 'void handleTap(', '}')
    code(T('C.2  src/main.cpp : boucle principale (loop)', 'C.2  src/main.cpp: main loop'),
         'src/main.cpp', 'void loop() {', '}')

    fix_grids(doc.tables)
    doc.core_properties.title = T('Smart Attendance System – Rapport de mini-projet', 'Smart Attendance System – Mini-project report')
    doc.core_properties.author = 'Evidence Tsongodza'
    doc.core_properties.language = T('fr-FR', 'en-GB')
    out = os.path.join(BASE, f'Rapport_Smart_Attendance_System_{lang.upper()}.docx' if lang == 'fr'
                       else 'Report_Smart_Attendance_System_EN.docx')
    doc.save(out)
    print('written', out)


if __name__ == '__main__':
    for lang in ('fr', 'en'):
        build(lang)

#!/usr/bin/env python3
"""Block diagram (schéma synoptique) and flowcharts (organigrammes) of the report, drawn with Graphviz (dot).
Theme: gray, light blue, light cream.   Run:  python3 fig_diagrams.py
"""
import os, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'figures')
GRAY_D, GRAY, GRAY_L = '#4A5560', '#8C969F', '#E4E7EA'
BLUE_L, BLUE, BLUE_D = '#D4E6F6', '#6FA8DC', '#2F78BD'
CREAM, CREAM_D = '#EEF1F4', '#AEB8C2'   # light gray (the theme is blue + gray only)
FONT = 'Liberation Sans'


EN = [  # French label -> English label, applied to the dot source for the English figures (longest first)
    ('Même carte\\nil y a moins\\nde 1,5 s ?', 'Same card\\nless than\\n1.5 s ago?'),
    ("DS3231\\nprésent et\\nà l'heure ?", 'DS3231\\nfound and\\ntime valid?'),
    ('Horloge et\\nSD prêtes ?', 'Clock and\\nSD ready?'),
    ('Session\\nen cours ?', 'Session\\nrunning?'),
    ('Carte déjà\\nlue dans cette\\nsession ?', 'Card already\\nread in this\\nsession?'),
    ('Carte microSD\\nmontée ?', 'microSD card\\nmounted?'),
    ('Écriture\\nréussie ?', 'Write\\nsucceeded?'),
    ('Horloge et\\nSD OK ?', 'Clock and\\nSD OK?'),
    ('Diode Schottky\\n1N5819', 'Schottky diode\\n1N5819'),
    ('Bouton 1 ?', 'Button 1?'), ('Bouton 2 ?', 'Button 2?'),
    ('Étudiant\\nconnu ?', 'Known\\nstudent?'),
    ('Trame RFID\\nvalide ?', 'Valid RFID\\nframe?'),
    ("PC branché\\nsur l'USB ?", 'PC plugged\\ninto USB?'),
    ('Créer le fichier de session\\n(en-tête CSV)', 'Create the session file\\n(CSV header)'),
    ('Écrire la liste finale triée\\npar nom dans /final (.txt)', 'Write the final list sorted\\nby name in /final (.txt)'),
    ('Écrire la ligne de bilan\\n(présents, inconnus)', 'Write the summary line\\n(present, unknown)'),
    ('Ajouter une ligne au fichier\\n/attendance/AAAAMMJJ_hhmmss.csv', 'Append a line to the file\\n/attendance/YYYYMMDD_hhmmss.csv'),
    ('2 boutons poussoirs\\nsession / info (TOP)', '2 push buttons\\nsession / info (TOP)'),
    ('3 LED\\nverte / rouge / bleue', '3 LEDs\\ngreen / red / blue'),
    ('ALIMENTATION (carte BOTTOM)', 'POWER SUPPLY (BOTTOM board)'),
    ('Antenne / bobine\\n35 x 46 mm (TOP)', 'Antenna coil\\n35 x 46 mm (TOP)'),
    ('Batterie Li-ion\\n18650 (3,7 V)', 'Li-ion battery\\n18650 (3.7 V)'),
    ('Carte étudiant\\nRFID 125 kHz', 'Student card\\nRFID 125 kHz'),
    ('Carte microSD\\nfichiers CSV (BOTTOM)', 'microSD card\\nCSV files (BOTTOM)'),
    ('label=" champ 125 kHz"', 'label=" 125 kHz field"'),
    ('label=" charge"', 'label=" charging"'),
    ('Chargeur TP4056\\n(USB-C + protection)', 'TP4056 charger\\n(USB-C + protection)'),
    ('Écran OLED 0,96', 'OLED display 0.96'),
    ('Élévateur MT3608\\n(réglé à 5,0 V)', 'MT3608 boost\\n(set to 5.0 V)'),
    ('microcontrôleur\\n(carte MIDDLE)', 'microcontroller\\n(MIDDLE board)'),
    ('Horloge temps réel\\nDS3231 (BOTTOM)', 'Real-time clock\\nDS3231 (BOTTOM)'),
    ('Interrupteur\\nmarche / arrêt', 'On / off\\nswitch'),
    ('Lecteur RDM6300\\n125 kHz (MIDDLE)', 'RDM6300 reader\\n125 kHz (MIDDLE)'),
    ("PC de l'enseignant\\n(clé USB / moniteur série)", "Lecturer's PC\\n(USB drive / serial monitor)"),
    ('Prise USB-C\\n(recharge)', 'USB-C socket\\n(charging)'),
    ('STOCKAGE ET INTERFACE', 'STORAGE AND INTERFACE'),
    ('UART 9600 bauds', 'UART 9600 baud'), ('USB-C natif', 'native USB-C'),
    ('Retour à la boucle', 'Back to the loop'),
    ('Bouton 1 : appui court', 'Button 1: short press'), ('Bouton 1 : appui long', 'Button 1: long press'),
    ('Début (mise sous tension)', 'Start (power on)'),
    ('Trame RFID valide reçue (UID)', 'Valid RFID frame received (UID)'),
    ('Court : démarrer la session\\nLong (1,5 s) : arrêter la session\\n+ liste finale triée',
     'Short: start the session\\nLong (1.5 s): stop the session\\n+ sorted final list'),
    ('Court : afficher heure + bilan\\nLong (3 s) : mode clé USB', 'Short: show time + summary\\nLong (3 s): USB drive mode'),
    ('Traiter la carte\\n(organigramme 2)', 'Process the card\\n(flowchart 2)'),
    ('Mode clé USB :\\nla microSD est vue par le PC', 'USB drive mode:\\nthe PC sees the microSD'),
    ('Vider la liste des cartes lues\\nCompteurs à zéro\\nBips « session démarrée »', 'Clear the list of cards read\\nReset the counters\\n“Session started” beeps'),
    ('Bips de démarrage\\n(LED verte)', 'Start-up beeps\\n(green LED)'),
    ("Motif d'erreur\\n(LED rouge)", 'Error pattern\\n(red LED)'),
    ('Bips « session terminée »', '“Session ended” beeps'),
    ('rtcOk = faux\\n(sessions refusées)', 'rtcOk = false\\n(sessions refused)'),
    ('sdOk = faux\\n(pas de session)', 'sdOk = false\\n(no session)'),
    ("Chercher l'UID dans la liste\\n(students.csv)", 'Look the UID up in the list\\n(students.csv)'),
    ("Lire la date et l'heure\\n(DS3231)", 'Read the date and time\\n(DS3231)'),
    ('Configurer les broches\\nLED, buzzer, boutons', 'Configure the pins\\nLEDs, buzzer, buttons'),
    ('Démarrer le bus I2C\\n(SDA GPIO9, SCL GPIO8)', 'Start the I2C bus\\n(SDA GPIO9, SCL GPIO8)'),
    ("Chercher l'écran OLED\\n(0x3C puis 0x3D)", 'Look for the OLED\\n(0x3C then 0x3D)'),
    ('Charger students.csv\\nen mémoire', 'Load students.csv\\ninto memory'),
    ('UART1 lecteur RFID\\n9600 bauds, RX GPIO18\\nPréparer la clé USB', 'UART1 RFID reader\\n9600 baud, RX GPIO18\\nPrepare the USB drive'),
    ("PRÉSENT : LED verte + 1 bip\\nNom + matricule sur l'OLED", 'PRESENT: green LED + 1 beep\\nName + ID number on the OLED'),
    ("INCONNU : LED rouge + bip long\\nUID affiché sur l'OLED", 'UNKNOWN: red LED + long beep\\nUID shown on the OLED'),
    ('BOUCLE loop()\\n(sans attente bloquante)', 'MAIN LOOP loop()\\n(never blocks)'),
    ('Mettre à jour LED, buzzer\\net LED de vie (2 éclats / 3 s)', 'Update LEDs, buzzer\\nand heartbeat LED (2 blinks / 3 s)'),
    ("Commandes série (HELP, SETTIME…)\\nRafraîchir l'écran OLED", 'Serial commands (HELP, SETTIME…)\\nRefresh the OLED'),
    ('Ignorer\\n(carte encore posée)', 'Ignore\\n(card still on the reader)'),
    ('LED rouge + 2 bips\\n« pas de session »', 'Red LED + 2 beeps\\n“no session”'),
    ("Motif d'erreur\\nsession refusée", 'Error pattern\\nsession refused'),
    ("Double éclat rouge\\n« doublon », rien n'est écrit", 'Double red blink\\n“duplicate”, nothing written'),
    ("Motif d'erreur\\n(SD hors service)", 'Error pattern\\n(SD failed)'),
    ('xlabel=" non"', 'xlabel=" no"'), ('xlabel="non "', 'xlabel="no "'), ('xlabel=" oui"', 'xlabel=" yes"'),
    ('xlabel="  répéter  "', 'xlabel="  repeat  "'),
]


def render(name, dot, dpi=220):
    for lang in ('fr', 'en'):
        src_text = dot
        if lang == 'en':
            for a, b in EN:
                src_text = src_text.replace(a, b)
        out = name + ('_en' if lang == 'en' else '')
        src = os.path.join(OUT, out + '.dot')
        open(src, 'w').write(src_text)
        subprocess.run(['dot', '-Tpng', f'-Gdpi={dpi}', src, '-o', os.path.join(OUT, out + '.png')], check=True)
        os.remove(src)
        print('written', out + '.png')


HEAD = f'''  graph [fontname="{FONT}", bgcolor="white", pad=0.25, nodesep=0.35, ranksep=0.42, splines=ortho];
  node  [fontname="{FONT}", fontsize=11, color="{GRAY}", penwidth=1.2, style="filled,rounded", shape=box, fillcolor="{BLUE_L}", fontcolor="{GRAY_D}", margin="0.15,0.07"];
  edge  [fontname="{FONT}", fontsize=9, color="{GRAY_D}", penwidth=1.1, arrowsize=0.7, fontcolor="{BLUE_D}"];
'''


def synoptique():
    dot = 'digraph G {\n' + HEAD.replace('splines=ortho', 'splines=spline') + f'''
  rankdir=LR; newrank=true;
  node [width=1.9];
  subgraph cluster_alim {{ label="ALIMENTATION (carte BOTTOM)"; fontname="{FONT}"; fontsize=11; fontcolor="{GRAY_D}";
     style="rounded,filled"; fillcolor="{CREAM}"; color="{CREAM_D}";
     bat [label="Batterie Li-ion\\n18650 (3,7 V)"];
     chg [label="Chargeur TP4056\\n(USB-C + protection)"];
     sw  [label="Interrupteur\\nmarche / arrêt"];
     boost [label="Élévateur MT3608\\n(réglé à 5,0 V)"];
     usbc [label="Prise USB-C\\n(recharge)", fillcolor="{GRAY_L}"];
  }}
  subgraph cluster_in {{ label="ACQUISITION"; fontname="{FONT}"; fontsize=11; fontcolor="{GRAY_D}";
     style="rounded,filled"; fillcolor="{CREAM}"; color="{CREAM_D}";
     card [label="Carte étudiant\\nRFID 125 kHz", shape=box, style="filled,rounded,dashed", fillcolor="white"];
     coil [label="Antenne / bobine\\n35 x 46 mm (TOP)"];
     rdm  [label="Lecteur RDM6300\\n125 kHz (MIDDLE)"];
     btn  [label="2 boutons poussoirs\\nsession / info (TOP)"];
     rtc  [label="Horloge temps réel\\nDS3231 (BOTTOM)"];
  }}
  mcu [label="ESP32-S3 N16R8\\nmicrocontrôleur\\n(carte MIDDLE)", fillcolor="{BLUE}", fontcolor="white", color="{BLUE_D}", fontsize=13, width=2.2, height=1.3];
  diode [label="Diode Schottky\\n1N5819 → 5V_SYS", fillcolor="{GRAY_L}"];
  subgraph cluster_out {{ label="STOCKAGE ET INTERFACE"; fontname="{FONT}"; fontsize=11; fontcolor="{GRAY_D}";
     style="rounded,filled"; fillcolor="{CREAM}"; color="{CREAM_D}";
     sd   [label="Carte microSD\\nfichiers CSV (BOTTOM)"];
     oled [label="Écran OLED 0,96\\"\\nSSD1306 (TOP)"];
     led  [label="3 LED\\nverte / rouge / bleue"];
     buz  [label="Buzzer + transistor\\n2N2222A (TOP)"];
  }}
  pc [label="PC de l'enseignant\\n(clé USB / moniteur série)", fillcolor="{GRAY_L}"];

  usbc -> chg [label=" 5 V"];
  bat -> chg [dir=both, label=" charge"];
  chg -> sw -> boost;
  boost -> diode [label=" 5V_BOOST"];
  diode -> mcu [label=" 5V_SYS", color="{BLUE_D}", penwidth=1.6];
  card -> coil [label=" champ 125 kHz", style=dashed, dir=both];
  coil -> rdm;
  rdm -> mcu [label=" UART 9600 bauds"];
  btn -> mcu [label=" GPIO40 / 41"];
  rtc -> mcu [dir=both, label=" I2C"];
  mcu -> sd [dir=both, label=" SPI"];
  mcu -> oled [label=" I2C"];
  mcu -> led [label=" GPIO1 / 2 / 5"];
  mcu -> buz [label=" GPIO42"];
  mcu -> pc [dir=both, label=" USB-C natif"];
  {{rank=same; mcu; diode;}}
}}
'''
    render('schema_synoptique', dot)


def start(n, t):
    return f'  {n} [label="{t}", shape=box, style="filled,rounded", fillcolor="{GRAY_D}", fontcolor="white", color="{GRAY_D}", width=1.6];\n'


def step(n, t, c=None):
    return f'  {n} [label="{t}"' + (f', fillcolor="{c}"' if c else '') + '];\n'


def ask(n, t):
    return f'  {n} [label="{t}", shape=diamond, style="filled", fillcolor="{CREAM}", color="{CREAM_D}", penwidth=1.6, margin="0.04,0.02", fontsize=10];\n'


def io(n, t):
    return f'  {n} [label="{t}", shape=parallelogram, style="filled", fillcolor="{GRAY_L}", margin="0.05,0.05"];\n'


def org_principal():
    d = 'digraph G {\n' + HEAD + '  rankdir=TB;\n'
    d += start('S', 'Début (mise sous tension)')
    d += step('I1', 'Configurer les broches\\nLED, buzzer, boutons')
    d += step('I2', 'Démarrer le bus I2C\\n(SDA GPIO9, SCL GPIO8)')
    d += ask('Q1', 'DS3231\\nprésent et\\nà l\'heure ?')
    d += step('E1', 'rtcOk = faux\\n(sessions refusées)', GRAY_L)
    d += step('I3', 'Chercher l\'écran OLED\\n(0x3C puis 0x3D)')
    d += ask('Q2', 'Carte microSD\\nmontée ?')
    d += step('I4', 'Charger students.csv\\nen mémoire')
    d += step('E2', 'sdOk = faux\\n(pas de session)', GRAY_L)
    d += step('I5', 'UART1 lecteur RFID\\n9600 bauds, RX GPIO18\\nPréparer la clé USB')
    d += ask('Q3', 'Horloge et\\nSD OK ?')
    d += step('B1', 'Bips de démarrage\\n(LED verte)')
    d += step('B2', 'Motif d\'erreur\\n(LED rouge)', GRAY_L)
    d += step('L0', 'BOUCLE loop()\\n(sans attente bloquante)', BLUE)
    d += step('L1', 'Mettre à jour LED, buzzer\\net LED de vie (2 éclats / 3 s)')
    d += ask('Q4', 'Bouton 1 ?')
    d += step('A1', 'Court : démarrer la session\\nLong (1,5 s) : arrêter la session\\n+ liste finale triée')
    d += ask('Q5', 'Bouton 2 ?')
    d += step('A2', 'Court : afficher heure + bilan\\nLong (3 s) : mode clé USB')
    d += ask('Q6', 'Trame RFID\\nvalide ?')
    d += step('A3', 'Traiter la carte\\n(organigramme 2)', CREAM)
    d += ask('Q7', 'PC branché\\nsur l\'USB ?')
    d += step('A4', 'Mode clé USB :\\nla microSD est vue par le PC')
    d += step('L2', 'Commandes série (HELP, SETTIME…)\\nRafraîchir l\'écran OLED')
    d += '''
  S -> I1 -> I2 -> Q1;
  Q1 -> E1 [xlabel="non "];
  Q1 -> I3 [xlabel=" oui"];
  E1 -> I3;
  I3 -> Q2;
  Q2 -> I4 [xlabel=" oui"];
  Q2 -> E2 [xlabel="non "];
  I4 -> I5; E2 -> I5;
  I5 -> Q3;
  Q3 -> B1 [xlabel=" oui"];
  Q3 -> B2 [xlabel="non "];
  B1 -> L0; B2 -> L0;
  L0 -> L1 -> Q4;
  Q4 -> A1 [xlabel=" oui"];
  Q4 -> Q5 [xlabel=" non"];
  A1 -> Q5;
  Q5 -> A2 [xlabel=" oui"];
  Q5 -> Q6 [xlabel=" non"];
  A2 -> Q6;
  Q6 -> A3 [xlabel=" oui"];
  Q6 -> Q7 [xlabel=" non"];
  A3 -> Q7;
  Q7 -> A4 [xlabel=" oui"];
  Q7 -> L2 [xlabel=" non"];
  A4 -> L2;
  S [group=m]; I1 [group=m]; I2 [group=m]; Q1 [group=m]; I3 [group=m]; Q2 [group=m]; I4 [group=m]; I5 [group=m];
  Q3 [group=m]; L0 [group=m]; L1 [group=m]; Q4 [group=m]; Q5 [group=m]; Q6 [group=m]; Q7 [group=m]; L2 [group=m];
  L2:w -> L0:w [constraint=false, xlabel="  répéter  ", color="''' + BLUE_D + '''", penwidth=1.5];
  {rank=same; Q1; E1;} {rank=same; Q2; E2;} {rank=same; B1; B2;}
  {rank=same; Q4; A1;} {rank=same; Q5; A2;} {rank=same; Q6; A3;} {rank=same; Q7; A4;}
}
'''
    render('organigramme_principal', d)


def org_carte():
    d = 'digraph G {\n' + HEAD + '  rankdir=TB;\n'
    d += start('S', 'Trame RFID valide reçue (UID)')
    d += ask('Q0', 'Même carte\\nil y a moins\\nde 1,5 s ?')
    d += step('X0', 'Ignorer\\n(carte encore posée)', GRAY_L)
    d += ask('Q1', 'Session\\nen cours ?')
    d += step('X1', 'LED rouge + 2 bips\\n« pas de session »', GRAY_L)
    d += ask('Q2', 'Carte déjà\\nlue dans cette\\nsession ?')
    d += step('X2', 'Double éclat rouge\\n« doublon », rien n\'est écrit', GRAY_L)
    d += step('F1', 'Chercher l\'UID dans la liste\\n(students.csv)')
    d += step('F2', 'Lire la date et l\'heure\\n(DS3231)')
    d += io('W', 'Ajouter une ligne au fichier\\n/attendance/AAAAMMJJ_hhmmss.csv')
    d += ask('Q3', 'Écriture\\nréussie ?')
    d += step('X3', 'Motif d\'erreur\\n(SD hors service)', GRAY_L)
    d += ask('Q4', 'Étudiant\\nconnu ?')
    d += step('K1', 'PRÉSENT : LED verte + 1 bip\\nNom + matricule sur l\'OLED', BLUE)
    d += step('K2', 'INCONNU : LED rouge + bip long\\nUID affiché sur l\'OLED', GRAY_L)
    d += start('E', 'Retour à la boucle')
    d += '''
  S [group=m]; Q0 [group=m]; Q1 [group=m]; Q2 [group=m]; F1 [group=m]; F2 [group=m]; W [group=m]; Q3 [group=m]; Q4 [group=m]; E [group=m];
  S -> Q0;
  Q0 -> X0 [xlabel=" oui"];
  Q0 -> Q1 [xlabel=" non"];
  Q1 -> X1 [xlabel=" non"];
  Q1 -> Q2 [xlabel=" oui"];
  Q2 -> X2 [xlabel=" oui"];
  Q2 -> F1 [xlabel=" non"];
  F1 -> F2 -> W -> Q3;
  Q3 -> X3 [xlabel=" non"];
  Q3 -> Q4 [xlabel=" oui"];
  Q4 -> K1 [xlabel=" oui"];
  Q4 -> K2 [xlabel=" non"];
  K1 -> E; K2 -> E;
  {rank=same; Q0; X0;} {rank=same; Q1; X1;} {rank=same; Q2; X2;} {rank=same; Q3; X3;} {rank=same; K1; K2;}
}
'''
    render('organigramme_carte', d)

    d = 'digraph G {\n' + HEAD + '  rankdir=TB;\n'
    d += start('S', 'Bouton 1 : appui court')
    d += ask('Q1', 'Horloge et\\nSD prêtes ?')
    d += step('X1', 'Motif d\'erreur\\nsession refusée', GRAY_L)
    d += io('C', 'Créer le fichier de session\\n(en-tête CSV)')
    d += step('A', 'Vider la liste des cartes lues\\nCompteurs à zéro\\nBips « session démarrée »')
    d += start('T', 'Bouton 1 : appui long')
    d += io('R', 'Écrire la ligne de bilan\\n(présents, inconnus)')
    d += io('F', 'Écrire la liste finale triée\\npar nom dans /final (.txt)')
    d += step('B', 'Bips « session terminée »')
    d += '''
  S -> Q1;
  Q1 -> X1 [xlabel=" non"];
  Q1 -> C [xlabel=" oui"];
  C -> A;
  T -> R -> F -> B;
  {rank=same; Q1; X1;}
  {rank=same; S; T;}
}
'''
    render('organigramme_session', d)


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    synoptique()
    org_principal()
    org_carte()

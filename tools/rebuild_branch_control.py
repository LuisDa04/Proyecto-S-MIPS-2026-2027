"""Reconstruye Branch_Control: colocar -> descubrir puertos -> cablear por redes.

FASE 1: coloca los componentes (sin cables) y los guarda.
FASE 2: corre Ports.java (headless) para obtener las coordenadas REALES de
         cada puerto. Sin esto se inventan coordenadas y se crean bucles.
FASE 3: genera los cables y tuneles correctos y valida que no cuelgue.

Diseno (docs/diseno.md 8.4):
    EQ  = (A == B)                        Comparator 32 bits
    BEQ = EQ     AND BRANCH_TYPE==01      Comparator 2 bits vs constante 1
    BNE = NOT EQ AND BRANCH_TYPE==10      Comparator 2 bits vs constante 2
    PC_WRITE_BRANCH = BRANCH_ENABLE AND (BEQ OR BNE)

BRANCH_TYPE se decodifica con dos comparadores contra constantes en vez de
un Decoder: no depende del orden de bits ni del pin Enable, y el Decoder
dejaba las salidas indefinidas (U).

Componentes: 3 Comparator, 1 NOT, 3 AND, 1 OR, 2 Constant = 10.
"""
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JAR = r'C:\Program Files\logisim-evolution\app\logisim-evolution-5.0.0-all.jar'
PORTS = ROOT / 'tools' / 'Ports.java'
BASE = ROOT / 'circuit' / 'smips.circ'
TMP = Path.home() / 'AppData' / 'Local' / 'Temp' / 'opencode' / 'bc'
TMP.mkdir(parents=True, exist_ok=True)

POS = {
    'cmp_eq':   (300, 130),
    'cmp_beq':  (300, 300),
    'cmp_bne':  (300, 430),
    'not':      (560, 130),
    'and_beq':  (760, 180),
    'and_bne':  (760, 400),
    'or':       (980, 280),
    'and_fin':  (1180, 280),
    'const_beq': (150, 300),
    'const_bne': (150, 430),
}

GRID = 10


def fase1_colocar():
    tree = ET.parse(BASE)
    root = tree.getroot()
    bc = [c for c in root.findall('./circuit') if c.get('name') == 'Branch_Control'][0]

    for w in list(bc.findall('./wire')):
        bc.remove(w)
    for comp in list(bc.findall('./comp')):
        if comp.get('name') != 'Pin':
            bc.remove(comp)

    def add(name, lib, attrs, pos):
        x, y = pos
        c = ET.SubElement(bc, 'comp', {'name': name, 'loc': f'({x},{y})', 'lib': lib})
        for k, v in attrs.items():
            ET.SubElement(c, 'a', {'name': k, 'val': v})

    add('Comparator', '3', {'width': '32'}, POS['cmp_eq'])
    add('Comparator', '3', {'width': '2'}, POS['cmp_beq'])
    add('Comparator', '3', {'width': '2'}, POS['cmp_bne'])
    add('NOT Gate', '1', {'size': '20'}, POS['not'])
    add('AND Gate', '1', {'size': '30'}, POS['and_beq'])
    add('AND Gate', '1', {'size': '30'}, POS['and_bne'])
    add('OR Gate', '1', {'size': '30'}, POS['or'])
    add('AND Gate', '1', {'size': '30'}, POS['and_fin'])
    add('Constant', '0', {'value': '0x1', 'width': '2'}, POS['const_beq'])
    add('Constant', '0', {'value': '0x2', 'width': '2'}, POS['const_bne'])

    ET.ElementTree(root).write(BASE, encoding='UTF-8', xml_declaration=True)
    print('FASE 1: 10 componentes colocados (3 Comparator, NOT, 3 AND, OR, 2 Constant)')


def fase2_descubrir():
    tree = ET.parse(BASE)
    root = tree.getroot()
    for circ in list(root.findall('./circuit')):
        if circ.get('name') != 'Branch_Control':
            root.remove(circ)
    main = root.find('./main')
    if main is not None:
        main.set('name', 'Branch_Control')
    stage = TMP / 'stage.circ'
    ET.ElementTree(root).write(stage, encoding='UTF-8', xml_declaration=True)

    orden = ['java', '-Djava.awt.headless=true',
             f'-Djava.util.prefs.userRoot={TMP}/prefs',
             '--class-path', JAR, str(PORTS), str(stage)]
    try:
        r = subprocess.run(orden, capture_output=True, text=True, timeout=40)
    except subprocess.TimeoutExpired:
        sys.exit('TIMEOUT en fase 2: el circuito cuelga')
    if r.returncode:
        sys.exit(f'ERROR en fase 2:\n{r.stderr[:1500]}')

    ports = []
    for linea in r.stdout.splitlines():
        if not linea.strip():
            continue
        f = linea.split('\t')
        if len(f) != 9:
            continue
        x, y = map(int, f[5].split(','))
        bx, by, bw, bh = map(int, f[8].split(','))
        ports.append({'kind': f[1], 'loc': f[2], 'index': int(f[3]), 'tip': f[4],
                      'x': x, 'y': y, 'width': int(f[6]), 'type': int(f[7]),
                      'box': (bx, by, bw, bh)})
    print(f'FASE 2: {len(ports)} puertos descubiertos')
    return ports


def L(nombre):
    x, y = POS[nombre]
    return f'({x},{y})'


def fase3_cablear(ports):
    tree = ET.parse(BASE)
    root = tree.getroot()
    bc = [c for c in root.findall('./circuit') if c.get('name') == 'Branch_Control'][0]

    def by_loc(kind, loc):
        return [p for p in ports if p['kind'] == kind and p['loc'] == loc]

    def pin_by_label(label):
        for p in ports:
            if p['kind'] == 'Pin' and p['tip'] == label:
                return p
        raise SystemExit(f'Pin {label} no encontrado')

    def comp_port(kind, loc, index=None, ptype=None):
        cands = by_loc(kind, loc)
        if index is not None:
            cands = [p for p in cands if p['index'] == index]
        if ptype is not None:
            cands = [p for p in cands if p['type'] == ptype]
        if len(cands) != 1:
            raise SystemExit(f'Puerto ambiguo {kind} {loc} idx={index}: {cands}')
        return cands[0]

    def cmp_ports(nombre):
        """Comparator: 0=A, 1=B, 2=Greater, 3=Equal, 4=Less."""
        loc = L(nombre)
        return (comp_port('Comparator', loc, index=0),
                comp_port('Comparator', loc, index=1),
                comp_port('Comparator', loc, index=3))

    def gate(nombre):
        loc = L(nombre)
        g = by_loc('AND Gate', loc) or by_loc('OR Gate', loc)
        out = [p for p in g if p['type'] == 2][0]
        ins = sorted([p for p in g if p['type'] == 1], key=lambda p: p['y'])
        return out, ins[0], ins[1]

    def const_out(nombre):
        cands = by_loc('Constant', L(nombre))
        if len(cands) != 1:
            raise SystemExit(f'Constant {nombre} ambiguo: {cands}')
        return cands[0]

    eq_a, eq_b, eq_out = cmp_ports('cmp_eq')
    beq_a, beq_b, beq_sel = cmp_ports('cmp_beq')
    bne_a, bne_b, bne_sel = cmp_ports('cmp_bne')
    not_in = comp_port('NOT Gate', L('not'), ptype=1)
    not_out = comp_port('NOT Gate', L('not'), ptype=2)
    const_beq = const_out('const_beq')
    const_bne = const_out('const_bne')

    beq_out, beq_in0, beq_in1 = gate('and_beq')
    bne_out, bne_in0, bne_in1 = gate('and_bne')
    or_out, or_in0, or_in1 = gate('or')
    fin_out, fin_in0, fin_in1 = gate('and_fin')

    pA = pin_by_label('A')
    pB = pin_by_label('B')
    pBT = pin_by_label('BRANCH_TYPE')
    pBE = pin_by_label('BRANCH_ENABLE')
    pEQ = pin_by_label('EQ')
    pPCWB = pin_by_label('PC_WRITE_BRANCH')

    # Cada red es un conjunto de puertos unidos por un tunel.
    # TODO va por red: en Logisim un cable largo o diagonal conecta todo lo que
    # toca por el camino y eso crea bucles combinacionales.
    redes = {
        'A':               [pA, eq_a],
        'B':               [pB, eq_b],
        'BRANCH_TYPE':     [pBT, beq_a, bne_a],
        'BEQ_CONST':       [const_beq, beq_b],
        'BNE_CONST':       [const_bne, bne_b],
        'EQ':              [eq_out, pEQ, not_in, beq_in1],
        'NOT_EQ':          [not_out, bne_in0],
        'BEQ_SEL':         [beq_sel, beq_in0],
        'BNE_SEL':         [bne_sel, bne_in1],
        'BEQ_COND':        [beq_out, or_in0],
        'BNE_COND':        [bne_out, or_in1],
        'BRANCH_COND':     [or_out, fin_in1],
        'BRANCH_EN':       [pBE, fin_in0],
        'PC_WRITE_BRANCH': [fin_out, pPCWB],
    }

    ocupados = set()
    cajas = [p['box'] for p in ports if p['kind'] not in ('Pin', 'Tunnel')]

    def libre(x, y):
        if (x, y) in ocupados:
            return False
        if x % GRID or y % GRID:
            return False
        for (bx, by, bw, bh) in cajas:
            if bx - 5 <= x <= bx + bw + 5 and by - 5 <= y <= by + bh + 5:
                return False
        return True

    def segmento_libre(p, tx, ty):
        """El cable p->(tx,ty) no debe pasar por ningun otro puerto.

        Si el cable cruza otro puerto, Logisim los conecta: eso crea bucles
        combinacionales y el circuito se cuelga.
        """
        for otro in ports:
            if otro is p:
                continue
            ox, oy = otro['x'], otro['y']
            if p['x'] == tx:
                if ox == p['x'] and min(p['y'], ty) < oy < max(p['y'], ty):
                    return False
            elif p['y'] == ty:
                if oy == p['y'] and min(p['x'], tx) < ox < max(p['x'], tx):
                    return False
        return True

    # Solo desplazamientos en un eje: un cable diagonal toca los puertos
    # intermedios y conecta redes distintas.
    OFFSETS = [(30, 0), (-30, 0), (0, -30), (0, 30),
               (20, 0), (-20, 0), (0, -20), (0, 20),
               (40, 0), (-40, 0), (0, -40), (0, 40),
               (50, 0), (-50, 0), (0, -50), (0, 50),
               (60, 0), (-60, 0), (0, -60), (0, 60),
               (70, 0), (-70, 0), (0, -70), (0, 70),
               (80, 0), (-80, 0), (0, -80), (0, 80),
               (90, 0), (-90, 0), (0, -90), (0, 90),
               (100, 0), (-100, 0), (0, -100), (0, 100),
               (110, 0), (-110, 0), (0, -110), (0, 110),
               (120, 0), (-120, 0), (0, -120), (0, 120),
               (130, 0), (-130, 0), (0, -130), (0, 130),
               (140, 0), (-140, 0), (0, -140), (0, 140)]

    def posicion_para(p):
        for dx, dy in OFFSETS:
            x, y = p['x'] + dx, p['y'] + dy
            if libre(x, y) and segmento_libre(p, x, y):
                return (x, y)
        raise SystemExit(f'No hay posicion libre para el tunel de {p["kind"]} en ({p["x"]},{p["y"]})')

    wires = []
    tuneles = {}

    for tag, miembros in redes.items():
        for p in miembros:
            tx, ty = posicion_para(p)
            ocupados.add((tx, ty))
            tuneles.setdefault(tag, []).append((tx, ty))
            wires.append((f'({p["x"]},{p["y"]})', f'({tx},{ty})'))

    for tag, posiciones in tuneles.items():
        for (px, py) in posiciones:
            c = ET.SubElement(bc, 'comp', {'name': 'Tunnel', 'loc': f'({px},{py})', 'lib': '0'})
            ET.SubElement(c, 'a', {'name': 'label', 'val': tag})
            ET.SubElement(c, 'a', {'name': 'labelfont', 'val': 'SansSerif plain 12'})

    for a, b in wires:
        ET.SubElement(bc, 'wire', {'from': a, 'to': b})

    ET.ElementTree(root).write(BASE, encoding='UTF-8', xml_declaration=True)
    n_tun = sum(len(v) for v in tuneles.values())
    print(f'FASE 3: {len(wires)} cables, {n_tun} tuneles en {len(tuneles)} redes')
    for tag, posiciones in tuneles.items():
        print(f'  {tag:16s} {posiciones}')


def fase4_validar():
    orden = ['java', '-Djava.awt.headless=true',
             f'-Djava.util.prefs.userRoot={TMP}/prefs',
             '--class-path', JAR, str(PORTS), str(BASE)]
    try:
        r = subprocess.run(orden, capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        print('FASE 4: TIMEOUT - el circuito sigue colgando')
        return False
    if r.returncode:
        print(f'FASE 4: ERROR al cargar el archivo completo\n{r.stderr[:1500]}')
        return False
    n = len([l for l in r.stdout.splitlines() if l.strip()])
    print(f'FASE 4: OK - el archivo completo carga sin colgarse ({n} puertos)')
    return True


if __name__ == '__main__':
    fase1_colocar()
    ports = fase2_descubrir()
    fase3_cablear(ports)
    sys.exit(0 if fase4_validar() else 1)

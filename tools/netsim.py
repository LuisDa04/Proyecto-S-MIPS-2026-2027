#!/usr/bin/env python3
"""
Simulador de netlist para circuitos .circ de Logisim (combinacional).

Sirve para:
  1. Detectar ciclos combinacionales (la causa del cuelgue de Logisim).
  2. Verificar la logica de un subcircuito sin arrancar Logisim.

Como funciona:
  - Las redes (nets) se construyen uniendo extremos de cable y tuneles
    con la misma etiqueta.
  - Cada puerto de componente pertenece a una red.
  - Se evalua en orden topologico (Kahn). Si quedan nodos sin evaluar,
    hay un ciclo.
  - Componentes soportados: Pin, Constant, Comparator, Adder, Subtractor,
    gates (AND/OR/XOR/NAND/NOR/NOT), Multiplexer, Decoder, Splitter,
    Shifter, Bit Extender, Register (secuencial, se ignora en combinacional).
"""
from pathlib import Path
import xml.etree.ElementTree as ET
from collections import defaultdict, deque

WIDTH = 32
MASK = (1 << WIDTH) - 1


class Componente:
    __slots__ = ('kind', 'loc', 'attrs', 'ports', 'net')

    def __init__(self, kind, loc, attrs):
        self.kind = kind
        self.loc = loc
        self.attrs = attrs
        self.ports = []      # lista de (x, y, width, tipo)  tipo 1=entrada 2=salida
        self.net = []        # indice de red por puerto

    def a(self, name, default=None):
        return self.attrs.get(name, default)


def _loc(comp):
    loc = comp.get('loc', '')
    x, y = loc.strip('()').split(',')
    return int(x), int(y)


def cargar_circuito(ruta):
    """Devuelve {nombre_circuito: [Componente]} con la red de cada puerto."""
    tree = ET.parse(ruta)
    root = tree.getroot()
    circuitos = {}
    for circ in root.findall('./circuit'):
        comps = []
        for c in circ.findall('./comp'):
            attrs = {a.get('name'): a.get('val') for a in c.findall('./a')}
            comps.append(Componente(c.get('name'), _loc(c), attrs))
        circuitos[circ.get('name')] = comps
    return circuitos, root


def puertos_reales(ruta, nombres_circuitos=None):
    """Puertos reales de cada componente, descubiertos con Ports.java.

    Devuelve {nombre_circuito: {loc_componente: [(x, y, width, tipo), ...]}}
    donde tipo 1 = entrada y 2 = salida segun Ports.java.
    """
    import os
    import subprocess
    jar = os.environ.get('LOGISIM_JAR',
                          r'C:\Program Files\logisim-evolution\app\logisim-evolution-5.0.0-all.jar')
    here = Path(__file__).resolve().parent
    orden = ['java', '-Djava.awt.headless=true',
             f'-Djava.util.prefs.userRoot={here.parent}/.prefs',
             '--class-path', jar, str(here / 'Ports.java'), str(ruta)]
    r = subprocess.run(orden, capture_output=True, text=True, timeout=180)
    if r.returncode:
        raise SystemExit(f'Ports.java no pudo cargar {ruta}:\n{r.stderr[:1000]}')

    salida = defaultdict(lambda: defaultdict(list))
    for linea in r.stdout.splitlines():
        f = linea.split('\t')
        if len(f) != 9:
            continue
        circ, kind, loc, index, tip, xy, width, tipo, bounds = f
        x, y = map(int, xy.split(','))
        salida[circ][loc].append((x, y, int(width), int(tipo)))
    return salida


def _puertos_esperados(comp):
    """Puertos de un componente segun Logisim (coordenadas relativas a loc)."""
    k = comp.kind
    w = int(comp.a('width', 1) or 1)
    x, y = comp.loc
    if k == 'Pin':
        return [(x, y, w, 2)]                       # el pin entrega su valor
    if k == 'Constant':
        return [(x, y, w, 2)]
    if k == 'Comparator':
        return [(x-40, y-10, w, 1), (x-40, y+10, w, 1),
                (x, y-10, 1, 2), (x, y, 1, 2), (x, y+10, 1, 2)]
    if k in ('Adder', 'Subtractor'):
        return [(x-40, y-10, w, 1), (x-40, y+10, w, 1), (x, y, w, 2)]
    if k in ('AND Gate', 'OR Gate', 'XOR Gate', 'NAND Gate', 'NOR Gate'):
        # dos entradas a la izquierda, salida a la derecha
        return [(x-30, y-10, 1, 1), (x-30, y+10, 1, 1), (x, y, 1, 2)]
    if k == 'NOT Gate':
        return [(x-20, y, 1, 1), (x, y, 1, 2)]
    if k == 'Multiplexer':
        n = 2 ** int(comp.a('select', 1) or 1)
        sel_w = int(comp.a('select', 1) or 1)
        ports = []
        for i in range(n):
            ports.append((x-30, y-20 + i*20, w, 1))
        ports.append((x-30, y+20+10, sel_w, 1))   # select
        ports.append((x, y, w, 2))
        return ports
    if k == 'Decoder':
        sel_w = int(comp.a('select', 1) or 1)
        n = 2 ** sel_w
        ports = []
        for i in range(n):
            ports.append((x+10, y-30 + i*20, 1, 2))
        ports.append((x, y, sel_w, 1))
        if comp.a('enable', 'true') == 'true':
            ports.append((x-10, y, 1, 1))
        return ports
    if k == 'Splitter':
        incoming = int(comp.a('incoming', w) or w)
        fanout = int(comp.a('fanout', 2) or 2)
        bwo = int(comp.a('bitWidthOut', 1) or 1)
        ports = [(x, y, incoming, 1)]
        for i in range(fanout):
            ports.append((x+20, y-20 + i*10, bwo, 3))
        return ports
    if k == 'Shifter':
        return [(x-40, y-10, w, 1), (x, y, w, 2)]
    if k == 'Bit Extender':
        iw = int(comp.a('in_width', w) or w)
        ow = int(comp.a('out_width', w) or w)
        return [(x-10, y, iw, 1), (x+10, y, ow, 2)]
    if k == 'Register':
        return [(x, y-30, w, 1), (x+60, y, w, 2),      # D, Q
                (x, y, 1, 1), (x+30, y, 1, 1), (x, y+10, 1, 1)]  # enable, clock, clear
    return []


def construir_redes(circ, comps, puertos=None):
    """Asigna indice de red a cada puerto. Devuelve (num_redes, net_de_puerto).

    Si se pasa `puertos` (salida de puertos_reales), se usan esas coordenadas;
    si no, se estiman con _puertos_esperados (solo valido para aproximaciones).
    """
    # Mapa de punto -> ids de red unificados
    padre = {}

    def buscar(a):
        padre.setdefault(a, a)
        while padre[a] != a:
            padre[a] = padre[padre[a]]
            a = padre[a]
        return a

    def unir(a, b):
        ra, rb = buscar(a), buscar(b)
        if ra != rb:
            padre[rb] = ra

    # 1. Cada cable une sus dos extremos.
    for w in circ.findall('./wire'):
        f = _loc_str(w.get('from'))
        t = _loc_str(w.get('to'))
        unir(f, t)

    # 2. Los tuneles con la misma etiqueta se unen.
    por_etiqueta = defaultdict(list)
    for c in circ.findall('.//comp[@name="Tunnel"]'):
        etiqueta = None
        for a in c.findall('./a'):
            if a.get('name') == 'label':
                etiqueta = a.get('val')
                break
        if etiqueta:
            por_etiqueta[etiqueta].append(_loc(c))
    for etiqueta, puntos in por_etiqueta.items():
        for p in puntos[1:]:
            unir(puntos[0], p)

    # 3. Numero de redes.
    ids = {}
    for a in list(padre):
        r = buscar(a)
        ids.setdefault(r, len(ids))

    # 4. Puerto de cada componente -> red.
    net_de_puerto = []
    for comp in comps:
        if puertos is not None:
            loc = f'({comp.loc[0]},{comp.loc[1]})'
            comp.ports = puertos.get(loc, [])
        else:
            comp.ports = _puertos_esperados(comp)
        comp.net = [ids.get(buscar(p[:2]), -1) for p in comp.ports]
        net_de_puerto.append(comp.net)
    return len(ids), net_de_puerto


def _loc_str(s):
    x, y = s.strip('()').split(',')
    return (int(x), int(y))


def evaluar(circ, comps, entradas, n_redes, net_de_puerto):
    """Evalua el circuito combinacional. entradas = {etiqueta_pin: valor}."""
    valores = [None] * n_redes
    net_pin_in = {}
    net_pin_out = {}
    for comp in comps:
        etiqueta = comp.a('label')
        if comp.kind != 'Pin' or not etiqueta:
            continue
        if comp.a('type', 'input') == 'output':
            net_pin_out[etiqueta] = comp.net[0]
        else:
            net_pin_in[etiqueta] = comp.net[0]

    for etiqueta, red in net_pin_in.items():
        if etiqueta not in entradas:
            raise SystemExit(f'Falta el valor de entrada {etiqueta}')
        valores[red] = entradas[etiqueta] & MASK

    # Bucle de punto fijo: en cada ronda se evalua un componente cuyas
    # entradas ya tienen valor.
    for _ in range(60):
        progreso = False
        for i, comp in enumerate(comps):
            if comp.kind in ('Pin', 'Tunnel', 'Register'):
                continue
            entradas_comp = []
            listo = True
            for j, p in enumerate(comp.ports):
                if p[3] != 1:
                    continue
                v = valores[comp.net[j]] if comp.net[j] >= 0 else None
                if v is None:
                    listo = False
                    break
                entradas_comp.append(v)
            if not listo and comp.kind != 'Constant':
                continue
            outs = _evaluar_comp(comp, entradas_comp)
            for j, p in enumerate(comp.ports):
                if p[3] != 2:
                    continue
                red = comp.net[j]
                if red < 0 or valores[red] is not None:
                    continue
                idx = sum(1 for q in comp.ports[:j] if q[3] == 2)
                v = outs[idx] if idx < len(outs) else outs[0]
                valores[red] = v & ((1 << p[2]) - 1) if p[2] > 1 else (v & 1)
                progreso = True
        if not progreso:
            break

    indefinidas = [r for r, v in enumerate(valores) if v is None]
    return valores, net_pin_out, indefinidas


def _evaluar_comp(comp, ins):
    """Devuelve la lista de valores de SALIDA del componente.

    La mayoria tiene una sola salida; el Comparator tiene tres
    (Greater, Equal, Less) y el Decoder/Splitter varias.
    """
    k = comp.kind
    if k == 'Constant':
        return [int(comp.a('value', '0x0'), 16) & MASK]
    if k == 'Comparator':
        a, b = ins[0], ins[1]
        return [1 if a > b else 0, 1 if a == b else 0, 1 if a < b else 0]
    if k == 'Adder':
        return [(ins[0] + ins[1]) & MASK]
    if k == 'Subtractor':
        return [(ins[0] - ins[1]) & MASK]
    if k == 'AND Gate':
        return [ins[0] & ins[1]]
    if k == 'OR Gate':
        return [ins[0] | ins[1]]
    if k == 'XOR Gate':
        return [ins[0] ^ ins[1]]
    if k == 'NAND Gate':
        return [1 - (ins[0] & ins[1])]
    if k == 'NOR Gate':
        return [1 - (ins[0] | ins[1])]
    if k == 'NOT Gate':
        return [1 - ins[0]]
    if k == 'Multiplexer':
        n = len(ins) - 1
        sel = ins[-1]
        return [ins[sel] if sel < n else 0]
    if k == 'Decoder':
        n = len(ins) - 1
        sel = ins[-1]
        outs = [0] * n
        if sel < n:
            outs[sel] = 1
        return outs
    if k == 'Shifter':
        sh = int(comp.a('shift', 1) or 1)
        if comp.a('direction', 'lr') == 'lr':
            return [ins[0] >> sh]
        return [(ins[0] << sh) & MASK]
    if k == 'Bit Extender':
        iw = int(comp.a('in_width', 32) or 32)
        ow = int(comp.a('out_width', 32) or 32)
        v = ins[0] & ((1 << iw) - 1)
        if comp.a('type', 'zero') == 'sign' and (v >> (iw - 1)) & 1:
            v |= ((1 << (ow - iw)) - 1) << iw
        return [v & ((1 << ow) - 1)]
    if k == 'Pin':
        return [ins[0] if ins else 0]
    return [0]

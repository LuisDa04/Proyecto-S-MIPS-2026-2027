#!/usr/bin/env python3
"""
Verifica Branch_Control con el simulador de netlist:
  1. Detecta ciclos combinacionales (causa del cuelgue de Logisim).
  2. Evalua la tabla de verdad completa.

Uso: python tools/check_branch.py
"""
from pathlib import Path
import sys
from collections import defaultdict, deque

sys.path.insert(0, str(Path(__file__).resolve().parent))
from netsim import cargar_circuito, construir_redes, evaluar, puertos_reales, _loc_str

ROOT = Path(__file__).resolve().parent.parent
CIRC = ROOT / 'circuit' / 'smips.circ'

circuitos, root = cargar_circuito(CIRC)
print(f'Circuitos en el archivo: {list(circuitos)}')

# Buscar el circuito Branch_Control
circ_el = None
for c in root.findall('./circuit'):
    if c.get('name') == 'Branch_Control':
        circ_el = c
        break
if circ_el is None:
    sys.exit('No existe el circuito Branch_Control')

comps = circuitos['Branch_Control']
# Puertos reales descubiertos con Ports.java (nunca se inventan coordenadas).
puertos = puertos_reales(CIRC)['Branch_Control']
n_redes, net_de_puerto = construir_redes(circ_el, comps, puertos)
print(f'Branch_Control: {len(comps)} componentes, {n_redes} redes')

# Comprobar que todas las ENTRADAS de componente caen en alguna red.
# Las salidas sin conectar son legitimas (p.ej. Greater/Less del Comparator).
sueltos = []
for c in comps:
    for j, p in enumerate(c.ports):
        if p[3] == 1 and c.net[j] < 0:
            sueltos.append((c.kind, c.loc, c.a('label'), j))
if sueltos:
    print(f'\n{len(sueltos)} ENTRADA(s) sin red (cable mal puesto):')
    for s in sueltos:
        print(f'  {s[0]} at {s[1]} label={s[2]} puerto {s[3]}')
    sys.exit(1)

# ---- 1. Deteccion de ciclos a nivel de RED ----
# Una red depende de otra si un componente usa la segunda como entrada y
# produce la primera.
dependencia = defaultdict(set)   # red_origen -> redes de las que depende
productoras = defaultdict(list)   # red -> componentes que la producen
fuentes = set()

for i, comp in enumerate(comps):
    entradas_red = set()
    for j, p in enumerate(comp.ports):
        if p[3] == 1 and comp.net[j] >= 0:
            entradas_red.add(comp.net[j])
    salidas_red = [comp.net[j] for j, p in enumerate(comp.ports)
                   if p[3] == 2 and comp.net[j] >= 0]
    if comp.kind == 'Pin' and comp.a('type', 'input') != 'output':
        fuentes.add(comp.net[0])
        continue
    if comp.kind == 'Constant':
        fuentes.add(comp.net[0])
        continue
    for rs in salidas_red:
        productoras[rs].append(i)
        for re in entradas_red:
            dependencia[rs].add(re)

# Kahn sobre redes.
pendientes = {r: set(dependencia.get(r, ())) - fuentes for r in dependencia}
pendientes.update({r: set() for r in productoras if r not in pendientes})
for r in pendientes:
    pendientes[r] = {x for x in pendientes[r] if x in pendientes or x in fuentes}

listas = [r for r, deps in pendientes.items() if not deps]
cola = deque(listas)
resueltas = set()
while cola:
    r = cola.popleft()
    if r in resueltas:
        continue
    resueltas.add(r)
    for otra, deps in pendientes.items():
        if r in deps:
            deps.discard(r)
            if not deps and otra not in resueltas and otra not in listas:
                listas.append(otra)
                cola.append(otra)

cicladas = [r for r, deps in pendientes.items() if deps and r not in resueltas]
if cicladas:
    print(f'\nCICLO COMBINACIONAL en {len(cicladas)} red(es):')
    for r in sorted(cicladas):
        print(f'  red {r} depende de {sorted(pendientes[r])}')
        for i in productoras.get(r, []):
            comp = comps[i]
            print(f'      producida por {comp.kind} at {comp.loc} label={comp.a("label")}')
    sys.exit(1)

print('\nSin ciclos combinacionales: OK')

# ---- 2. Tabla de verdad ----
CASOS = [
    (5, 5, 1, 1, 1, 1), (5, 3, 1, 1, 0, 0), (5, 3, 2, 1, 0, 1), (5, 5, 2, 1, 1, 0),
    (5, 5, 0, 1, 1, 0), (5, 5, 3, 1, 1, 0), (5, 3, 1, 0, 0, 0), (5, 3, 2, 0, 0, 0),
    (0, 0, 1, 1, 1, 1), (0, 1, 2, 1, 0, 1), (7, 7, 2, 1, 1, 0),
    (255, 255, 1, 1, 1, 1), (255, 254, 2, 1, 0, 1),
]

fallos = 0
print()
for a, b, bt, en, eq_esp, pcw_esp in CASOS:
    entradas = {'A': a, 'B': b, 'BRANCH_TYPE': bt, 'BRANCH_ENABLE': en}
    valores, net_pin_out, indef = evaluar(circ_el, comps, entradas, n_redes, net_de_puerto)
    if indef:
        print(f'  Redes indefinidas: {indef}')
        fallos += 1
        continue
    eq = valores[net_pin_out['EQ']]
    pcw = valores[net_pin_out['PC_WRITE_BRANCH']]
    ok = (eq == eq_esp) and (pcw == pcw_esp)
    if not ok:
        fallos += 1
    print(f"{'OK   ' if ok else 'FALLO'} A={a} B={b} BT={bt} EN={en} | "
          f"EQ={eq}(esp {eq_esp}) PCW={pcw}(esp {pcw_esp})")

print()
if fallos:
    print(f'{fallos} CASOS FALLAN')
    sys.exit(1)
print(f'LOGICA OK - {len(CASOS)} casos')

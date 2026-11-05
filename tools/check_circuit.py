#!/usr/bin/env python3
"""Verifica invariantes del circuito entregable antes de simular.

Uso:
    python tools/check_circuit.py [circuit/smips.circ] [--base]

Comprueba:
  R2   pines exactos del subcircuito CPU (nombre, ancho y sentido)
  R16  los seis subcircuitos obligatorios (circuito o entidad VHDL)
  R17  ninguna RAM/ROM dentro del subcircuito CPU
  --   tuneles huerfanos (una etiqueta usada una sola vez)
  --   extremos de cable en la rejilla de 10 px
  --   pines de CPU conectados (solo en modo completo)

Con --base solo se comprueban R2, rejilla y tuneles: es util mientras la CPU
todavia esta vacia.
"""
from pathlib import Path
import argparse
import sys
import xml.etree.ElementTree as E

GRID = 10
CPU_PINS = {
    'CLK': (1, 'input'),
    'RESET': (1, 'input'),
    'MEM_RDATA': (32, 'input'),
    'MEM_ADDR': (32, 'output'),
    'MEM_WDATA': (32, 'output'),
    'MEM_BE': (4, 'output'),
    'MEM_WE': (1, 'output'),
    'TTY_DATA': (7, 'output'),
    'TTY_WE': (1, 'output'),
    'HALT': (1, 'output'),
}
REQUIRED = ['Instruction_Decoder', 'Control_Unit', 'Branch_Control',
            'Datapath', 'Register_File', 'ALU']


def attrs(node):
    return {a.get('name'): a.get('val') for a in node.findall('a')}


def circuits(root):
    return {c.get('name'): c for c in root.findall('circuit')}


def vhdl_entities(root):
    return [v.get('name') for v in root.findall('vhdl')]


def pins(circuit):
    out = {}
    for comp in circuit.findall('comp'):
        if comp.get('name') != 'Pin':
            continue
        values = attrs(comp)
        label = values.get('label', '')
        out[label] = {
            'width': int(values.get('width', 1)),
            'direction': values.get('type', 'input'),
            'loc': comp.get('loc'),
        }
    return out


def parse_xy(text):
    x, y = text.strip('()').split(',')
    return int(x), int(y)


def check_cpu_pins(root, errors):
    cpu = circuits(root).get('CPU')
    if cpu is None:
        errors.append('R2: no existe el subcircuito CPU')
        return set()
    reales = pins(cpu)
    for name, (width, direction) in CPU_PINS.items():
        if name not in reales:
            errors.append(f'R2: falta el pin {name} en CPU')
            continue
        if reales[name]['width'] != width:
            errors.append(f'R2: {name} mide {reales[name]["width"]} bits, se esperaban {width}')
        if reales[name]['direction'] != direction:
            errors.append(f'R2: {name} es {reales[name]["direction"]}, se esperaba {direction}')
    for name in reales:
        if name not in CPU_PINS:
            errors.append(f'R2: pin {name} sobra en CPU')
    return {name for name in reales if name in CPU_PINS}


def check_required(root, errors):
    disponibles = {name.lower(): name for name in circuits(root)}
    disponibles.update({name.lower(): name for name in vhdl_entities(root)})
    for name in REQUIRED:
        if name.lower() not in disponibles:
            errors.append(f'R16: falta el subcircuito {name}')


def check_no_memory(root, errors):
    todo = circuits(root)
    vistos = set()

    def visitar(nombre):
        if nombre in vistos:
            return
        vistos.add(nombre)
        circ = todo.get(nombre)
        if circ is None:
            return
        for comp in circ.findall('comp'):
            hijo = comp.get('name')
            if hijo in ('RAM', 'ROM', 'Memory'):
                errors.append(f'R17: {nombre} contiene {hijo} (RAM/ROM prohibida dentro de CPU)')
            if hijo in todo:
                visitar(hijo)

    if 'CPU' in todo:
        visitar('CPU')


def check_tunnels(root, errors, warnings):
    for circ in root.findall('circuit'):
        etiquetas = {}
        for comp in circ.findall('comp'):
            if comp.get('name') != 'Tunnel':
                continue
            label = attrs(comp).get('label', '')
            etiquetas[label] = etiquetas.get(label, 0) + 1
        for label, cuenta in etiquetas.items():
            if cuenta == 1:
                warnings.append(f'{circ.get("name")}: tunel {label!r} aparece una sola vez')


def check_grid(root, errors):
    for circ in root.findall('circuit'):
        for w in circ.findall('wire'):
            for extremo in ('from', 'to'):
                x, y = parse_xy(w.get(extremo))
                if x % GRID or y % GRID:
                    errors.append(f'{circ.get("name")}: cable {extremo}=({x},{y}) fuera de la rejilla')


def check_pin_connections(root, errors):
    cpu = circuits(root).get('CPU')
    if cpu is None:
        return
    extremos = set()
    for w in cpu.findall('wire'):
        extremos.add(parse_xy(w.get('from')))
        extremos.add(parse_xy(w.get('to')))
    tuneles = {parse_xy(c.get('loc')) for c in cpu.findall('comp') if c.get('name') == 'Tunnel'}
    for name, data in pins(cpu).items():
        if data['loc'] and parse_xy(data['loc']) not in extremos | tuneles:
            errors.append(f'CPU: el pin {name} no esta conectado')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archivo', nargs='?', default='circuit/smips.circ')
    parser.add_argument('--base', action='store_true',
                        help='solo R2, rejilla y tuneles (CPU todavia vacia)')
    args = parser.parse_args()

    path = Path(args.archivo)
    if not path.exists():
        print(f'ERROR: no existe {path}')
        return 2
    root = E.parse(path).getroot()

    errors, warnings = [], []
    check_cpu_pins(root, errors)
    if not args.base:
        check_required(root, errors)
        check_no_memory(root, errors)
        check_pin_connections(root, errors)
    check_grid(root, errors)
    check_tunnels(root, errors, warnings)

    for w in warnings:
        print(f'AVISO: {w}')
    for e in errors:
        print(f'ERROR: {e}')
    if errors:
        print(f'\n{len(errors)} error(es), {len(warnings)} aviso(s)')
        return 1
    print(f'OK: {len(warnings)} aviso(s), sin errores')
    return 0


if __name__ == '__main__':
    sys.exit(main())

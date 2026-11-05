#!/usr/bin/env python3
"""Prueba de humo de tools/circuitlib.py y tools/check_circuit.py.

Genera un circuito trivial con una compuerta AND, descubre sus puertos con
Logisim, lo cablea, lo vuelve a cargar y comprueba que el merge respeta
Board/Memory. No toca circuit/smips.circ.
"""
from pathlib import Path
import subprocess
import sys
import tempfile

from circuitlib import (
    MEMORY, cable, circuit, comp, connect_port, discover_ports, find_circuit,
    gate, load, merge_circuits, new_project, save, select, subcircuit, text,
    tunnel, wire,
)

ROOT = Path(__file__).resolve().parent.parent


def build_smoke():
    root = new_project('Smoke')
    c, coords = subcircuit(root, 'Smoke', [('A', 1), ('B', 1)], [('Y', 1)], 'Smoke')
    gate(c, 'AND Gate', (500, 180), width=1, inputs=2, size=30)

    rows = discover_ports(root)
    puertos_and = select(rows, circuit_name='Smoke', kind='AND Gate')
    assert len(puertos_and) == 3, f'la AND deberia tener 3 puertos, tiene {len(puertos_and)}'
    oeste = sorted([p for p in puertos_and if p['index'] < 2], key=lambda p: p['y'])
    este = [p for p in puertos_and if p['index'] == 2][0]

    # A -> AND, con un codo ortogonal
    cable(c, [coords['A'], (480, coords['A'][1]),
              (480, oeste[0]['y']), (oeste[0]['x'], oeste[0]['y'])])

    # B -> tunel -> AND: prueba la conectividad por nombre
    tunnel(c, (160, coords['B'][1]), 'B', 1, 'east')
    wire(c, coords['B'], (160, coords['B'][1]))
    tunnel(c, (460, oeste[1]['y']), 'B', 1, 'east')
    wire(c, (460, oeste[1]['y']), (oeste[1]['x'], oeste[1]['y']))

    # AND -> Y, con otro codo
    cable(c, [(este['x'], este['y']), (700, este['y']),
              (700, coords['Y'][1]), coords['Y']])
    return root


def test_roundtrip(tmp):
    root = build_smoke()
    path = tmp / 'smoke.circ'
    save(root, path)
    rows = discover_ports(load(path))  # recarga el archivo guardado, no el arbol vivo
    assert select(rows, circuit_name='Smoke', kind='Pin'), 'no se encontraron pines'
    assert len(select(rows, circuit_name='Smoke', kind='Tunnel')) == 2
    assert len(select(rows, circuit_name='Smoke', kind='AND Gate')) == 3
    assert find_circuit(load(path), 'Smoke') is not None
    print(f'  roundtrip OK: {path} ({len(rows)} puertos)')


def test_connect_port(tmp):
    """connect_port debe crear un cable y un tunel con el nombre pedido."""
    root = new_project('Smoke')
    c, _ = subcircuit(root, 'Smoke', [('A', 1)], [('Y', 1)], 'Smoke')
    gate(c, 'AND Gate', (500, 180), size=30)
    rows = discover_ports(root)
    este = [p for p in select(rows, kind='AND Gate') if p['index'] == 2][0]
    connect_port(c, este, 'RESULT', length=30)

    path = tmp / 'connect.circ'
    save(root, path)
    recargado = load(path)
    circ = find_circuit(recargado, 'Smoke')
    tuneles = [t for t in circ.findall('comp') if t.get('name') == 'Tunnel']
    assert len(tuneles) == 1, f'se esperaba 1 tunel, hay {len(tuneles)}'
    label = [a.get('val') for a in tuneles[0].findall('a') if a.get('name') == 'label'][0]
    assert label == 'RESULT', f'etiqueta inesperada: {label}'
    assert len(circ.findall('wire')) == 1, 'se esperaba un unico tramo recto'
    assert discover_ports(recargado), 'el archivo con tunel no carga'
    print('  connect_port OK: 1 cable + 1 tunel RESULT, recarga correcta')


def test_gate_sizes():
    """Un size invalido debe fallar en Python, no al cargar el .circ."""
    root = new_project('Smoke')
    c = circuit(root, 'Smoke')
    for malo in (20, 40, 60):
        try:
            gate(c, 'AND Gate', (250, 490), size=malo)
        except ValueError:
            pass
        else:
            raise AssertionError(f'gate() deberia rechazar size={malo} en AND')
    gate(c, 'NOT Gate', (250, 490), size=20)  # valido solo en NOT
    print('  gate sizes OK: se rechazan 20/40/60 en AND y se acepta 20 en NOT')


def test_merge():
    base = new_project('Board')
    board = circuit(base, 'Board')
    text(board, (100, 100), 'Board intacto')
    memoria = circuit(base, 'Memory')
    comp(memoria, 'RAM', (200, 200), MEMORY, addrWidth=12, dataWidth=32)

    generado = new_project('Datapath')
    subcircuit(generado, 'Datapath', [('CLK', 1)], [('RESULT', 32)], 'Datapath')
    merge_circuits(base, generado, ['Datapath'])

    assert find_circuit(base, 'Datapath') is not None
    assert find_circuit(base, 'Board') is board, 'Board se reemplazo'
    assert find_circuit(base, 'Memory') is memoria, 'Memory se reemplazo'
    try:
        merge_circuits(base, generado, ['Board'])
    except ValueError:
        pass
    else:
        raise AssertionError('merge_circuits deberia rechazar Board (R2)')
    print('  merge OK: Board y Memory intactos, R2 protegido')


def test_checker():
    result = subprocess.run(
        [sys.executable, str(ROOT / 'tools/check_circuit.py'),
         str(ROOT / 'circuit/smips.circ'), '--base'],
        capture_output=True, text=True,
    )
    if result.returncode:
        raise AssertionError(result.stdout + result.stderr)
    print('  checker OK: ' + result.stdout.strip().splitlines()[-1])


def main():
    with tempfile.TemporaryDirectory(prefix='smoke-circuitlib-') as directory:
        tmp = Path(directory)
        print('circuitlib:')
        test_gate_sizes()
        test_connect_port(tmp)
        test_roundtrip(tmp)
        test_merge()
        test_checker()
    print('TODO OK')


if __name__ == '__main__':
    main()

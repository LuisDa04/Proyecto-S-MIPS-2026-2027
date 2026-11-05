#!/usr/bin/env python3
"""Utilidades para generar circuitos de Logisim Evolution 5.0.0 desde Python.

La idea es la misma que ya usa tools/build.py, pero empaquetada para reutilizarla:

  1. se describen componentes y pines con coordenadas de rejilla;
  2. se guarda un .circ temporal y se carga con tools/Ports.java en modo headless;
  3. Ports.java devuelve la coordenada exacta de cada puerto de cada componente;
  4. se conectan los puertos con cables cortos y tuneles con nombre.

Con esto no hace falta calcular a mano donde cae cada puerto ni dibujar cables
largos: la conectividad se declara por nombre de senal (tunel) y el layout solo
necesita evitar solapamientos.

El modulo no escribe en circuit/smips.circ por si solo. Para integrar lo
generado se usa merge_circuits(), que conserva Board y Memory intactos (R2).
"""
from pathlib import Path
import copy
import os
import subprocess
import tempfile
import xml.etree.ElementTree as E

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
JAR = os.environ.get(
    'LOGISIM_JAR',
    r'C:\Program Files\logisim-evolution\app\logisim-evolution-5.0.0-all.jar',
)
JAVA = os.environ.get('JAVA', 'java')

LIBRERIAS = ['#Wiring', '#Gates', '#Plexers', '#Arithmetic', '#FPArithmetic', '#Memory', '#I/O', '#Base']
WIRING, GATES, PLEXERS, ARITH, FPARITH, MEMORY, IO, BASE = '0', '1', '2', '3', '4', '5', '6', '7'

GRID = 10  # Logisim une cables cuyos extremos caen en la rejilla de 10 px

# Logisim rechaza silenciosamente (via dialogo de error) los tamanos de compuerta
# que no estan en estas listas; el .circ entonces no carga en modo headless.
GATE_SIZES = (30, 50, 70)
NOT_GATE_SIZES = (20, 30)


# ---------------------------------------------------------------------------
# Proyecto y serializacion
# ---------------------------------------------------------------------------

def new_project(main='Board'):
    """Crea un proyecto vacio con las librerias que usa la placa."""
    root = E.Element('project', {'source': '5.0.0', 'version': '1.0'})
    root.text = ('\n  This file is intended to be loaded by Logisim-evolution '
                 'v5.0.0(https://github.com/logisim-evolution/).\n\n  ')
    for index, desc in enumerate(LIBRERIAS):
        E.SubElement(root, 'lib', {'desc': desc, 'name': str(index)})
    E.SubElement(root, 'main', {'name': main})
    options = E.SubElement(root, 'options')
    for key, value in (('gateUndefined', 'ignore'), ('simlimit', '1000'), ('simrand', '0')):
        E.SubElement(options, 'a', {'name': key, 'val': value})
    return root


def load(path):
    """Carga un .circ y devuelve la raiz XML."""
    return E.parse(path).getroot()


def save(root, path):
    """Escribe el .circ con indentacion legible."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    E.indent(root, space='  ')
    E.ElementTree(root).write(path, encoding='UTF-8', xml_declaration=True)


def circuit(root, name):
    """Devuelve el circuito `name`, creandolo si no existe."""
    for c in root.findall('circuit'):
        if c.get('name') == name:
            return c
    return E.SubElement(root, 'circuit', {'name': name})


def find_circuit(root, name):
    for c in root.findall('circuit'):
        if c.get('name') == name:
            return c
    return None


# ---------------------------------------------------------------------------
# Componentes
# ---------------------------------------------------------------------------

def comp(circ, name, xy, lib=None, **attrs):
    """Anade un componente. `xy` es su punto de anclaje en la rejilla."""
    data = {'name': name, 'loc': f'({xy[0]},{xy[1]})'}
    if lib is not None:
        data['lib'] = lib
    node = E.SubElement(circ, 'comp', data)
    for key, value in attrs.items():
        E.SubElement(node, 'a', {'name': key, 'val': str(value)})
    return node


def wire(circ, a, b):
    """Anade un cable recto si los extremos son distintos."""
    if a != b:
        E.SubElement(circ, 'wire', {'from': f'({a[0]},{a[1]})', 'to': f'({b[0]},{b[1]})'})


def cable(circ, puntos):
    """Anade una polilinea de cables entre puntos consecutivos."""
    for a, b in zip(puntos, puntos[1:]):
        wire(circ, a, b)


def tunnel(circ, xy, label, width=1, facing='east'):
    """Anade un tunel (net con nombre)."""
    comp(circ, 'Tunnel', xy, WIRING, label=label, width=width, facing=facing,
         labelfont='SansSerif plain 12')


def gate(circ, name, xy, width=1, inputs=None, size=None):
    """Coloca una compuerta validando `size` contra los valores que acepta Logisim.

    Las compuertas de 2+ entradas solo admiten 30, 50 o 70; la NOT admite 20 o 30.
    Un valor invalido no da un error de Python: Logisim muestra un dialogo al
    cargar el archivo y, en modo headless, termina en HeadlessException.
    """
    validos = NOT_GATE_SIZES if name == 'NOT Gate' else GATE_SIZES
    if size is not None and size not in validos:
        raise ValueError(f'{name}: size={size} no es valido; usa {validos}')
    attrs = {'width': width}
    if inputs is not None:
        attrs['inputs'] = inputs
    if size is not None:
        attrs['size'] = size
    return comp(circ, name, xy, GATES, **attrs)


def text(circ, xy, content, size=14, bold=False):
    comp(circ, 'Text', xy, BASE, text=content,
         font=f'SansSerif {"bold" if bold else "plain"} {size}')


def pin(circ, xy, name, width=1, direction='in'):
    """Anade un pin. El punto de conexion es `xy`."""
    attrs = dict(label=name, width=width, appearance='classic', labelfont='SansSerif plain 12')
    if direction == 'out':
        attrs.update(type='output', facing='west', labelloc='east')
    return comp(circ, 'Pin', xy, WIRING, **attrs)


# ---------------------------------------------------------------------------
# Subcircuitos (caja + pines + apariencia)
# ---------------------------------------------------------------------------

def subcircuit(root, name, inputs, outputs, title,
               x_in=120, x_out=880, y0=120, dy=60, width=260):
    """Crea un subcircuito con pines en coordenadas conocidas.

    `inputs` y `outputs` son listas de (nombre, ancho).
    Devuelve (circuito, {nombre_pin: (x, y)}).
    """
    c = circuit(root, name)
    for child in list(c):
        c.remove(child)  # regenerar el circuito desde cero
    E.SubElement(c, 'a', {'name': 'appearance', 'val': 'custom'})

    filas = max(len(inputs), len(outputs), 1)
    alto = dy * filas + 40
    ancho = width
    appear = E.SubElement(c, 'appear')
    E.SubElement(appear, 'rect', {
        'fill': 'none', 'height': str(alto), 'stroke': '#000000', 'stroke-width': '2',
        'width': str(ancho), 'x': '50', 'y': '50',
    })
    E.SubElement(appear, 'text', {
        'dominant-baseline': 'central', 'font-family': 'SansSerif', 'font-size': '16',
        'font-weight': 'bold', 'text-anchor': 'middle',
        'x': str(50 + ancho // 2), 'y': str(50 + alto // 2),
    }).text = title

    coords = {}
    for direction, pines in (('in', inputs), ('out', outputs)):
        for index, (pin_name, pin_width) in enumerate(pines):
            y = y0 + dy * index
            x = x_in if direction == 'in' else x_out
            coords[pin_name] = (x, y)
            pin(c, (x, y), pin_name, pin_width, 'in' if direction == 'in' else 'out')
            borde_x = 50 if direction == 'in' else 50 + ancho
            E.SubElement(appear, 'text', {
                'dominant-baseline': 'central', 'font-family': 'SansSerif', 'font-size': '11',
                'text-anchor': 'start' if direction == 'in' else 'end',
                'x': str(borde_x + 5 if direction == 'in' else borde_x - 5),
                'y': str(50 + 30 + dy * index),
            }).text = pin_name
            E.SubElement(appear, 'circ-port', {
                'dir': direction, 'pin': f'{x},{y}',
                'x': str(borde_x), 'y': str(50 + 30 + dy * index),
            })
    E.SubElement(appear, 'circ-anchor', {'facing': 'east', 'x': '50', 'y': '50'})
    return c, coords


# ---------------------------------------------------------------------------
# Descubrimiento de puertos con Logisim (Ports.java)
# ---------------------------------------------------------------------------

def discover_ports(root, timeout=180):
    """Carga el proyecto con Logisim y devuelve una lista de puertos.

    Cada elemento es un dict con: circuit, kind, loc, index, tip, x, y,
    width, type (int: 1=entrada, 2=salida, 3=tunel), bounds. Lanza
    RuntimeError si Logisim no puede cargar el .circ.

    Ojo: `type` es la direccion del puerto **del componente**, no la del pin.
    En un Pin de entrada vale 2 y en uno de salida vale 1. Para una compuerta,
    sus entradas valen 1 y su salida vale 2.
    """
    with tempfile.TemporaryDirectory(prefix='circuitlib-') as directory:
        stage = Path(directory) / 'stage.circ'
        save(root, stage)
        comando = [
            JAVA, '-Djava.awt.headless=true',
            f'-Djava.util.prefs.userRoot={directory}/prefs',
            '--class-path', JAR, str(HERE / 'Ports.java'), str(stage),
        ]
        result = subprocess.run(comando, capture_output=True, text=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError(
            'Logisim no pudo cargar el circuito generado:\n'
            + (result.stdout or '') + (result.stderr or '')
        )
    rows = []
    for line in result.stdout.splitlines():
        fields = line.split('\t')
        if len(fields) != 9:
            continue
        circuit_name, kind, loc, index, tip, xy, width, typ, bounds = fields
        x, y = map(int, xy.split(','))
        rows.append({
            'circuit': circuit_name, 'kind': kind, 'loc': loc, 'index': int(index),
            'tip': tip, 'x': x, 'y': y, 'width': int(width), 'type': int(typ),
            'bounds': tuple(map(int, bounds.split(','))),
        })
    return rows


def side(port):
    """Lado del componente por el que sale un puerto (west/east/north/south)."""
    if port['kind'] == 'Splitter':
        return 'west' if port['index'] == 0 else 'east'
    bx, by, bw, bh = port['bounds']
    distancias = {
        'west': port['x'] - bx,
        'east': bx + bw - port['x'],
        'north': port['y'] - by,
        'south': by + bh - port['y'],
    }
    return min(distancias, key=distancias.get)


def connect_port(circ, port, label, length=30):
    """Conecta un puerto a un tunel con un tramo recto."""
    dx, dy, facing = {
        'west': (-1, 0, 'east'), 'east': (1, 0, 'west'),
        'north': (0, -1, 'south'), 'south': (0, 1, 'north'),
    }[side(port)]
    end = (port['x'] + dx * length, port['y'] + dy * length)
    wire(circ, (port['x'], port['y']), end)
    tunnel(circ, end, label, port['width'], facing)


def select(rows, circuit_name=None, kind=None, tip=None, loc=None):
    """Filtra la salida de discover_ports()."""
    out = rows
    if circuit_name is not None:
        out = [r for r in out if r['circuit'] == circuit_name]
    if kind is not None:
        out = [r for r in out if r['kind'] == kind]
    if tip is not None:
        out = [r for r in out if r['tip'] == tip]
    if loc is not None:
        out = [r for r in out if r['loc'] == loc]
    return out


# ---------------------------------------------------------------------------
# Fusion con un .circ existente (R2: Board y Memory no se tocan)
# ---------------------------------------------------------------------------

def merge_circuits(base_root, extra_root, names):
    """Reemplaza en `base_root` los circuitos `names` por los de `extra_root`.

    Solo se copian elementos <circuit>. Nunca se toca <main>, <options>, <lib>,
    Board ni Memory.
    """
    for name in names:
        if name in ('Board', 'Memory'):
            raise ValueError(f'R2: no se puede reemplazar el circuito {name}')
        actual = find_circuit(base_root, name)
        if actual is not None:
            base_root.remove(actual)
        nuevo = find_circuit(extra_root, name)
        if nuevo is None:
            raise KeyError(f'El proyecto generado no contiene el circuito {name}')
        base_root.append(copy.deepcopy(nuevo))

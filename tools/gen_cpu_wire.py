#!/usr/bin/env python3
"""Cablear CPU directamente en XML con coordenadas aproximadas y túneles nombrados."""
import sys
sys.path.insert(0, r'D:\EscuelaLuisi\AC\Proyecto\Proyecto-S-MIPS-2026-2027\tools')
import circuitlib as cl
import xml.etree.ElementTree as E

ROOT = r'D:\EscuelaLuisi\AC\Proyecto\Proyecto-S-MIPS-2026-2027'
SALIDA = ROOT + r'\circuit\smips.circ'

root = cl.load(SALIDA)

# Encontrar CPU existente
cpu = None
for c in root.findall('circuit'):
    if c.get('name') == 'CPU':
        cpu = c
        break

if cpu is None:
    print('ERROR: no se encontró CPU')
    sys.exit(1)

# Definir pines (mismos que en gen_cpu_direct.py)
pines_entrada = [('CLK', 1, 60), ('RESET', 1, 120), ('MEM_RDATA', 32, 180)]
pines_salida = [('MEM_ADDR', 32, 60), ('MEM_WDATA', 32, 120), ('MEM_BE', 4, 180),
                ('MEM_WE', 1, 240), ('TTY_DATA', 7, 300), ('TTY_WE', 1, 360),
                ('HALT', 1, 420)]

# ============================================================
# Helper: conectar un puerto aproximado a un túnel
# ============================================================
def wire_to_tunnel(circ, px, py, label, width=1, direction='east'):
    """Crea un cable corto desde el puerto hasta un túnel en coordenadas de rejilla."""
    if direction == 'east':
        tx = ((px + 30) // 10) * 10
        wire(circ, (px, py), (tx, py))
    else:
        tx = ((px - 30) // 10) * 10
        wire(circ, (px, py), (tx, py))
    ty = (py // 10) * 10
    cl.tunnel(circ, (tx, ty), label, width, facing=direction)

def wire(circ, a, b):
    if a != b:
        E.SubElement(circ, 'wire', {'from': f'({a[0]},{a[1]})', 'to': f'({b[0]},{b[1]})'})

# ============================================================
# Conectar pines de CPU a túneles (señales de entrada/salida de la placa)
# Los pines están en: entrada x=120, salida x=880
# ============================================================
# Entradas: conectar pin (x=120) a túnel hacia la derecha
wire_to_tunnel(cpu, 120, 60, 'CLK')
wire_to_tunnel(cpu, 120, 120, 'RESET')
wire_to_tunnel(cpu, 120, 180, 'MEM_RDATA', 32)

# Salidas: conectar pin (x=880) a túnel hacia la izquierda
for name, width, y in pines_salida:
    # Cable desde pin (880,y) hasta (850,y), luego túnel en (820,y)
    tx = 820
    wire(cpu, (880, y), (850, y))
    wire(cpu, (850, y), (tx, y))
    cl.tunnel(cpu, (tx, y), name, width, facing='west')
    print(f'  Pin salida {name} conectado a túnel en ({tx},{y})')

print('Pines de CPU conectados a túneles')

# ============================================================
# Nota: El cableado interno de componentes (Control_Unit, Datapath, etc.)
# requiere discover_ports, que no funciona con componentes dentro de CPU.
# Los componentes están instanciados pero sin cableado interno.
# Esto se completará en una fase posterior.
# ============================================================

E.indent(root, space='  ')
E.ElementTree(root).write(SALIDA, encoding='UTF-8', xml_declaration=True)
print(f'OK: CPU con pines conectados escrito en {SALIDA}')

# Verificar con check_circuit.py completo
import subprocess
result = subprocess.run([sys.executable, 'tools/check_circuit.py', SALIDA],
                       capture_output=True, text=True)
print('\n--- check_circuit.py completo ---')
print(result.stdout)
if result.stderr:
    print('STDERR:', result.stderr)

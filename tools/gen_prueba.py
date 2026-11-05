#!/usr/bin/env python3
"""Genera circuit/prueba_generador.circ: demo combinacional del generador.

Circuito principal "Prueba_Generador":
  entradas A, B  ->  AND, OR, XOR, NOT  ->  salidas AND_OUT, OR_OUT, XOR_OUT, NOT_OUT

Cada puerto se conecta con un tramo corto a un tunel con el nombre de la senal.
No hay cables largos ni coordenadas de puerto calculadas a mano: se descubren
con tools/Ports.java en modo headless.

Uso:
    python tools/gen_prueba.py
    python tools/Verify.java circuit/prueba_generador.circ
"""
from pathlib import Path
import sys

from circuitlib import (
    circuit, connect_port, discover_ports, gate, new_project, pin, save, select,
)

ROOT = Path(__file__).resolve().parent.parent
SALIDA = ROOT / 'circuit/prueba_generador.circ'


def main():
    root = new_project('Prueba_Generador')
    c = circuit(root, 'Prueba_Generador')

    pin(c, (100, 100), 'A', 1, 'in')
    pin(c, (100, 220), 'B', 1, 'in')
    pin(c, (820, 100), 'AND_OUT', 1, 'out')
    pin(c, (820, 220), 'OR_OUT', 1, 'out')
    pin(c, (820, 340), 'XOR_OUT', 1, 'out')
    pin(c, (820, 460), 'NOT_OUT', 1, 'out')

    gate(c, 'AND Gate', (400, 100), size=30)
    gate(c, 'OR Gate', (400, 220), size=50)
    gate(c, 'XOR Gate', (400, 340), size=70)
    gate(c, 'NOT Gate', (400, 460), size=20)

    # Descubrir la coordenada exacta de cada puerto antes de cablear.
    rows = discover_ports(root)

    def puertos_entrada(kind):
        """Puertos de entrada de la compuerta, ordenados de arriba a abajo.

        Ojo: en Logisim el indice 0 de una compuerta no es la primera entrada;
        la salida suele ser el indice 0. Por eso se filtra por `type` (1=input,
        2=output) y no por indice.
        """
        encontrados = [p for p in select(rows, kind=kind) if p['type'] == 1]
        return sorted(encontrados, key=lambda p: p['y'])

    def puerto_salida(kind):
        encontrados = [p for p in select(rows, kind=kind) if p['type'] == 2]
        if len(encontrados) != 1:
            raise RuntimeError(f'{kind}: se esperaba 1 salida, hay {len(encontrados)}')
        return encontrados[0]

    def pin_por_nombre(nombre):
        encontrados = [p for p in select(rows, kind='Pin') if p['tip'] == nombre]
        if len(encontrados) != 1:
            raise RuntimeError(f'pin {nombre}: se esperaba 1, hay {len(encontrados)}')
        return encontrados[0]

    # Entradas: pin -> tunel A / B (la misma senal se reutiliza en varias puertas).
    connect_port(c, pin_por_nombre('A'), 'A', length=30)
    connect_port(c, pin_por_nombre('B'), 'B', length=30)

    # Compuertas: entradas desde tuneles, salidas a tuneles con nombre.
    for kind, senal_salida, senales_entrada in (
        ('AND Gate', 'AND_OUT', ('A', 'B')),
        ('OR Gate', 'OR_OUT', ('A', 'B')),
        ('XOR Gate', 'XOR_OUT', ('A', 'B')),
        ('NOT Gate', 'NOT_OUT', ('A',)),
    ):
        pines_entrada = puertos_entrada(kind)
        if len(pines_entrada) != len(senales_entrada):
            raise RuntimeError(
                f'{kind}: {len(pines_entrada)} entradas, se esperaban {len(senales_entrada)}')
        for puerto, senal in zip(pines_entrada, senales_entrada):
            connect_port(c, puerto, senal, length=30)
        connect_port(c, puerto_salida(kind), senal_salida, length=30)

    # Salidas: tunel -> pin (mismo nombre, otra coordenada).
    for nombre in ('AND_OUT', 'OR_OUT', 'XOR_OUT', 'NOT_OUT'):
        connect_port(c, pin_por_nombre(nombre), nombre, length=30)

    save(root, SALIDA)
    print(f'generado {SALIDA}')
    return 0


if __name__ == '__main__':
    sys.exit(main())

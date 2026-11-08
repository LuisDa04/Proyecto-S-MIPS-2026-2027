#!/usr/bin/env python3
"""Genera y fusiona los subcircuitos ALU y Datapath en circuit/smips.circ.

Sigue el patron del proyecto: se describen los componentes en Python, Logisim
(Ports.java) devuelve la coordenada exacta de cada puerto y la conectividad se
declara con tuneles por nombre. El resultado se fusiona sin tocar Board,
Memory, CPU ni <main> (R2).

El Datapath implementa docs/diseno.md 10.4 con una instancia de Register_File
(entidad VHDL de la Fase 2) y una sola instancia de ALU (R14/R16):

  * PC, IR, A, B, ALUOUT y MDR.
  * PC+4 en FETCH y destino de rama con la ALU.
  * JUMP_TARGET = {PC[31:28], IR[25:0], 2'b00}.
  * Extension de inmediato: zero, sign, shamt y branch (<<2).
  * LUI dentro de la ALU; jr por A; jal escribe $31 con PC (PC+4).
  * MEM_ADDR, MEM_WDATA, MEM_BE y TTY_DATA por carriles de byte.

Uso:
    python tools/gen_datapath.py
    python tools/check_circuit.py circuit/smips.circ --base
"""
from pathlib import Path
import copy
import xml.etree.ElementTree as E

import circuitlib as cl

ROOT = Path(__file__).resolve().parent.parent
SALIDA = ROOT / 'circuit/smips.circ'
VHDL = ROOT / 'circuit/register_file.vhd'


def bits(*ranges, incoming=32):
    """Mapa bit->fanout para Splitter; ranges es (indice, primero, ultimo).

    Logisim deduce el ancho de cada fanout de los atributos bitN. Si los bits
    no declarados se omiten, un splitter con fanout=1 expone el ancho de la
    entrada (32) y los tuneles quedan inconsistentes; por eso se emiten todos
    los bits, con 'none' en los no usados.
    """
    out = {f'bit{i}': 'none' for i in range(incoming)}
    for idx, lo, hi in ranges:
        for i in range(lo, hi + 1):
            out[f'bit{i}'] = str(idx)
    return out


def indice(rows):
    """Agrupa discover_ports() por (circuito, loc) y ordena por indice."""
    by = {}
    for r in rows:
        by.setdefault(r['circuit'], {}).setdefault(r['loc'], []).append(r)
    return by


def puertos(by, circuito, xy):
    key = f'({xy[0]},{xy[1]})' if isinstance(xy, tuple) else xy
    return sorted(by[circuito][key], key=lambda r: r['index'])


def build_alu(root):
    """Construye la ALU del contrato (8 operaciones, sin CLK y sin ROM)."""
    alu, pins = cl.subcircuit(
        root, 'ALU',
        [('A', 32), ('B', 32), ('ALU_OP', 3)],
        [('Y', 32), ('ZERO', 1)],
        'ALU', x_in=120, x_out=400, width=280)

    items = [
        ('ADD',     'Adder',        0, 0, cl.ARITH, dict(width=32)),
        ('SUB',     'Subtractor',   1, 0, cl.ARITH, dict(width=32)),
        ('G_AND',   'AND Gate',     2, 0, cl.GATES, dict(width=32, inputs=2)),
        ('G_OR',    'OR Gate',      0, 1, cl.GATES, dict(width=32, inputs=2)),
        ('G_XA',    'XOR Gate',     1, 1, cl.GATES, dict(width=32, inputs=2)),
        ('G_XB',    'XOR Gate',     2, 1, cl.GATES, dict(width=32, inputs=2)),
        ('CMP_SLT', 'Comparator',   0, 2, cl.ARITH, dict(width=32)),
        ('EXT_LT',  'Bit Extender', 1, 2, cl.WIRING, dict(in_width=1, out_width=32, type='zero')),
        ('SLL',     'Shifter',      2, 2, cl.ARITH, dict(width=32, shift='ll')),
        ('SRL',     'Shifter',      0, 3, cl.ARITH, dict(width=32, shift='lr')),
        ('SPL_SH',  'Splitter',     1, 3, cl.WIRING,
         dict(incoming=32, fanout=1, appear='center', **bits((0, 0, 4)))),
        ('SPL_B16', 'Splitter',     2, 3, cl.WIRING,
         dict(incoming=32, fanout=1, appear='center', **bits((0, 0, 15)))),
        ('SPL_LUI', 'Splitter',     0, 4, cl.WIRING,
         dict(incoming=32, fanout=2, appear='center',
              **bits((0, 0, 15), (1, 16, 31)))),
        ('C_Z16',   'Constant',     1, 4, cl.WIRING, dict(value='0x0', width=16)),
        ('MUX',     'Multiplexer',  2, 4, cl.PLEXERS, dict(width=32, select=3, selloc='tr')),
        ('CMP_Z',   'Comparator',   0, 5, cl.ARITH, dict(width=32)),
        ('C_Z32',   'Constant',     1, 5, cl.WIRING, dict(value='0x0', width=32)),
        ('C_SIGN',  'Constant',     2, 5, cl.WIRING, dict(value='0x80000000', width=32)),
    ]
    locs = {}
    for cid, name, col, row, lib, attrs in items:
        xy = (700 + col * 400, 300 + row * 260)
        cl.comp(alu, name, xy, lib, **attrs)
        locs[cid] = xy

    by = indice(cl.discover_ports(root))

    def conn(cid, idx, label, length=30):
        cl.connect_port(alu, puertos(by, 'ALU', locs[cid])[idx], label, length)

    for name in ('A', 'B', 'ALU_OP'):
        cl.connect_port(alu, puertos(by, 'ALU', pins[name])[0], name)
    cl.connect_port(alu, puertos(by, 'ALU', pins['Y'])[0], 'MAIN')
    cl.connect_port(alu, puertos(by, 'ALU', pins['ZERO'])[0], 'ZERO')

    conn('ADD', 0, 'A'); conn('ADD', 1, 'B')
    conn('SUB', 0, 'A'); conn('SUB', 1, 'B')
    conn('G_AND', 1, 'A'); conn('G_AND', 2, 'B')
    conn('G_OR', 1, 'A'); conn('G_OR', 2, 'B')
    conn('G_XA', 1, 'A'); conn('G_XA', 2, 'C_SIGN')
    conn('G_XB', 1, 'B'); conn('G_XB', 2, 'C_SIGN')
    conn('G_XA', 0, 'A_SIGN'); conn('G_XB', 0, 'B_SIGN')
    conn('CMP_SLT', 0, 'A_SIGN'); conn('CMP_SLT', 1, 'B_SIGN')
    conn('CMP_SLT', 4, 'LT')
    conn('EXT_LT', 1, 'LT')
    conn('SLL', 0, 'A'); conn('SLL', 1, 'SHAMT')
    conn('SRL', 0, 'A'); conn('SRL', 1, 'SHAMT')
    conn('SPL_SH', 0, 'B'); conn('SPL_SH', 1, 'SHAMT')
    conn('SPL_B16', 0, 'B'); conn('SPL_B16', 1, 'B16')
    conn('SPL_LUI', 0, 'LUI')
    conn('SPL_LUI', 1, 'Z16')
    conn('SPL_LUI', 2, 'B16')
    conn('C_Z16', 0, 'Z16')
    conn('C_Z32', 0, 'Z32')
    conn('C_SIGN', 0, 'C_SIGN')
    conn('MUX', 8, 'ALU_OP')

    for cid, label in (('ADD', 'ADD'), ('SUB', 'SUB'), ('G_AND', 'AND'),
                       ('G_OR', 'OR'), ('EXT_LT', 'SLT'), ('SLL', 'SLL'),
                       ('SRL', 'SRL')):
        conn(cid, 2 if cid in ('ADD', 'SUB', 'SLL', 'SRL') else 0, label)
    for i, label in enumerate(['ADD', 'SUB', 'AND', 'OR', 'SLT', 'SLL', 'SRL', 'LUI']):
        conn('MUX', i, label)
    conn('MUX', 9, 'MAIN')

    # ZERO = (MAIN == 0). El Comparator de Logisim es unsigned, pero solo se
    # usa la salida Equal, que no depende del signo.
    conn('CMP_Z', 0, 'MAIN'); conn('CMP_Z', 1, 'Z32'); conn('CMP_Z', 3, 'ZERO')
    return alu


def build_datapath(root):
    """Construye el Datapath del contrato 10.4."""
    inputs = [
        ('CLK', 1), ('RESET', 1), ('MEM_RDATA', 32),
        ('PC_WRITE', 1), ('PC_SRC', 2), ('IR_WRITE', 1),
        ('A_WRITE', 1), ('B_WRITE', 1), ('ALU_WRITE', 1), ('MDR_WRITE', 1),
        ('REG_WRITE', 1), ('RS1_SEL', 1), ('RS2_SEL', 1),
        ('ALU_SRC_A', 2), ('ALU_SRC_B', 2), ('ALU_OP', 3),
        ('MEM_ADDR_SEL', 1), ('EXT_TYPE', 2), ('REG_DST', 2),
        ('MEM_TO_REG', 2), ('MEM_SIZE', 2), ('MEM_SIGNED', 1),
        ('JUMP_TYPE', 2), ('MEM_WE', 1),
    ]
    outputs = [
        ('MEM_ADDR', 32), ('MEM_WDATA', 32), ('MEM_BE', 4),
        ('IR', 32), ('A', 32), ('B', 32), ('ALU_ZERO', 1), ('TTY_DATA', 7),
    ]
    dp, pins = cl.subcircuit(root, 'Datapath', inputs, outputs, 'Datapath',
                             x_in=120, x_out=400, y0=120, dy=40, width=280)

    items = [
        # id, nombre, col, fila, lib, attrs
        ('RF',        'Register_File', 0, 0, None, {}),
        ('ALU',       'ALU',           1, 0, None, {}),
        ('PC',        'Register',      2, 0, cl.MEMORY,
         dict(width=32, label='PC', appearance='logisim_evolution')),
        ('IR',        'Register',      3, 0, cl.MEMORY,
         dict(width=32, label='IR', appearance='logisim_evolution')),

        ('MUX_PC',    'Multiplexer',   0, 1, cl.PLEXERS, dict(width=32, select=2, selloc='tr')),
        ('MUX_RS1',   'Multiplexer',   1, 1, cl.PLEXERS, dict(width=5, select=1, selloc='tr')),
        ('A',         'Register',      2, 1, cl.MEMORY,
         dict(width=32, label='A', appearance='logisim_evolution')),
        ('B',         'Register',      3, 1, cl.MEMORY,
         dict(width=32, label='B', appearance='logisim_evolution')),

        ('MUX_ALUA',  'Multiplexer',   0, 2, cl.PLEXERS, dict(width=32, select=2, selloc='tr')),
        ('MUX_MEMADDR', 'Multiplexer', 1, 2, cl.PLEXERS, dict(width=32, select=1, selloc='tr')),
        ('ALUOUT',    'Register',      2, 2, cl.MEMORY,
         dict(width=32, label='ALUOUT', appearance='logisim_evolution')),
        ('MDR',       'Register',      3, 2, cl.MEMORY,
         dict(width=32, label='MDR', appearance='logisim_evolution')),

        ('MUX_ALUB',  'Multiplexer',   0, 3, cl.PLEXERS, dict(width=32, select=2, selloc='tr')),
        ('MUX_RS2',   'Multiplexer',   1, 3, cl.PLEXERS, dict(width=5, select=1, selloc='tr')),
        ('MUX_RD',    'Multiplexer',   2, 3, cl.PLEXERS, dict(width=5, select=2, selloc='tr')),
        ('MUX_WD',    'Multiplexer',   3, 3, cl.PLEXERS, dict(width=32, select=2, selloc='tr')),

        ('MUX_IMM',   'Multiplexer',   0, 4, cl.PLEXERS, dict(width=32, select=2, selloc='tr')),
        ('MUX_BYTE',  'Multiplexer',   1, 4, cl.PLEXERS, dict(width=8, select=2, selloc='tr')),
        ('MUX_SIGN',  'Multiplexer',   2, 4, cl.PLEXERS, dict(width=32, select=1, selloc='tr')),
        ('MUX_LOAD',  'Multiplexer',   3, 4, cl.PLEXERS, dict(width=32, select=2, selloc='tr')),
        ('MUX_WDATA', 'Multiplexer',   4, 4, cl.PLEXERS, dict(width=32, select=2, selloc='tr')),

        ('MUX_BE',    'Multiplexer',   0, 5, cl.PLEXERS, dict(width=4, select=2, selloc='tr')),
        ('SHIFT_BR',  'Shifter',       1, 5, cl.ARITH, dict(width=32, shift='ll')),
        ('SHIFT_BE',  'Shifter',       2, 5, cl.ARITH, dict(width=4, shift='ll')),
        ('AND_BE',    'AND Gate',      3, 5, cl.GATES, dict(width=4, inputs=2)),

        ('EXT_Z16',   'Bit Extender',  0, 6, cl.WIRING, dict(in_width=16, out_width=32, type='zero')),
        ('EXT_S16',   'Bit Extender',  1, 6, cl.WIRING, dict(in_width=16, out_width=32, type='sign')),
        ('EXT_Z5',    'Bit Extender',  2, 6, cl.WIRING, dict(in_width=5, out_width=32, type='zero')),
        ('EXT_Z8',    'Bit Extender',  3, 6, cl.WIRING, dict(in_width=8, out_width=32, type='zero')),
        ('EXT_S8',    'Bit Extender',  4, 6, cl.WIRING, dict(in_width=8, out_width=32, type='sign')),

        ('SPL_RS',    'Splitter',      0, 7, cl.WIRING,
         dict(incoming=32, fanout=1, appear='center', **bits((0, 21, 25)))),
        ('SPL_RT',    'Splitter',      1, 7, cl.WIRING,
         dict(incoming=32, fanout=1, appear='center', **bits((0, 16, 20)))),
        ('SPL_RD',    'Splitter',      2, 7, cl.WIRING,
         dict(incoming=32, fanout=1, appear='center', **bits((0, 11, 15)))),
        ('SPL_IMM',   'Splitter',      3, 7, cl.WIRING,
         dict(incoming=32, fanout=1, appear='center', **bits((0, 0, 15)))),
        ('SPL_SHAMT', 'Splitter',      4, 7, cl.WIRING,
         dict(incoming=32, fanout=1, appear='center', **bits((0, 6, 10)))),

        ('SPL_ALULO', 'Splitter',      0, 8, cl.WIRING,
         dict(incoming=32, fanout=1, appear='center', **bits((0, 0, 1)))),
        ('SPL_PCHI',  'Splitter',      1, 8, cl.WIRING,
         dict(incoming=32, fanout=1, appear='center', **bits((0, 28, 31)))),
        ('SPL_IR26',  'Splitter',      2, 8, cl.WIRING,
         dict(incoming=32, fanout=1, appear='center', **bits((0, 0, 25)))),
        ('SPL_JT',    'Splitter',      3, 8, cl.WIRING,
         dict(incoming=32, fanout=3, appear='center',
              **bits((0, 0, 1), (1, 2, 27), (2, 28, 31)))),
        ('SPL_MDR',   'Splitter',      4, 8, cl.WIRING,
         dict(incoming=32, fanout=4, appear='center',
              **bits((0, 0, 7), (1, 8, 15), (2, 16, 23), (3, 24, 31)))),
        ('SPL_B8',    'Splitter',      5, 8, cl.WIRING,
         dict(incoming=32, fanout=1, appear='center', **bits((0, 0, 7)))),

        ('SPL_REP_BYTE', 'Splitter',   0, 9, cl.WIRING,
         dict(incoming=32, fanout=4, appear='center',
              **bits((0, 0, 7), (1, 8, 15), (2, 16, 23), (3, 24, 31)))),
        ('SPL_B7',    'Splitter',      1, 9, cl.WIRING,
         dict(incoming=32, fanout=1, appear='center', **bits((0, 0, 6)))),
        ('SPL_BE_REP', 'Splitter',     2, 9, cl.WIRING,
         dict(incoming=4, fanout=4, appear='center',
              **bits((0, 0, 0), (1, 1, 1), (2, 2, 2), (3, 3, 3), incoming=4))),

        ('C4_32',     'Constant',      6, 0, cl.WIRING, dict(value='0x4', width=32)),
        ('Z32',       'Constant',      6, 1, cl.WIRING, dict(value='0x0', width=32)),
        ('C2_5',      'Constant',      6, 2, cl.WIRING, dict(value='0x2', width=5)),
        ('C4_5',      'Constant',      6, 3, cl.WIRING, dict(value='0x4', width=5)),
        ('C31_5',     'Constant',      6, 4, cl.WIRING, dict(value='0x1f', width=5)),
        ('Z5',        'Constant',      6, 5, cl.WIRING, dict(value='0x0', width=5)),
        ('Z2',        'Constant',      6, 6, cl.WIRING, dict(value='0x0', width=2)),
        ('WORD_MASK', 'Constant',      6, 7, cl.WIRING, dict(value='0xf', width=4)),
        ('ONE4',      'Constant',      6, 8, cl.WIRING, dict(value='0x1', width=4)),
    ]

    locs = {}
    for cid, name, col, row, lib, attrs in items:
        xy = (700 + col * 500, 300 + row * 260)
        cl.comp(dp, name, xy, lib, **attrs)
        locs[cid] = xy

    by = indice(cl.discover_ports(root))

    def conn(cid, idx, label, length=30):
        cl.connect_port(dp, puertos(by, 'Datapath', locs[cid])[idx], label, length)

    def conn_pin(name, label):
        cl.connect_port(dp, puertos(by, 'Datapath', pins[name])[0], label)

    # Pines del contrato 10.4. JUMP_TYPE se mantiene aunque no se use: PC_SRC
    # ya codifica j/jal/jr. Queda como entrada sin cable, sin efecto.
    for name in ('CLK', 'RESET', 'MEM_RDATA', 'PC_WRITE', 'PC_SRC', 'IR_WRITE',
                 'A_WRITE', 'B_WRITE', 'ALU_WRITE', 'MDR_WRITE', 'REG_WRITE',
                 'RS1_SEL', 'RS2_SEL', 'ALU_SRC_A', 'ALU_SRC_B', 'ALU_OP',
                 'MEM_ADDR_SEL', 'EXT_TYPE', 'REG_DST', 'MEM_TO_REG', 'MEM_SIZE',
                 'MEM_SIGNED', 'MEM_WE'):
        conn_pin(name, name)
    conn_pin('MEM_ADDR', 'MEM_ADDR')
    conn_pin('MEM_WDATA', 'MEM_WDATA')
    conn_pin('MEM_BE', 'MEM_BE')
    conn_pin('IR', 'D_IR')
    conn_pin('A', 'D_A')
    conn_pin('B', 'D_B')
    conn_pin('ALU_ZERO', 'D_ALU_ZERO')
    conn_pin('TTY_DATA', 'TTY_DATA')

    # Register_File: CLK, RESET, RS1, RS2, RD, WD, REG_WRITE, RD1, RD2.
    conn('RF', 0, 'CLK')
    conn('RF', 1, 'RESET')
    conn('RF', 2, 'RF_RS1')
    conn('RF', 3, 'RF_RS2')
    conn('RF', 4, 'RF_RD')
    conn('RF', 5, 'RF_WD')
    conn('RF', 6, 'REG_WRITE')
    conn('RF', 7, 'D_RD1')
    conn('RF', 8, 'D_RD2')

    # ALU: A, B, ALU_OP, Y, ZERO.
    conn('ALU', 0, 'D_ALU_A')
    conn('ALU', 1, 'D_ALU_B')
    conn('ALU', 2, 'ALU_OP')
    conn('ALU', 3, 'D_ALU_Y')
    conn('ALU', 4, 'D_ALU_ZERO')

    # Registros internos: out, data, CLK, clear, enable.
    conn('PC', 0, 'D_PC');   conn('PC', 1, 'D_PC_NEXT'); conn('PC', 2, 'CLK')
    conn('PC', 3, 'RESET');  conn('PC', 4, 'PC_WRITE')
    conn('IR', 0, 'D_IR');   conn('IR', 1, 'MEM_RDATA'); conn('IR', 2, 'CLK')
    conn('IR', 3, 'RESET');  conn('IR', 4, 'IR_WRITE')
    conn('A', 0, 'D_A');     conn('A', 1, 'D_RD1');     conn('A', 2, 'CLK')
    conn('A', 3, 'RESET');   conn('A', 4, 'A_WRITE')
    conn('B', 0, 'D_B');     conn('B', 1, 'D_RD2');     conn('B', 2, 'CLK')
    conn('B', 3, 'RESET');   conn('B', 4, 'B_WRITE')
    conn('ALUOUT', 0, 'D_ALUOUT'); conn('ALUOUT', 1, 'D_ALU_Y'); conn('ALUOUT', 2, 'CLK')
    conn('ALUOUT', 3, 'RESET');    conn('ALUOUT', 4, 'ALU_WRITE')
    conn('MDR', 0, 'D_MDR');  conn('MDR', 1, 'MEM_RDATA'); conn('MDR', 2, 'CLK')
    conn('MDR', 3, 'RESET');  conn('MDR', 4, 'MDR_WRITE')

    # PC_SRC=00 (FETCH) y 01 (BRANCH) usan la salida combinacional de la ALU.
    # 01 no puede leer ALUOUT: PC y ALUOUT capturan en el mismo flanco y PC
    # veria el destino de la rama anterior (docs/diseno.md 3.2/8.4).
    conn('MUX_PC', 0, 'D_ALU_Y')
    conn('MUX_PC', 1, 'D_ALU_Y')
    conn('MUX_PC', 2, 'D_JUMP_TARGET')
    conn('MUX_PC', 3, 'D_A')
    conn('MUX_PC', 4, 'PC_SRC')
    conn('MUX_PC', 5, 'D_PC_NEXT')

    # Mux de registros de lectura y destino.
    conn('MUX_RS1', 0, 'D_RS_FIELD'); conn('MUX_RS1', 1, 'D_C2_5')
    conn('MUX_RS1', 2, 'RS1_SEL');    conn('MUX_RS1', 3, 'RF_RS1')
    conn('MUX_RS2', 0, 'D_RT_FIELD'); conn('MUX_RS2', 1, 'D_C4_5')
    conn('MUX_RS2', 2, 'RS2_SEL');    conn('MUX_RS2', 3, 'RF_RS2')
    conn('MUX_RD', 0, 'D_RD_FIELD');  conn('MUX_RD', 1, 'D_RT_FIELD')
    conn('MUX_RD', 2, 'D_C31_5');     conn('MUX_RD', 3, 'D_Z5')
    conn('MUX_RD', 4, 'REG_DST');     conn('MUX_RD', 5, 'RF_RD')

    # Mux de operandos de la ALU.
    conn('MUX_ALUA', 0, 'D_A');  conn('MUX_ALUA', 1, 'D_PC')
    conn('MUX_ALUA', 2, 'D_B');  conn('MUX_ALUA', 3, 'D_Z32')
    conn('MUX_ALUA', 4, 'ALU_SRC_A'); conn('MUX_ALUA', 5, 'D_ALU_A')
    conn('MUX_ALUB', 0, 'D_B');  conn('MUX_ALUB', 1, 'D_IMM')
    conn('MUX_ALUB', 2, 'D_C4_32'); conn('MUX_ALUB', 3, 'D_Z32')
    conn('MUX_ALUB', 4, 'ALU_SRC_B'); conn('MUX_ALUB', 5, 'D_ALU_B')

    # Mux de direccion de memoria y writeback.
    conn('MUX_MEMADDR', 0, 'D_PC'); conn('MUX_MEMADDR', 1, 'D_ALUOUT')
    conn('MUX_MEMADDR', 2, 'MEM_ADDR_SEL'); conn('MUX_MEMADDR', 3, 'MEM_ADDR')

    conn('MUX_LOAD', 0, 'D_MDR'); conn('MUX_LOAD', 1, 'D_MDR_BYTE_EXT')
    conn('MUX_LOAD', 2, 'D_MDR_BYTE_EXT'); conn('MUX_LOAD', 3, 'D_MDR_BYTE_EXT')
    conn('MUX_LOAD', 4, 'MEM_SIZE'); conn('MUX_LOAD', 5, 'D_LOAD_DATA')

    conn('MUX_WD', 0, 'D_ALUOUT'); conn('MUX_WD', 1, 'D_LOAD_DATA')
    conn('MUX_WD', 2, 'D_PC');     conn('MUX_WD', 3, 'D_Z32')
    conn('MUX_WD', 4, 'MEM_TO_REG'); conn('MUX_WD', 5, 'RF_WD')

    # Extension de inmediato y seleccion por EXT_TYPE.
    conn('EXT_Z16', 1, 'D_IMM16'); conn('EXT_Z16', 0, 'D_IMM_ZEXT')
    conn('EXT_S16', 1, 'D_IMM16'); conn('EXT_S16', 0, 'D_IMM_SEXT')
    conn('EXT_Z5', 1, 'D_SHAMT5'); conn('EXT_Z5', 0, 'D_IMM_SHAMT')
    conn('SHIFT_BR', 0, 'D_IMM_SEXT'); conn('SHIFT_BR', 1, 'D_C2_5')
    conn('SHIFT_BR', 2, 'D_IMM_BRANCH')
    conn('MUX_IMM', 0, 'D_IMM_ZEXT'); conn('MUX_IMM', 1, 'D_IMM_SEXT')
    conn('MUX_IMM', 2, 'D_IMM_SHAMT'); conn('MUX_IMM', 3, 'D_IMM_BRANCH')
    conn('MUX_IMM', 4, 'EXT_TYPE'); conn('MUX_IMM', 5, 'D_IMM')

    # Campos de IR y JUMP_TARGET.
    conn('SPL_RS', 0, 'D_IR'); conn('SPL_RS', 1, 'D_RS_FIELD')
    conn('SPL_RT', 0, 'D_IR'); conn('SPL_RT', 1, 'D_RT_FIELD')
    conn('SPL_RD', 0, 'D_IR'); conn('SPL_RD', 1, 'D_RD_FIELD')
    conn('SPL_IMM', 0, 'D_IR'); conn('SPL_IMM', 1, 'D_IMM16')
    conn('SPL_SHAMT', 0, 'D_IR'); conn('SPL_SHAMT', 1, 'D_SHAMT5')

    conn('SPL_PCHI', 0, 'D_PC'); conn('SPL_PCHI', 1, 'D_PC_HI4')
    conn('SPL_IR26', 0, 'D_IR'); conn('SPL_IR26', 1, 'D_IR26')
    conn('SPL_JT', 0, 'D_JUMP_TARGET')
    conn('SPL_JT', 1, 'D_Z2')
    conn('SPL_JT', 2, 'D_IR26')
    conn('SPL_JT', 3, 'D_PC_HI4')

    # Carga de bytes: MDR -> byte segun ALUOUT[1:0] -> extension.
    conn('SPL_ALULO', 0, 'D_ALUOUT'); conn('SPL_ALULO', 1, 'D_ALUOUT_LO2')
    conn('SPL_MDR', 0, 'D_MDR')
    conn('SPL_MDR', 1, 'D_MDR_B0'); conn('SPL_MDR', 2, 'D_MDR_B1')
    conn('SPL_MDR', 3, 'D_MDR_B2'); conn('SPL_MDR', 4, 'D_MDR_B3')
    conn('MUX_BYTE', 0, 'D_MDR_B0'); conn('MUX_BYTE', 1, 'D_MDR_B1')
    conn('MUX_BYTE', 2, 'D_MDR_B2'); conn('MUX_BYTE', 3, 'D_MDR_B3')
    conn('MUX_BYTE', 4, 'D_ALUOUT_LO2'); conn('MUX_BYTE', 5, 'D_MDR_BYTE')
    conn('EXT_Z8', 1, 'D_MDR_BYTE'); conn('EXT_Z8', 0, 'D_MDR_BYTE_ZEXT')
    conn('EXT_S8', 1, 'D_MDR_BYTE'); conn('EXT_S8', 0, 'D_MDR_BYTE_SEXT')
    conn('MUX_SIGN', 0, 'D_MDR_BYTE_ZEXT'); conn('MUX_SIGN', 1, 'D_MDR_BYTE_SEXT')
    conn('MUX_SIGN', 2, 'MEM_SIGNED'); conn('MUX_SIGN', 3, 'D_MDR_BYTE_EXT')

    # MEM_WDATA y MEM_BE.
    conn('SPL_B8', 0, 'D_B'); conn('SPL_B8', 1, 'D_B_LO8')
    conn('SPL_REP_BYTE', 0, 'D_BYTE_REP')
    conn('SPL_REP_BYTE', 1, 'D_B_LO8'); conn('SPL_REP_BYTE', 2, 'D_B_LO8')
    conn('SPL_REP_BYTE', 3, 'D_B_LO8'); conn('SPL_REP_BYTE', 4, 'D_B_LO8')
    conn('SPL_B7', 0, 'D_B'); conn('SPL_B7', 1, 'TTY_DATA')

    conn('MUX_WDATA', 0, 'D_B'); conn('MUX_WDATA', 1, 'D_BYTE_REP')
    conn('MUX_WDATA', 2, 'D_BYTE_REP'); conn('MUX_WDATA', 3, 'D_BYTE_REP')
    conn('MUX_WDATA', 4, 'MEM_SIZE'); conn('MUX_WDATA', 5, 'MEM_WDATA')

    conn('SHIFT_BE', 0, 'D_ONE4'); conn('SHIFT_BE', 1, 'D_ALUOUT_LO2')
    conn('SHIFT_BE', 2, 'D_BYTE_MASK')
    conn('MUX_BE', 0, 'D_WORD_MASK'); conn('MUX_BE', 1, 'D_BYTE_MASK')
    conn('MUX_BE', 2, 'D_BYTE_MASK'); conn('MUX_BE', 3, 'D_BYTE_MASK')
    conn('MUX_BE', 4, 'MEM_SIZE'); conn('MUX_BE', 5, 'D_MEM_BE_MASK')
    conn('SPL_BE_REP', 0, 'D_MEM_WE4')
    conn('SPL_BE_REP', 1, 'MEM_WE'); conn('SPL_BE_REP', 2, 'MEM_WE')
    conn('SPL_BE_REP', 3, 'MEM_WE'); conn('SPL_BE_REP', 4, 'MEM_WE')
    conn('AND_BE', 1, 'D_MEM_BE_MASK'); conn('AND_BE', 2, 'D_MEM_WE4')
    conn('AND_BE', 0, 'MEM_BE')

    for cid, label in (('C4_32', 'D_C4_32'), ('Z32', 'D_Z32'), ('C2_5', 'D_C2_5'),
                       ('C4_5', 'D_C4_5'), ('C31_5', 'D_C31_5'), ('Z5', 'D_Z5'),
                       ('Z2', 'D_Z2'), ('WORD_MASK', 'D_WORD_MASK'),
                       ('ONE4', 'D_ONE4')):
        conn(cid, 0, label)
    return dp


def main():
    # 1. Construir ALU y Datapath en un proyecto temporal en memoria.
    root = cl.new_project('Datapath')
    build_alu(root)

    # La entidad VHDL se embebe en el proyecto; Logisim la resuelve por nombre
    # y el componente se instancia sin atributo lib.
    vhd = E.SubElement(root, 'vhdl', {'appearance': 'logisim_evolution', 'name': 'Register_File'})
    vhd.text = VHDL.read_text(encoding='utf-8')

    build_datapath(root)

    # 2. Fusionar sobre el entregable, conservando Board, Memory y CPU (R2).
    base = cl.load(SALIDA)
    for viejo in list(base.findall('vhdl')):
        if viejo.get('name') == 'Register_File':
            base.remove(viejo)
    base.append(copy.deepcopy(vhd))

    cl.merge_circuits(base, root, ['ALU', 'Datapath'])
    cl.save(base, SALIDA)
    print(f'OK: ALU y Datapath fusionados en {SALIDA}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

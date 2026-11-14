#!/usr/bin/env python3
"""Construye Control_Unit (FSM Moore) y lo fusiona en circuit/smips.circ.

Todos los componentes declarados en items[] para que discover_ports los vea.
"""
import sys
sys.path.insert(0, r'D:\EscuelaLuisi\AC\Proyecto\Proyecto-S-MIPS-2026-2027\tools')
import copy
import circuitlib as cl

ROOT = r'D:\EscuelaLuisi\AC\Proyecto\Proyecto-S-MIPS-2026-2027'
SALIDA = ROOT + r'\circuit\smips.circ'

S = {
    'FETCH':      0b0000,
    'DECODE':     0b0001,
    'EXEC_R':     0b0010,
    'EXEC_I':     0b0011,
    'ADDR':       0b0100,
    'MEM_READ':   0b0101,
    'MEM_WRITE':  0b0110,
    'BRANCH':     0b0111,
    'JUMP':       0b1000,
    'SYSCALL':    0b1001,
    'WB':         0b1010,
    'HALT':       0b1011,
}


def bits(*ranges, incoming=32):
    out = {f'bit{i}': 'none' for i in range(incoming)}
    for idx, lo, hi in ranges:
        for i in range(lo, hi + 1):
            out[f'bit{i}'] = str(idx)
    return out


def indice(rows):
    by = {}
    for r in rows:
        by.setdefault(r['circuit'], {}).setdefault(r['loc'], []).append(r)
    return by


def puertos(by, circuito, xy):
    key = f'({xy[0]},{xy[1]})' if isinstance(xy, tuple) else xy
    return sorted(by[circuito][key], key=lambda r: r['index'])


def build_control_unit(root):
    cu, pins = cl.subcircuit(
        root, 'Control_Unit',
        [
            ('CLK', 1), ('RESET', 1),
            ('ILLEGAL', 1), ('IS_RTYPE', 1), ('IS_ITYPE', 1), ('IS_JTYPE', 1),
            ('ALU_OP_DEC', 3), ('EXT_TYPE_DEC', 2), ('MEM_READ', 1), ('MEM_WRITE', 1),
            ('MEM_SIZE_DEC', 2), ('MEM_SIGNED_DEC', 1),
            ('BRANCH_TYPE_DEC', 2), ('JUMP_TYPE_DEC', 2),
            ('REG_WRITE_ENABLE', 1), ('REG_DST_DEC', 2), ('MEM_TO_REG_DEC', 2),
            ('SYS_CALL', 1), ('LUI_OP', 1), ('A', 32),
        ],
        [
            ('PC_WRITE_CTL', 1), ('PC_SRC', 2), ('IR_WRITE', 1),
            ('A_WRITE', 1), ('B_WRITE', 1), ('ALU_WRITE', 1), ('MDR_WRITE', 1),
            ('REG_WRITE', 1), ('RS1_SEL', 1), ('RS2_SEL', 1),
            ('ALU_SRC_A', 2), ('ALU_SRC_B', 2), ('ALU_OP', 3),
            ('MEM_ADDR_SEL', 1), ('BRANCH_ENABLE', 1), ('MEM_WE', 1),
            ('TTY_WE', 1), ('HALT', 1),
            ('EXT_TYPE', 2), ('REG_DST', 2), ('MEM_TO_REG', 2),
            ('MEM_SIZE', 2), ('MEM_SIGNED', 1), ('BRANCH_TYPE', 2), ('JUMP_TYPE', 2),
        ],
        'Control_Unit', x_in=120, x_out=400, y0=60, dy=35, width=280)

    items = [
        ('STATE_REG', 'Register', 0, 0, cl.MEMORY,
         dict(width=4, label='STATE', appearance='logisim_evolution')),
    ]
    for i, (n, v) in enumerate(S.items()):
        items.append((f'C_{n}', 'Constant', i, 0, cl.WIRING,
                      dict(value=f'0x{v:x}', width=4)))
    for i, n in enumerate(S.keys()):
        items.append((f'CMP_{n}', 'Comparator', i, 1, cl.ARITH, dict(width=4)))
    items.append(('MUX_NEXT', 'Multiplexer', 0, 2, cl.PLEXERS,
                  dict(width=4, select=4, selloc='tr')))
    items.append(('NOT_RESET', 'NOT Gate', 0, 3, cl.GATES, dict(width=1)))
    for i, n in enumerate(S.keys()):
        items.append((f'EN_{n}', 'AND Gate', i, 3, cl.GATES,
                      dict(width=1, inputs=2)))
    items.append(('PC_WRITE_CTL_LOGIC', 'OR Gate', 0, 4, cl.GATES,
                  dict(width=1, inputs=2)))
    items.append(('MUX_PC_SRC', 'Multiplexer', 1, 4, cl.PLEXERS,
                  dict(width=2, select=4, selloc='tr')))
    items.append(('NOT_ILLEGAL', 'NOT Gate', 2, 4, cl.GATES, dict(width=1)))
    items.append(('A_WRITE_LOGIC', 'AND Gate', 3, 4, cl.GATES,
                  dict(width=1, inputs=2)))
    items.append(('B_WRITE_LOGIC', 'AND Gate', 4, 4, cl.GATES,
                  dict(width=1, inputs=2)))
    items.append(('ALU_WRITE_LOGIC', 'OR Gate', 5, 4, cl.GATES,
                  dict(width=1, inputs=4)))
    items.append(('C_JAL', 'Constant', 0, 5, cl.WIRING, dict(value='0x2', width=2)))
    items.append(('CMP_JAL', 'Comparator', 1, 5, cl.ARITH, dict(width=2)))
    items.append(('JAL_COND', 'AND Gate', 2, 5, cl.GATES, dict(width=1, inputs=2)))
    items.append(('WB_REG_WR', 'AND Gate', 3, 5, cl.GATES, dict(width=1, inputs=2)))
    items.append(('REG_WRITE_LOGIC', 'OR Gate', 4, 5, cl.GATES,
                  dict(width=1, inputs=2)))
    items.append(('RS1_SEL_LOGIC', 'AND Gate', 5, 5, cl.GATES,
                  dict(width=1, inputs=2)))
    items.append(('RS2_SEL_LOGIC', 'AND Gate', 6, 5, cl.GATES,
                  dict(width=1, inputs=2)))
    items.append(('MUX_ALU_SRC_A', 'Multiplexer', 0, 6, cl.PLEXERS,
                  dict(width=2, select=4, selloc='tr')))
    items.append(('MUX_ALU_SRC_B', 'Multiplexer', 1, 6, cl.PLEXERS,
                  dict(width=2, select=4, selloc='tr')))
    items.append(('MUX_ALU_OP', 'Multiplexer', 2, 6, cl.PLEXERS,
                  dict(width=3, select=4, selloc='tr')))
    items.append(('MEM_ADDR_SEL_LOGIC', 'OR Gate', 3, 6, cl.GATES,
                  dict(width=1, inputs=2)))
    items.append(('C_SYS11', 'Constant', 0, 7, cl.WIRING, dict(value='0xb', width=32)))
    items.append(('CMP_SYS11', 'Comparator', 1, 7, cl.ARITH, dict(width=32)))
    items.append(('SYS11_COND', 'AND Gate', 2, 7, cl.GATES, dict(width=1, inputs=2)))
    items.append(('TTY_WE_LOGIC', 'OR Gate', 3, 7, cl.GATES, dict(width=1, inputs=1)))
    items.append(('C_SYS10', 'Constant', 4, 7, cl.WIRING, dict(value='0xa', width=32)))
    items.append(('CMP_SYS10', 'Comparator', 5, 7, cl.ARITH, dict(width=32)))
    items.append(('SYS10_COND', 'AND Gate', 6, 7, cl.GATES, dict(width=1, inputs=2)))
    items.append(('ILL_COND', 'AND Gate', 7, 7, cl.GATES, dict(width=1, inputs=2)))
    items.append(('HALT_LOGIC', 'OR Gate', 8, 7, cl.GATES, dict(width=1, inputs=3)))
    items.append(('C_Z2', 'Constant', 0, 8, cl.WIRING, dict(value='0x0', width=2)))
    items.append(('C_PC10', 'Constant', 1, 8, cl.WIRING, dict(value='0x1', width=2)))
    items.append(('C_ALU4', 'Constant', 2, 8, cl.WIRING, dict(value='0x2', width=2)))
    items.append(('C_ALU0', 'Constant', 3, 8, cl.WIRING, dict(value='0x0', width=3)))
    items.append(('C_Z3', 'Constant', 4, 8, cl.WIRING, dict(value='0x0', width=3)))

    locs = {}
    for cid, name, col, row, lib, attrs in items:
        xy = (700 + col * 450, 200 + row * 200)
        cl.comp(cu, name, xy, lib, **attrs)
        locs[cid] = xy

    by = indice(cl.discover_ports(root))

    def conn(cid, idx, label, length=30):
        cl.connect_port(cu, puertos(by, 'Control_Unit', locs[cid])[idx], label, length)

    def conn_pin(name, label):
        cl.connect_port(cu, puertos(by, 'Control_Unit', pins[name])[0], label)

    for name in ('CLK', 'RESET', 'ILLEGAL', 'IS_RTYPE', 'IS_ITYPE', 'IS_JTYPE',
                 'ALU_OP_DEC', 'EXT_TYPE_DEC', 'MEM_READ', 'MEM_WRITE',
                 'MEM_SIZE_DEC', 'MEM_SIGNED_DEC', 'BRANCH_TYPE_DEC', 'JUMP_TYPE_DEC',
                 'REG_WRITE_ENABLE', 'REG_DST_DEC', 'MEM_TO_REG_DEC',
                 'SYS_CALL', 'LUI_OP'):
        conn_pin(name, name)
    conn_pin('A', 'A_IN')

    for name in ('PC_WRITE_CTL', 'PC_SRC', 'IR_WRITE', 'A_WRITE', 'B_WRITE',
                 'ALU_WRITE', 'MDR_WRITE', 'REG_WRITE', 'RS1_SEL', 'RS2_SEL',
                 'ALU_SRC_A', 'ALU_SRC_B', 'ALU_OP', 'MEM_ADDR_SEL',
                 'BRANCH_ENABLE', 'MEM_WE', 'TTY_WE', 'HALT'):
        conn_pin(name, name)

    for name in ('EXT_TYPE', 'REG_DST', 'MEM_TO_REG', 'MEM_SIZE',
                 'MEM_SIGNED', 'BRANCH_TYPE', 'JUMP_TYPE'):
        conn_pin(name, name)
        conn_pin(f'{name}_DEC', name)

    conn('MUX_NEXT', 0, 'NEXT_STATE')
    conn('STATE_REG', 1, 'NEXT_STATE')
    conn('STATE_REG', 2, 'CLK')
    conn('STATE_REG', 3, 'RESET')

    for n in S.keys():
        conn(f'CMP_{n}', 0, 'STATE')
        conn(f'CMP_{n}', 1, f'C_{n}')
        conn(f'CMP_{n}', 3, f'EQ_{n}')

    conn('NOT_RESET', 1, 'RESET')
    conn('NOT_RESET', 0, 'RESET_L')

    for n in S.keys():
        conn(f'EN_{n}', 1, f'EQ_{n}')
        conn(f'EN_{n}', 2, 'RESET_L')
        conn(f'EN_{n}', 0, f'EN_{n}')

    conn('PC_WRITE_CTL_LOGIC', 1, 'EN_FETCH')
    conn('PC_WRITE_CTL_LOGIC', 2, 'EN_JUMP')
    conn('PC_WRITE_CTL_LOGIC', 0, 'PC_WRITE_CTL')

    conn('EN_FETCH', 0, 'IR_WRITE')

    conn('A_WRITE_LOGIC', 1, 'EN_DECODE')
    conn('A_WRITE_LOGIC', 2, 'NOT_ILLEGAL')
    conn('A_WRITE_LOGIC', 0, 'A_WRITE')

    conn('B_WRITE_LOGIC', 1, 'EN_DECODE')
    conn('B_WRITE_LOGIC', 2, 'NOT_ILLEGAL')
    conn('B_WRITE_LOGIC', 0, 'B_WRITE')

    conn('ALU_WRITE_LOGIC', 1, 'EN_EXEC_R')
    conn('ALU_WRITE_LOGIC', 2, 'EN_EXEC_I')
    conn('ALU_WRITE_LOGIC', 3, 'EN_ADDR')
    conn('ALU_WRITE_LOGIC', 4, 'EN_BRANCH')
    conn('ALU_WRITE_LOGIC', 0, 'ALU_WRITE')

    conn('EN_MEM_READ', 0, 'MDR_WRITE')

    conn('WB_REG_WR', 1, 'EN_WB')
    conn('WB_REG_WR', 2, 'REG_WRITE_ENABLE')
    conn('WB_REG_WR', 0, 'WB_REG_WR_OUT')
    conn('JAL_COND', 1, 'EN_JUMP')
    conn('CMP_JAL', 0, 'JUMP_TYPE_DEC')
    conn('CMP_JAL', 1, 'C_JAL')
    conn('CMP_JAL', 3, 'EQ_JAL')
    conn('JAL_COND', 2, 'EQ_JAL')
    conn('JAL_COND', 0, 'JAL_OUT')
    conn('REG_WRITE_LOGIC', 1, 'WB_REG_WR_OUT')
    conn('REG_WRITE_LOGIC', 2, 'JAL_OUT')
    conn('REG_WRITE_LOGIC', 0, 'REG_WRITE')

    conn('RS1_SEL_LOGIC', 1, 'EN_DECODE')
    conn('RS1_SEL_LOGIC', 2, 'SYS_CALL')
    conn('RS1_SEL_LOGIC', 0, 'RS1_SEL')

    conn('RS2_SEL_LOGIC', 1, 'EN_DECODE')
    conn('RS2_SEL_LOGIC', 2, 'SYS_CALL')
    conn('RS2_SEL_LOGIC', 0, 'RS2_SEL')

    conn('MEM_ADDR_SEL_LOGIC', 1, 'EN_MEM_READ')
    conn('MEM_ADDR_SEL_LOGIC', 2, 'EN_MEM_WRITE')
    conn('MEM_ADDR_SEL_LOGIC', 0, 'MEM_ADDR_SEL')

    conn('EN_BRANCH', 0, 'BRANCH_ENABLE')
    conn('EN_MEM_WRITE', 0, 'MEM_WE')

    conn('CMP_SYS11', 0, 'A_IN')
    conn('CMP_SYS11', 1, 'C_SYS11')
    conn('CMP_SYS11', 3, 'EQ_SYS11')
    conn('SYS11_COND', 1, 'EN_SYSCALL')
    conn('SYS11_COND', 2, 'EQ_SYS11')
    conn('SYS11_COND', 0, 'TTY_WE')

    conn('CMP_SYS10', 0, 'A_IN')
    conn('CMP_SYS10', 1, 'C_SYS10')
    conn('CMP_SYS10', 3, 'EQ_SYS10')
    conn('SYS10_COND', 1, 'EN_SYSCALL')
    conn('SYS10_COND', 2, 'EQ_SYS10')
    conn('SYS10_COND', 0, 'SYS10_OUT')
    conn('ILL_COND', 1, 'EN_DECODE')
    conn('ILL_COND', 2, 'ILLEGAL')
    conn('ILL_COND', 0, 'ILL_OUT')
    conn('HALT_LOGIC', 1, 'EN_HALT')
    conn('HALT_LOGIC', 2, 'SYS10_OUT')
    conn('HALT_LOGIC', 3, 'ILL_OUT')
    conn('HALT_LOGIC', 0, 'HALT')

    for n in S.keys():
        conn(f'C_{n}', 0, f'C_{n}')
    for i, n in enumerate(S.keys()):
        conn('MUX_NEXT', i, f'C_{n}')
    for i in range(12, 16):
        conn('MUX_NEXT', i, 'C_HALT')

    conn('MUX_PC_SRC', 0, 'C_Z2')
    conn('MUX_PC_SRC', 1, 'C_Z2')
    conn('MUX_PC_SRC', 2, 'C_Z2')
    conn('MUX_PC_SRC', 3, 'C_Z2')
    conn('MUX_PC_SRC', 4, 'C_Z2')
    conn('MUX_PC_SRC', 5, 'C_Z2')
    conn('MUX_PC_SRC', 6, 'C_Z2')
    conn('MUX_PC_SRC', 7, 'C_Z2')
    conn('MUX_PC_SRC', 8, 'C_PC10')
    conn('MUX_PC_SRC', 9, 'C_Z2')
    conn('MUX_PC_SRC', 10, 'C_Z2')
    conn('MUX_PC_SRC', 11, 'C_Z2')
    for i in range(12, 16):
        conn('MUX_PC_SRC', i, 'C_Z2')

    conn('MUX_ALU_SRC_A', 0, 'C_PC10')
    conn('MUX_ALU_SRC_A', 1, 'C_Z2')
    conn('MUX_ALU_SRC_A', 2, 'C_Z2')
    conn('MUX_ALU_SRC_A', 3, 'C_Z2')
    conn('MUX_ALU_SRC_A', 4, 'C_Z2')
    conn('MUX_ALU_SRC_A', 5, 'C_Z2')
    conn('MUX_ALU_SRC_A', 6, 'C_Z2')
    conn('MUX_ALU_SRC_A', 7, 'C_PC10')
    conn('MUX_ALU_SRC_A', 8, 'C_Z2')
    conn('MUX_ALU_SRC_A', 9, 'C_Z2')
    conn('MUX_ALU_SRC_A', 10, 'C_Z2')
    conn('MUX_ALU_SRC_A', 11, 'C_Z2')
    for i in range(12, 16):
        conn('MUX_ALU_SRC_A', i, 'C_Z2')

    conn('MUX_ALU_SRC_B', 0, 'C_ALU4')
    conn('MUX_ALU_SRC_B', 1, 'C_Z2')
    conn('MUX_ALU_SRC_B', 2, 'C_ALU4')
    conn('MUX_ALU_SRC_B', 3, 'C_ALU4')
    conn('MUX_ALU_SRC_B', 4, 'C_ALU4')
    conn('MUX_ALU_SRC_B', 5, 'C_Z2')
    conn('MUX_ALU_SRC_B', 6, 'C_Z2')
    conn('MUX_ALU_SRC_B', 7, 'C_ALU4')
    conn('MUX_ALU_SRC_B', 8, 'C_Z2')
    conn('MUX_ALU_SRC_B', 9, 'C_Z2')
    conn('MUX_ALU_SRC_B', 10, 'C_Z2')
    conn('MUX_ALU_SRC_B', 11, 'C_Z2')

    conn('MUX_ALU_OP', 0, 'C_ALU0')
    conn('MUX_ALU_OP', 1, 'C_Z3')
    conn('MUX_ALU_OP', 2, 'ALU_OP_DEC')
    conn('MUX_ALU_OP', 3, 'ALU_OP_DEC')
    conn('MUX_ALU_OP', 4, 'C_ALU0')
    conn('MUX_ALU_OP', 5, 'C_Z3')
    conn('MUX_ALU_OP', 6, 'C_Z3')
    conn('MUX_ALU_OP', 7, 'C_ALU0')
    conn('MUX_ALU_OP', 8, 'C_Z3')
    conn('MUX_ALU_OP', 9, 'C_Z3')
    conn('MUX_ALU_OP', 10, 'C_Z3')
    conn('MUX_ALU_OP', 11, 'C_Z3')

    return cu


def main():
    root = cl.new_project('Control_Unit')
    build_control_unit(root)

    base = cl.load(SALIDA)
    cl.merge_circuits(base, root, ['Control_Unit'])
    cl.save(base, SALIDA)
    print(f'OK: Control_Unit fusionado en {SALIDA}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

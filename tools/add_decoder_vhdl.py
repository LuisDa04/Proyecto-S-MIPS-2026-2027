#!/usr/bin/env python3
"""Agrega la entidad VHDL Instruction_Decoder a circuit/smips.circ."""
import sys
sys.path.insert(0, r'D:\EscuelaLuisi\AC\Proyecto\Proyecto-S-MIPS-2026-2027\tools')
import circuitlib as cl
import xml.etree.ElementTree as E

ROOT = r'D:\EscuelaLuisi\AC\Proyecto\Proyecto-S-MIPS-2026-2027'
SALIDA = ROOT + r'\circuit\smips.circ'

# Leer el archivo VHDL
vhdl_path = ROOT + r'\circuit\instruction_decoder.vhd'
with open(vhdl_path, 'r', encoding='utf-8') as f:
    vhdl_content = f.read()

root = cl.load(SALIDA)

# Verificar si ya existe
existing = root.find('./vhdl[@name="Instruction_Decoder"]')
if existing is not None:
    print('Instruction_Decoder ya existe en smips.circ')
    sys.exit(0)

# Crear el elemento vhdl
vhdl = E.SubElement(root, 'vhdl', {'appearance': 'logisim_evolution', 'name': 'Instruction_Decoder'})
vhdl.text = '\n' + vhdl_content + '\n'

cl.save(root, SALIDA)
print(f'OK: Instruction_Decoder VHDL agregado a {SALIDA}')

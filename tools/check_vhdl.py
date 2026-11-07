#!/usr/bin/env python3
"""Analiza, comprueba y ejecuta el VHDL del proyecto con GHDL.

Uso:
    python tools/check_vhdl.py [--ghdl RUTA] [--std 02] [--stop-time 1us] [--lint]

Hace, en un directorio temporal:
  1. Analiza con `--std=02 --warn-all` el VHDL de `circuit/`, el wrapper
     capturado en `docs/contrato-logisim/` y los testbenches de `tests/vhdl/`.
  2. Elabora y ejecuta cada entidad `*_tb` con `--assert-level=error` y
     `--stop-time` (los testbenches terminan con `wait;` y el reloj no para).
  3. Exige que la ejecucion imprima `TB_OK` y devuelva 0.

Con `--lint` ademas revisa el VHDL sintetizable de `circuit/` (R19/R20):
  * solo ieee.std_logic_1164 e ieee.numeric_std;
  * sin wait, after, assert, report ni file;
  * sin valores iniciales en señales;
  * puertos de Register_File con los nombres, sentidos y anchos del contrato.

Devuelve 0 si todo pasa y 1 si hay cualquier error.
"""
from pathlib import Path
import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent
CIRCUIT = ROOT / 'circuit'
CONTRACT = ROOT / 'docs' / 'contrato-logisim'
TESTS = ROOT / 'tests' / 'vhdl'

GHDL_CANDIDATOS = [
    os.environ.get('GHDL'),
    r'D:\EscuelaLuisi\AC\GHDL\bin\ghdl.exe',
    shutil.which('ghdl'),
]

# Contrato congelado en la Fase 0 (docs/contrato-logisim/README.md).
CONTRATO = {
    'Register_File': {
        'CLK': ('in', 1),
        'RESET': ('in', 1),
        'RS1': ('in', 5),
        'RS2': ('in', 5),
        'RD': ('in', 5),
        'WD': ('in', 32),
        'REG_WRITE': ('in', 1),
        'RD1': ('out', 32),
        'RD2': ('out', 32),
    },
}

LIBRERIAS_OK = {'ieee.std_logic_1164', 'ieee.numeric_std'}
PROHIBIDO = ('wait', 'after', 'assert', 'report', 'file')


def localizar_ghdl(preferido):
    for candidato in [preferido, *GHDL_CANDIDATOS]:
        if not candidato:
            continue
        ruta = Path(candidato)
        if ruta.exists():
            return str(ruta)
        if shutil.which(candidato):
            return candidato
    return None


def sin_comentarios(texto):
    return '\n'.join(linea.split('--', 1)[0] for linea in texto.splitlines())


def entidades(texto):
    return re.findall(r'\bentity\s+(\w+)\s+is\b', texto, re.IGNORECASE)


def puertos(texto, entidad):
    """Devuelve {nombre: (sentido, ancho)} del bloque port de una entidad."""
    limpio = sin_comentarios(texto)
    patron_entidad = re.search(
        rf'\bentity\s+{re.escape(entidad)}\s+is\b(.*?)\bend\s+(?:entity\b)?',
        limpio, re.IGNORECASE | re.DOTALL)
    if not patron_entidad:
        return None
    apertura = re.search(r'\bport\s*\(', patron_entidad.group(1), re.IGNORECASE)
    if not apertura:
        return {}
    # Los tipos std_logic_vector(4 downto 0) llevan parentesis propios: hay que
    # localizar el parentesis de cierre del bloque port, no el primero.
    inicio = apertura.end()
    nivel = 1
    fin = inicio
    while fin < len(patron_entidad.group(1)) and nivel:
        if patron_entidad.group(1)[fin] == '(':
            nivel += 1
        elif patron_entidad.group(1)[fin] == ')':
            nivel -= 1
        fin += 1
    if nivel:
        return None
    bloque = patron_entidad.group(1)[inicio:fin - 1]
    salida = {}
    patron = re.compile(
        r'(\w+)\s*:\s*(in|out|inout)\s+'
        r'(std_logic_vector\s*\(\s*(\d+)\s+downto\s+(\d+)\s*\)|std_logic)',
        re.IGNORECASE)
    for m in patron.finditer(bloque):
        nombre = m.group(1).upper()
        sentido = m.group(2).lower()
        if m.group(3).lower() == 'std_logic':
            ancho = 1
        else:
            ancho = abs(int(m.group(4)) - int(m.group(5))) + 1
        salida[nombre] = (sentido, ancho)
    return salida


def lint_archivo(path, errores):
    texto = sin_comentarios(path.read_text(encoding='utf-8'))
    bajo = texto.lower()
    nombre = path.relative_to(ROOT).as_posix()

    for palabra in PROHIBIDO:
        if re.search(rf'\b{palabra}\b', bajo):
            errores.append(f'R20: {nombre} usa {palabra!r} (prohibido en VHDL sintetizable)')

    if re.search(r'\bsignal\b[^;]*:=', bajo):
        errores.append(f'R20: {nombre} da valor inicial a una señal')

    for uso in re.findall(r'\buse\s+([\w.]+)\s*;', bajo):
        base = uso[:-4] if uso.endswith('.all') else uso
        if base not in LIBRERIAS_OK and base != 'work':
            errores.append(f'R19: {nombre} importa {uso} (solo std_logic_1164 y numeric_std)')

    for entidad, esperado in CONTRATO.items():
        if entidad.lower() not in [e.lower() for e in entidades(texto)]:
            continue
        real = puertos(texto, entidad)
        if real is None:
            continue
        for puerto, (sentido, ancho) in esperado.items():
            if puerto not in real:
                errores.append(f'R16: {nombre}: falta el puerto {puerto} de {entidad}')
            elif real[puerto] != (sentido, ancho):
                errores.append(
                    f'R16: {nombre}: {entidad}.{puerto} es {real[puerto]}, '
                    f'se esperaba {(sentido, ancho)}')
        for puerto in real:
            if puerto not in esperado:
                errores.append(f'R16: {nombre}: {entidad} tiene un puerto de mas: {puerto}')


def ejecutar(orden, cwd):
    return subprocess.run(orden, cwd=cwd, capture_output=True, text=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--ghdl', default=None, help='ruta a ghdl (por defecto GHDL o PATH)')
    parser.add_argument('--std', default='02', help='estandar VHDL (por defecto 02)')
    parser.add_argument('--stop-time', default='1us', help='limite de simulacion (por defecto 1us)')
    parser.add_argument('--lint', action='store_true', help='revisa R19/R20 y el contrato de puertos')
    args = parser.parse_args()

    ghdl = localizar_ghdl(args.ghdl)
    if not ghdl:
        print('ERROR: no se encontro ghdl; pase --ghdl o defina GHDL')
        return 2

    sintetizable = sorted(CIRCUIT.glob('*.vhd')) + sorted(CIRCUIT.glob('*.vhdl'))
    contrato = sorted(CONTRACT.glob('*.vhdl')) + sorted(CONTRACT.glob('*.vhd'))
    testbenches = sorted(TESTS.glob('*_tb.vhd')) + sorted(TESTS.glob('*_tb.vhdl'))

    # docs/contrato-logisim guarda el stub con el que se capturo el contrato.
    # Si el circuito ya define esa entidad, el stub no debe analizarse: en la
    # misma libreria work sobrescribiria el diseno real.
    definidas = set()
    for path in sintetizable:
        definidas.update(e.lower() for e in entidades(path.read_text(encoding='utf-8')))
    contrato = [
        path for path in contrato
        if not (set(e.lower() for e in entidades(path.read_text(encoding='utf-8'))) & definidas)
    ]

    fuentes = sintetizable + contrato + testbenches

    errores = []
    if not sintetizable:
        errores.append('no hay VHDL en circuit/')
    if not testbenches:
        errores.append('no hay testbenches en tests/vhdl/')
    if args.lint:
        for path in sintetizable:
            lint_archivo(path, errores)
    if errores:
        for e in errores:
            print(f'ERROR: {e}')
        return 1

    print(f'GHDL: {ghdl}')
    with tempfile.TemporaryDirectory(prefix='smips-vhdl-') as temporal:
        for path in fuentes:
            resultado = ejecutar(
                [ghdl, '-a', f'--std={args.std}', '--warn-all', str(path)], temporal)
            if resultado.returncode:
                print(f'ERROR: no analiza {path.relative_to(ROOT).as_posix()}')
                print((resultado.stdout + resultado.stderr).strip())
                errores.append(f'analisis de {path.name}')
            else:
                print(f'OK   analiza {path.relative_to(ROOT).as_posix()}')
        if errores:
            for e in errores:
                print(f'ERROR: {e}')
            return 1

        for path in testbenches:
            texto = path.read_text(encoding='utf-8')
            nombres = [e for e in entidades(texto)]
            if not nombres:
                errores.append(f'{path.name}: no declara ninguna entidad')
                continue
            for tb in nombres:
                elaborado = ejecutar([ghdl, '-e', f'--std={args.std}', tb], temporal)
                if elaborado.returncode:
                    print(f'ERROR: no elabora {tb}')
                    print((elaborado.stdout + elaborado.stderr).strip())
                    errores.append(f'elaboracion de {tb}')
                    continue
                corrido = ejecutar(
                    [ghdl, '-r', f'--std={args.std}', tb,
                     '--assert-level=error', f'--stop-time={args.stop_time}'], temporal)
                salida = (corrido.stdout + corrido.stderr).strip()
                ok = corrido.returncode == 0 and 'TB_OK' in salida
                print(f'{"OK   " if ok else "ERROR"} ejecuta {tb}')
                if not ok:
                    errores.append(f'ejecucion de {tb}')
                    print(salida)
                else:
                    for linea in salida.splitlines():
                        if 'TB_OK' in linea:
                            print(f'       {linea}')

    if errores:
        print(f'\n{len(errores)} error(es)')
        return 1
    print(f'\nOK: {len(fuentes)} archivo(s) analizados, {len(testbenches)} testbench(s) correctos')
    return 0


if __name__ == '__main__':
    sys.exit(main())

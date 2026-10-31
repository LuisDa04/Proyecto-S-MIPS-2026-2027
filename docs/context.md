# Contexto y Progreso del Proyecto S-MIPS

## Propósito de este archivo

Registro de contexto y progreso. Debe actualizarse en cada commit con:
- Qué se implementó/modificó.
- Qué se probó y resultados.
- Qué queda pendiente.
- Decisiones de diseño tomadas.
- Problemas encontrados y soluciones aplicadas.

---

## Estado Actual del Repositorio (base)

| Elemento | Estado | Observaciones |
|----------|--------|---------------|
| `circuit/smips.circ` | Vacío (solo pines de CPU) | CPU sin implementar |
| `circuit/register_file.vhd` | No existe | Pendiente (Fase 2) |
| `circuit/instruction_decoder.vhd` | No existe | Pendiente (Fase 3) |
| `programs/*.asm` | 7 programas | Hello, arithmetic, memory, branches, gcd, multiply, array_sum |
| `images/*.hex` | Ya generados | Imágenes de ejemplo |
| `tests/` | No existe | Pendiente (Fase 9) - R21 |
| `informe.pdf` | No existe | Pendiente (Fase 10) - R23 |
| `salida-tests.txt` | No existe | Pendiente (Fase 10) |

---

## Decisiones de Arquitectura (pendiente de confirmar en implementación)

| Decisión | Opción seleccionada | Justificación |
|----------|-------------------|---------------|
| VHDL componentes | Register_File + Instruction_Decoder | Máx 2 permitidos (R18); son los de mayor complejidad de cableado en Logisim |
| ALU | Logisim nativo | Solo una instancia; componentes aritméticos nativos disponibles |
| Reset | Pendiente (asíncrono o síncrono) | R6 permite cualquiera |
| Máquina de estados | Pendiente (Moore o Mealy) | R15 permite cualquiera |
| Estados de control | Pendiente | Definir en Fase 1 |

---

## Registro de Commits y Progreso

Formato sugerido por commit:

```
## [Fecha] - Commit <hash>
### ¿Qué se hizo?
- ...

### ¿Qué se probó?
- ...

### Resultados
- ...

### ¿Qué queda pendiente?
- ...

### Problemas y soluciones
- ...

### Decisiones de diseño
- ...
```

---

### (Vacío - primera entrada por hacer al primer commit de implementación)

---

## Checklist de Requisitos (R1-R23)

| Req | Descripción | Estado | Evidencia |
|-----|-------------|--------|-----------|
| R1 | CPU en smips.circ, Logisim 5.0.0 | Pendiente | |
| R2 | No modificar Board/Memory/pines CPU | Pendiente | |
| R3 | Secuenciales en flanco CLK, sin relojes derivados | Pendiente | |
| R4 | TTY_WE = 1 un ciclo por carácter | Pendiente | |
| R5 | MEM_WE = 1 solo en sw/sb | Pendiente | |
| R6 | Reset: PC=0, gp=0x1800, sp=0x3FFC, regs=0 | Pendiente | |
| R7 | Reset no borra memoria | Pendiente | |
| R8 | 23 instrucciones S-MIPS | Pendiente | |
| R9 | addu≡add, addiu≡addi | Pendiente | |
| R10 | Instrucción ilegal → HALT; 0x00000000 = NOP | Pendiente | |
| R11 | Identificación solo por op/funct | Pendiente | |
| R12 | Multiciclo, una instrucción a la vez | Pendiente | |
| R13 | Memoria unificada, IR guarda instrucción | Pendiente | |
| R14 | Una sola ALU, sin otros sumadores | Pendiente | |
| R15 | Control_Unit = máquina de estados síncrona | Pendiente | |
| R16 | 6 subcircuitos con nombres exactos | Pendiente | |
| R17 | Sin RAM/ROM en CPU | Pendiente | |
| R18 | Máx 2 VHDL de 3 permitidos | Pendiente | |
| R19 | VHDL puertos std_logic, sin generics | Pendiente | |
| R20 | VHDL sintetizable, sin wait/after | Pendiente | |
| R21 | tests/ cubriendo tabla de casos | Pendiente | |
| R22 | Repo GitHub por Telegram | Pendiente | |
| R23 | smips.circ, .vhd, informe.pdf, tests/, salida-tests.txt | Pendiente | |

---

## Próximos Pasos Inmediatos

1. Crear `docs/plan.md` (este plan).
2. Fase 1: Diseño y especificación de arquitectura.
3. Fase 2: Implementar `register_file.vhd`.
4. Fase 3: Implementar `instruction_decoder.vhd`.
5. Fase 4-6: Implementar Datapath, Control_Unit, Branch_Control, integración CPU en Logisim.
6. Fase 7-8: Testeo modular y general con run_tests.py.
7. Fase 9: Crear `tests/` propios cubriendo R21.
8. Fase 10: Informe, salida-tests.txt, entrega en GitHub.

---

## Comandos de Referencia

```bash
# Ensamblar un programa
python3 tools/assemble.py programs/hello.asm

# Ejecutar batería de pruebas completa
python3 tools/run_tests.py

# Ejecutar un solo programa
python3 tools/run_tests.py programs/memory.asm

# Abrir circuito en Logisim
bash open.sh
```

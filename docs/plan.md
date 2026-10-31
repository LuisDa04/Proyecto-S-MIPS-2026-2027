# Plan de Implementación - CPU Multiciclo S-MIPS

## Información General

| Campo | Valor |
|-------|-------|
| Proyecto | CPU multiciclo S-MIPS en Logisim Evolution 5.0.0 |
| Curso | Arquitectura de Computadoras 2026-2027 |
| Lenguaje de descripción | Logisim-Evolution (circuitos), VHDL-2002 (2 componentes máx.) |
| Especificación fuente | `docs/guide.tex` / `docs/guide.pdf` |
| Criterio de aceptación | `tools/run_tests.py` compara TTY vs MARS (60,000 ciclos máx.) |

---

## Requisitos Obligatorios (Resumen de guide.tex)

### Requisitos de admisión (no evaluable si fallan)

- **R1**: CPU dentro de `circuit/smips.circ`, Logisim Evolution 5.0.0.
- **R2**: No modificar `Board` ni `Memory`. No cambiar nombre, ancho, sentido ni apariencia de pines de `CPU`.

### Requisitos temporales y de memoria

- **R3**: Elementos secuenciales en flanco de subida de CLK. Sin relojes derivados.
- **R4**: `TTY_WE = 1` exactamente un flanco por carácter.
- **R5**: `MEM_WE = 1` solo en ciclo de escritura `sw`/`sb`.
- **R6**: Reset: PC=0, $gp=0x1800, $sp=0x3FFC, otros 30 registros a 0, salidas a 0. Reset asíncrono o síncrono.
- **R7**: Reset no borra memoria.

### Requisitos de ISA

- **R8**: Las 23 instrucciones S-MIPS con semántica de tabla (sección ISA).
- **R9**: `addu` ≡ `add`, `addiu` ≡ `addi`.
- **R10**: Palabra ilegal → HALT=1, sin modificar estado. `0x00000000` = `nop` legal.
- **R11**: Instrucción identificada solo por op y funct (op=0).

### Requisitos de microarquitectura

- **R12**: Multiciclo, una instrucción a la vez, sin pipeline.
- **R13**: Memoria unificada instrucciones/datos; IR guarda instrucción durante sus ciclos.
- **R14**: Una sola ALU; ningún otro sumador. PC+4 y saltos usan la ALU.
- **R15**: `Control_Unit` = máquina de estados síncrona (Moore/Mealy), estados libres.
- **R16**: Seis subcircuitos obligatorios con nombres exactos y jerarquía.
- **R17**: Sin RAM/ROM en CPU. `Register_File` con registros/muxes/decoders.
- **R18**: Máx. 2 de 3 en VHDL: `Register_File`, `ALU`, `Instruction_Decoder`.
- **R19**: Entidades VHDL con puertos solo `std_logic`/`std_logic_vector`, sin generics, librerías `std_logic_1164` + `numeric_std`, VHDL-2002.
- **R20**: VHDL descriptivo/sintetizable: sin `wait`, `after`, archivos.

### Requisitos de entrega

- **R21**: Carpeta `tests/` con programas propios cubriendo TODAS las filas de la tabla de casos (R21).
- **R22**: Repo GitHub enviado por Telegram antes del límite.
- **R23**: Repo contiene: `circuit/smips.circ`, `.vhd` (si VHDL), `informe.pdf` (≤10 págs), `tests/`, `salida-tests.txt`.

---

## Jerarquía Obligatoria de Subcircuitos (R16)

```
CPU
├── Instruction_Decoder   (combinacional, sin estado)
├── Control_Unit          (máquina de estados síncrona)
├── Branch_Control        (combinacional, decide escritura PC)
└── Datapath
    ├── Register_File     (32 regs, 2 lecturas comb, 1 escritura flanco)
    └── ALU               (una sola, combinacional, + zero)
```

---

## Decisión de VHDL (R18)

Se implementan en VHDL:
1. **Register_File** — mayor complejidad de cableado en Logisim (32 registros, muxes 32:1, decoder 5→32, $zero hardwired).
2. **Instruction_Decoder** — tabla grande de decodificación, difícil de mantener en gates/muxes.

Se implementa en Logisim nativo:
3. **ALU** — Logisim trae componentes aritméticos nativos; una sola instancia.

---

## Fases Modulares de Implementación

### Fase 1: Análisis y Diseño (Especificación)

**Objetivo:** Definir arquitectura antes de tocar Logisim.

**Entregables:**
- Diagrama de ruta de datos con nombres de señales de control.
- Tabla de estados de la `Control_Unit` (nombres, transiciones, condiciones).
- Tabla de señales de control por estado.
- Codificación de operaciones de ALU y salidas del decodificador.
- Número de ciclos por clase de instrucción.

**Tareas:**
1.1 Leer `docs/guide.tex` completo y extraer todos los requisitos R1-R23.
1.2 Definir juego de señales de control (muxes, enables, ALU op, MEM_BE, TTY_WE, MEM_WE, HALT).
1.3 Diseñar máquina de estados (sugerida: FETCH, DECODE, EXECUTE, MEM, WRITEBACK, plus estados específicos para saltos/syscall).
1.4 Definir formato de IR y campos extraídos (op, rs, rt, rd, shamt, funct, inmediato).
1.5 Especificar interface de `Instruction_Decoder` (entradas OP/FUNCT, salidas de control).
1.6 Especificar interface de `Register_File` VHDL (CLK, RESET, RS1, RS2, RD, WD, REG_WRITE, RD1, RD2).
1.7 Revisión cruzada del diseño contra R3-R20.

**Criterio de salida:** Documento de diseño aprobado (puede ser parte del informe final).

---

### Fase 2: Implementación VHDL — Register_File

**Objetivo:** Banco de registros de 32×32 bits con dos puertos de lectura combinacional y un puerto de escritura en flanco de subida.

**Archivo:** `circuit/register_file.vhd`

**Especificación técnica:**

```vhdl
entity Register_File is
  port (
    CLK      : in  std_logic;
    RESET    : in  std_logic;
    RS1      : in  std_logic_vector(4 downto 0);
    RS2      : in  std_logic_vector(4 downto 0);
    RD       : in  std_logic_vector(4 downto 0);
    WD       : in  std_logic_vector(31 downto 0);
    REG_WRITE: in  std_logic;
    RD1      : out std_logic_vector(31 downto 0);
    RD2      : out std_logic_vector(31 downto 0)
  );
end entity;
```

**Comportamiento (base científica: archivo de registros síncrono con lecturas asíncronas):**
- Lectura de `RD1` = `mem[RS1]`, `RD2` = `mem[RS2]` de forma combinacional.
- Si `RS1 = "00000"` → `RD1 = 0` siempre ($zero hardwired).
- Si `RS2 = "00000"` → `RD2 = 0` siempre ($zero hardwired).
- Escritura: si `REG_WRITE=1` y `RD ≠ "00000"` en flanco de subida de CLK → `mem[RD] <= WD`.
- Reset (asíncrono o síncrono): todos los registros a 0 excepto $zero que es 0 por definición.
- Valores iniciales: $gp (registro 28) = 0x1800, $sp (registro 29) = 0x3FFC, resto 0.

**Tareas:**
2.1 Escribir `register_file.vhd` cumpliendo R17, R19, R20.
2.2 Verificar compilación VHDL-2002 sin avisos.
2.3 Crear testbench VHDL para verificar lecturas/escrituras y $zero.
2.4 Integrar en Logisim como entidad VHDL (Proyecto → Añadir entidad VHDL).
2.5 Probar isoladamente en Logisim con estímulos manuales.

---

### Fase 3: Implementación VHDL — Instruction_Decoder

**Objetivo:** Decodificar op (6 bits) y funct (6 bits) en señales de control para la `Control_Unit`.

**Archivo:** `circuit/instruction_decoder.vhd`

**Entradas:** `OP` (5 downto 0), `FUNCT` (5 downto 0).

**Salidas sugeridas (ajustables al diseño):**
- `ILLEGAL` : std_logic — instrucción no en tabla (R10).
- `IS_RTYPE`, `IS_ITYPE`, `IS_JTYPE` : clasificación.
- `ALU_OP` : codificación de operación ALU (add, sub, and, or, slt, sll, srl, lui, addi, etc.)
- `EXT_TYPE` : sign-extend vs zero-extend para inmediato.
- `MEM_READ`, `MEM_WRITE`, `MEM_BYTE` : tipo de acceso memoria.
- `BRANCH_TYPE` : beq, bne, none.
- `JUMP_TYPE` : j, jal, jr, none.
- `REG_WRITE_ENABLE` : escritura a registro.
- `REG_DST` : destino es rd (R) o rt (I).
- `SYS_CALL` : es syscall.
- `LUI_OP` : es lui (carga inmediata en bits altos).

**Comportamiento:**
- Combinacional puro (sin estado).
- `op=0` → mirar `funct`; `op≠0` → mirar solo `op` (R11).
- Detectar ilegal: par (op, funct) no en tabla → `ILLEGAL='1'` (R10).
- `0x00000000` (op=0, funct=0) = `sll $zero,$zero,0` = NOP legal.

**Tareas:**
3.1 Escribir `instruction_decoder.vhd` cumpliendo R19, R20.
3.2 Mapear todas las 25 instrucciones (23 S-MIPS + addu + addiu).
3.3 Crear testbench VHDL con vectores de prueba para cada instrucción.
3.4 Integrar en Logisim como entidad VHDL.
3.5 Probar isoladamente en Logisim.

---

### Fase 4: Implementación Logisim — Datapath

**Objetivo:** Ruta de datos con PC, IR, registros intermedios, muxes, extensión de inmediato, alineación de bytes, cálculo de destino j/jal.

**Subcircuitos dentro de Datapath:** `Register_File` (VHDL de Fase 2), `ALU` (Logisim nativo).

**Componentes del Datapath:**
- **PC**: registro de 32 bits, habilitado por `Branch_Control`, reset a 0.
- **IR**: registro de 32 bits, carga instrucción desde MEM_RDATA.
- **ALU**: una sola, operaciones: add, sub, and, or, slt, sll, srl, lui, addi, etc. Salida + `zero`.
- **Extensión inmediato**: sign-extend y zero-extend de 16→32 bits.
- **Alineación bytes para lb/lbu/sb**: splitter/selectores según `MEM_ADDR[1:0]`.
- **Cálculo destino j/jal**: `{PC+4[31:28], dir26, 00}`.
- **Muxes**: seleccionar origen ALU (registro vs inmediato), destino escritura (ALU vs MEM vs PC+4), etc.

**Restricciones críticas (R14):**
- SOLO una ALU en todo el Datapath.
- PC+4 se calcula con la ALU (operación add con operando constante 4).
- Dirección de memoria (lw/sw/lb/lbu/sb) se calcula con la ALU: `RS1 + SignExt(imm)`.
- Destino de salto (j/jal/jr/branch) se calcula con la ALU o lógica derivada.

**Tareas:**
4.1 Dibujar `Datapath` en Logisim con PC, IR, muxes, extensión, alineación.
4.2 Instanciar `Register_File` (VHDL) y `ALU` (Logisim nativo).
4.3 Conectar señales de control (pendiente de Control_Unit, usar túneles temporales).
4.4 Verificar que no haya RAM/ROM dentro de CPU (R17).
4.5 Verificar que todos los elementos secuenciales usen CLK directo (R3).

---

### Fase 5: Implementación Logisim — Control_Unit y Branch_Control

**Objetivo:** Máquina de estados que genera señales de control, y lógica de decisión de escritura PC.

**Control_Unit (R15):**
- Máquina de estados síncrona con biestables/registros.
- Entradas: CLK, RESET, estado actual, salidas de `Instruction_Decoder`.
- Salidas: señales de control a Datapath, `MEM_WE`, `TTY_WE`, `HALT`.
- Puede ser Moore o Mealy.

**Estados sugeridos (mínimo funcional):**
1. `FETCH` — leer instrucción de MEM en PC, guardar en IR.
2. `DECODE` — decodificar, preparar señales.
3. `EXECUTE` — operación ALU (add/sub/and/or/slt/sll/srl/lui/addi).
4. `MEM_ACCESS` — lectura/escritura memoria (lw/sw/lb/lbu/sb).
5. `WRITEBACK` — escribir resultado en Register_File.
6. `BRANCH` — evaluar beq/bne, actualizar PC si tomado.
7. `JUMP` — actualizar PC para j/jal/jr.
8. `SYSCALL` — manejar syscall 10 (HALT) y 11 (TTY).
9. `ILLEGAL` — HALT=1, detener (R10).
10. `RESET` — estado inicial tras reset.

**Branch_Control (combinacional):**
- Entradas: señales de control, resultado comparación (zero de ALU o comparador separado permitido por R14).
- Salida: `PC_WRITE` (1 si se debe escribir PC este ciclo).

**Tareas:**
5.1 Diseñar FSM de `Control_Unit` (diagrama de estados y transiciones).
5.2 Implementar `Control_Unit` en Logisim con registros de estado.
5.3 Implementar `Branch_Control` combinacional.
5.4 Conectar `Control_Unit` → Datapath, `Branch_Control` → PC.
5.5 Generar `MEM_WE`, `TTY_WE`, `HALT` según R4, R5.
5.6 Manejar `RESET` según R6.

---

### Fase 6: Implementación Logisim — CPU (integración)

**Objetivo:** Ensamblar CPU completa con los 6 subcircuitos obligatorios y conectar pines de la placa.

**Tareas:**
6.1 Crear subcircuito `CPU` con los 10 pines exactos (no modificar R2).
6.2 Instanciar `Instruction_Decoder`, `Control_Unit`, `Branch_Control`, `Datapath`.
6.3 Conectar internas por túneles con nombres descriptivos (recomendado por guide.tex FAQ).
6.4 Conectar pines de CPU a señales internas:
   - `CLK`, `RESET` → entradas de Control_Unit y registros.
   - `MEM_RDATA` → entrada a IR y Datapath.
   - `MEM_ADDR` → salida de Datapath (ALU o PC).
   - `MEM_WDATA` → salida de Register_File o Datapath.
   - `MEM_BE` → salida de lógica de alineación bytes.
   - `MEM_WE` → salida de Control_Unit.
   - `TTY_DATA` → salida de Register_File ($a0[6:0]).
   - `TTY_WE` → salida de Control_Unit.
   - `HALT` → salida de Control_Unit.
6.5 Verificar apariencia de CPU no modificada (R2).
6.6 Verificar que Board y Memory no se tocan (R2).

---

### Fase 7: Testeo Modular (unidad por unidad)

**Objetivo:** Verificar cada subcircuito isoladamente antes del test general.

**7.1 Register_File (VHDL)**
- Testbench: escribir/leer todos los 32 registros.
- Verificar $zero siempre 0 aunque se intente escribir.
- Verificar reset inicializa $gp=0x1800, $sp=0x3FFC.
- Verificar dos lecturas simultáneas independientes.

**7.2 Instruction_Decoder (VHDL)**
- Vector de pruebas para cada una de las 25 instrucciones.
- Verificar `ILLEGAL='1'` para opcodes/functs no en tabla.
- Verificar `0x00000000` decodifica como NOP legal.

**7.3 ALU (Logisim)**
- Probar cada operación con valores conocidos.
- Verificar salida `zero`.

**7.4 Datapath (Logisim)**
- Probar flujo de una instrucción de cada tipo (R, I, J) paso a paso.
- Verificar lecturas/escrituras de memoria con byte enables.

**7.5 Control_Unit (Logisim)**
- Simular FSM para cada clase de instrucción.
- Verificar transiciones de estado y señales de control.

**7.6 Branch_Control (Logisim)**
- Verificar PC_WRITE para beq tomado/no tomado, bne, j, jal, jr.

---

### Fase 8: Testeo General (run_tests.py)

**Objetivo:** Ejecutar batería completa y corregir fallos.

**Programas de prueba proporcionados (no cuentan como tests propios):**
- `programs/hello.asm` — syscall 11, syscall 10.
- `programs/arithmetic.asm` — add, sub, and, or, slt, sll, srl, addi, slti, andi, ori, lui, li (addiu), move (addu), $zero.
- `programs/memory.asm` — lw, sw, lb, lbu, sb, $gp, $sp, pila.
- `programs/branches.asm` — beq, bne, j, jal, jr, saltos hacia atrás, recursividad.
- `programs/gcd.asm`, `programs/multiply.asm`, `programs/array_sum.asm`.

**Comando:**
```bash
python3 tools/run_tests.py
```

**Criterio de éxito:** 100% programas OK, detenido=true, salida TTY idéntica a MARS, <60,000 ciclos.

**Depuración si falla:**
1. Revisar `detenido=false` → CPU no llega a syscall 10 (bucle infinito o estado bloqueado).
2. Revisar `MEM_ADDR final` → último PC antes de parar.
3. Comparar TTY obtenido vs esperado línea por línea.
4. Revisar ciclos: si cerca de 60,000, optimizar estados (menos ciclos por instrucción).

---

### Fase 9: Programas de Prueba Propios (R21) — carpeta tests/

**Objetivo:** Crear `tests/` cubriendo TODAS las filas de la tabla de casos de guide.tex.

**Requisitos por programa (R21):**
1. Solo instrucciones S-MIPS + pseudoinstrucciones (move, li, la, blt, bge, bgt, ble, nop) + syscalls 10 y 11.
2. Imprimir valores calculados (no solo mensajes fijos).
3. Salida idéntica en MARS y CPU (verificado con run_tests.py).
4. Máximo 12 líneas de 48 caracteres (TTY).
5. Comentario inicial enumerando instrucciones y casos cubiertos.

**Tabla de casos a cubrir (debe mapearse a programas tests/):**

| Instrucciones | Casos obligatorios |
|---------------|-------------------|
| add, sub | Positivos y al menos un negativo |
| and, or | Operandos con unos en bits altos |
| slt, slti | Resultado 1 y 0; al menos un negativo donde sign vs unsigned difiera |
| sll, srl | shamt=0 y shamt≠0; srl sobre negativo (entran ceros) |
| addi | Inmediato negativo |
| addiu, addu | Mediante li (constante -2^15 a 2^15-1) y move |
| andi, ori | Inmediato con bit 15 = 1 (zero-extend) |
| lui | Inmediato con bit 15 = 1 |
| lw, sw | Desplazamiento positivo y negativo |
| lb, lbu | Byte con bit 7 = 1, al menos dos posiciones d[1:0] distintas |
| sb | Cuatro posiciones d[1:0]=0,1,2,3; verificar otros bytes no cambian con lw |
| beq, bne | Tomado y no tomado; al menos un salto hacia atrás |
| j | Al menos una vez |
| jal, jr | Procedimiento que llama a otro, guardar $ra en pila, retorno correcto |
| syscall | Servicios 11 y 10 |
| $zero | Escribir en $zero, verificar sigue valiendo 0 |

**Sugerencia de organización de tests/:**
- `tests/test_arith.asm` — add, sub, and, or, slt, slti, sll, srl, addi, lui, andi, ori.
- `tests/test_move_li.asm` — addiu (li), addu (move).
- `tests/test_memory.asm` — lw, sw, lb, lbu, sb (4 posiciones), desplazamientos +/-.
- `tests/test_control.asm` — beq, bne, j, jal, jr, salto atrás, pila.
- `tests/test_syscall.asm` — syscall 11 (varios chars), syscall 10.
- `tests/test_zero.asm` — escribir en $zero, verificar 0.
- `tests/test_negatives.asm` — casos con operandos negativos para slt, add, etc.

**Tareas:**
9.1 Escribir cada programa .asm con comentario de cobertura.
9.2 Ensamblar cada uno y ejecutar con run_tests.py.
9.3 Verificar salida idéntica MARS vs CPU.
9.4 Verificar ≤12 líneas de 48 chars.
9.5 Documentar cobertura en informe (tabla fila→programa).

---

### Fase 10: Documentación y Entrega (R22, R23)

**Objetivo:** Preparar repo para entrega.

**Entregables:**
- `circuit/smips.circ` — CPU implementada.
- `circuit/register_file.vhd` — si se usa VHDL.
- `circuit/instruction_decoder.vhd` — si se usa VHDL.
- `informe.pdf` — ≤10 páginas, en orden:
  1. Nombre estudiante + componentes VHDL + justificación.
  2. Diagrama de ruta de datos con señales de control.
  3. Diagrama/tabla de máquina de estados.
  4. Tabla de señales de control por estado.
  5. Codificación ALU y salidas decodificador.
  6. Ciclos por clase de instrucción.
  7. Tabla de cobertura tests/ (R21).
  8. Resultados run_tests.py + limitaciones/errores conocidos.
- `tests/` — programas propios.
- `salida-tests.txt` — salida completa de `python3 tools/run_tests.py`.

**Tareas:**
10.1 Escribir informe según estructura obligatoria.
10.2 Generar `salida-tests.txt`.
10.3 Subir todo a GitHub.
10.4 Enviar enlace por Telegram al profesor.

---

## Puntos Clave del Proyecto (recordatorio constante)

| Punto | Detalle |
|-------|---------|
| R2 | NUNCA tocar Board/Memory ni apariencia/pines de CPU. |
| R3 | Solo flanco de subida CLK; sin relojes derivados. |
| R14 | Una sola ALU; PC+4 y direcciones usan la ALU. |
| R17 | Sin RAM/ROM en CPU; Register_File con registros+muxes. |
| R18 | Máx 2 VHDL (elegidos: Register_File + Instruction_Decoder). |
| R21 | tests/ debe cubrir TODAS las filas de la tabla de casos. |
| run_tests.py | 60,000 ciclos límite; salida TTY debe coincidir con MARS. |

---

## Sugerencias y Recomendaciones de Mejora

1. **Usar túneles nombrados** dentro de CPU para evitar cableado espagueti (recomendado en FAQ de guide.tex).
2. **Documentar cada señal** con texto explicativo en Logisim (criterio "Claridad del circuito", 10% de evaluación).
3. **No usar VHDL si no es necesario** — evita dependencia de Questa y licencia; simplifica run_tests.py.
4. **Estados de control simples** — menos estados = menos ciclos = menos riesgo de timeout en 60,000 ciclos.
5. **Mantener $zero hardwired** en Register_File VHDL (entrada RD="00000" no escribe, lecturas de RS=0 devuelven 0).
6. **Byte alignment para sb/lb/lbu** — usar splitter en MEM_ADDR[1:0] para seleccionar carril de byte; es el error más común.
7. **PC+4 con ALU** — configurar ALU en modo add, operando B = 4 (constante), operando A = PC.
8. **Declarar errores conocidos en el informe** — un error declarado se penaliza menos que uno oculto (guide.tex).
9. **Probar tests/ antes de entregar** — cada programa de tests/ debe pasar run_tests.py individualmente.
10. **Versión Java 21** — requerida por run_tests.py y assemble.py.

---

## Cronograma Sugerido (orientativo)

| Fase | Duración estimada | Entregable clave |
|------|------------------|------------------|
| 1. Diseño | 1-2 días | Documento de arquitectura |
| 2. Register_File VHDL | 1 día | register_file.vhd + testbench |
| 3. Instruction_Decoder VHDL | 1-2 días | instruction_decoder.vhd + testbench |
| 4. Datapath Logisim | 2-3 días | Datapath funcional |
| 5. Control_Unit + Branch_Control | 2-3 días | FSM + señales de control |
| 6. Integración CPU | 1 día | smips.circ con CPU completa |
| 7. Testeo modular | 1-2 días | Verificación por unidad |
| 8. Testeo general run_tests.py | 2-3 días | Todos los programs/ OK |
| 9. tests/ propios | 2-3 días | tests/ cubriendo R21 |
| 10. Documentación y entrega | 1-2 días | informe.pdf, salida-tests.txt, GitHub |

**Total estimado:** 2-3 semanas.

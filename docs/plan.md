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

**Verificación local:** GHDL 6.0.0 (`--std=02 --warn-all`) para cada entidad y un testbench espejo del wrapper de Logisim. La cosimulación con Questa queda **diferida** (ver Fase 0 y Fase 8); no se considera validada la integración hasta que `run_tests.py` complete con éxito.

---

## Generación de Circuitos Logisim (sin cableado manual)

Los circuitos se generan desde Python con el mismo patrón de dos fases que ya usa `tools/build.py`:

1. **Describir:** `tools/circuitlib.py` coloca componentes, pines y subcircuitos en coordenadas de rejilla.
2. **Descubrir:** se guarda un `.circ` temporal y `tools/Ports.java` lo carga en Logisim headless; devuelve la coordenada exacta de cada puerto.
3. **Conectar:** cada puerto se une con un tramo corto a un túnel con el nombre de la señal. La conectividad se declara por nombre, no por geometría.
4. **Fusionar:** `merge_circuits()` reemplaza solo los circuitos de la CPU y conserva `Board`, `Memory`, `<main>` y `<lib>` (R2).
5. **Verificar:** `tools/check_circuit.py` comprueba pines de `CPU`, nombres R16, ausencia de RAM/ROM (R17), rejilla y túneles huérfanos.

```text
python tools/build.py             # placa base (Board + Memory)
python tools/gen_*.py             # circuitos de la CPU por bloque
python tools/check_circuit.py     # invariantes antes de simular
python tools/smoke_circuitlib.py  # prueba de humo del generador

# demostracion end-to-end (genera un .circ y simula su tabla de verdad)
python tools/gen_prueba.py
java "-Djava.awt.headless=true" --class-path "$env:LOGISIM_JAR" tools/Verify.java circuit/prueba_generador.circ
```

**Reglas:** un túnel por señal y ancho; nunca calcular a mano la coordenada de un puerto; extremos de cable en la rejilla de 10 px; validar cada `.circ` generado cargándolo con `Ports.java`.

**Límites:** el XML de `.circ` es un formato interno de Logisim 5.0.0, no una API pública. No se genera ruteo automático general: con túneles basta con tramos rectos. Atributos con valores inválidos (por ejemplo `size` de compuerta) hacen que Logisim muestre un diálogo y el archivo no cargue; la librería valida los casos conocidos.

---

## Fases Modulares de Implementación

### Fase 0: Entorno, línea base y contrato Logisim↔VHDL

**Objetivo:** Dejar el entorno reproducible y fijar el contrato exacto entre Logisim y las entidades VHDL antes de escribir código.

**Estado:** ✅ **Completada el 2026-11-05.** Artefactos en `docs/contrato-logisim/`; resumen del contrato en `docs/contrato-logisim/README.md`; línea base registrada en `docs/context.md`.

**Contexto:** Logisim-Evolution 5.0.0 no usa GHDL para las entidades VHDL: lanza Questa/ModelSim (`vsim`) y espera su socket. En este equipo no hay Questa, así que GHDL 6.0.0 se usa para verificar el VHDL por separado y la validación de integración queda **diferida** hasta que exista Questa o hasta el checkpoint de la Fase 6. Esta decisión está registrada en `docs/context.md`.

**Entregables:**
- Tabla de herramientas verificadas (versión, ruta, variable de entorno).
- Wrapper y testbench que genera Logisim para una entidad VHDL, guardados como referencia.
- Comando único de prueba de humo.

**Tareas:**
0.1 Verificar Java 21, Logisim 5.0.0 (`LOGISIM_JAR`), MARS (`MARS_JAR`) y GHDL 6.0.0 (`--std=02`).
0.2 Confirmar ausencia/presencia de Questa: `QUESTA_BIN`, `SALT_LICENSE_SERVER`, `where vsim`.
0.3 Copiar `circuit/smips.circ` a un archivo temporal (nunca modificar el original, R2), añadir una entidad VHDL mínima, ejecutar `tools/run_tests.py` y **capturar el wrapper y el testbench generados** antes de que falle por falta de Questa.
0.4 Documentar el contrato: nombres de puertos, tipos, cómo se conduce el reloj, reset y orden de instanciación.
0.5 Ejecutar `python tools/run_tests.py` con la CPU vacía y registrar el fallo esperado (línea base).
0.6 Ajustar los comandos a Windows (`python` en lugar de `python3`, rutas con `\`, variables de entorno).

**Criterio de salida:** Entorno documentado y contrato Logisim↔VHDL escrito; se sabe exactamente qué wrapper espera Questa. Si en cualquier momento se instala Questa, se repite 0.3 y se habilita la validación completa sin cambiar el VHDL.

**Resultado de la Fase 0 (2026-11-05):**
- Java 21, Logisim 5.0.0, MARS 4.5 (`D:\EscuelaLuisi\AC\Mars4_5.jar`) y GHDL 6.0.0 verificados; Questa ausente.
- Captura real con `Register_File`: wrapper `top_sim.vhdl`, `comp.tcl`, `run.tcl` y `questasim_binder.tcl` en `docs/contrato-logisim/`.
- Contrato confirmado: prefijo `LogisimVhdlSimComp_Register_File_0_<Puerto>`, anchos 1/5/32 y protocolo del binder (`tipo:nombre:valor:id`, `run 100`, `sync`).
- Línea base con CPU vacía: `hello.asm` falla a los 60 000 ciclos con `detenido=false`; es el fallo esperado antes de implementar.

---

### Fase 1: Análisis y Diseño (Especificación)

**Objetivo:** Definir arquitectura antes de tocar Logisim.

**Estado:** ✅ **Completada el 2026-11-05.** El diseño definitivo, con ISA,
control, FSM, interfaces y matriz R1–R23, está en `docs/diseno.md`.

**Entregables:**
- Diagrama de ruta de datos con nombres de señales de control.
- Tabla de estados de la `Control_Unit` (nombres, transiciones, condiciones).
- Tabla de señales de control por estado.
- Codificación de operaciones de ALU y salidas del decodificador.
- Número de ciclos por clase de instrucción.
- Matriz de trazabilidad R1–R23 → elemento del diseño → evidencia de prueba.

**Tareas:**
1.1 Leer `docs/guide.tex` completo y extraer todos los requisitos R1-R23.
1.2 Definir juego de señales de control (muxes, enables, ALU op, MEM_BE, TTY_WE, MEM_WE, HALT).
1.3 Diseñar máquina de estados. La tabla definitiva quedó en `docs/diseno.md` §6: `FETCH`, `DECODE`, `EXEC_R`, `EXEC_I`, `ADDR`, `MEM_READ`, `MEM_WRITE`, `BRANCH`, `JUMP`, `SYSCALL`, `WB`, `HALT`.
1.4 Definir formato de IR y campos extraídos (op, rs, rt, rd, shamt, funct, inmediato).
1.5 Especificar interface de `Instruction_Decoder` (entradas OP/FUNCT, salidas de control).
1.6 Especificar interface de `Register_File` VHDL (CLK, RESET, RS1, RS2, RD, WD, REG_WRITE, RD1, RD2).
1.7 Revisión cruzada del diseño contra R3-R20.
1.8 Construir la matriz de trazabilidad R1–R23 (requisito → componente/señal → prueba que lo evidencia).
1.9 Escribir la tabla de estados explícita: estado actual → salidas → condición de transición → estado siguiente.
1.10 Fijar la lista completa de señales de control, incluida `BE` (4 bits), `TTY_WE` y `HALT`, y quién las genera.
1.11 Definir la convención de nombres de túneles y etiquetas (una señal, un nombre, en toda la jerarquía).

**Criterio de salida:** Documento de diseño aprobado (puede ser parte del informe final) y matriz de trazabilidad completa.

**Resultado de la Fase 1 (2026-11-05):**
- `docs/diseno.md` con la ISA (23 base + 2 alias), tabla de decodificación de 25 filas, codificación de la ALU, ruta de datos, FSM de 12 estados, salidas por estado, casos especiales, ciclos, interfaces y convención de túneles.
- Decisiones cerradas: reset asíncrono activo alto; `PC+4` con la ALU en `FETCH`; comparador de igualdad en `Branch_Control`; `MEM_TO_REG=PC` para `jal`; `HALT` solo por ilegal o `syscall 10`.
- Matriz R1–R23 completa con la evidencia prevista para cada requisito.

---

### Fase 2: Implementación VHDL — Register_File

**Objetivo:** Banco de registros de 32×32 bits con dos puertos de lectura combinacional y un puerto de escritura en flanco de subida.

**Archivo:** `circuit/register_file.vhd`

**Contrato de nombres (R16/R19):** la entidad VHDL se llama `Register_File` (VHDL no distingue mayúsculas; el archivo es `register_file.vhd`), y el subcircuito de Logisim debe llamarse exactamente `Register_File`. Los nombres y tipos de los puertos se fijan en la Fase 0 y **no se cambian después**.

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
- Reset asíncrono activo alto (decisión de Fase 1): `$gp` (registro 28) = `0x1800`, `$sp` (registro 29) = `0x3FFC`, el resto a 0; `$zero` siempre 0.
- No se usan valores iniciales de VHDL (R20): los valores anteriores se cargan en el mismo proceso de reset.

**Reglas VHDL conservadoras (para minimizar diferencias GHDL/Questa):**
- VHDL-2002 estricto; solo `ieee.std_logic_1164` y `ieee.numeric_std` (R19).
- Sin valores iniciales en señales, sin `wait`, sin `after`, sin ficheros (R20).
- Reset asíncrono activo alto, con `RESET` en la lista de sensibilidad del proceso (decisión de Fase 1).
- `$zero` protegido también en escritura, no solo en lectura.

**Tareas:**
2.1 Escribir `register_file.vhd` cumpliendo R17, R19, R20.
2.2 Verificar compilación VHDL-2002 sin avisos: `ghdl -a --std=02 --warn-all register_file.vhd`.
2.3 Crear testbench funcional (32 registros, `$zero`, reset con `$gp=0x1800` y `$sp=0x3FFC`, dos lecturas simultáneas) y testbench **espejo** que replique el wrapper de Logisim capturado en la Fase 0.
2.4 Integrar en Logisim como entidad VHDL (Proyecto → Añadir entidad VHDL) y comprobar que los pines coinciden con el contrato.
2.5 Probar aisladamente en Logisim con estímulos manuales (sin ejecutar la CPU completa).

---

### Fase 3: Implementación VHDL — Instruction_Decoder

**Objetivo:** Decodificar op (6 bits) y funct (6 bits) en señales de control para la `Control_Unit`.

**Archivo:** `circuit/instruction_decoder.vhd`

**Entradas:** `OP` (5 downto 0), `FUNCT` (5 downto 0).

**Salidas obligatorias (corrigen los defectos detectados en el repo guía):**
- `ILLEGAL` : std_logic — instrucción no en tabla (R10).
- `IS_RTYPE`, `IS_ITYPE`, `IS_JTYPE` : clasificación.
- `ALU_OP` : codificación de operación ALU (add, sub, and, or, slt, sll, srl, lui, addi, etc.).
- `EXT_TYPE` : sign-extend vs zero-extend para inmediato.
- `MEM_READ`, `MEM_WRITE` : acceso a memoria.
- `MEM_SIZE` : 2 bits — word / byte (para `lw`/`sw` vs `lb`/`lbu`/`sb`).
- `BRANCH_TYPE` : 2 bits — none / beq / bne.
- `JUMP_TYPE` : 2 bits — none / j / jal / jr (**no** fusionar en un único `IsJump`).
- `REG_WRITE_ENABLE` : escritura a registro.
- `REG_DST` : 2 bits — rd (R) / rt (I) / $31 (`jal`).
- `MEM_TO_REG` : 2 bits — ALU / MDR / PC+4 (`jal`).
- `SYS_CALL` : es syscall.
- `LUI_OP` : es lui (carga inmediata en bits altos).

**Comportamiento:**
- Combinacional puro (sin estado).
- `op=0` → mirar `funct`; `op≠0` → mirar solo `op` (R11).
- Detectar ilegal: par (op, funct) no en tabla → `ILLEGAL='1'` (R10).
- `0x00000000` (op=0, funct=0) = `sll $zero,$zero,0` = NOP legal.
- `jal` debe distinguirse de `j` y `jr`; `jr` debe poder llevar `rs` al PC.

**Tareas:**
3.1 Escribir `instruction_decoder.vhd` cumpliendo R19, R20.
3.2 Mapear todas las 25 instrucciones (23 S-MIPS + addu + addiu).
3.3 Crear un **modelo de referencia en Python** con la tabla de `guide.tex` y comparar exhaustivamente las 2^12 combinaciones (op, funct) contra el VHDL (GHDL) o contra los vectores generados.
3.4 Crear testbench VHDL con vectores de prueba para cada instrucción y para cada caso ilegal.
3.5 Integrar en Logisim como entidad VHDL y comprobar el contrato de puertos.
3.6 Probar aisladamente en Logisim.

---

### Fase 4: Implementación Logisim — Datapath

**Objetivo:** Ruta de datos con PC, IR, registros intermedios, muxes, extensión de inmediato, alineación de bytes, cálculo de destino j/jal.

**Subcircuitos dentro de Datapath:** `Register_File` (VHDL de Fase 2), `ALU` (Logisim nativo).

**Componentes del Datapath:**
- **PC**: registro de 32 bits, habilitado por `PC_WRITE = PC_WRITE_CTL OR PC_WRITE_BRANCH`, reset a 0.
- **IR**: registro de 32 bits, carga instrucción desde MEM_RDATA.
- **ALU**: una sola, operaciones: add, sub, and, or, slt, sll, srl, lui, addi, etc. Salida + `zero`.
- **Extensión inmediato**: sign-extend y zero-extend de 16→32 bits.
- **Alineación bytes para lb/lbu/sb**: splitter/selectores según `MEM_ADDR[1:0]`.
- **Cálculo destino j/jal**: `{PC[31:28], IR[25:0], 2'b00}` (el registro `PC` ya vale `PC+4`).
- **Muxes**: seleccionar origen ALU (registro vs inmediato), destino escritura (ALU vs MEM vs PC+4), etc.

**Restricciones críticas (R14):**
- SOLO una ALU en todo el Datapath.
- PC+4 se calcula con la ALU (operación add con operando constante 4).
- Dirección de memoria (lw/sw/lb/lbu/sb) se calcula con la ALU: `RS1 + SignExt(imm)`.
- Destino de salto: `j`/`jal` por concatenación `{PC[31:28], IR[25:0], 2'b00}`; `jr` por `A`; `beq`/`bne` con la ALU (`PC + (SignExt(imm)<<2)`).

**Trampas obligatorias (todas detectadas en el repo guía y todas bloqueantes):**
- **Sin `Memory` dentro del `Datapath`.** La CPU recibe `MEM_RDATA` por su pin y devuelve `MEM_ADDR`/`MEM_WDATA`/`MEM_BE`/`MEM_WE`; la única RAM es la de `Board` (R13/R17).
- **Puerto `RESET` en el `Datapath`** y cableado hasta el `Register_File`; sin él no se inicializan `$gp`, `$sp` ni el resto (R6).
- **Fuente PC+4** para `jal`: el registro `PC` ya contiene `PC+4` al terminar `FETCH`; `MEM_TO_REG=PC` lleva ese valor al writeback de `jal`.
- **Camino `$31`**: `REG_DST` debe poder seleccionar el registro 31 para `jal`.
- **Camino `jr`**: la dirección de `rs` debe poder llegar al PC.
- **Desplazamiento de `lui`**: `imm << 16` antes de entrar a la ALU o al writeback.
- **Carriles de byte** para `lb`/`lbu`/`sb` según `MEM_ADDR[1:0]`, con `MEM_BE` de 4 bits.
- **Nada de ROM** para decodificar la ALU ni para la FSM: R17 prohíbe RAM y ROM dentro de la CPU.

**Tareas:**
4.1 Dibujar `Datapath` en Logisim con PC, IR, muxes, extensión, alineación.
4.2 Instanciar `Register_File` (VHDL) y `ALU` (Logisim nativo).
4.3 Conectar señales de control (pendiente de Control_Unit, usar túneles temporales).
4.4 Verificar que no haya RAM/ROM dentro de CPU (R17).
4.5 Verificar que todos los elementos secuenciales usen CLK directo (R3).
4.6 Verificar una a una las trampas anteriores antes de pasar a la Fase 5.

---

### Fase 5: Implementación Logisim — Control_Unit y Branch_Control

**Objetivo:** Máquina de estados que genera señales de control, y lógica de decisión de escritura PC.

**Control_Unit (R15):**
- Máquina de estados síncrona con biestables/registros; el estado es **interno**, no una entrada.
- Entradas: `CLK`, `RESET`, salidas de `Instruction_Decoder` y `A` (32, para distinguir `syscall` 10/11).
- Salidas: `PC_WRITE_CTL`, `PC_SRC`, `IR_WRITE`, `A_WRITE`, `B_WRITE`, `ALU_WRITE`, `MDR_WRITE`, `REG_WRITE`, `RS1_SEL`, `RS2_SEL`, `ALU_SRC_A`, `ALU_SRC_B`, `ALU_OP`, `MEM_ADDR_SEL`, `BRANCH_ENABLE`, `MEM_WE`, `TTY_WE`, `HALT` y el paso directo de `EXT_TYPE`, `REG_DST`, `MEM_TO_REG`, `MEM_SIZE`, `MEM_SIGNED`, `BRANCH_TYPE` y `JUMP_TYPE`.
- Es **Moore**: las salidas dependen del estado y de entradas registradas (IR, A, B, decodificador). `Branch_Control` es combinacional y se mantiene fuera de la FSM. `MEM_BE` se genera en el `Datapath`.

**Reglas de salida (R4/R5/R10):**
- `HALT=1` **solo** por instrucción ilegal o por `syscall 10`; nunca cableado directamente a `Illegal` sin pasar por la FSM.
- `TTY_WE=1` durante **exactamente un** flanco por carácter (`syscall 11`), y 0 en cualquier otro ciclo.
- `MEM_WE=1` **solo** en el ciclo de escritura de `sw`/`sb` (R5).
- `MEM_WE`, `TTY_WE` y `HALT` valen 0 mientras `RESET=1` (R6).

**Implementación del próximo estado:** tabla explícita (estado actual × condición → estado siguiente) construida con puertas, muxes y decodificadores. **Prohibido usar ROM** (R17). La tabla se copia tal cual al informe.

**Estados definitivos (ver `docs/diseno.md` §6):**
1. `FETCH` — leer instrucción de MEM en PC, guardar en IR y avanzar PC con la ALU.
2. `DECODE` — cargar `A`/`B` desde `Register_File`; para `syscall`, `$v0`/`$a0`.
3. `EXEC_R` — operación ALU de tipo R (incluye desplazamientos).
4. `EXEC_I` — operación ALU con inmediato (incluye `lui`).
5. `ADDR` — calcular `A + SignExt(imm)` con la ALU.
6. `MEM_READ` — leer memoria y cargar `MDR`.
7. `MEM_WRITE` — escribir memoria (`MEM_WE=1`).
8. `BRANCH` — comparar `A`/`B` y calcular el destino con la ALU.
9. `JUMP` — actualizar PC para `j`/`jal`/`jr`; `jal` escribe `$31`.
10. `SYSCALL` — servicio 10 (HALT) u 11 (TTY).
11. `WB` — escribir el resultado en `Register_File`.
12. `HALT` — `HALT=1`; permanece hasta el reset.

No hay estado `RESET`: el reset es asíncrono y fuerza la FSM a `FETCH`. La tabla
completa de transiciones y salidas está en `docs/diseno.md` §6 y §7.

**Branch_Control (combinacional):**
- Entradas: `A` (32), `B` (32), `BRANCH_TYPE` (2) y `BRANCH_ENABLE`.
- Comparador de igualdad de 32 bits (permitido por R14); no usa la ALU.
- Salidas: `EQ` y `PC_WRITE_BRANCH = BRANCH_ENABLE AND ((BRANCH_TYPE=01 AND EQ) OR (BRANCH_TYPE=10 AND NOT EQ))`.
- La CPU calcula `PC_WRITE = PC_WRITE_CTL OR PC_WRITE_BRANCH`.

**Tareas:**
5.1 Diseñar FSM de `Control_Unit` (diagrama de estados y transiciones).
5.2 Implementar `Control_Unit` en Logisim con registros de estado.
5.3 Implementar `Branch_Control` combinacional.
5.4 Conectar `Control_Unit` → Datapath, `Branch_Control` → PC.
5.5 Generar `MEM_WE`, `TTY_WE`, `HALT` según R4, R5, R10.
5.6 Manejar `RESET` según R6 y comprobar que las tres salidas valen 0 durante el reset.
5.7 Documentar la tabla de estados completa (estado → salidas → transición) y volcarla al informe.
5.8 Verificar con simulación que `TTY_WE` dura exactamente un ciclo y que `HALT` solo se activa en los dos casos permitidos.
5.9 Verificar que `syscall 10` detiene la CPU y `syscall 11` imprime, sin afectar al PC de forma incorrecta.

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
- **Testbench espejo** con el wrapper exacto de Logisim (Fase 0): mismos puertos, mismo reloj, mismo reset.
- Compilar con `ghdl -a --std=02 --warn-all` sin errores **ni avisos**.

**7.2 Instruction_Decoder (VHDL)**
- Vector de pruebas para cada una de las 25 instrucciones.
- Verificar `ILLEGAL='1'` para opcodes/functs no en tabla.
- Verificar `0x00000000` decodifica como NOP legal.
- Comparación exhaustiva de las 2^12 combinaciones (op, funct) contra el modelo Python de referencia.
- Verificar por separado `j` / `jal` / `jr`, `REG_DST=$31`, `MEM_TO_REG=PC+4` y `MEM_SIZE` byte/word.

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

**7.7 Prueba de humo de integración**
- Con la CPU ya cableada, ejecutar solo `programs/hello.asm` antes de la batería completa.
- Si falla, aislar por capas: pines de CPU → `Control_Unit` → `Datapath` → memoria.
- Registrar el resultado en `docs/context.md` como primer hito de integración.

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

**Validación diferida (mientras no haya Questa):** `run_tests.py` abortará con `Questa no arranco` en cuanto detecte entidades VHDL (`tools/Run.java:88-92`). En ese escenario la verificación se hace por capas: GHDL para el VHDL, simulación manual en Logisim para el cableado y revisión del wrapper capturado en la Fase 0. `run_tests.py` queda como puerta final, no como criterio diario.

**Diagnóstico de `Questa no arranco`:**
1. `QUESTA_BIN` debe apuntar a la carpeta `bin` que contiene `vsim` (y `vcom`).
2. Comprobar licencia: `SALT_LICENSE_SERVER` o fichero de licencia local.
3. Revisar la consola de Logisim: puede haber un error de compilación VHDL antes del timeout, no solo un fallo de arranque.
4. Verificar que la entidad y los puertos coinciden con el wrapper de la Fase 0 (nombres y tipos).

**Criterio de éxito:** 100% programas OK, detenido=true, salida TTY idéntica a MARS, <60,000 ciclos.

**Depuración si falla:**
1. Revisar `detenido=false` → CPU no llega a syscall 10 (bucle infinito o estado bloqueado).
2. Revisar `MEM_ADDR final` → último PC antes de parar.
3. Comparar TTY obtenido vs esperado línea por línea.
4. Revisar ciclos: si cerca de 60,000, optimizar estados (menos ciclos por instrucción).
5. Si el TTY está vacío pero `detenido=true`, revisar `syscall 11`, `TTY_DATA` y `TTY_WE`.

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
| R16 | Nombres exactos: `Instruction_Decoder`, `Control_Unit`, `Branch_Control`, `Datapath`, `Register_File`, `ALU`. |
| R17 | Sin RAM/ROM en CPU; Register_File con registros+muxes; tampoco ROM para la FSM. |
| R18 | Máx 2 VHDL (elegidos: Register_File + Instruction_Decoder). |
| R21 | tests/ debe cubrir TODAS las filas de la tabla de casos. |
| run_tests.py | 60,000 ciclos límite; salida TTY debe coincidir con MARS. |

---

## Sugerencias y Recomendaciones de Mejora

1. **Usar túneles nombrados** dentro de CPU para evitar cableado espagueti (recomendado en FAQ de guide.tex).
2. **Documentar cada señal** con texto explicativo en Logisim (criterio "Claridad del circuito", 10% de evaluación).
3. **VHDL solo con Questa disponible o con aceptación explícita del riesgo** — sin Questa no se puede ejecutar `run_tests.py`; GHDL valida el VHDL pero no la cosimulación. Si no se instala Questa, el checkpoint de la Fase 6 decide entre continuar con VHDL o sustituirlo por circuitos Logisim.
4. **Estados de control simples** — menos estados = menos ciclos = menos riesgo de timeout en 60,000 ciclos.
5. **Mantener $zero hardwired** en Register_File VHDL (entrada RD="00000" no escribe, lecturas de RS=0 devuelven 0).
6. **Byte alignment para sb/lb/lbu** — usar splitter en MEM_ADDR[1:0] para seleccionar carril de byte; es el error más común.
7. **PC+4 con ALU** — configurar ALU en modo add, operando B = 4 (constante), operando A = PC.
8. **Declarar errores conocidos en el informe** — un error declarado se penaliza menos que uno oculto (guide.tex).
9. **Probar tests/ antes de entregar** — cada programa de tests/ debe pasar run_tests.py individualmente.
10. **Versión Java 21** — requerida por run_tests.py y assemble.py.
11. **Nombres exactos R16 desde el primer día** — `Control_Unit`, `Branch_Control`, `Register_File`, `Datapath`, `Instruction_Decoder`, `ALU`. Renombrar al final suele romper cables y apariencias.
12. **Ninguna RAM/ROM dentro de la CPU (R17)** — ni para el decodificador de ALU ni para la tabla de la FSM; usar puertas, muxes y decodificadores.
13. **Checkpoint de la Fase 6** — si la integración VHDL no se puede verificar, activar el plan de contingencia (sustituir las dos entidades por circuitos Logisim) antes de invertir tiempo en la Fase 8.

---

## Anexo A: Análisis del Repositorio Guía

**Repositorio:** `https://github.com/luisiafk/Proyecto-S-MIPS-2026-2027`
**Commit analizado:** `57c67b6` (2026-11-04), *"implementacion del decoder, y volviendo a hacer la FSM"*.
**Contenido:** 8 commits (7 de implementación); solo añade `circuit/REGFILE.vhd` y `circuit/smips.circ`. **No** tiene `tests/`, `informe.pdf` ni `salida-tests.txt`: no es una entrega ni una solución validada.

**Regla de uso:** referencia de intención y estructura, **nunca fuente de código para copiar**.

### A.1 Reutilizable

| Elemento | Uso propuesto |
|---|---|
| Conjunto de señales de control (`PCwr, IRwr, Regwr, Awr, Bwr, ALUwr, MDRwr, IorD, RegDst, MemToReg, ALUSrcA, ALUSrcB, MemWrite, PcwrCond, ALUOP`) | Punto de partida; añadir `BE`, `TTY_WE`, `HALT` |
| Registros intermedios PC / IR / A / B / ALUOUT / MDR | Adoptar (R13) |
| `WE = Pcwr ∧ ((IsBeq ∧ Zero) ∨ (IsBne ∧ ¬Zero))` | Adoptar en `Branch_Control` (R14) |
| Tabla de opcodes/functs del `Instruction_Decoder` | Adoptar y verificar fila por fila contra `guide.tex` |
| Codificación ALU de 3 bits (000 add … 110 srl) | Adoptar y documentar |
| `register_file` VHDL | Base reutilizable: GHDL 6.0.0 `--std=02 --warn-all` sin errores ni avisos; testbench propio pasa (reset, `$gp=0x1800`, `$sp=0x3FFC`, `$zero` protegido, escritura/lectura) |

### A.2 Defectos que no deben repetirse

| # | Hallazgo | Evidencia en `smips.circ` | Severidad | Medida correctiva |
|---|---|---|---|---|
| 1 | ROM dentro de la CPU (R17): el subcircuito `Decoder` usa una ROM 8×3 y se instancia en `Datapath` | ROM en línea 1304; instancia en 2045 | Bloqueante | Decodificar la ALU con puertas/muxes o dentro del `Instruction_Decoder` VHDL |
| 2 | Dos memorias (R13/R17): `Datapath` instancia `Memory` (RAM 4096×32) igual que `Board` | `<comp ... name="Memory"/>` en 2044 | Bloqueante | Quitar `Memory` del `Datapath`; usar `MEM_RDATA` de la CPU |
| 3 | Nombres R16 incorrectos: `FSM`, `BranchControl`, `register_file` | 436-439, 2043 | Bloqueante (admisión) | `Control_Unit`, `Branch_Control`, `Register_File` |
| 4 | Reset no llega al banco de registros (R6): `Datapath` sin `RESET`/`rst`; `rst` de `register_file` sin conectar | 1457; bloque 1325-2214 | Bloqueante | Puerto `RESET` en `Datapath` y cableado a `Register_File` |
| 5 | `TTY_WE`, `HALT` y `syscall` 10/11 no existen en la FSM (R4/R10): `HALT` cableado directo a `Illegal`; `TTY_DATA`/`TTY_WE` sin conectar | etiquetas de `FSM` 2359-3044 | Bloqueante | Generar las tres señales en `Control_Unit` |
| 6 | `jal`/`jr` incompletos: un solo `IsJ` en la FSM; sin `$31` en `RegDst`; sin PC+4 en writeback; sin camino `rs`→PC | 2905, 2933, 2985 | Bloqueante | Separar `j`/`jal`/`jr`; `RegDst` y `MemToReg` de 2 bits |
| 7 | PC+4 y `lui` sin camino: no hay fuente PC+4 ni desplazamiento; único `Constant` del `Datapath` = `0x100` | 1457 | Bloqueante | Añadir fuente PC+4 y desplazamiento `imm << 16` |
| 8 | FSM inauditable: próximo estado con registro de 4 bits + decoder 4→16 y puertas sin documentar (S0-S15) | 3045 y siguientes | Alta (claridad, 10 %) | Tabla de estados explícita y documentada |
| 9 | ALU con pin `CLK` sin uso; nombres `InOp`/`ALUOP`/`OP` ambiguos | 707-716 | Menor | Eliminar `CLK`; unificar convención de nombres |

### A.3 Lecciones

- La arquitectura conceptual del repo guía es correcta; sus fallos son de **integración y verificación**, no de planteamiento.
- Los errores más caros (R16, R17) son de **admisión**: se detectan revisando nombres y presencia de RAM/ROM antes de simular.
- El VHDL del banco de registros es el único artefacto que se puede reutilizar con confianza, y aun así requiere limpieza de comentarios y un testbench espejo.

---

## Cronograma Sugerido (orientativo)

| Fase | Duración estimada | Entregable clave |
|------|------------------|------------------|
| 0. Entorno y contrato | 0.5-1 día | Herramientas verificadas + wrapper de Logisim |
| 1. Diseño | 1-2 días | Documento de arquitectura + matriz R1-R23 |
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

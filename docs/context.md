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
| `circuit/smips.circ` | Board + CPU vacía + Memory + `ALU` + `Datapath` | Fase 4; CPU aún sin cablear (Fase 6) |
| `circuit/register_file.vhd` | Implementado | Fase 2; validado con GHDL |
| `circuit/instruction_decoder.vhd` | Implementado | Fase 3; validado con GHDL |
| `programs/*.asm` | 7 programas | Hello, arithmetic, memory, branches, gcd, multiply, array_sum |
| `images/*.hex` | Ya generados | Imágenes de ejemplo |
| `tests/` | No existe | Pendiente (Fase 9) - R21 |
| `informe.pdf` | No existe | Pendiente (Fase 10) - R23 |
| `salida-tests.txt` | No existe | Pendiente (Fase 10) |
| `docs/plan.md` | Creado | Plan en 10 fases + Fase 0 + Anexo A |
| `docs/diseno.md` | Creado | Diseño de Fase 1: ISA, control, FSM, interfaces y matriz R1–R23 |
| `docs/contrato-logisim/` | Creado | Wrapper y scripts Tcl capturados de Logisim 5.0.0 |
| `docs/context.md` | Creado | Este archivo |

---

## Entorno Local Verificado

| Herramienta | Versión / ruta | Estado | Notas |
|---|---|---|---|
| Java | OpenJDK 21.0.13 (Temurin) | OK | Requerido por Logisim, MARS y los scripts |
| Logisim-Evolution | 5.0.0 (`C:\Program Files\logisim-evolution\app\logisim-evolution-5.0.0-all.jar`) | OK | `LOGISIM_JAR` |
| MARS | 4.5 (`D:\EscuelaLuisi\AC\Mars4_5.jar`) | OK | `MARS_JAR` |
| GHDL | 6.0.0 (`D:\EscuelaLuisi\AC\GHDL\bin\ghdl.exe`) | OK | No está en `PATH`; usar `--std=02` |
| Questa / ModelSim | No instalado | **BLOQUEANTE** | `QUESTA_BIN` y `SALT_LICENSE_SERVER` vacíos; `vsim` no existe |

**Consecuencia:** `tools/run_tests.py` no puede ejecutar circuitos con entidades VHDL (`tools/Run.java:88-92` aborta con `Questa no arranco`). GHDL valida el VHDL por separado; la cosimulación queda **diferida** hasta que haya Questa o hasta el checkpoint de la Fase 6.

---

## Repositorio Guía Analizado

| Campo | Valor |
|---|---|
| URL | `https://github.com/luisiafk/Proyecto-S-MIPS-2026-2027` |
| Commit | `e518e22` (última revisión consultada el 2026-11-08) |
| Contenido | `circuit/REGFILE.vhd`, `circuit/smips.circ` (4036 líneas) |
| Ausente | `tests/`, `informe.pdf`, `salida-tests.txt` |
| Veredicto | Prototipo en progreso; no es entrega ni solución validada |
| Uso | Referencia de intención; solo lectura |

**Reutilizable:** conjunto de señales de control, registros intermedios PC/IR/A/B/ALUOUT/MDR, ecuación de `Branch_Control`, tabla de opcodes/functs y codificación ALU de 3 bits. Su `register_file` VHDL se analizó pero **no se adoptó**: el proyecto usa el de la Fase 2.

**Defectos bloqueantes detectados:**
- ROM dentro de la CPU (R17) en el subcircuito `Decoder`, instanciado en `Datapath`.
- `Datapath` instancia `Memory` (R13/R17): hay dos RAM y la imagen cargada en `Board` no se usa.
- Nombres R16 incorrectos: `FSM`, `BranchControl`, `register_file`.
- `Datapath` sin `RESET`; el `rst` de `register_file` queda sin conectar (R6).
- `Control_Unit`/`FSM` sin `TTY_WE` ni `HALT`; `HALT` cableado directo a `Illegal`; sin `syscall` 10/11 (R4/R10).
- `jal`/`jr` incompletos: un solo `IsJ`, sin `$31`, sin PC+4 en writeback, sin `rs`→PC.
- Sin fuente PC+4 ni desplazamiento de `lui`.

Detalle completo y evidencia en `docs/plan.md`, Anexo A.

---

## Riesgos Activos

| Riesgo | Impacto | Mitigación |
|---|---|---|
| Questa no instalado | No se puede validar la integración VHDL con `run_tests.py` | GHDL + testbench espejo; checkpoint Fase 6; contingencia 100 % Logisim |
| R16 (nombres) y R17 (RAM/ROM) | No evaluable / bloqueante | Diseño en Fase 1; revisión en Fase 6; sin ROM para FSM ni ALU |
| Límite de 60 000 ciclos | Programas largos abortan | 3-5 ciclos por instrucción; medir en Fase 8 |
| Carriles de byte (`lb`/`lbu`/`sb`) | Salida distinta a MARS | Pruebas dedicadas en Fase 7 y Fase 9 |
| Reset no cableado | `$gp`/`$sp` incorrectos | Puerto `RESET` en `Datapath`; prueba en Fase 7 |

---

## Decisiones de Arquitectura (cerradas en Fase 1)

| Decisión | Opción seleccionada | Justificación |
|----------|-------------------|---------------|
| VHDL componentes | Register_File + Instruction_Decoder | Máx 2 permitidos (R18); son los de mayor complejidad de cableado en Logisim |
| ALU | Logisim nativo | Solo una instancia; componentes aritméticos nativos disponibles |
| Reset | Asíncrono activo alto | R6 lo permite; fuerza PC, RF y FSM sin estado `RESET` |
| Máquina de estados | Moore, 12 estados | Salidas dependen del estado y de entradas registradas; tabla auditable |
| Estados de control | `FETCH`, `DECODE`, `EXEC_R`, `EXEC_I`, `ADDR`, `MEM_READ`, `MEM_WRITE`, `BRANCH`, `JUMP`, `SYSCALL`, `WB`, `HALT` | `docs/diseno.md` §6 |
| Verificación VHDL | GHDL local + Questa diferida | No hay Questa instalado; GHDL valida compilación y testbenches |
| Contingencia VHDL | Sustituir por circuitos Logisim | R18 permite cero VHDL si la integración no se puede validar |

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

### 2026-11-05 - Fase 1 cerrada: diseño de la CPU multiciclo

**¿Qué se hizo?**
- `docs/diseno.md`: ISA de 23 instrucciones base + 2 alias R9, tabla de decodificación de 25 filas, salidas del `Instruction_Decoder`, señales de control y codificación de muxes, ALU de 8 operaciones, ruta de datos, FSM de 12 estados, tabla de salidas por estado, casos especiales, ciclos, interfaces de los 6 subcircuitos, convención de túneles y matriz R1–R23.
- `docs/plan.md`: Fase 1 marcada como completada; Fase 2 alineada con reset asíncrono y `$gp`/`$sp`; Fases 4–5 alineadas con la FSM y `Branch_Control` definitivos.
- `docs/context.md`: decisiones de arquitectura cerradas y checklist de requisitos actualizado.

**¿Qué se probó?**
- Contraste de la ISA contra `docs/guide.tex`: 23 instrucciones base, 2 alias de R9, `TTY_DATA` de 7 bits, `$v0`/`$a0` como registros 2 y 4.
- Revisión cruzada de la tabla de decodificación: `jal` usa `REG_DST=10` (`$31`), `MEM_TO_REG=PC`; `sll`/`srl` intercambian operandos vía `ALU_SRC_A=B`; `lb`/`lbu`/`sb` usan `ALUOUT[1:0]`; `syscall` usa `RS1_SEL=1`/`RS2_SEL=1`.
- Coherencia plan↔diseño: estados, transiciones, reset, `PC+4` y `jal` sin contradicciones.

**Resultados**
- Diseño cerrado sin decisiones abiertas de arquitectura. La FSM tarda 3–5 ciclos por instrucción y no usa RAM/ROM (R17).
- El reset es asíncrono activo alto: `FETCH` como estado inicial, sin estado `RESET`; `$gp=0x1800`, `$sp=0x3FFC`, resto 0.

**¿Qué queda pendiente?**
- Fase 2: `circuit/register_file.vhd` + testbench funcional + testbench espejo, validado con GHDL.
- Fase 3: `circuit/instruction_decoder.vhd` + modelo Python de contraste.
- Fases 4–10 según `docs/plan.md`.

**Problemas y soluciones**
- El plan decía “todos los registros a 0” en reset y usaba estados genéricos (`EXECUTE`, `MEM_ACCESS`, `WRITEBACK`, `ILLEGAL`, `RESET`). Se corrigió para exigir `$gp`/`$sp` y para referenciar la FSM definitiva de 12 estados.
- La tabla de decodificación usaba `REG_DST=31` para `jal`, que se confundía con el número de registro; se cambió al código `10` con leyenda explícita.

**Decisiones de diseño**
- FSM Moore de 12 estados; reset asíncrono activo alto.
- `PC+4` con la ALU en `FETCH`; `PC` ya contiene `PC+4` en `WB`/`JUMP`.
- Comparador de igualdad de 32 bits en `Branch_Control` (R14).
- `jal` escribe `$31` con `MEM_TO_REG=PC`; `jr` usa `A` como destino.
- `HALT` solo por instrucción ilegal o `syscall 10`; `syscall 11` activa `TTY_WE` un solo ciclo.

---

### 2026-11-06 - Fase 2 cerrada: Register_File VHDL y testbenches (GHDL)

**¿Qué se hizo?**
- `circuit/register_file.vhd`: entidad `Register_File` de 32×32 bits, lecturas combinacionales `RD1`/`RD2`, escritura en flanco de subida con `REG_WRITE`, `$zero` protegido en lectura y escritura, reset asíncrono activo alto con `$gp=0x1800` (registro 28) y `$sp=0x3FFC` (registro 29), resto a 0. VHDL-2002, solo `ieee.std_logic_1164` e `ieee.numeric_std`, sin `wait`, `after`, ficheros ni valores iniciales (R19/R20).
- `tests/vhdl/register_file_tb.vhd`: testbench funcional que cubre reset (`$gp`/`$sp`/31 registros/`$zero`), lecturas simultáneas, `REG_WRITE=0`, escritura en flanco, protección de `$zero` y reset asíncrono a mitad de simulación.
- `tests/vhdl/top_sim_tb.vhd`: testbench espejo del wrapper `top_sim` capturado en la Fase 0; instancia `top_sim` con los nombres exactos `LogisimVhdlSimComp_Register_File_0_*` y comprueba el contrato de Logisim↔VHDL (R16/R19).
- `tools/check_vhdl.py`: validador repetible que analiza con `--std=02 --warn-all`, filtra el stub de `docs/contrato-logisim/` cuando el circuito ya define la entidad, comprueba el contrato de puertos y R19/R20 con `--lint`, elabora y ejecuta cada `*_tb` con `--assert-level=error --stop-time`.

**¿Qué se probó?**
- `python tools/check_vhdl.py --lint`: 4 archivos analizados, 2 testbenches ejecutados, salida 0, `TB_OK: Register_File funcional` (411 ns) y `TB_OK: top_sim (contrato Logisim)` (47 ns).
- `python tools/check_vhdl.py` (sin `--lint`): mismo resultado sin las reglas de lint.
- `tools/Ports.java` en modo headless sobre un `.circ` temporal: `Register_File` con 9 puertos exactos y anchos correctos (`CLK`, `RESET`, `REG_WRITE` de 1 bit; `RS1`, `RS2`, `RD` de 5 bits; `WD`, `RD1`, `RD2` de 32 bits; 7 entradas, 2 salidas).
- `python tools/check_circuit.py circuit/smips.circ --base`: `OK: 0 aviso(s), sin errores` (el `.circ` entregable sigue intacto, R2).

**Resultados**
- Fase 2 lista para commitear. El VHDL de `Register_File` cumple el contrato congelado en Fase 0 y el testbench espejo demuestra que Logisim podrá instanciarlo sin renombrar puertos.
- La cosimulación real con Questa sigue bloqueada (`QUESTA_BIN` vacío), pero la validación del contrato con GHDL es equivalente para esta fase (contingencia 100 % Logisim diferida al checkpoint de Fase 6).

**¿Qué queda pendiente?**
- Fase 3: `circuit/instruction_decoder.vhd` + modelo de referencia en Python y validación GHDL.
- Fases 4–10 según `docs/plan.md`.

**Decisiones de diseño**
- Ninguna nueva: el reset asíncrono activo alto y `$gp`/`$sp` ya estaban cerrados en Fase 1.

---

### 2026-11-07 - Fase 3 cerrada: Instruction_Decoder VHDL y testbench (GHDL)

**¿Qué se hizo?**
- `circuit/instruction_decoder.vhd`: entidad `Instruction_Decoder` combinacional pura, 16 puertos de salida, sin estado. Decodifica `OP` (6 bits) y `FUNCT` (6 bits) según la tabla de `docs/diseno.md` §2.3: 25 instrucciones legales (23 base S-MIPS + `addu`/`addiu` alias R9) + 3 casos ilegales. `op=0` → mira `funct`; `op≠0` → mira solo `op` (R11). `ILLEGAL='1'` para pares no en tabla (R10); `0x00000000` = `sll $zero,$zero,0` legal (NOP). Codificaciones: `ALU_OP` (3 bits, 8 ops), `EXT_TYPE` (2 bits: zero/sign/shamt/branch), `MEM_SIZE` (word/byte), `BRANCH_TYPE` (none/beq/bne), `JUMP_TYPE` (none/j/jal/jr), `REG_DST` (rd/rt/$31), `MEM_TO_REG` (ALU/MDR/PC). `jal` usa `REG_DST=10` ($31) y `MEM_TO_REG=10` (PC). VHDL-2002, solo `ieee.std_logic_1164` e `ieee.numeric_std`, sin `wait`, `after`, ficheros ni valores iniciales (R19/R20).
- `tests/vhdl/instruction_decoder_tb.vhd`: testbench funcional con 28 casos (25 legales + 3 ilegales). Cada caso establece `OP`/`FUNCT` y verifica las 17 salidas contra el valor esperado.
- `tools/check_vhdl.py` (ya creado en Fase 2) valida ambos VHDL y los 3 testbenches.

**¿Qué se probó?**
- `python tools/check_vhdl.py --lint`: 6 archivos analizados, 3 testbenches ejecutados, salida 0. Mensajes `TB_OK`:
  - `Instruction_Decoder funcional` (28 ns)
  - `Register_File funcional` (411 ns)
  - `top_sim (contrato Logisim)` (47 ns)
- El validador comprueba R19/R20 (solo librerías permitidas, sin `wait`/`after`/valores iniciales) y el contrato de puertos del `Register_File`.

**Resultados**
- Fase 3 lista para commitear. El decodificador cubre toda la ISA S-MIPS y produce las señales que espera la FSM de `docs/diseno.md` §6–7.
- Cosimulación con Questa sigue bloqueada; validación del contrato mediante GHDL y `check_vhdl.py`.

**¿Qué queda pendiente?**
- Fase 4: `Datapath` en Logisim (PC, IR, ALU, muxes, extension, alineación bytes).
- Fases 5–10 según `docs/plan.md`.

**Decisiones de diseño**
- `Instruction_Decoder` puramente combinacional (sin biestables), todas las salidas se asignan en un único `process (OP, FUNCT)`.
- Las 3 salidas de clasificación (`IS_RTYPE`, `IS_ITYPE`, `IS_JTYPE`) son mutuamente excluyentes salvo `syscall`/`jr` que son R-type.
- `LUI_OP` redundante con `ALU_OP=111` pero mantenida por claridad en `Control_Unit`.

---

### 2026-11-08 - Fase 4: Datapath Logisim adaptado al contrato

**¿Qué se hizo?**
- Se descartó el `Datapath` generado anteriormente y se reconstruyó con `tools/circuitlib.py`, tomando como referencia la *topología* del `Datapath` del repo guía (commit `e518e22`) y adaptándola a `docs/diseno.md` §10.4. El proceso quedó como script reproducible en `tools/gen_datapath.py`.
- `circuit/smips.circ` ahora contiene los subcircuitos `ALU` y `Datapath` y la entidad VHDL `Register_File` embebida. `Board`, `Memory` y los 10 pines de `CPU` no se tocaron (R2).
- `ALU` nativa con 8 operaciones (`ADD`, `SUB`, `AND`, `OR`, `SLT` con signo, `SLL`, `SRL`, `LUI`) y `ZERO = (Y == 0)`; sin `CLK` y sin ROM.
- `Datapath` con PC, IR, A, B, ALUOUT y MDR; `Register_File` VHDL propio (Fase 2), muxes de operandos/destino/writeback, extensión de inmediato, `lui`, `PC+4`, `JUMP_TARGET`, carriles de byte y `MEM_BE`.
- Se eliminaron del diseño guía el `Decoder` con ROM (R17) y la `Memory` interna (R13/R17); `ALU_OP` entra como pin desde el `Instruction_Decoder`.

**¿Qué se probó?**
- `ALU`: valores conocidos para las 8 operaciones, incluidos `slt` con signo (`-5 < 3 → 1`, `5 < -3 → 0`, `INT_MAX < INT_MIN → 0`, `INT_MIN < INT_MAX → 1`) y `ZERO`.
- `Datapath`: carga headless con Logisim 5.0.0 (`Ports.java`, salida 0). 218 cables, 218 túneles, 81 etiquetas, sin anchos inconsistentes, sin túneles solapados/huérfanos y sin puertos de componente sin cable.
- Los 32 pines del `Datapath` coinciden con §10.4 (24 entradas + 8 salidas); `Register_File` conserva sus 9 puertos y la instancia `ALU` sus 5.
- `python tools/check_circuit.py circuit/smips.circ --base` → `OK: 0 aviso(s), sin errores`.
- `git diff circuit/smips.circ` no elimina líneas: `Board`, `CPU` y `Memory` quedan intactos.

**Resultados**
- Estructura del `Datapath` completa y cargable. La adaptación corrige los defectos bloqueantes del repo guía sin copiar su banco de registros, su ALU ni su control.

**Problemas y soluciones**
- Los `Splitter` con `fanout=1` reportaban 32 bits si no se declaraban todos los atributos `bitN`; los túneles quedaban con anchos inconsistentes (2/4/5/26 bits mezclados con 32). Solución: emitir los 32 `bitN` con `none` en los no usados y fusionar rangos en una sola llamada.
- `PC_SRC=01` no puede leer `ALUOUT`: `PC` y `ALUOUT` capturan en el mismo flanco y `PC` vería el destino anterior. Solución: `PC_SRC=00` y `01` seleccionan ambos `D_ALU_Y`; documentado en `docs/diseno.md` §3.2/§5.1/§7/§8.4.
- La tabla `EXT_TYPE` de `docs/diseno.md` §5.2 estaba invertida respecto a `instruction_decoder.vhd`; corregida a `00 ZERO`, `01 SIGN`, `10 SHAMT`, `11 BRANCH`.
- `JUMP_TYPE` se mantiene por contrato pero no se usa internamente: `PC_SRC` ya codifica `j`/`jal`/`jr`. Es la única entrada sin cable del `Datapath`.

**¿Qué queda pendiente?**
- Fase 5: `Control_Unit` y `Branch_Control`.
- Fase 6: cablear la `CPU` con los seis subcircuitos.
- Verificación funcional del `Datapath` completo y cosimulación VHDL: bloqueadas por falta de Questa.
- `tools/check_circuit.py` sin `--base` seguirá fallando hasta que existan los subcircuitos de control y el cableado de `CPU`.

**Decisiones de diseño**
- Se adapta la topología del repo guía, pero se reescribe con `circuitlib` y se usa el `Register_File` propio; no se copia VHDL, ALU ni FSM del repo guía.
- `MEM_BE` se genera en el `Datapath` a partir de `MEM_SIZE`, `ALUOUT[1:0]` y `MEM_WE`, como fija §5.4.
- `TTY_DATA = B[6:0]` (sin registro adicional), tal como espera el `Board`.

---

### 2026-11-05 - Fase 0 cerrada: contrato Logisim↔VHDL y línea base

**¿Qué se hizo?**
- Copia temporal `prueba_regfile.circ` con la entidad `Register_File` (stub) instanciada en `CPU`; el `circuit/smips.circ` original no se modificó (R2).
- `docs/contrato-logisim/`: `README.md`, `top_sim.vhdl`, `Register_File.vhdl`, `comp.tcl`, `run.tcl` y `questasim_binder.tcl` capturados de Logisim 5.0.0.
- Corregida la ruta de MARS a `D:\EscuelaLuisi\AC\Mars4_5.jar` en la documentación y en las variables de la sesión.

**¿Qué se probó?**
- `Ports.java` cargó `Register_File` con el nombre exacto y 9 puertos: `CLK`, `RESET`, `RS1[4:0]`, `RS2[4:0]`, `RD[4:0]`, `WD[31:0]`, `REG_WRITE`, `RD1[31:0]`, `RD2[31:0]`.
- `run_tests.py` con la entidad VHDL generó wrapper, testbench y scripts Tcl antes de abortar por Questa.
- Línea base con la CPU vacía y `programs/hello.asm`: fallo esperado, `60000 ciclos`, `detenido=false`, `MEM_ADDR final 0xffffffffffffffff`, `0/1 correctos`.

**Resultados**
- Contrato fijado: prefijo `LogisimVhdlSimComp_<Entidad>_<índice>_<Puerto>`, mapeo por nombre y binder con mensajes `tipo:nombre:valor:id` (`1=in`, `2=out`, `3=inout`), `run 100` y `sync`.
- La línea base confirma que la placa arranca y que el fallo actual es la CPU vacía, no el entorno.

**Problemas y soluciones**
- Logisim aborta con `Cannot run program "nullvsim.exe"` porque `QUESTA_BIN` está vacío. No impide la captura de los artefactos; la cosimulación sigue bloqueada.
- La ruta de MARS documentada no existía; la real es `D:\EscuelaLuisi\AC\Mars4_5.jar`.

**¿Qué queda pendiente?**
- Fase 1: tabla de estados, señales de control, codificación ALU y matriz de trazabilidad R1–R23.
- Repetir la captura si se instala Questa; el VHDL del proyecto no debe cambiar.

**Decisiones de diseño**
- Los artefactos capturados se guardan como referencia de solo lectura; no se regeneran en cada build.
- El contrato de puertos de `Register_File` queda congelado a partir de esta captura.

---

### 2026-11-05 - Circuito de prueba generado y verificado por simulación

**¿Qué se hizo?**
- `tools/gen_prueba.py`: genera `circuit/prueba_generador.circ` con entradas `A`/`B`, compuertas `AND`/`OR`/`XOR`/`NOT` (tamaños 30/50/70/20) y salidas `AND_OUT`/`OR_OUT`/`XOR_OUT`/`NOT_OUT`, todo conectado con túneles.
- `tools/Verify.java`: carga el `.circ` en Logisim headless, conduce `A` y `B` y comprueba la tabla de verdad real leyendo los túneles de salida.

**¿Qué se probó?**
- `java -Djava.awt.headless=true --class-path "$env:LOGISIM_JAR" tools/Verify.java circuit/prueba_generador.circ` → 4 filas OK + `TODO OK`.
- El `.circ` carga con `Ports.java` y no contiene cables largos: cada puerto usa un túnel con nombre.

**Resultados**
- Queda demostrado el ciclo completo: describir en Python → descubrir puertos → cablear por nombre → cargar en Logisim → simular.

**Problemas y soluciones**
- En Logisim el **índice 0 de una compuerta es la salida**, no la primera entrada. Seleccionar puertos por índice producía un circuito que cargaba pero no calculaba lo esperado. Solución: filtrar por `type` (1=entrada, 2=salida) y ordenar las entradas por `y`.
- `discover_ports` devolvía `type` como texto; ahora es `int`, y la documentación aclara que en un `Pin` la dirección del puerto es la contraria a la del pin.

**¿Qué queda pendiente?**
- Usar el mismo patrón para `Datapath`, `Control_Unit`, `Branch_Control` y `CPU`.

**Decisiones de diseño**
- El `.circ` de prueba es un artefacto de verificación, no parte de la entrega; `circuit/smips.circ` sigue intacto.

---

### 2026-11-05 - Generador de circuitos Logisim (circuitlib) y verificador

**¿Qué se hizo?**
- `tools/circuitlib.py`: creación de proyecto, componentes, pines, subcircuitos con apariencia, túneles, cables, descubrimiento de puertos vía `Ports.java` y fusión que preserva `Board`/`Memory` (R2).
- `tools/check_circuit.py`: verifica pines exactos de `CPU` (R2), nombres R16, ausencia de RAM/ROM dentro de `CPU` (R17), rejilla de 10 px, túneles huérfanos y pines conectados. Modo `--base` para la CPU vacía.
- `tools/smoke_circuitlib.py`: prueba de humo con compuerta AND, túnel, recarga real del `.circ`, `connect_port`, validación de tamaños y merge que no toca `Board`/`Memory`.

**¿Qué se probó?**
- `python tools/smoke_circuitlib.py` → `TODO OK` (5 pruebas).
- `python tools/check_circuit.py circuit/smips.circ --base` → `OK: 0 aviso(s), sin errores`.
- Carga headless de los `.circ` generados con Logisim 5.0.0 (`Ports.java`).

**Resultados**
- Se puede generar, cablear y recargar circuitos sin abrir Logisim ni cablear a mano.

**Problemas y soluciones**
- Un `.circ` con `<a name="size" val="40"/>` en una `AND Gate` no cargaba: Logisim solo admite `size` 30/50/70 en compuertas de 2+ entradas (20/30 en `NOT`). El error real se ocultaba como `HeadlessException`. Solución: helper `gate()` que valida el tamaño antes de serializar y constantes `GATE_SIZES`/`NOT_GATE_SIZES`.
- El checker comparaba `in`/`out`, pero Logisim serializa `input`/`output`. Corregido.

**¿Qué queda pendiente?**
- Generadores por bloque (`gen_datapath.py`, `gen_control.py`, `gen_branch.py`, `gen_cpu.py`).
- Fase 0.3: capturar el wrapper/testbench que genera Logisim para una entidad VHDL.

**Decisiones de diseño**
- La conectividad se declara por nombre de señal (túnel), no por geometría; el layout solo evita solapamientos.
- Nunca se calcula a mano la coordenada de un puerto: se pregunta a `Ports.java`.
- Los circuitos generados se integran por merge, nunca regenerando el archivo completo (R2).

---

### 2026-11-05 - Actualización del plan y del contexto (pre-implementación)

**¿Qué se hizo?**
- Análisis completo del repo guía `luisiafk/Proyecto-S-MIPS-2026-2027` (commit `57c67b6`).
- Se añadió la Fase 0 (entorno y contrato Logisim↔VHDL) y el Anexo A al plan.
- Se reforzaron las fases 1, 2, 3, 4, 5, 7 y 8 con las trampas detectadas en el repo guía.
- Se registraron entorno, riesgos y decisiones en este archivo.

**¿Qué se probó?**
- GHDL 6.0.0 `--std=02 --warn-all` sobre el `register_file` VHDL del repo guía: compila y elabora sin errores ni avisos.
- Testbench propio: reset, `$gp=0x1800`, `$sp=0x3FFC`, `$zero` protegido, escritura/lectura → `TB_OK`.
- Entorno: Java 21, Logisim 5.0.0 y MARS 4.5 presentes; Questa ausente.

**Resultados**
- El VHDL de referencia es válido; la integración con Logisim no se puede verificar localmente por falta de Questa.

**¿Qué queda pendiente?**
- Fase 0: capturar el wrapper/testbench que genera Logisim.
- Fases 1-10 según `docs/plan.md`.

**Problemas y soluciones**
- Sin Questa: se adopta GHDL + testbench espejo y validación diferida; contingencia 100 % Logisim en el checkpoint de la Fase 6.

**Decisiones de diseño**
- VHDL para `Register_File` e `Instruction_Decoder`; `ALU` nativa en Logisim.
- Nombres exactos R16 desde el inicio; sin RAM/ROM dentro de la CPU.

---

## Checklist de Requisitos (R1-R23)

**Leyenda:** `Diseñado` = decisión y trazabilidad registradas en `docs/diseno.md`, todavía sin implementar. `Implementado` = circuito/VHDL presente. `Verificado` = prueba ejecutada con evidencia.

| Req | Descripción | Estado | Evidencia |
|-----|-------------|--------|-----------|
| R1 | CPU en smips.circ, Logisim 5.0.0 | Pendiente | Logisim 5.0.0 + Java 21 verificados (Fase 0); diseño en `docs/diseno.md` |
| R2 | No modificar Board/Memory/pines CPU | Verificado (parcial) | `check_circuit.py --base` OK; `git diff` de `smips.circ` solo añade circuitos (Fase 4) |
| R3 | Secuenciales en flanco CLK, sin relojes derivados | Diseñado | `docs/diseno.md` §5.1 y §6.3 |
| R4 | TTY_WE = 1 un ciclo por carácter | Diseñado | `docs/diseno.md` §8.1 |
| R5 | MEM_WE = 1 solo en sw/sb | Diseñado | `docs/diseno.md` §6.2 y §7 |
| R6 | Reset: PC=0, gp=0x1800, sp=0x3FFC, regs=0 | Diseñado | `docs/diseno.md` §6.3 |
| R7 | Reset no borra memoria | Diseñado | `docs/diseno.md` §6.3 (`MEM_WE=0`) |
| R8 | 23 instrucciones S-MIPS | Diseñado | `docs/diseno.md` §2.1: 23 base + 2 alias R9 = 25 filas |
| R9 | addu≡add, addiu≡addi | Diseñado | `docs/diseno.md` §2.3 |
| R10 | Instrucción ilegal → HALT; 0x00000000 = NOP | Diseñado | `docs/diseno.md` §8.2 |
| R11 | Identificación solo por op/funct | Diseñado | `docs/diseno.md` §2.1 |
| R12 | Multiciclo, una instrucción a la vez | Diseñado | `docs/diseno.md` §6 y §9: 3–5 ciclos |
| R13 | Memoria unificada, IR guarda instrucción | Diseñado | `docs/diseno.md` §5.1 y §10.7 |
| R14 | Una sola ALU, sin otros sumadores | Implementado (parcial) | `Datapath` instancia una única `ALU`, reconstruida sin ROM (Fase 4) |
| R15 | Control_Unit = máquina de estados síncrona | Diseñado | `docs/diseno.md` §6 |
| R16 | 6 subcircuitos con nombres exactos | Implementado (parcial) | `Register_File`, `Instruction_Decoder`, `ALU` y `Datapath` existen; faltan `Control_Unit`, `Branch_Control` y el cableado de `CPU` (Fases 2–5) |
| R17 | Sin RAM/ROM en CPU | Implementado (parcial) | `ALU` y `Datapath` sin RAM/ROM; se eliminó el `Decoder` con ROM del repo guía (Fase 4) |
| R18 | Máx 2 VHDL de 3 permitidos | Decidido | `Register_File` + `Instruction_Decoder`; `ALU` nativa |
| R19 | VHDL puertos std_logic, sin generics | Implementado (parcial) | Ambos VHDL compilan con `--std=02 --warn-all`; puertos exactos del contrato (Fases 2–3) |
| R20 | VHDL sintetizable, sin wait/after | Implementado (parcial) | Entidades sin `wait`/`after`/ficheros/valores iniciales; testbenches sí los usan (Fases 2–3) |
| R21 | tests/ cubriendo tabla de casos | Pendiente | Fase 9 |
| R22 | Repo GitHub por Telegram | Pendiente | Entrega final |
| R23 | smips.circ, .vhd, informe.pdf, tests/, salida-tests.txt | Pendiente | Fase 10 |

---

## Próximos Pasos Inmediatos

**Estado:** Fases 0–4 completadas (entorno, contrato Logisim↔VHDL, diseño, ambos VHDL y `Datapath`). El siguiente hito es la Fase 5 (`Control_Unit` + `Branch_Control`).

1. ~~Fase 0: verificar entorno, capturar el wrapper/testbench de Logisim y documentar el contrato Logisim↔VHDL.~~ Hecha.
2. ~~Fase 1: diseño, tabla de estados y matriz de trazabilidad R1–R23.~~ Hecha; ver `docs/diseno.md`.
3. ~~Fase 2: implementar `register_file.vhd` + testbench funcional + testbench espejo (GHDL).~~ Hecha.
4. ~~Fase 3: implementar `instruction_decoder.vhd` + modelo de referencia en Python (GHDL).~~ Hecha.
5. ~~Fase 4: `Datapath` en Logisim con `ALU` y `Register_File`.~~ Estructura hecha; verificación funcional pendiente de Questa.
6. Fase 5: `Control_Unit` y `Branch_Control` en Logisim.
7. Fase 6: integración de la `CPU` y **checkpoint** de integración VHDL.
8. Fases 7–10: testeo modular/general, `tests/` propios, informe y entrega.

---

## Comandos de Referencia

```powershell
# Variables de entorno (PowerShell)
$env:LOGISIM_JAR = "C:\Program Files\logisim-evolution\app\logisim-evolution-5.0.0-all.jar"
$env:MARS_JAR    = "D:\EscuelaLuisi\AC\Mars4_5.jar"

# Ensamblar un programa
python tools/assemble.py programs/hello.asm

# Ejecutar batería de pruebas completa
python tools/run_tests.py

# Ejecutar un solo programa
python tools/run_tests.py programs/memory.asm

# Validar VHDL con GHDL (no sustituye a Questa)
D:\EscuelaLuisi\AC\GHDL\bin\ghdl.exe -a --std=02 --warn-all register_file.vhd
D:\EscuelaLuisi\AC\GHDL\bin\ghdl.exe -e --std=02 register_file

# Abrir circuito en Logisim (Git Bash)
bash open.sh

# Generador de circuitos: prueba de humo y verificador
python tools/smoke_circuitlib.py
python tools/gen_datapath.py      # regenera ALU + Datapath en circuit/smips.circ
python tools/check_circuit.py circuit/smips.circ --base

# Circuito de prueba: generar y simular su tabla de verdad en Logisim
python tools/gen_prueba.py
java "-Djava.awt.headless=true" --class-path "$env:LOGISIM_JAR" tools/Verify.java circuit/prueba_generador.circ
```

**Nota:** `Logisim` serializa los pines como `input`/`output` (no `in`/`out`) y solo admite `size` 30/50/70 en compuertas de 2+ entradas (20/30 en `NOT`). Usar `circuitlib.gate()` para no generar un `.circ` que no carga.

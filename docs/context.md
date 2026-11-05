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
| `docs/plan.md` | Creado | Plan en 10 fases + Fase 0 + Anexo A |
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
| Commit | `57c67b6` (2026-11-04) |
| Contenido | `circuit/REGFILE.vhd`, `circuit/smips.circ` (4036 líneas) |
| Ausente | `tests/`, `informe.pdf`, `salida-tests.txt` |
| Veredicto | Prototipo en progreso; no es entrega ni solución validada |
| Uso | Referencia de intención; **no copiar** |

**Reutilizable:** conjunto de señales de control, registros intermedios PC/IR/A/B/ALUOUT/MDR, ecuación de `Branch_Control`, tabla de opcodes/functs, codificación ALU de 3 bits y el `register_file` VHDL (validado con GHDL 6.0.0 `--std=02 --warn-all`).

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
| R16 (nombres) y R17 (RAM/ROM) | No evaluable / bloqueante | Revisión en Fase 1 y Fase 6; sin ROM para FSM ni ALU |
| Límite de 60 000 ciclos | Programas largos abortan | 3-5 ciclos por instrucción; medir en Fase 8 |
| Carriles de byte (`lb`/`lbu`/`sb`) | Salida distinta a MARS | Pruebas dedicadas en Fase 7 y Fase 9 |
| Reset no cableado | `$gp`/`$sp` incorrectos | Puerto `RESET` en `Datapath`; prueba en Fase 7 |

---

## Decisiones de Arquitectura (pendiente de confirmar en implementación)

| Decisión | Opción seleccionada | Justificación |
|----------|-------------------|---------------|
| VHDL componentes | Register_File + Instruction_Decoder | Máx 2 permitidos (R18); son los de mayor complejidad de cableado en Logisim |
| ALU | Logisim nativo | Solo una instancia; componentes aritméticos nativos disponibles |
| Reset | Pendiente (asíncrono o síncrono) | R6 permite cualquiera |
| Máquina de estados | Pendiente (Moore o Mealy) | R15 permite cualquiera |
| Estados de control | Pendiente | Definir en Fase 1 |
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

| Req | Descripción | Estado | Evidencia |
|-----|-------------|--------|-----------|
| R1 | CPU en smips.circ, Logisim 5.0.0 | Pendiente | Logisim 5.0.0 + Java 21 verificados (Fase 0) |
| R2 | No modificar Board/Memory/pines CPU | Pendiente | Regla activa; comprobar en cada commit |
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
| R18 | Máx 2 VHDL de 3 permitidos | Decidido | `Register_File` + `Instruction_Decoder`; `ALU` nativa |
| R19 | VHDL puertos std_logic, sin generics | Pendiente | GHDL 6.0.0 listo; `register_file` de referencia compila sin avisos |
| R20 | VHDL sintetizable, sin wait/after | Pendiente | Reglas conservadoras en plan, Fase 2 |
| R21 | tests/ cubriendo tabla de casos | Pendiente | |
| R22 | Repo GitHub por Telegram | Pendiente | |
| R23 | smips.circ, .vhd, informe.pdf, tests/, salida-tests.txt | Pendiente | |

---

## Próximos Pasos Inmediatos

**Estado:** Fase 0 completada (entorno, contrato Logisim↔VHDL y línea base). El siguiente hito es la Fase 1.

1. ~~Fase 0: verificar entorno, capturar el wrapper/testbench de Logisim y documentar el contrato Logisim↔VHDL.~~ Hecha.
2. Fase 1: diseño, tabla de estados y matriz de trazabilidad R1–R23.
3. Fase 2: implementar `register_file.vhd` + testbench funcional + testbench espejo (GHDL).
4. Fase 3: implementar `instruction_decoder.vhd` + modelo de referencia en Python (GHDL).
5. Fase 4-6: Datapath, Control_Unit, Branch_Control e integración CPU en Logisim; **checkpoint** de integración VHDL.
6. Fase 7-8: testeo modular y general.
7. Fase 9: crear `tests/` propios cubriendo R21.
8. Fase 10: informe, `salida-tests.txt`, entrega en GitHub.

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
python tools/check_circuit.py circuit/smips.circ --base

# Circuito de prueba: generar y simular su tabla de verdad en Logisim
python tools/gen_prueba.py
java "-Djava.awt.headless=true" --class-path "$env:LOGISIM_JAR" tools/Verify.java circuit/prueba_generador.circ
```

**Nota:** `Logisim` serializa los pines como `input`/`output` (no `in`/`out`) y solo admite `size` 30/50/70 en compuertas de 2+ entradas (20/30 en `NOT`). Usar `circuitlib.gate()` para no generar un `.circ` que no carga.

# Diseño de la CPU multiciclo S-MIPS

Documento de la **Fase 1** del plan. Fija la arquitectura antes de escribir VHDL o
generar circuitos. Cualquier cambio posterior debe actualizar este archivo y
`docs/context.md`.

Referencia normativa: `docs/guide.tex` (R1–R23). Contrato Logisim↔VHDL:
`docs/contrato-logisim/README.md`.

---

## 1. Estado arquitectónico y formatos

- 32 registros de 32 bits (`$0`–`$31`); `$zero` vale siempre 0 y no se puede escribir.
- PC de 32 bits, fuera del banco de registros.
- Sin registro de banderas ni HI/LO.
- Memoria única de 4096 palabras (16 KiB), little-endian, con escritura por bytes.
- Formatos: R (`op|rs|rt|rd|shamt|funct`), I (`op|rs|rt|imm16`) y J (`op|dir26`).
- `$gp` inicial = `0x00001800`; `$sp` inicial = `0x00003FFC`; resto de registros = 0.

---

## 2. Repertorio y decodificación

### 2.1 Las 25 instrucciones legales

| Instrucción | Fmt | op | funct | Clase de control |
|---|---|---|---|---|
| `add rd,rs,rt` | R | `00` | `20` | ALU_R |
| `addu rd,rs,rt` | R | `00` | `21` | ALU_R (idéntica a `add`) |
| `sub rd,rs,rt` | R | `00` | `22` | ALU_R |
| `and rd,rs,rt` | R | `00` | `24` | ALU_R |
| `or rd,rs,rt` | R | `00` | `25` | ALU_R |
| `slt rd,rs,rt` | R | `00` | `2A` | ALU_R |
| `sll rd,rt,shamt` | R | `00` | `00` | ALU_R (desplazamiento) |
| `srl rd,rt,shamt` | R | `00` | `02` | ALU_R (desplazamiento) |
| `jr rs` | R | `00` | `08` | JUMP (JR) |
| `syscall` | R | `00` | `0C` | SYSCALL |
| `addi rt,rs,imm` | I | `08` | — | ALU_I (signo) |
| `addiu rt,rs,imm` | I | `09` | — | ALU_I (idéntica a `addi`) |
| `slti rt,rs,imm` | I | `0A` | — | ALU_I (signo) |
| `andi rt,rs,imm` | I | `0C` | — | ALU_I (cero) |
| `ori rt,rs,imm` | I | `0D` | — | ALU_I (cero) |
| `lui rt,imm` | I | `0F` | — | ALU_I (LUI) |
| `lb rt,imm(rs)` | I | `20` | — | LOAD (byte con signo) |
| `lw rt,imm(rs)` | I | `23` | — | LOAD (palabra) |
| `lbu rt,imm(rs)` | I | `24` | — | LOAD (byte sin signo) |
| `sb rt,imm(rs)` | I | `28` | — | STORE (byte) |
| `sw rt,imm(rs)` | I | `2B` | — | STORE (palabra) |
| `beq rs,rt,etiq` | I | `04` | — | BRANCH (BEQ) |
| `bne rs,rt,etiq` | I | `05` | — | BRANCH (BNE) |
| `j etiq` | J | `02` | — | JUMP (J) |
| `jal etiq` | J | `03` | — | JUMP (JAL) |

R8 exige las **23 instrucciones base** de la tabla de `guide.tex`; R9 añade
`addu` y `addiu` como alias obligatorios de `add` y `addi`. Por eso esta tabla
tiene **25 filas legales**: 23 base + 2 alias.

Reglas de identificación (R11):

- Si `OP = 0x00`, la instrucción se decide **solo** por `FUNCT`.
- Si `OP ≠ 0x00`, la instrucción se decide **solo** por `OP`.
- Cualquier par `(OP, FUNCT)` que no esté en la tabla produce `ILLEGAL = 1` (R10).
- `0x00000000` es `sll $zero,$zero,0`: legal, sin efecto (NOP). No se comprueba
  que los campos no usados valgan 0.

### 2.2 Salidas del `Instruction_Decoder`

| Señal | Ancho | Valores | Significado |
|---|---|---|---|
| `ILLEGAL` | 1 | 0/1 | Par `(op,funct)` fuera de tabla (R10). |
| `IS_RTYPE` | 1 | 0/1 | `op = 0x00` (incluye `jr` y `syscall`). |
| `IS_ITYPE` | 1 | 0/1 | `op` de formato I de la tabla. |
| `IS_JTYPE` | 1 | 0/1 | `op` de formato J (`j`, `jal`). |
| `ALU_OP` | 3 | ver §4 | Operación de la ALU. |
| `EXT_TYPE` | 2 | ver §2.3 | Extensión del inmediato o `shamt`. |
| `MEM_READ` | 1 | 0/1 | La instrucción lee memoria (`lw`, `lb`, `lbu`). |
| `MEM_WRITE` | 1 | 0/1 | La instrucción escribe memoria (`sw`, `sb`). |
| `MEM_SIZE` | 2 | `00`=palabra, `01`=byte | Tamaño del acceso. |
| `MEM_SIGNED` | 1 | 0/1 | `lb`=1, `lbu`/`lw`=0. |
| `BRANCH_TYPE` | 2 | `00`=ninguno, `01`=beq, `10`=bne | Tipo de salto condicional. |
| `JUMP_TYPE` | 2 | `00`=ninguno, `01`=j, `10`=jal, `11`=jr | Tipo de salto incondicional. |
| `REG_WRITE_ENABLE` | 1 | 0/1 | La instrucción escribe el banco de registros. |
| `REG_DST` | 2 | `00`=rd, `01`=rt, `10`=$31 | Registro destino. |
| `MEM_TO_REG` | 2 | `00`=ALUOUT, `01`=MDR, `10`=PC | Origen del dato de writeback. |
| `SYS_CALL` | 1 | 0/1 | La instrucción es `syscall`. |
| `LUI_OP` | 1 | 0/1 | La instrucción es `lui` (redundante con `ALU_OP=111`). |

### 2.3 Tabla de decodificación

Valores por defecto para toda instrucción legal: `ILLEGAL=0`, `MEM_READ=0`,
`MEM_WRITE=0`, `MEM_SIZE=00` (palabra), `MEM_SIGNED=0`, `BRANCH_TYPE=00`,
`JUMP_TYPE=00`, `SYS_CALL=0`, `LUI_OP=0`. `IS_RTYPE=1` solo si `op=00`;
`IS_ITYPE=1` para todo `op` de formato I de la tabla; `IS_JTYPE=1` solo para
`j`/`jal`.

| Instrucción | ALU_OP | EXT_TYPE | REG_DST | MEM_TO_REG | REG_WR | MEM_R | MEM_W | SIZE | SIGNED | BRANCH | JUMP | SYS |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `add` | ADD | ZERO | RD | ALU | 1 | 0 | 0 | W | 0 | — | — | 0 |
| `addu` | ADD | ZERO | RD | ALU | 1 | 0 | 0 | W | 0 | — | — | 0 |
| `sub` | SUB | ZERO | RD | ALU | 1 | 0 | 0 | W | 0 | — | — | 0 |
| `and` | AND | ZERO | RD | ALU | 1 | 0 | 0 | W | 0 | — | — | 0 |
| `or` | OR | ZERO | RD | ALU | 1 | 0 | 0 | W | 0 | — | — | 0 |
| `slt` | SLT | ZERO | RD | ALU | 1 | 0 | 0 | W | 0 | — | — | 0 |
| `sll` | SLL | SHAMT | RD | ALU | 1 | 0 | 0 | W | 0 | — | — | 0 |
| `srl` | SRL | SHAMT | RD | ALU | 1 | 0 | 0 | W | 0 | — | — | 0 |
| `jr` | ADD | ZERO | RD | ALU | 0 | 0 | 0 | W | 0 | — | JR | 0 |
| `syscall` | ADD | ZERO | RD | ALU | 0 | 0 | 0 | W | 0 | — | — | 1 |
| `addi` | ADD | SIGN | RT | ALU | 1 | 0 | 0 | W | 0 | — | — | 0 |
| `addiu` | ADD | SIGN | RT | ALU | 1 | 0 | 0 | W | 0 | — | — | 0 |
| `slti` | SLT | SIGN | RT | ALU | 1 | 0 | 0 | W | 0 | — | — | 0 |
| `andi` | AND | ZERO | RT | ALU | 1 | 0 | 0 | W | 0 | — | — | 0 |
| `ori` | OR | ZERO | RT | ALU | 1 | 0 | 0 | W | 0 | — | — | 0 |
| `lui` | LUI | ZERO | RT | ALU | 1 | 0 | 0 | W | 0 | — | — | 0 |
| `lb` | ADD | SIGN | RT | MDR | 1 | 1 | 0 | B | 1 | — | — | 0 |
| `lw` | ADD | SIGN | RT | MDR | 1 | 1 | 0 | W | 0 | — | — | 0 |
| `lbu` | ADD | SIGN | RT | MDR | 1 | 1 | 0 | B | 0 | — | — | 0 |
| `sb` | ADD | SIGN | RT | ALU | 0 | 0 | 1 | B | 0 | — | — | 0 |
| `sw` | ADD | SIGN | RT | ALU | 0 | 0 | 1 | W | 0 | — | — | 0 |
| `beq` | ADD | BRANCH | RT | ALU | 0 | 0 | 0 | W | 0 | BEQ | — | 0 |
| `bne` | ADD | BRANCH | RT | ALU | 0 | 0 | 0 | W | 0 | BNE | — | 0 |
| `j` | ADD | ZERO | RD | ALU | 0 | 0 | 0 | W | 0 | — | J | 0 |
| `jal` | ADD | ZERO | `10` (`$31`) | PC | 1 | 0 | 0 | W | 0 | — | JAL | 0 |

`LUI_OP=1` solo en `lui`; en el resto vale 0. Leyenda de la tabla: `W`=`00`
(palabra), `B`=`01` (byte); `ALU`=`00` (`ALUOUT`), `MDR`=`01`, `PC`=`10`;
`RD`=`00`, `RT`=`01`, `$31`=`10`. Los campos `REG_DST` y `MEM_TO_REG` de
instrucciones que no escriben registro son irrelevantes, pero se fijan a un
valor estable para que la simulación sea reproducible.

---

## 3. Señales de control

Todas las señales las genera `Control_Unit` (R16). Las que dependen solo de la
instrucción son paso directo de `Instruction_Decoder`; las que dependen del
estado se calculan en la FSM. La FSM es de tipo **Moore**: las salidas dependen
solo del estado y de las entradas registradas (IR, A, B, decoder), nunca de una
realimentación combinacional.

### 3.1 Habilitaciones y selección

| Señal | Ancho | Origen | Efecto |
|---|---|---|---|
| `PC_WRITE_CTL` | 1 | FSM | Escribe PC en `FETCH` y `JUMP`; en `BRANCH` la escritura la decide `Branch_Control`. |
| `PC_SRC` | 2 | FSM | Selector de la fuente de PC (§3.2). |
| `IR_WRITE` | 1 | FSM | Carga `IR` desde `MEM_RDATA` en `FETCH`. |
| `A_WRITE` | 1 | FSM | Carga `A` desde `RD1` en `DECODE`. |
| `B_WRITE` | 1 | FSM | Carga `B` desde `RD2` en `DECODE`. |
| `ALU_WRITE` | 1 | FSM | Carga `ALUOUT` con la salida de la ALU. |
| `MDR_WRITE` | 1 | FSM | Carga `MDR` desde `MEM_RDATA` en `MEM_READ`. |
| `REG_WRITE` | 1 | FSM | Escribe `Register_File` en `WB` (si `REG_WRITE_ENABLE=1`) o en `JUMP` (solo `jal`). |
| `MEM_WE` | 1 | FSM | Habilitación de escritura de la RAM; solo en `MEM_WRITE` (R5). |
| `TTY_WE` | 1 | FSM | Habilitación del TTY; solo en `SYSCALL` con servicio 11 (R4). |
| `HALT` | 1 | FSM | LED Halt; solo en `HALT` (R10 y syscall 10). |
| `RS1_SEL` | 1 | FSM | Dirección del primer puerto de lectura. |
| `RS2_SEL` | 1 | FSM | Dirección del segundo puerto de lectura. |
| `ALU_SRC_A` | 2 | FSM | Selector del operando A de la ALU. |
| `ALU_SRC_B` | 2 | FSM | Selector del operando B de la ALU. |
| `ALU_OP` | 3 | FSM | Operación de la ALU. |
| `MEM_ADDR_SEL` | 1 | FSM | Selector de `MEM_ADDR`. |
| `BRANCH_ENABLE` | 1 | FSM | Vale 1 solo en el estado `BRANCH`; habilita la decisión de `Branch_Control`. |

### 3.2 Codificación de los selectores

| Señal | Código | Selección |
|---|---|---|
| `PC_SRC` | `00` | Salida de la ALU (`PC+4` en `FETCH`). |
| | `01` | `ALUOUT` (destino de `beq`/`bne`). |
| | `10` | `JUMP_TARGET` (`{PC[31:28], IR[25:0], 00}`). |
| | `11` | `A` (dirección de `jr`). |
| `ALU_SRC_A` | `00` | Registro `A`. |
| | `01` | `PC`. |
| | `10` | Registro `B` (para `sll`/`srl`). |
| `ALU_SRC_B` | `00` | Registro `B`. |
| | `01` | `IMM_VALUE` (extensor según `EXT_TYPE`). |
| | `10` | Constante 4 (para `PC+4`). |
| `RS1_SEL` | `0` | `IR[25:21]` (`rs`). |
| | `1` | Constante 2 (`$v0`, solo `syscall`). |
| `RS2_SEL` | `0` | `IR[20:16]` (`rt`). |
| | `1` | Constante 4 (`$a0`, solo `syscall`). |
| `MEM_ADDR_SEL` | `0` | `PC`. |
| | `1` | `ALUOUT`. |

### 3.3 Señales estáticas (paso desde el decodificador)

| Señal | Ancho | Uso |
|---|---|---|
| `EXT_TYPE` | 2 | Extensor de inmediato (§5.2). |
| `REG_DST` | 2 | Registro destino en `WB` y `JUMP`. |
| `MEM_TO_REG` | 2 | Origen del dato de writeback. |
| `MEM_SIZE` | 2 | Palabra o byte para `MEM_BE` y extracción. |
| `MEM_SIGNED` | 1 | Extensión con signo en `lb`. |
| `BRANCH_TYPE` | 2 | Tipo de comparación en `Branch_Control`. |
| `JUMP_TYPE` | 2 | `j`, `jal` o `jr`. |

---

## 4. ALU

Una sola ALU combinacional (R14), con dos operandos de 32 bits, código de 3 bits,
resultado de 32 bits y salida `ZERO` (`1` si el resultado es 0).

| Código | Operación | Fórmula | Instrucciones |
|---|---|---|---|
| `000` | ADD | `A + B` | `add`, `addu`, `addi`, `addiu`, `lw/sw/lb/lbu/sb` (dirección), `PC+4`, destino de rama |
| `001` | SUB | `A - B` | `sub` |
| `010` | AND | `A and B` | `and`, `andi` |
| `011` | OR | `A or B` | `or`, `ori` |
| `100` | SLT | `1` si `signed(A) < signed(B)`, si no `0` | `slt`, `slti` |
| `101` | SLL | `A << B[4:0]` | `sll` |
| `110` | SRL | `A >> B[4:0]` (entran ceros) | `srl` |
| `111` | LUI | `{B[15:0], 16'b0}` | `lui` |

Notas:

- En `sll`/`srl`, `Control_Unit` pone `ALU_SRC_A = B` (valor de `RF[rt]`) y
  `ALU_SRC_B = IMM_VALUE` (`shamt`). Así la ALU ve el valor en `A` y el
  desplazamiento en `B`.
- En `lui`, `IMM_VALUE` es `ZeroExt(imm)`; la ALU toma `B[15:0]` y lo coloca en
  los 16 bits altos.
- `ZERO` se expone y se prueba, pero `Branch_Control` usa un comparador de
  igualdad propio (permitido por R14) para no ocupar la ALU: en el estado
  `BRANCH` la ALU calcula el destino y el comparador decide si se escribe PC.
- No hay ningún otro sumador en la CPU: `PC+4`, direcciones de memoria y destino
  de rama se calculan con esta ALU en ciclos distintos.

---

## 5. Ruta de datos

### 5.1 Registros internos

Todos son de 32 bits, se actualizan en el flanco de subida de `CLK` y tienen
reset asíncrono activo alto (R3/R6). Ninguno genera un reloj derivado.

| Registro | Origen | Uso |
|---|---|---|
| `PC` | `PC_SRC` | Dirección de la instrucción y base de `PC+4`. |
| `IR` | `MEM_RDATA` | Instrucción en curso durante todos sus ciclos (R13). |
| `A` | `Register_File.RD1` | Primer operando y dirección de `jr`. |
| `B` | `Register_File.RD2` | Segundo operando, dato de `sw`/`sb` y argumento de `syscall`. |
| `ALUOUT` | Salida de la ALU | Resultado, dirección de memoria o destino de rama. |
| `MDR` | `MEM_RDATA` | Palabra leída de memoria para `lw`/`lb`/`lbu`. |

`PC` es un registro con `Enable = PC_WRITE` y reset a 0. `IR`, `A`, `B`,
`ALUOUT` y `MDR` tienen enable propio y reset a 0. `Register_File` tiene reset
asíncrono con `$gp=0x1800` y `$sp=0x3FFC`.

### 5.2 Extensor de inmediato (`IMM_VALUE`)

| `EXT_TYPE` | Salida | Uso |
|---|---|---|
| `00` SIGN | `SignExt(IR[15:0])` | `addi`, `addiu`, `slti`, `lw`, `sw`, `lb`, `lbu`, `sb` |
| `01` ZERO | `ZeroExt(IR[15:0])` | `andi`, `ori`, `lui` |
| `10` BRANCH | `SignExt(IR[15:0]) << 2` | `beq`, `bne` |
| `11` SHAMT | `ZeroExt(IR[10:6])` | `sll`, `srl` |

El desplazamiento de `BRANCH` es concatenar dos ceros a la izquierda lógica; no
usa ningún sumador. El de `LUI` lo aplica la propia ALU (§4).

### 5.3 Destino de salto

```text
JUMP_TARGET = { PC[31:28], IR[25:0], 2'b00 }
```

Como `PC` ya vale `PC_original + 4` al terminar `FETCH`, la fórmula coincide con
`{(PC+4)[31:28], dir, 00}` y con el valor que `jal` guarda en `$31` (R14).

### 5.4 Memoria y bytes

- `MEM_ADDR` = `PC` en `FETCH`; `ALUOUT` en `MEM_READ` y `MEM_WRITE`.
- `MEM_BE` se calcula combinacionalmente:

| `MEM_WE` | `MEM_SIZE` | `MEM_BE` |
|---|---|---|
| 0 | cualquiera | `0000` |
| 1 | `00` palabra | `1111` |
| 1 | `01` byte | `0001 << ALUOUT[1:0]` |

- `MEM_WDATA`:
  - palabra (`sw`): `B`.
  - byte (`sb`): `{4{B[7:0]}}`; como `MEM_BE` habilita un único carril, el byte
    queda en la posición `ALUOUT[1:0]` sin afectar a los demás.
- `MDR` guarda la palabra completa leída. En `WB`:
  - `lw`: `WD = MDR`.
  - `lb`/`lbu`: se selecciona el byte `MDR[8*ALUOUT[1:0] +: 8]`; se aplica
    `SignExt` si `MEM_SIGNED=1`, `ZeroExt` si vale 0.
- `ALUOUT` conserva la dirección durante `MEM_READ` y `WB`, porque ninguno de
  esos estados lo sobrescribe.

### 5.5 Origen del dato de writeback

| `MEM_TO_REG` | Dato | Instrucciones |
|---|---|---|
| `00` ALUOUT | Resultado de la ALU | R-type, I-type ALU |
| `01` MDR | Palabra o byte extendido | `lw`, `lb`, `lbu` |
| `10` PC | `PC+4` | `jal` |

---

## 6. Máquina de estados (`Control_Unit`)

### 6.1 Codificación

| Estado | Código | Función |
|---|---|---|
| `FETCH` | `0000` | `IR <- mem[PC]`; `PC <- PC+4` con la ALU. |
| `DECODE` | `0001` | `A <- RF[rs]`, `B <- RF[rt]`; para `syscall`, `A <- $v0`, `B <- $a0`. |
| `EXEC_R` | `0010` | Operación ALU de tipo R. |
| `EXEC_I` | `0011` | Operación ALU con inmediato. |
| `ADDR` | `0100` | Calcula la dirección `A + SignExt(imm)`. |
| `MEM_READ` | `0101` | Lee memoria y carga `MDR`. |
| `MEM_WRITE` | `0110` | Escribe memoria (`MEM_WE=1`). |
| `BRANCH` | `0111` | Compara `A`/`B` y calcula el destino con la ALU. |
| `JUMP` | `1000` | Actualiza PC para `j`/`jal`/`jr`. |
| `SYSCALL` | `1001` | Servicio 10 (HALT) u 11 (TTY). |
| `WB` | `1010` | Escribe el resultado en `Register_File`. |
| `HALT` | `1011` | `HALT=1`; permanece hasta el reset. |

Los códigos `1100`–`1111` no se usan. Si aparecieran por una metaestabilidad, la
lógica de próximo estado los envía a `HALT` (defensa, no forma parte del
funcionamiento normal).

### 6.2 Transiciones

| Estado actual | Condición | Estado siguiente |
|---|---|---|
| `FETCH` | siempre | `DECODE` |
| `DECODE` | `ILLEGAL=1` | `HALT` |
| `DECODE` | `SYS_CALL=1` | `SYSCALL` |
| `DECODE` | `IS_JTYPE=1` o `JUMP_TYPE=11` (`jr`) | `JUMP` |
| `DECODE` | `BRANCH_TYPE≠00` | `BRANCH` |
| `DECODE` | `MEM_READ=1` o `MEM_WRITE=1` | `ADDR` |
| `DECODE` | `IS_RTYPE=1` | `EXEC_R` |
| `DECODE` | `IS_ITYPE=1` | `EXEC_I` |
| `DECODE` | otro caso (defensa) | `HALT` |
| `EXEC_R` | siempre | `WB` |
| `EXEC_I` | siempre | `WB` |
| `ADDR` | `MEM_READ=1` | `MEM_READ` |
| `ADDR` | `MEM_WRITE=1` | `MEM_WRITE` |
| `ADDR` | otro caso (defensa) | `HALT` |
| `MEM_READ` | siempre | `WB` |
| `MEM_WRITE` | siempre | `FETCH` |
| `BRANCH` | siempre | `FETCH` |
| `JUMP` | siempre | `FETCH` |
| `SYSCALL` | `A = 10` | `HALT` |
| `SYSCALL` | otro servicio | `FETCH` |
| `WB` | siempre | `FETCH` |
| `HALT` | siempre | `HALT` |
| cualquiera | `RESET=1` | `FETCH` (asíncrono) |

Prioridad en `DECODE`: `ILLEGAL` primero, después `SYS_CALL`, luego salto,
rama, memoria, R e I. Las salidas del decodificador son mutuamente excluyentes,
así que la prioridad solo protege ante una combinación anómala.

### 6.3 Reset

Se usa **reset asíncrono activo alto**. Mientras `RESET=1`:

- `PC=0`, `IR=0`, `A=0`, `B=0`, `ALUOUT=0`, `MDR=0`.
- `Register_File`: `$gp=0x1800`, `$sp=0x3FFC`, resto 0.
- Estado de la FSM = `FETCH`.
- `MEM_WE=0`, `TTY_WE=0`, `HALT=0`.
- Todas las habilitaciones de escritura incluyen `AND NOT RESET`.

No se escribe memoria durante el reset (R7): `MEM_WE` está forzado a 0.

---

## 7. Salidas por estado

Convenciones de la tabla: `D` = valor del decodificador; `BC` = decisión de
`Branch_Control`; `S11` = 1 solo si el servicio es 11; `JAL` = 1 solo para
`jal`; `~ILL` = 1 si la instrucción no es ilegal; `X` = no importa. Todas las
habilitaciones se AND con `NOT RESET`.

La columna `PC_WR` es la señal final `PC_WRITE` de la CPU: en `BRANCH` vale
`BC` (la salida `PC_WRITE_CTL` de `Control_Unit` es 0 y `PC_WRITE_BRANCH`
decide); en `FETCH` y `JUMP` vale 1 por `PC_WRITE_CTL`. La columna `REG_WR` es
el enable final del banco: `D` (`REG_WRITE_ENABLE`) en `WB` y `JAL` en `JUMP`.

| Estado | PC_WR | PC_SRC | IR_WR | A_WR | B_WR | ALU_WR | MDR_WR | REG_WR | MEM_WE | TTY_WE | HALT | ALU_SRC_A | ALU_SRC_B | ALU_OP | MEM_ADDR_SEL | RS1_SEL | RS2_SEL |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `FETCH` | 1 | ALU | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | PC | 4 | ADD | PC | X | X |
| `DECODE` | 0 | X | 0 | `~ILL` | `~ILL` | 0 | 0 | 0 | 0 | 0 | 0 | X | X | X | X | `SYS?2:rs` | `SYS?4:rt` |
| `EXEC_R` | 0 | X | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | `A/B` | `B/SH` | D | X | X | X |
| `EXEC_I` | 0 | X | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | A | IMM | D | X | X | X |
| `ADDR` | 0 | X | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | A | IMM | ADD | X | X | X |
| `MEM_READ` | 0 | X | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | X | X | X | ALUOUT | X | X |
| `MEM_WRITE` | 0 | X | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | X | X | X | ALUOUT | X | X |
| `BRANCH` | BC | ALUOUT | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | PC | IMM | ADD | X | X | X |
| `JUMP` | 1 | `JT/A` | 0 | 0 | 0 | 0 | 0 | JAL | 0 | 0 | 0 | X | X | X | X | X | X |
| `SYSCALL` | 0 | X | 0 | 0 | 0 | 0 | 0 | 0 | 0 | S11 | 0 | X | X | X | X | X | X |
| `WB` | 0 | X | 0 | 0 | 0 | 0 | 0 | D | 0 | 0 | 0 | X | X | X | X | X | X |
| `HALT` | 0 | X | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | X | X | X | X | X | X |

En `EXEC_R`, `A/B` significa: `A` salvo para `sll`/`srl`, que usan `B`;
`B/SH` significa `B` salvo para `sll`/`srl`, que usan `IMM_VALUE` (`shamt`).
`JT/A` significa `JUMP_TARGET` salvo `jr`, que usa `A`.

La señal `MEM_SIZE`, `MEM_SIGNED`, `EXT_TYPE`, `REG_DST`, `MEM_TO_REG`,
`BRANCH_TYPE` y `JUMP_TYPE` son paso directo del decodificador en todos los
estados; el Datapath solo las usa en los estados que corresponden.

---

## 8. Casos especiales

### 8.1 `syscall`

- En `DECODE`, `Control_Unit` fuerza `RS1_SEL=1` y `RS2_SEL=1`, de modo que
  `A=$v0` y `B=$a0` al terminar el ciclo.
- En `SYSCALL`:
  - `A=10` (`0x0000000A`): transición a `HALT`; no se escribe TTY ni registro.
  - `A=11` (`0x0000000B`): `TTY_DATA = B[6:0]` y `TTY_WE=1` durante el estado.
    El estado dura exactamente un ciclo, así que hay exactamente un flanco con
    `TTY_WE=1` (R4); después se va a `FETCH`.
  - Otro valor: no tiene efecto; se va a `FETCH`.
- `HALT` permanece en 1 porque `HALT` se autoenlaza hasta el reset. Durante
  `RESET=1`, el estado vuelve a `FETCH` y `HALT=0` (R6).

### 8.2 Instrucción ilegal y NOP

- `ILLEGAL=1` se detecta en `DECODE`. Se suprimen `A_WRITE` y `B_WRITE` y se
  pasa a `HALT`. No se escribe `Register_File`, no se escribe memoria y no se
  altera el TTY. `PC` e `IR` ya se cargaron en `FETCH`; a partir de `HALT` no
  hay ningún cambio más hasta el reset.
- `0x00000000` se decodifica como `sll $zero,$zero,0` (NOP legal). Recorre
  `EXEC_R` y `WB`, pero `Register_File` ignora la escritura a `$zero`.

### 8.3 `jal`, `jr` y `lui`

- `jal`: en `JUMP`, `PC_WRITE=1`, `PC_SRC=JUMP_TARGET`, `REG_WRITE=1`,
  `REG_DST=10` (`$31`), `MEM_TO_REG=PC`. El valor escrito es el registro `PC`,
  que ya contiene `PC+4` desde `FETCH`; no se necesita otra suma (R14).
- `jr`: en `JUMP`, `PC_WRITE=1`, `PC_SRC=A`. No escribe registro.
- `j`: en `JUMP`, `PC_WRITE=1`, `PC_SRC=JUMP_TARGET`. No escribe registro.
- `lui`: en `EXEC_I`, `ALU_OP=LUI`, `EXT_TYPE=ZERO`; la ALU devuelve
  `{IMM_VALUE[15:0], 16'b0}`.

### 8.4 Ramas

- `Branch_Control` compara `A` y `B` con un comparador de igualdad de 32 bits.
- `PC_WRITE_BRANCH = BRANCH_ENABLE AND ((BRANCH_TYPE=01 AND EQ) OR
  (BRANCH_TYPE=10 AND NOT EQ))`.
- El destino se calcula en la ALU como `PC + (SignExt(imm)<<2)` y se guarda en
  `ALUOUT`; si la rama no se toma, `PC_WRITE=0` y `PC` no cambia.
- `PC` ya es `PC+4`, así que la fórmula coincide con la del enunciado.

### 8.5 `lb`, `lbu`, `sb` y `sw`

- `lb`/`lbu`: `MEM_SIZE=01`, `MEM_SIGNED=1/0`; la extracción usa
  `ALUOUT[1:0]` (dirección efectiva).
- `sb`: `MEM_SIZE=01`; `MEM_WDATA={4{B[7:0]}}`; `MEM_BE` activa solo el carril
  `ALUOUT[1:0]`. Como solo se habilita un carril, replicar el byte en los cuatro
  es equivalente a colocarlo únicamente en el carril seleccionado.
- `sw`: `MEM_SIZE=00`; `MEM_WDATA=B`; `MEM_BE=1111`.
- La memoria de la placa ignora `MEM_ADDR[1:0]` al leer la palabra; la CPU es
  quien selecciona el byte.

---

## 9. Ciclos por instrucción

| Clase | Estados recorridos | Ciclos |
|---|---|---|
| ALU tipo R (`add`, `sub`, `and`, `or`, `slt`, `addu`) | `FETCH → DECODE → EXEC_R → WB` | 4 |
| Desplazamiento (`sll`, `srl`) | `FETCH → DECODE → EXEC_R → WB` | 4 |
| ALU con inmediato (`addi`, `addiu`, `slti`, `andi`, `ori`, `lui`) | `FETCH → DECODE → EXEC_I → WB` | 4 |
| Carga (`lw`, `lb`, `lbu`) | `FETCH → DECODE → ADDR → MEM_READ → WB` | 5 |
| Almacenamiento (`sw`, `sb`) | `FETCH → DECODE → ADDR → MEM_WRITE` | 4 |
| Rama (`beq`, `bne`) | `FETCH → DECODE → BRANCH` | 3 |
| Salto (`j`, `jal`, `jr`) | `FETCH → DECODE → JUMP` | 3 |
| `syscall` | `FETCH → DECODE → SYSCALL` | 3 |
| Ilegal | `FETCH → DECODE → HALT` | 3 |
| NOP (`sll $zero,$zero,0`) | `FETCH → DECODE → EXEC_R → WB` | 4 |

El máximo es 5 ciclos por instrucción, dentro de la referencia de 3–5 del
enunciado y muy por debajo del límite de 60 000 ciclos de `run_tests.py`.

---

## 10. Interfaces de los subcircuitos

### 10.1 `Instruction_Decoder` (VHDL)

```vhdl
entity Instruction_Decoder is
  port (
    OP               : in  std_logic_vector(5 downto 0);
    FUNCT            : in  std_logic_vector(5 downto 0);
    ILLEGAL          : out std_logic;
    IS_RTYPE         : out std_logic;
    IS_ITYPE         : out std_logic;
    IS_JTYPE         : out std_logic;
    ALU_OP           : out std_logic_vector(2 downto 0);
    EXT_TYPE         : out std_logic_vector(1 downto 0);
    MEM_READ         : out std_logic;
    MEM_WRITE        : out std_logic;
    MEM_SIZE         : out std_logic_vector(1 downto 0);
    MEM_SIGNED       : out std_logic;
    BRANCH_TYPE      : out std_logic_vector(1 downto 0);
    JUMP_TYPE        : out std_logic_vector(1 downto 0);
    REG_WRITE_ENABLE : out std_logic;
    REG_DST          : out std_logic_vector(1 downto 0);
    MEM_TO_REG       : out std_logic_vector(1 downto 0);
    SYS_CALL         : out std_logic;
    LUI_OP           : out std_logic
  );
end entity;
```

Cumple R19: solo `std_logic`/`std_logic_vector`, sin generics, VHDL-2002.

### 10.2 `Control_Unit` (Logisim)

Entradas: `CLK`, `RESET`, `ILLEGAL`, `IS_RTYPE`, `IS_ITYPE`, `IS_JTYPE`,
`ALU_OP_DEC` (3), `EXT_TYPE_DEC` (2), `MEM_READ`, `MEM_WRITE`, `MEM_SIZE_DEC`
(2), `MEM_SIGNED_DEC`, `BRANCH_TYPE_DEC` (2), `JUMP_TYPE_DEC` (2),
`REG_WRITE_ENABLE`, `REG_DST_DEC` (2), `MEM_TO_REG_DEC` (2), `SYS_CALL`,
`LUI_OP`, `A` (32).

Salidas: todas las de §3, incluida `BRANCH_ENABLE`. La FSM usa un registro de
estado de 4 bits, lógica combinacional de próximo estado con muxes/puertas y
ninguna ROM/RAM (R17).

Los nombres de puerto de esta sección son lógicos. En los túneles del `.circ` se
aplican los prefijos de §11: las salidas del decodificador se llaman
`DEC_*` (`DEC_ALU_OP`, `DEC_EXT_TYPE`, …) y las de `Control_Unit`, `CTL_*`
(`CTL_ALU_OP`, `CTL_PC_WRITE`, …). Así se evita que dos señales distintas
compartan nombre.

### 10.3 `Branch_Control` (Logisim)

Entradas: `A` (32), `B` (32), `BRANCH_TYPE` (2), `BRANCH_ENABLE`.

Salidas: `EQ` (1), `PC_WRITE_BRANCH` (1).

```text
EQ              = (A = B)
PC_WRITE_BRANCH = BRANCH_ENABLE AND
                  ((BRANCH_TYPE = 01 AND EQ) OR
                   (BRANCH_TYPE = 10 AND NOT EQ))
```

### 10.4 `Datapath` (Logisim)

Entradas: `CLK`, `RESET`, `MEM_RDATA` (32), `PC_WRITE`, `PC_SRC` (2),
`IR_WRITE`, `A_WRITE`, `B_WRITE`, `ALU_WRITE`, `MDR_WRITE`, `REG_WRITE`,
`RS1_SEL`, `RS2_SEL`, `ALU_SRC_A` (2), `ALU_SRC_B` (2), `ALU_OP` (3),
`MEM_ADDR_SEL`, `EXT_TYPE` (2), `REG_DST` (2), `MEM_TO_REG` (2),
`MEM_SIZE` (2), `MEM_SIGNED`, `JUMP_TYPE` (2), `MEM_WE`.

Salidas: `MEM_ADDR` (32), `MEM_WDATA` (32), `MEM_BE` (4), `IR` (32), `A` (32),
`B` (32), `ALU_ZERO`, `TTY_DATA` (7, `= B[6:0]`).

Contiene instancias de `Register_File` y `ALU` (R16). No contiene RAM/ROM (R17).

### 10.5 `Register_File` (VHDL)

Contrato congelado en `docs/contrato-logisim/README.md`:

```vhdl
entity Register_File is
  port (
    CLK       : in  std_logic;
    RESET     : in  std_logic;
    RS1       : in  std_logic_vector(4 downto 0);
    RS2       : in  std_logic_vector(4 downto 0);
    RD        : in  std_logic_vector(4 downto 0);
    WD        : in  std_logic_vector(31 downto 0);
    REG_WRITE : in  std_logic;
    RD1       : out std_logic_vector(31 downto 0);
    RD2       : out std_logic_vector(31 downto 0)
  );
end entity;
```

### 10.6 `ALU` (Logisim)

Entradas: `A` (32), `B` (32), `ALU_OP` (3). Salidas: `Y` (32), `ZERO` (1).
Una sola instancia en todo el diseño (R14).

### 10.7 `CPU`

Los 10 pines exactos de R2: `CLK`, `RESET`, `MEM_RDATA`, `MEM_ADDR`,
`MEM_WDATA`, `MEM_BE`, `MEM_WE`, `TTY_DATA`, `TTY_WE`, `HALT`.

Instancia `Instruction_Decoder`, `Control_Unit`, `Branch_Control` y `Datapath`.
`PC_WRITE = PC_WRITE_CTL OR PC_WRITE_BRANCH`. `HALT`, `TTY_WE` y `MEM_WE` salen
de `Control_Unit`; `TTY_DATA` sale del `Datapath`.

---

## 11. Convención de nombres de túneles

Regla: **una señal, un nombre y un ancho** en toda la jerarquía. No se reutiliza
un túnel para dos señales distintas ni se cambia el ancho entre niveles.

| Prefijo | Uso | Ejemplos |
|---|---|---|
| `D_` | Datos internos del Datapath | `D_PC`, `D_IR`, `D_A`, `D_B`, `D_ALUOUT`, `D_MDR`, `D_IMM`, `D_JUMP_TARGET` |
| `CTL_` | Control generado por `Control_Unit` | `CTL_PC_WRITE`, `CTL_IR_WRITE`, `CTL_ALU_OP`, `CTL_MEM_WE` |
| `DEC_` | Salidas del decodificador | `DEC_ILLEGAL`, `DEC_ALU_OP`, `DEC_EXT_TYPE` |
| `RF_` | Puertos del banco de registros | `RF_RS1`, `RF_RS2`, `RF_RD`, `RF_WD`, `RF_RD1`, `RF_RD2` |
| `ALU_` | Puertos de la ALU | `ALU_A`, `ALU_B`, `ALU_OP`, `ALU_Y`, `ALU_ZERO` |
| `MEM_` | Interfaz de memoria (nombres de pin) | `MEM_ADDR`, `MEM_WDATA`, `MEM_BE`, `MEM_WE` |
| `STATE_` | Estado de la FSM | `STATE`, `STATE_NEXT` |
| `TTY_`, `HALT` | Pines de la placa | `TTY_DATA`, `TTY_WE`, `HALT` |

Los nombres de los 10 pines de `CPU` son intocables (R2). Los estados se
codifican con constantes, no con túneles.

---

## 12. Matriz de trazabilidad R1–R23

| Req | Requisito | Elemento del diseño | Evidencia prevista |
|---|---|---|---|
| R1 | CPU en `circuit/smips.circ`, Logisim 5.0.0 | Subcircuito `CPU` generado y fusionado | `check_circuit.py` + apertura en Logisim 5.0.0 |
| R2 | `Board`/`Memory` y pines de `CPU` intactos | `merge_circuits()` conserva `Board`/`Memory`; 10 pines exactos | `git diff` + `check_circuit.py --base` en cada commit |
| R3 | Secuenciales en flanco de subida, sin relojes derivados | Todos los registros reciben `CLK` directo | Inspección del `.circ` + traza de simulación |
| R4 | `TTY_WE=1` exactamente un flanco por carácter | Salida Moore en `SYSCALL` con servicio 11 | `hello.asm` + traza de `TTY_WE` |
| R5 | `MEM_WE=1` solo en `sw`/`sb` | Salida Moore solo en `MEM_WRITE` | `memory.asm` + traza de `MEM_WE` |
| R6 | Reset: PC=0, `$gp=0x1800`, `$sp=0x3FFC`, resto 0 | Reset asíncrono en PC, RF y FSM; salidas forzadas a 0 | Testbench de reset + traza |
| R7 | Reset no borra memoria | `MEM_WE=0` durante reset | Test de memoria antes/después de reset |
| R8 | 23 instrucciones S-MIPS | Tabla del decodificador + FSM | `arithmetic.asm`, `memory.asm`, `branches.asm` |
| R9 | `addu≡add`, `addiu≡addi` | Filas alias en el decodificador | Programas con `li`/`move` |
| R10 | Ilegal → HALT; `0x00000000` = NOP legal | `ILLEGAL` + estado `HALT`; `funct=0` legal | Vectores del decodificador + programa con palabra ilegal |
| R11 | Identificación solo por `op`/`funct` | Decodificador usa solo `OP` y `FUNCT` | Comparación exhaustiva de 2^12 pares |
| R12 | Multiciclo, una instrucción a la vez | FSM de 12 estados | Traza de estados y ciclos |
| R13 | Memoria unificada, IR guarda la instrucción | Solo pines `MEM_*`; `IR` durante todos los ciclos | `check_circuit.py` (sin RAM/ROM) + traza |
| R14 | Una sola ALU, ningún otro sumador | Una instancia de `ALU`; `PC+4`, direcciones y destino de rama por la ALU | Inspección del `.circ` + pruebas |
| R15 | `Control_Unit` = FSM síncrona | Registro de estado + lógica combinacional de próximo estado | Tabla §6 + simulación de la FSM |
| R16 | 6 subcircuitos con nombres y jerarquía exactos | `CPU`, `Instruction_Decoder`, `Control_Unit`, `Branch_Control`, `Datapath`, `Register_File`, `ALU` | `check_circuit.py` |
| R17 | Sin RAM/ROM dentro de la CPU | Sin componentes `Memory`/`ROM` en `CPU` | `check_circuit.py` + inspección |
| R18 | Máx. 2 VHDL de 3 permitidos | Solo `Register_File` e `Instruction_Decoder` | Búsqueda de entidades VHDL en el `.circ` |
| R19 | Puertos `std_logic`, sin generics, librerías permitidas, VHDL-2002 | Entidades VHDL del §10 | `ghdl -a --std=02 --warn-all` |
| R20 | VHDL sintetizable, sin `wait`/`after`/ficheros | VHDL descriptivo | GHDL + búsqueda de palabras prohibidas |
| R21 | `tests/` cubre todas las filas de la tabla de casos | Programas propios de Fase 9 | `tests/` + tabla del informe |
| R22 | Repo GitHub enviado por Telegram | Entrega | Enlace + fecha |
| R23 | `smips.circ`, `.vhd`, `informe.pdf`, `tests/`, `salida-tests.txt` | Estructura del repo | Revisión final |

---

## 13. Riesgos y verificaciones críticas de la Fase 1

1. **`PC+4` e `IR` en el mismo flanco de `FETCH`.** `MEM_ADDR` debe ser el PC
   *antiguo* de forma combinacional; en el flanco, `IR` captura `MEM_RDATA`
   mientras `PC` captura `PC+4`. Hay que verificarlo en la simulación: si `IR`
   captura la instrucción siguiente, el diseño está mal.
2. **`jal` escribe `$31` y `PC` en el mismo flanco.** `Register_File` debe
   capturar el `PC` antiguo (que ya es `PC+4`) antes de que el registro `PC`
   cambie. Es el mismo comportamiento que en `FETCH`: ambos registros muestrean
   sus entradas simultáneamente.
3. **`sll`/`srl` intercambian operandos.** `ALU_SRC_A` debe seleccionar `B`
   (`RF[rt]`) y `ALU_SRC_B` el `shamt`. Es el error más fácil de cometer.
4. **`lb`/`lbu`/`sb` dependen de `ALUOUT[1:0]`.** `ALUOUT` no debe
   sobrescribirse entre `ADDR`, `MEM_READ`/`MEM_WRITE` y `WB`.
5. **`syscall` lee `$v0` y `$a0`, no `rs`/`rt`.** `RS1_SEL`/`RS2_SEL` deben
   forzarse a 2 y 4 en `DECODE` cuando `SYS_CALL=1`.
6. **R10 y el PC.** La instrucción ilegal se detecta en `DECODE`, después de que
   `FETCH` haya cargado `IR` y avanzado `PC`. A partir de `HALT` no se modifica
   ningún registro, memoria ni salida; el PC interno ya avanzó y no es visible
   en los pines. Esto se documentará en el informe.
7. **Reset asíncrono y salidas.** Todas las habilitaciones deben incluir
   `AND NOT RESET`; si no, con `RESET=1` y estado `FETCH` se escribiría `PC+4`.
8. **Sin Questa.** La FSM y el Datapath se validan por capas: GHDL para el VHDL,
   simulación manual/Logisim para el cableado y `run_tests.py` como puerta final
   cuando exista Questa.

## 14. Criterio de salida de la Fase 1

- [x] Repertorio de 25 instrucciones y tabla de decodificación.
- [x] Señales de control, anchos y codificación de muxes.
- [x] Codificación de la ALU.
- [x] Registros internos y ruta de datos.
- [x] Tabla de estados, transiciones y salidas por estado.
- [x] Conteo de ciclos por clase de instrucción.
- [x] Interfaces de los seis subcircuitos.
- [x] Convención de nombres de túneles.
- [x] Matriz de trazabilidad R1–R23.

Con esto se puede empezar la Fase 2 (`register_file.vhd`) sin decisiones
abiertas sobre la arquitectura.






# Contrato Logisim↔VHDL (Logisim Evolution 5.0.0)

Esta carpeta guarda los archivos que **genera Logisim** al detectar una entidad VHDL
dentro de un `.circ`, antes de intentar lanzar Questa. No son código del proyecto:
son la referencia congelada del contrato que deben cumplir
`circuit/register_file.vhd` e `circuit/instruction_decoder.vhd`.

## Origen de la captura

| Campo | Valor |
|---|---|
| Fecha de generación | `2026-11-05T16:30:21-0500` |
| Herramienta | Logisim Evolution 5.0.0 |
| Archivo de entrada | Copia temporal de `circuit/smips.circ` (el original no se tocó, R2) |
| Entidad de prueba | `Register_File`, cuerpo **stub** que fuerza `RD1` y `RD2` a cero |
| Instancia en `CPU` | `<comp name="Register_File" loc="(500,200)" />` |
| Resultado | Logisim escribió wrapper, testbench y scripts Tcl; después abortó por falta de Questa |

El `circuit/smips.circ` del repositorio **no** contiene esta entidad: la captura se
hizo en `%TEMP%\opencode\fase0\prueba_regfile.circ`.

## Archivos capturados

| Archivo | Qué es |
|---|---|
| `top_sim.vhdl` | Wrapper generado por Logisim: declara los puertos `LogisimVhdlSimComp_<Entidad>_<índice>_<Puerto>` e instancia la entidad. |
| `Register_File.vhdl` | Copia del stub usado para la prueba. **No es** el banco de registros definitivo. |
| `comp.tcl` | Compila las entidades y el wrapper con `vcom` dentro de la librería `work`. |
| `run.tcl` | Crea `logisim_work`, ejecuta `comp.tcl`, arranca `vsim top_sim` y lanza el binder. |
| `questasim_binder.tcl` | Cliente de sockets que recibe señales de Logisim, las fuerza en la simulación, ejecuta `run 100` y devuelve las salidas. |

## Contrato de puertos de `Register_File`

La entidad de la prueba se serializó en el `.circ` así:

```xml
<vhdl appearance="logisim_evolution" name="Register_File">…</vhdl>
<comp name="Register_File" loc="(500,200)" />
```

Logisim respetó el nombre con mayúsculas y estos puertos, en este orden:

| Puerto | Dirección | Tipo VHDL | Ancho Logisim |
|---|---|---|---|
| `CLK` | in | `std_logic` | 1 |
| `RESET` | in | `std_logic` | 1 |
| `RS1` | in | `std_logic_vector(4 downto 0)` | 5 |
| `RS2` | in | `std_logic_vector(4 downto 0)` | 5 |
| `RD` | in | `std_logic_vector(4 downto 0)` | 5 |
| `WD` | in | `std_logic_vector(31 downto 0)` | 32 |
| `REG_WRITE` | in | `std_logic` | 1 |
| `RD1` | out | `std_logic_vector(31 downto 0)` | 32 |
| `RD2` | out | `std_logic_vector(31 downto 0)` | 32 |

El wrapper generado confirma la correspondencia uno a uno:

```vhdl
LogisimVhdlSimComp_Register_File_0_CLK       : in  std_logic;
LogisimVhdlSimComp_Register_File_0_RESET     : in  std_logic;
LogisimVhdlSimComp_Register_File_0_RS1       : in  std_logic_vector(4 downto 0);
LogisimVhdlSimComp_Register_File_0_RS2       : in  std_logic_vector(4 downto 0);
LogisimVhdlSimComp_Register_File_0_RD        : in  std_logic_vector(4 downto 0);
LogisimVhdlSimComp_Register_File_0_WD        : in  std_logic_vector(31 downto 0);
LogisimVhdlSimComp_Register_File_0_REG_WRITE : in  std_logic;
LogisimVhdlSimComp_Register_File_0_RD1       : out std_logic_vector(31 downto 0);
LogisimVhdlSimComp_Register_File_0_RD2       : out std_logic_vector(31 downto 0);
```

Con una sola entidad VHDL, el índice es `0`. El puerto del wrapper es siempre
`LogisimVhdlSimComp_<NombreEntidad>_<índice>_<NombrePuerto>` y se mapea por nombre
en el `port map`; por eso **renombrar un puerto en VHDL rompe el contrato**.

## Cómo conduce Logisim la simulación

1. `run.tcl` borra y recrea la librería `logisim_work`, hace `vmap work` y ejecuta
   `do ../comp.tcl`.
2. `comp.tcl` compila primero cada entidad y después `top_sim.vhdl`:

   ```tcl
   vcom -reportprogress 300 -work work ../src/Register_File.vhdl
   vcom -reportprogress 300 -work work ../src/top_sim.vhdl
   ```

   El orden importa: la entidad debe existir antes que el wrapper.
3. `vsim top_sim` arranca la simulación y `questasim_binder.tcl $puerto` se conecta
   al socket TCP que abre Logisim en `localhost`.

`CLK` y `RESET` **no tienen tratamiento especial**: son entradas normales del
wrapper. Logisim envía su valor como cualquier otra señal. No hay reloj derivado
dentro de la entidad; el flanco lo produce el cambio de `CLK`.

## Protocolo del binder

Logisim abre un socket en `localhost` y pasa el puerto como `$1` a
`questasim_binder.tcl`. El binder usa un mensaje por línea.

### Señales

Formato:

```text
tipo:nombre:valor:id
```

| `tipo` | Significado | Acción del binder |
|---|---|---|
| `1` | entrada | `force -freeze sim:/top_sim/<nombre> <valor>` |
| `2` | salida | Se lee con `examine` y se devuelve |
| `3` | inout | `force -deposit sim:/top_sim/<nombre> <valor>` |

El `nombre` que usa el binder es el **puerto completo del wrapper**, porque lo
concatena como `sim:/top_sim/$name`. Ejemplo:
`LogisimVhdlSimComp_Register_File_0_REG_WRITE`.

### Secuencia de un paso

1. Logisim envía una o más señales (`tipo:nombre:valor:id`).
2. Logisim envía `sync`.
3. El binder fuerza las entradas y ejecuta `run 100`.
4. El binder lee cada salida y responde `nombre:valor:id`.
5. El binder responde `sync` para indicar el fin del paso.

Comandos especiales:

| Mensaje | Efecto |
|---|---|
| `restart` | `restart -f`, limpia la lista de señales pendientes |
| `end` | Cierra el socket, `quit -force` y termina |

El binder imprime `TCL_BINDER_CONNECTED` y `TCL_BINDER_RUNNING` al conectar, y
`TCL_BINDER_ENDED` al salir.

## Reglas para el VHDL del proyecto

Estas reglas vienen de R19/R20 y de lo observado en la captura:

- VHDL-2002 estricto.
- Solo `ieee.std_logic_1164` e `ieee.numeric_std`.
- Puertos únicamente `std_logic` y `std_logic_vector`, sin `generics`.
- Sin `wait`, `after`, ficheros ni valores iniciales en señales.
- Nombres de puertos y entidad exactamente como en la tabla; el subcircuito de
  Logisim debe llamarse `Register_File` / `Instruction_Decoder` (R16), aunque el
  archivo sea `register_file.vhd` / `instruction_decoder.vhd`.
- La lógica secuencial se describe dentro de un `process` disparado por `CLK`
  (y `RESET` si el reset es asíncrono), nunca con relojes derivados.
- `$zero` se protege tanto en lectura como en escritura.

## Límites de esta captura

- **No se pudo ejecutar la cosimulación**: Questa no está instalado y `vsim` no
  existe. Logisim genera los archivos y después falla en
  `VhdlSimulatorTclBinder.start` con `CreateProcess error=2`.
- Por tanto, la captura demuestra **qué archivos y nombres espera Logisim**, no
  que la simulación completa funcione.
- La validación local del VHDL se hace con GHDL 6.0.0 (`ghdl -a --std=02
  --warn-all`) y un testbench espejo que reproduzca el wrapper.
- Si se instala Questa, se repite la captura y se compara con esta carpeta; el
  VHDL del proyecto no debería cambiar.
- `modelsim.ini` generado por Logisim no se guarda: es configuración de Questa,
  no parte del contrato.

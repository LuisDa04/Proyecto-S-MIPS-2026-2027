--------------------------------------------------------------------------------
-- Register_File: banco de 32 registros de 32 bits para S-MIPS.
--
-- Contrato Logisim<->VHDL (R16/R19):
--   * Entidad y subcircuito: Register_File
--   * Puertos std_logic / std_logic_vector, sin generics
--   * VHDL-2002, solo ieee.std_logic_1164 e ieee.numeric_std
--   * Sin wait, after, ficheros ni valores iniciales (R20)
--
-- Comportamiento:
--   * Dos lecturas combinacionales: RD1 = R[RS1], RD2 = R[RS2].
--   * $zero (registro 0) vale siempre 0; escribir en el se ignora.
--   * Escritura sincrona en el flanco de subida de CLK si REG_WRITE = 1.
--   * Reset asincrono activo alto: $gp = 0x00001800, $sp = 0x00003FFC,
--     el resto de registros a 0.
--------------------------------------------------------------------------------

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

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
end entity Register_File;

architecture rtl of Register_File is
  type reg_array is array (0 to 31) of std_logic_vector(31 downto 0);
  signal regs : reg_array;
begin

  -- Lectura combinacional. El registro $zero se fuerza a 0 aunque su
  -- contenido interno ya sea 0 por el reset y por la proteccion de escritura.
  RD1 <= (others => '0') when RS1 = "00000"
         else regs(to_integer(unsigned(RS1)));

  RD2 <= (others => '0') when RS2 = "00000"
         else regs(to_integer(unsigned(RS2)));

  -- Escritura y reset. RESET es asincrono y activo alto (R6).
  process (CLK, RESET)
  begin
    if RESET = '1' then
      for i in 0 to 31 loop
        regs(i) <= (others => '0');
      end loop;
      regs(28) <= x"00001800";  -- $gp
      regs(29) <= x"00003FFC";  -- $sp
    elsif rising_edge(CLK) then
      if REG_WRITE = '1' and RD /= "00000" then
        regs(to_integer(unsigned(RD))) <= WD;
      end if;
    end if;
  end process;

end architecture rtl;

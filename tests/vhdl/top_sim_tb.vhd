--------------------------------------------------------------------------------
-- Testbench espejo del wrapper que genera Logisim Evolution 5.0.0.
--
-- Instancia la entidad top_sim capturada en docs/contrato-logisim/top_sim.vhdl,
-- cuyos puertos son exactamente:
--   LogisimVhdlSimComp_Register_File_0_<PUERTO>
--
-- Objetivo: comprobar que Register_File respeta el contrato de nombres, anchos
-- y direcciones que Logisim usara para la cosimulacion (R16/R19). No sustituye
-- a Questa; valida el contrato con GHDL.
--------------------------------------------------------------------------------

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity top_sim_tb is
end entity top_sim_tb;

architecture sim of top_sim_tb is
  constant CLK_PERIOD : time := 10 ns;

  signal LogisimVhdlSimComp_Register_File_0_CLK       : std_logic := '0';
  signal LogisimVhdlSimComp_Register_File_0_RESET     : std_logic := '1';
  signal LogisimVhdlSimComp_Register_File_0_RS1       : std_logic_vector(4 downto 0) := (others => '0');
  signal LogisimVhdlSimComp_Register_File_0_RS2       : std_logic_vector(4 downto 0) := (others => '0');
  signal LogisimVhdlSimComp_Register_File_0_RD        : std_logic_vector(4 downto 0) := (others => '0');
  signal LogisimVhdlSimComp_Register_File_0_WD        : std_logic_vector(31 downto 0) := (others => '0');
  signal LogisimVhdlSimComp_Register_File_0_REG_WRITE : std_logic := '0';
  signal LogisimVhdlSimComp_Register_File_0_RD1       : std_logic_vector(31 downto 0);
  signal LogisimVhdlSimComp_Register_File_0_RD2       : std_logic_vector(31 downto 0);

  procedure check32(
    constant actual   : in std_logic_vector(31 downto 0);
    constant expected : in std_logic_vector(31 downto 0);
    constant msg      : in string
  ) is
  begin
    assert actual = expected
      report msg
      severity failure;
  end procedure check32;

begin

  UUT: entity work.top_sim
    port map (
      LogisimVhdlSimComp_Register_File_0_CLK       => LogisimVhdlSimComp_Register_File_0_CLK,
      LogisimVhdlSimComp_Register_File_0_RESET     => LogisimVhdlSimComp_Register_File_0_RESET,
      LogisimVhdlSimComp_Register_File_0_RS1       => LogisimVhdlSimComp_Register_File_0_RS1,
      LogisimVhdlSimComp_Register_File_0_RS2       => LogisimVhdlSimComp_Register_File_0_RS2,
      LogisimVhdlSimComp_Register_File_0_RD        => LogisimVhdlSimComp_Register_File_0_RD,
      LogisimVhdlSimComp_Register_File_0_WD        => LogisimVhdlSimComp_Register_File_0_WD,
      LogisimVhdlSimComp_Register_File_0_REG_WRITE => LogisimVhdlSimComp_Register_File_0_REG_WRITE,
      LogisimVhdlSimComp_Register_File_0_RD1       => LogisimVhdlSimComp_Register_File_0_RD1,
      LogisimVhdlSimComp_Register_File_0_RD2       => LogisimVhdlSimComp_Register_File_0_RD2
    );

  LogisimVhdlSimComp_Register_File_0_CLK <= not LogisimVhdlSimComp_Register_File_0_CLK after CLK_PERIOD / 2;

  stimulus: process
  begin
    -- Reset asincrono a traves del puerto del wrapper.
    LogisimVhdlSimComp_Register_File_0_RESET <= '1';
    LogisimVhdlSimComp_Register_File_0_REG_WRITE <= '0';
    wait for 12 ns;

    LogisimVhdlSimComp_Register_File_0_RS1 <= std_logic_vector(to_unsigned(28, 5));
    LogisimVhdlSimComp_Register_File_0_RS2 <= std_logic_vector(to_unsigned(29, 5));
    wait for 1 ns;
    check32(LogisimVhdlSimComp_Register_File_0_RD1, x"00001800", "wrapper: $gp incorrecto tras reset");
    check32(LogisimVhdlSimComp_Register_File_0_RD2, x"00003FFC", "wrapper: $sp incorrecto tras reset");

    LogisimVhdlSimComp_Register_File_0_RS1 <= (others => '0');
    LogisimVhdlSimComp_Register_File_0_RS2 <= (others => '0');
    wait for 1 ns;
    check32(LogisimVhdlSimComp_Register_File_0_RD1, x"00000000", "wrapper: $zero no vale 0");
    check32(LogisimVhdlSimComp_Register_File_0_RD2, x"00000000", "wrapper: $zero no vale 0");

    LogisimVhdlSimComp_Register_File_0_RESET <= '0';
    wait for 1 ns;

    -- Escritura del registro 5 a traves del wrapper.
    LogisimVhdlSimComp_Register_File_0_RD <= std_logic_vector(to_unsigned(5, 5));
    LogisimVhdlSimComp_Register_File_0_WD <= x"CAFEBABE";
    LogisimVhdlSimComp_Register_File_0_REG_WRITE <= '1';
    wait until rising_edge(LogisimVhdlSimComp_Register_File_0_CLK);
    LogisimVhdlSimComp_Register_File_0_REG_WRITE <= '0';
    wait for 1 ns;

    LogisimVhdlSimComp_Register_File_0_RS1 <= std_logic_vector(to_unsigned(5, 5));
    LogisimVhdlSimComp_Register_File_0_RS2 <= std_logic_vector(to_unsigned(6, 5));
    wait for 1 ns;
    check32(LogisimVhdlSimComp_Register_File_0_RD1, x"CAFEBABE", "wrapper: lectura del registro 5 incorrecta");
    check32(LogisimVhdlSimComp_Register_File_0_RD2, x"00000000", "wrapper: el registro 6 no esta a 0");

    -- Segunda escritura y lectura simultanea.
    LogisimVhdlSimComp_Register_File_0_RD <= std_logic_vector(to_unsigned(6, 5));
    LogisimVhdlSimComp_Register_File_0_WD <= x"0BADF00D";
    LogisimVhdlSimComp_Register_File_0_REG_WRITE <= '1';
    wait until rising_edge(LogisimVhdlSimComp_Register_File_0_CLK);
    LogisimVhdlSimComp_Register_File_0_REG_WRITE <= '0';
    wait for 1 ns;

    LogisimVhdlSimComp_Register_File_0_RS1 <= std_logic_vector(to_unsigned(5, 5));
    LogisimVhdlSimComp_Register_File_0_RS2 <= std_logic_vector(to_unsigned(6, 5));
    wait for 1 ns;
    check32(LogisimVhdlSimComp_Register_File_0_RD1, x"CAFEBABE", "wrapper: RD1 simultaneo incorrecto");
    check32(LogisimVhdlSimComp_Register_File_0_RD2, x"0BADF00D", "wrapper: RD2 simultaneo incorrecto");

    -- $zero sigue protegido a traves del wrapper.
    LogisimVhdlSimComp_Register_File_0_RD <= (others => '0');
    LogisimVhdlSimComp_Register_File_0_WD <= x"FFFFFFFF";
    LogisimVhdlSimComp_Register_File_0_REG_WRITE <= '1';
    wait until rising_edge(LogisimVhdlSimComp_Register_File_0_CLK);
    LogisimVhdlSimComp_Register_File_0_REG_WRITE <= '0';
    wait for 1 ns;

    LogisimVhdlSimComp_Register_File_0_RS1 <= (others => '0');
    wait for 1 ns;
    check32(LogisimVhdlSimComp_Register_File_0_RD1, x"00000000", "wrapper: $zero cambio al escribirle");

    assert false report "TB_OK: top_sim (contrato Logisim)" severity note;
    wait;
  end process stimulus;

end architecture sim;

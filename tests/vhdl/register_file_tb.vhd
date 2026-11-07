--------------------------------------------------------------------------------
-- Testbench funcional de Register_File.
--
-- Cubre:
--   * Reset asincrono: $gp = 0x00001800, $sp = 0x00003FFC, resto a 0.
--   * Lectura combinacional y dos lecturas simultaneas.
--   * Escritura en el flanco de subida, con REG_WRITE = 0 sin efecto.
--   * Escritura y lectura de los 31 registros distintos de $zero.
--   * $zero no se puede escribir.
--   * Reset asincrono en mitad de la simulacion.
--
-- El testbench es solo para simulacion: usa 'after' y 'wait', prohibidos en
-- el VHDL sintetizable de la entidad (R20).
--------------------------------------------------------------------------------

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity register_file_tb is
end entity register_file_tb;

architecture sim of register_file_tb is
  constant CLK_PERIOD : time := 10 ns;

  signal CLK       : std_logic := '0';
  signal RESET     : std_logic := '1';
  signal RS1       : std_logic_vector(4 downto 0) := (others => '0');
  signal RS2       : std_logic_vector(4 downto 0) := (others => '0');
  signal RD        : std_logic_vector(4 downto 0) := (others => '0');
  signal WD        : std_logic_vector(31 downto 0) := (others => '0');
  signal REG_WRITE : std_logic := '0';
  signal RD1       : std_logic_vector(31 downto 0);
  signal RD2       : std_logic_vector(31 downto 0);

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

  DUT: entity work.Register_File
    port map (
      CLK       => CLK,
      RESET     => RESET,
      RS1       => RS1,
      RS2       => RS2,
      RD        => RD,
      WD        => WD,
      REG_WRITE => REG_WRITE,
      RD1       => RD1,
      RD2       => RD2
    );

  CLK <= not CLK after CLK_PERIOD / 2;

  stimulus: process
    procedure write_reg(
      constant idx   : in integer;
      constant value : in std_logic_vector(31 downto 0)
    ) is
    begin
      RD <= std_logic_vector(to_unsigned(idx, 5));
      WD <= value;
      REG_WRITE <= '1';
      wait until rising_edge(CLK);
      REG_WRITE <= '0';
      wait for 1 ns;
    end procedure write_reg;
  begin
    -- Reset asincrono inicial.
    RESET <= '1';
    REG_WRITE <= '0';
    RS1 <= (others => '0');
    RS2 <= (others => '0');
    wait for 12 ns;

    check32(RD1, x"00000000", "RD1 no vale 0 con RS1=$zero tras reset");
    check32(RD2, x"00000000", "RD2 no vale 0 con RS2=$zero tras reset");

    RS1 <= std_logic_vector(to_unsigned(28, 5));
    RS2 <= std_logic_vector(to_unsigned(29, 5));
    wait for 1 ns;
    check32(RD1, x"00001800", "$gp no vale 0x1800 tras reset");
    check32(RD2, x"00003FFC", "$sp no vale 0x3FFC tras reset");

    RS1 <= std_logic_vector(to_unsigned(1, 5));
    RS2 <= std_logic_vector(to_unsigned(2, 5));
    wait for 1 ns;
    check32(RD1, x"00000000", "el registro 1 no esta a 0 tras reset");
    check32(RD2, x"00000000", "el registro 2 no esta a 0 tras reset");

    RESET <= '0';
    wait for 1 ns;

    -- Escritura de un registro y lectura combinacional.
    write_reg(1, x"DEADBEEF");
    RS1 <= std_logic_vector(to_unsigned(1, 5));
    RS2 <= std_logic_vector(to_unsigned(2, 5));
    wait for 1 ns;
    check32(RD1, x"DEADBEEF", "el registro 1 no conserva el valor escrito");
    check32(RD2, x"00000000", "el registro 2 cambio al escribir el 1");

    write_reg(2, x"12345678");
    RS1 <= std_logic_vector(to_unsigned(1, 5));
    RS2 <= std_logic_vector(to_unsigned(2, 5));
    wait for 1 ns;
    check32(RD1, x"DEADBEEF", "lectura simultanea: RD1 incorrecto");
    check32(RD2, x"12345678", "lectura simultanea: RD2 incorrecto");

    -- $zero no se puede escribir.
    write_reg(0, x"FFFFFFFF");
    RS1 <= (others => '0');
    RS2 <= std_logic_vector(to_unsigned(1, 5));
    wait for 1 ns;
    check32(RD1, x"00000000", "$zero cambio tras intentar escribirlo");
    check32(RD2, x"DEADBEEF", "escribir $zero altero el registro 1");

    -- REG_WRITE = 0 no escribe.
    RD <= std_logic_vector(to_unsigned(3, 5));
    WD <= x"AAAAAAAA";
    REG_WRITE <= '0';
    wait until rising_edge(CLK);
    wait for 1 ns;
    RS1 <= std_logic_vector(to_unsigned(3, 5));
    wait for 1 ns;
    check32(RD1, x"00000000", "REG_WRITE=0 escribio el registro 3");

    -- La escritura ocurre en el flanco, no antes.
    RD <= std_logic_vector(to_unsigned(4, 5));
    WD <= x"11111111";
    REG_WRITE <= '1';
    RS1 <= std_logic_vector(to_unsigned(4, 5));
    wait for 1 ns;
    check32(RD1, x"00000000", "la escritura se adelanto al flanco");
    wait until rising_edge(CLK);
    wait for 1 ns;
    REG_WRITE <= '0';
    check32(RD1, x"11111111", "la escritura no ocurrio en el flanco de subida");

    -- Escritura y lectura de los 31 registros distintos de $zero.
    for i in 1 to 31 loop
      write_reg(i, std_logic_vector(to_unsigned(16#10000000# + i, 32)));
    end loop;

    for i in 1 to 31 loop
      RS1 <= std_logic_vector(to_unsigned(i, 5));
      RS2 <= std_logic_vector(to_unsigned((i mod 31) + 1, 5));
      wait for 1 ns;
      check32(
        RD1,
        std_logic_vector(to_unsigned(16#10000000# + i, 32)),
        "lectura incorrecta del registro " & integer'image(i)
      );
    end loop;

    -- Reset asincrono en mitad de la simulacion.
    RESET <= '1';
    wait for 1 ns;
    RS1 <= std_logic_vector(to_unsigned(28, 5));
    RS2 <= std_logic_vector(to_unsigned(29, 5));
    wait for 1 ns;
    check32(RD1, x"00001800", "reset asincrono: $gp incorrecto");
    check32(RD2, x"00003FFC", "reset asincrono: $sp incorrecto");

    RS1 <= std_logic_vector(to_unsigned(1, 5));
    wait for 1 ns;
    check32(RD1, x"00000000", "reset asincrono: el registro 1 no se borro");

    RESET <= '0';
    wait for 1 ns;

    assert false report "TB_OK: Register_File funcional" severity note;
    wait;
  end process stimulus;

end architecture sim;

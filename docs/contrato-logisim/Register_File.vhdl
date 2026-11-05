library ieee;
use ieee.std_logic_1164.all;

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
begin
    RD1 <= (others => '0');
    RD2 <= (others => '0');
end architecture rtl;

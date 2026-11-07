--------------------------------------------------------------------------------
-- Testbench funcional de Instruction_Decoder.
--
-- Recorre todas las instrucciones legales (23 base + addu/addiu = 25 filas)
-- y varios pares (OP, FUNCT) ilegales, comprobando cada salida de control
-- contra el valor esperado de docs/diseno.md §2.3.
--
-- El testbench es solo para simulacion: usa 'after' y 'wait', prohibidos en
-- el VHDL sintetizable de la entidad (R20).
--------------------------------------------------------------------------------

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity instruction_decoder_tb is
end entity instruction_decoder_tb;

architecture sim of instruction_decoder_tb is

  signal OP               : std_logic_vector(5 downto 0) := (others => '0');
  signal FUNCT            : std_logic_vector(5 downto 0) := (others => '0');
  signal ILLEGAL          : std_logic;
  signal IS_RTYPE         : std_logic;
  signal IS_ITYPE         : std_logic;
  signal IS_JTYPE         : std_logic;
  signal ALU_OP           : std_logic_vector(2 downto 0);
  signal EXT_TYPE         : std_logic_vector(1 downto 0);
  signal MEM_READ         : std_logic;
  signal MEM_WRITE        : std_logic;
  signal MEM_SIZE         : std_logic_vector(1 downto 0);
  signal MEM_SIGNED       : std_logic;
  signal BRANCH_TYPE      : std_logic_vector(1 downto 0);
  signal JUMP_TYPE        : std_logic_vector(1 downto 0);
  signal REG_WRITE_ENABLE : std_logic;
  signal REG_DST          : std_logic_vector(1 downto 0);
  signal MEM_TO_REG       : std_logic_vector(1 downto 0);
  signal SYS_CALL         : std_logic;
  signal LUI_OP           : std_logic;

  type caso_t is record
    nombre      : string(1 to 14);
    op          : std_logic_vector(5 downto 0);
    funct       : std_logic_vector(5 downto 0);
    illegal     : std_logic;
    is_rtype    : std_logic;
    is_itype    : std_logic;
    is_jtype    : std_logic;
    alu_op      : std_logic_vector(2 downto 0);
    ext_type    : std_logic_vector(1 downto 0);
    mem_read    : std_logic;
    mem_write   : std_logic;
    mem_size    : std_logic_vector(1 downto 0);
    mem_signed  : std_logic;
    branch_type : std_logic_vector(1 downto 0);
    jump_type   : std_logic_vector(1 downto 0);
    reg_write_en: std_logic;
    reg_dst     : std_logic_vector(1 downto 0);
    mem_to_reg  : std_logic_vector(1 downto 0);
    sys_call    : std_logic;
    lui_op      : std_logic;
  end record;

  type casos_t is array (natural range <>) of caso_t;

  constant CASOS : casos_t := (
    -- nombre      op     funct  ill r i j alu ext mr mw sz sg br ju rw dst mtr sys lui
    1  => (nombre => "add           ", op => "000000", funct => "100000",
           illegal => '0', is_rtype => '1', is_itype => '0', is_jtype => '0',
           alu_op => "000", ext_type => "00", mem_read => '0', mem_write => '0',
           mem_size => "00", mem_signed => '0', branch_type => "00",
           jump_type => "00", reg_write_en => '1', reg_dst => "00",
           mem_to_reg => "00", sys_call => '0', lui_op => '0'),
    2  => (nombre => "addu          ", op => "000000", funct => "100001",
           illegal => '0', is_rtype => '1', is_itype => '0', is_jtype => '0',
           alu_op => "000", ext_type => "00", mem_read => '0', mem_write => '0',
           mem_size => "00", mem_signed => '0', branch_type => "00",
           jump_type => "00", reg_write_en => '1', reg_dst => "00",
           mem_to_reg => "00", sys_call => '0', lui_op => '0'),
    3  => (nombre => "sub           ", op => "000000", funct => "100010",
           illegal => '0', is_rtype => '1', is_itype => '0', is_jtype => '0',
           alu_op => "001", ext_type => "00", mem_read => '0', mem_write => '0',
           mem_size => "00", mem_signed => '0', branch_type => "00",
           jump_type => "00", reg_write_en => '1', reg_dst => "00",
           mem_to_reg => "00", sys_call => '0', lui_op => '0'),
    4  => (nombre => "and           ", op => "000000", funct => "100100",
           illegal => '0', is_rtype => '1', is_itype => '0', is_jtype => '0',
           alu_op => "010", ext_type => "00", mem_read => '0', mem_write => '0',
           mem_size => "00", mem_signed => '0', branch_type => "00",
           jump_type => "00", reg_write_en => '1', reg_dst => "00",
           mem_to_reg => "00", sys_call => '0', lui_op => '0'),
    5  => (nombre => "or            ", op => "000000", funct => "100101",
           illegal => '0', is_rtype => '1', is_itype => '0', is_jtype => '0',
           alu_op => "011", ext_type => "00", mem_read => '0', mem_write => '0',
           mem_size => "00", mem_signed => '0', branch_type => "00",
           jump_type => "00", reg_write_en => '1', reg_dst => "00",
           mem_to_reg => "00", sys_call => '0', lui_op => '0'),
    6  => (nombre => "slt           ", op => "000000", funct => "101010",
           illegal => '0', is_rtype => '1', is_itype => '0', is_jtype => '0',
           alu_op => "100", ext_type => "00", mem_read => '0', mem_write => '0',
           mem_size => "00", mem_signed => '0', branch_type => "00",
           jump_type => "00", reg_write_en => '1', reg_dst => "00",
           mem_to_reg => "00", sys_call => '0', lui_op => '0'),
    7  => (nombre => "sll           ", op => "000000", funct => "000000",
           illegal => '0', is_rtype => '1', is_itype => '0', is_jtype => '0',
           alu_op => "101", ext_type => "10", mem_read => '0', mem_write => '0',
           mem_size => "00", mem_signed => '0', branch_type => "00",
           jump_type => "00", reg_write_en => '1', reg_dst => "00",
           mem_to_reg => "00", sys_call => '0', lui_op => '0'),
    8  => (nombre => "srl           ", op => "000000", funct => "000010",
           illegal => '0', is_rtype => '1', is_itype => '0', is_jtype => '0',
           alu_op => "110", ext_type => "10", mem_read => '0', mem_write => '0',
           mem_size => "00", mem_signed => '0', branch_type => "00",
           jump_type => "00", reg_write_en => '1', reg_dst => "00",
           mem_to_reg => "00", sys_call => '0', lui_op => '0'),
    9  => (nombre => "jr            ", op => "000000", funct => "001000",
           illegal => '0', is_rtype => '1', is_itype => '0', is_jtype => '0',
           alu_op => "000", ext_type => "00", mem_read => '0', mem_write => '0',
           mem_size => "00", mem_signed => '0', branch_type => "00",
           jump_type => "11", reg_write_en => '0', reg_dst => "00",
           mem_to_reg => "00", sys_call => '0', lui_op => '0'),
    10 => (nombre => "syscall       ", op => "000000", funct => "001100",
           illegal => '0', is_rtype => '1', is_itype => '0', is_jtype => '0',
           alu_op => "000", ext_type => "00", mem_read => '0', mem_write => '0',
           mem_size => "00", mem_signed => '0', branch_type => "00",
           jump_type => "00", reg_write_en => '0', reg_dst => "00",
           mem_to_reg => "00", sys_call => '1', lui_op => '0'),
    11 => (nombre => "addi          ", op => "001000", funct => "000000",
           illegal => '0', is_rtype => '0', is_itype => '1', is_jtype => '0',
           alu_op => "000", ext_type => "01", mem_read => '0', mem_write => '0',
           mem_size => "00", mem_signed => '0', branch_type => "00",
           jump_type => "00", reg_write_en => '1', reg_dst => "01",
           mem_to_reg => "00", sys_call => '0', lui_op => '0'),
    12 => (nombre => "addiu         ", op => "001001", funct => "000000",
           illegal => '0', is_rtype => '0', is_itype => '1', is_jtype => '0',
           alu_op => "000", ext_type => "01", mem_read => '0', mem_write => '0',
           mem_size => "00", mem_signed => '0', branch_type => "00",
           jump_type => "00", reg_write_en => '1', reg_dst => "01",
           mem_to_reg => "00", sys_call => '0', lui_op => '0'),
    13 => (nombre => "slti          ", op => "001010", funct => "000000",
           illegal => '0', is_rtype => '0', is_itype => '1', is_jtype => '0',
           alu_op => "100", ext_type => "01", mem_read => '0', mem_write => '0',
           mem_size => "00", mem_signed => '0', branch_type => "00",
           jump_type => "00", reg_write_en => '1', reg_dst => "01",
           mem_to_reg => "00", sys_call => '0', lui_op => '0'),
    14 => (nombre => "andi          ", op => "001100", funct => "000000",
           illegal => '0', is_rtype => '0', is_itype => '1', is_jtype => '0',
           alu_op => "010", ext_type => "00", mem_read => '0', mem_write => '0',
           mem_size => "00", mem_signed => '0', branch_type => "00",
           jump_type => "00", reg_write_en => '1', reg_dst => "01",
           mem_to_reg => "00", sys_call => '0', lui_op => '0'),
    15 => (nombre => "ori           ", op => "001101", funct => "000000",
           illegal => '0', is_rtype => '0', is_itype => '1', is_jtype => '0',
           alu_op => "011", ext_type => "00", mem_read => '0', mem_write => '0',
           mem_size => "00", mem_signed => '0', branch_type => "00",
           jump_type => "00", reg_write_en => '1', reg_dst => "01",
           mem_to_reg => "00", sys_call => '0', lui_op => '0'),
    16 => (nombre => "lui           ", op => "001111", funct => "000000",
           illegal => '0', is_rtype => '0', is_itype => '1', is_jtype => '0',
           alu_op => "111", ext_type => "00", mem_read => '0', mem_write => '0',
           mem_size => "00", mem_signed => '0', branch_type => "00",
           jump_type => "00", reg_write_en => '1', reg_dst => "01",
           mem_to_reg => "00", sys_call => '0', lui_op => '1'),
    17 => (nombre => "lb            ", op => "100000", funct => "000000",
           illegal => '0', is_rtype => '0', is_itype => '1', is_jtype => '0',
           alu_op => "000", ext_type => "01", mem_read => '1', mem_write => '0',
           mem_size => "01", mem_signed => '1', branch_type => "00",
           jump_type => "00", reg_write_en => '1', reg_dst => "01",
           mem_to_reg => "01", sys_call => '0', lui_op => '0'),
    18 => (nombre => "lw            ", op => "100011", funct => "000000",
           illegal => '0', is_rtype => '0', is_itype => '1', is_jtype => '0',
           alu_op => "000", ext_type => "01", mem_read => '1', mem_write => '0',
           mem_size => "00", mem_signed => '0', branch_type => "00",
           jump_type => "00", reg_write_en => '1', reg_dst => "01",
           mem_to_reg => "01", sys_call => '0', lui_op => '0'),
    19 => (nombre => "lbu           ", op => "100100", funct => "000000",
           illegal => '0', is_rtype => '0', is_itype => '1', is_jtype => '0',
           alu_op => "000", ext_type => "01", mem_read => '1', mem_write => '0',
           mem_size => "01", mem_signed => '0', branch_type => "00",
           jump_type => "00", reg_write_en => '1', reg_dst => "01",
           mem_to_reg => "01", sys_call => '0', lui_op => '0'),
    20 => (nombre => "sb            ", op => "101000", funct => "000000",
           illegal => '0', is_rtype => '0', is_itype => '1', is_jtype => '0',
           alu_op => "000", ext_type => "01", mem_read => '0', mem_write => '1',
           mem_size => "01", mem_signed => '0', branch_type => "00",
           jump_type => "00", reg_write_en => '0', reg_dst => "01",
           mem_to_reg => "00", sys_call => '0', lui_op => '0'),
    21 => (nombre => "sw            ", op => "101011", funct => "000000",
           illegal => '0', is_rtype => '0', is_itype => '1', is_jtype => '0',
           alu_op => "000", ext_type => "01", mem_read => '0', mem_write => '1',
           mem_size => "00", mem_signed => '0', branch_type => "00",
           jump_type => "00", reg_write_en => '0', reg_dst => "01",
           mem_to_reg => "00", sys_call => '0', lui_op => '0'),
    22 => (nombre => "beq           ", op => "000100", funct => "000000",
           illegal => '0', is_rtype => '0', is_itype => '1', is_jtype => '0',
           alu_op => "000", ext_type => "11", mem_read => '0', mem_write => '0',
           mem_size => "00", mem_signed => '0', branch_type => "01",
           jump_type => "00", reg_write_en => '0', reg_dst => "01",
           mem_to_reg => "00", sys_call => '0', lui_op => '0'),
    23 => (nombre => "bne           ", op => "000101", funct => "000000",
           illegal => '0', is_rtype => '0', is_itype => '1', is_jtype => '0',
           alu_op => "000", ext_type => "11", mem_read => '0', mem_write => '0',
           mem_size => "00", mem_signed => '0', branch_type => "10",
           jump_type => "00", reg_write_en => '0', reg_dst => "01",
           mem_to_reg => "00", sys_call => '0', lui_op => '0'),
    24 => (nombre => "j             ", op => "000010", funct => "000000",
           illegal => '0', is_rtype => '0', is_itype => '0', is_jtype => '1',
           alu_op => "000", ext_type => "00", mem_read => '0', mem_write => '0',
           mem_size => "00", mem_signed => '0', branch_type => "00",
           jump_type => "01", reg_write_en => '0', reg_dst => "00",
           mem_to_reg => "00", sys_call => '0', lui_op => '0'),
    25 => (nombre => "jal           ", op => "000011", funct => "000000",
           illegal => '0', is_rtype => '0', is_itype => '0', is_jtype => '1',
           alu_op => "000", ext_type => "00", mem_read => '0', mem_write => '0',
           mem_size => "00", mem_signed => '0', branch_type => "00",
           jump_type => "10", reg_write_en => '1', reg_dst => "10",
           mem_to_reg => "10", sys_call => '0', lui_op => '0'),
    -- Instrucciones ilegales
    26 => (nombre => "ilegal R      ", op => "000000", funct => "111111",
           illegal => '1', is_rtype => '1', is_itype => '0', is_jtype => '0',
           alu_op => "000", ext_type => "00", mem_read => '0', mem_write => '0',
           mem_size => "00", mem_signed => '0', branch_type => "00",
           jump_type => "00", reg_write_en => '0', reg_dst => "00",
           mem_to_reg => "00", sys_call => '0', lui_op => '0'),
    27 => (nombre => "ilegal I      ", op => "111111", funct => "000000",
           illegal => '1', is_rtype => '0', is_itype => '0', is_jtype => '0',
           alu_op => "000", ext_type => "00", mem_read => '0', mem_write => '0',
           mem_size => "00", mem_signed => '0', branch_type => "00",
           jump_type => "00", reg_write_en => '0', reg_dst => "00",
           mem_to_reg => "00", sys_call => '0', lui_op => '0'),
    28 => (nombre => "ilegal J      ", op => "000111", funct => "000000",
           illegal => '1', is_rtype => '0', is_itype => '0', is_jtype => '0',
           alu_op => "000", ext_type => "00", mem_read => '0', mem_write => '0',
           mem_size => "00", mem_signed => '0', branch_type => "00",
           jump_type => "00", reg_write_en => '0', reg_dst => "00",
           mem_to_reg => "00", sys_call => '0', lui_op => '0')
  );

  procedure check_caso(constant c : in caso_t) is
  begin
    wait for 1 ns;
    assert ILLEGAL = c.illegal
      report "Caso " & c.nombre & ": ILLEGAL incorrecto" severity error;
    assert IS_RTYPE = c.is_rtype
      report "Caso " & c.nombre & ": IS_RTYPE incorrecto" severity error;
    assert IS_ITYPE = c.is_itype
      report "Caso " & c.nombre & ": IS_ITYPE incorrecto" severity error;
    assert IS_JTYPE = c.is_jtype
      report "Caso " & c.nombre & ": IS_JTYPE incorrecto" severity error;
    assert ALU_OP = c.alu_op
      report "Caso " & c.nombre & ": ALU_OP incorrecto" severity error;
    assert EXT_TYPE = c.ext_type
      report "Caso " & c.nombre & ": EXT_TYPE incorrecto" severity error;
    assert MEM_READ = c.mem_read
      report "Caso " & c.nombre & ": MEM_READ incorrecto" severity error;
    assert MEM_WRITE = c.mem_write
      report "Caso " & c.nombre & ": MEM_WRITE incorrecto" severity error;
    assert MEM_SIZE = c.mem_size
      report "Caso " & c.nombre & ": MEM_SIZE incorrecto" severity error;
    assert MEM_SIGNED = c.mem_signed
      report "Caso " & c.nombre & ": MEM_SIGNED incorrecto" severity error;
    assert BRANCH_TYPE = c.branch_type
      report "Caso " & c.nombre & ": BRANCH_TYPE incorrecto" severity error;
    assert JUMP_TYPE = c.jump_type
      report "Caso " & c.nombre & ": JUMP_TYPE incorrecto" severity error;
    assert REG_WRITE_ENABLE = c.reg_write_en
      report "Caso " & c.nombre & ": REG_WRITE_ENABLE incorrecto" severity error;
    assert REG_DST = c.reg_dst
      report "Caso " & c.nombre & ": REG_DST incorrecto" severity error;
    assert MEM_TO_REG = c.mem_to_reg
      report "Caso " & c.nombre & ": MEM_TO_REG incorrecto" severity error;
    assert SYS_CALL = c.sys_call
      report "Caso " & c.nombre & ": SYS_CALL incorrecto" severity error;
    assert LUI_OP = c.lui_op
      report "Caso " & c.nombre & ": LUI_OP incorrecto" severity error;
  end procedure check_caso;

begin

  DUT: entity work.Instruction_Decoder
    port map (
      OP               => OP,
      FUNCT            => FUNCT,
      ILLEGAL          => ILLEGAL,
      IS_RTYPE         => IS_RTYPE,
      IS_ITYPE         => IS_ITYPE,
      IS_JTYPE         => IS_JTYPE,
      ALU_OP           => ALU_OP,
      EXT_TYPE         => EXT_TYPE,
      MEM_READ         => MEM_READ,
      MEM_WRITE        => MEM_WRITE,
      MEM_SIZE         => MEM_SIZE,
      MEM_SIGNED       => MEM_SIGNED,
      BRANCH_TYPE      => BRANCH_TYPE,
      JUMP_TYPE        => JUMP_TYPE,
      REG_WRITE_ENABLE => REG_WRITE_ENABLE,
      REG_DST          => REG_DST,
      MEM_TO_REG       => MEM_TO_REG,
      SYS_CALL         => SYS_CALL,
      LUI_OP           => LUI_OP
    );

  stimulus: process
  begin
    for i in CASOS'range loop
      OP <= CASOS(i).op;
      FUNCT <= CASOS(i).funct;
      check_caso(CASOS(i));
    end loop;

    assert false report "TB_OK: Instruction_Decoder funcional" severity note;
    wait;
  end process stimulus;

end architecture sim;

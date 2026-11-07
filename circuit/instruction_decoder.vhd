--------------------------------------------------------------------------------
-- Instruction_Decoder: decodifica OP (6 bits) y FUNCT (6 bits) de la instruccion
-- en señales de control para la Control_Unit de S-MIPS.
--
-- Contrato (R16/R19):
--   * Entidad y subcircuito: Instruction_Decoder
--   * Puertos std_logic / std_logic_vector, sin generics
--   * VHDL-2002, solo ieee.std_logic_1164 e ieee.numeric_std
--   * Sin wait, after, ficheros ni valores iniciales (R20)
--
-- Reglas de identificacion (R10/R11):
--   * Si OP = "000000", la instruccion se decide solo por FUNCT.
--   * Si OP /= "000000", la instruccion se decide solo por OP.
--   * Cualquier par (OP, FUNCT) que no esta en la tabla produce ILLEGAL = 1.
--   * 0x00000000 (OP=0, FUNCT=0) es sll $zero,$zero,0: legal, sin efecto (NOP).
--------------------------------------------------------------------------------

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

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
end entity Instruction_Decoder;

architecture rtl of Instruction_Decoder is

  -- Codificaciones de ALU_OP (3 bits)
  constant ALU_ADD  : std_logic_vector(2 downto 0) := "000";
  constant ALU_SUB  : std_logic_vector(2 downto 0) := "001";
  constant ALU_AND  : std_logic_vector(2 downto 0) := "010";
  constant ALU_OR   : std_logic_vector(2 downto 0) := "011";
  constant ALU_SLT  : std_logic_vector(2 downto 0) := "100";
  constant ALU_SLL  : std_logic_vector(2 downto 0) := "101";
  constant ALU_SRL  : std_logic_vector(2 downto 0) := "110";
  constant ALU_LUI  : std_logic_vector(2 downto 0) := "111";

  -- Codificaciones de EXT_TYPE (2 bits)
  constant EXT_ZERO : std_logic_vector(1 downto 0) := "00";
  constant EXT_SIGN : std_logic_vector(1 downto 0) := "01";
  constant EXT_SHAMT: std_logic_vector(1 downto 0) := "10";
  constant EXT_BRANCH: std_logic_vector(1 downto 0) := "11";

  -- Codificaciones de MEM_SIZE (2 bits)
  constant SIZE_WORD: std_logic_vector(1 downto 0) := "00";
  constant SIZE_BYTE: std_logic_vector(1 downto 0) := "01";

  -- Codificaciones de BRANCH_TYPE (2 bits)
  constant BRANCH_NONE : std_logic_vector(1 downto 0) := "00";
  constant BRANCH_BEQ  : std_logic_vector(1 downto 0) := "01";
  constant BRANCH_BNE  : std_logic_vector(1 downto 0) := "10";

  -- Codificaciones de JUMP_TYPE (2 bits)
  constant JUMP_NONE   : std_logic_vector(1 downto 0) := "00";
  constant JUMP_J      : std_logic_vector(1 downto 0) := "01";
  constant JUMP_JAL    : std_logic_vector(1 downto 0) := "10";
  constant JUMP_JR     : std_logic_vector(1 downto 0) := "11";

  -- Codificaciones de REG_DST (2 bits)
  constant DST_RD : std_logic_vector(1 downto 0) := "00";
  constant DST_RT : std_logic_vector(1 downto 0) := "01";
  constant DST_R31: std_logic_vector(1 downto 0) := "10";

  -- Codificaciones de MEM_TO_REG (2 bits)
  constant MEM_ALUOUT : std_logic_vector(1 downto 0) := "00";
  constant MEM_MDR    : std_logic_vector(1 downto 0) := "01";
  constant MEM_PC     : std_logic_vector(1 downto 0) := "10";

begin

  decodificar: process (OP, FUNCT)
  begin
    -- Valores por defecto para toda instrupcion legal/ilegal.
    ILLEGAL         <= '0';
    IS_RTYPE        <= '0';
    IS_ITYPE        <= '0';
    IS_JTYPE        <= '0';
    ALU_OP          <= ALU_ADD;
    EXT_TYPE        <= EXT_ZERO;
    MEM_READ        <= '0';
    MEM_WRITE       <= '0';
    MEM_SIZE        <= SIZE_WORD;
    MEM_SIGNED      <= '0';
    BRANCH_TYPE     <= BRANCH_NONE;
    JUMP_TYPE       <= JUMP_NONE;
    REG_WRITE_ENABLE<= '0';
    REG_DST         <= DST_RD;
    MEM_TO_REG      <= MEM_ALUOUT;
    SYS_CALL        <= '0';
    LUI_OP          <= '0';

    if OP = "000000" then
      -- Formato R: se decide solo por FUNCT.
      IS_RTYPE <= '1';
      case FUNCT is
        when "100000" =>            -- add (0x20)
          ALU_OP          <= ALU_ADD;
          EXT_TYPE        <= EXT_ZERO;
          REG_WRITE_ENABLE<= '1';
          REG_DST         <= DST_RD;
          MEM_TO_REG      <= MEM_ALUOUT;
        when "100001" =>            -- addu (0x21)
          ALU_OP          <= ALU_ADD;
          EXT_TYPE        <= EXT_ZERO;
          REG_WRITE_ENABLE<= '1';
          REG_DST         <= DST_RD;
          MEM_TO_REG      <= MEM_ALUOUT;
        when "100010" =>            -- sub (0x22)
          ALU_OP          <= ALU_SUB;
          EXT_TYPE        <= EXT_ZERO;
          REG_WRITE_ENABLE<= '1';
          REG_DST         <= DST_RD;
          MEM_TO_REG      <= MEM_ALUOUT;
        when "100100" =>            -- and (0x24)
          ALU_OP          <= ALU_AND;
          EXT_TYPE        <= EXT_ZERO;
          REG_WRITE_ENABLE<= '1';
          REG_DST         <= DST_RD;
          MEM_TO_REG      <= MEM_ALUOUT;
        when "100101" =>            -- or (0x25)
          ALU_OP          <= ALU_OR;
          EXT_TYPE        <= EXT_ZERO;
          REG_WRITE_ENABLE<= '1';
          REG_DST         <= DST_RD;
          MEM_TO_REG      <= MEM_ALUOUT;
        when "101010" =>            -- slt (0x2a)
          ALU_OP          <= ALU_SLT;
          EXT_TYPE        <= EXT_ZERO;
          REG_WRITE_ENABLE<= '1';
          REG_DST         <= DST_RD;
          MEM_TO_REG      <= MEM_ALUOUT;
        when "000000" =>            -- sll (0x00) -> NOP si todo cero
          ALU_OP          <= ALU_SLL;
          EXT_TYPE        <= EXT_SHAMT;
          REG_WRITE_ENABLE<= '1';
          REG_DST         <= DST_RD;
          MEM_TO_REG      <= MEM_ALUOUT;
        when "000010" =>            -- srl (0x02)
          ALU_OP          <= ALU_SRL;
          EXT_TYPE        <= EXT_SHAMT;
          REG_WRITE_ENABLE<= '1';
          REG_DST         <= DST_RD;
          MEM_TO_REG      <= MEM_ALUOUT;
        when "001000" =>            -- jr (0x08)
          ALU_OP          <= ALU_ADD;
          EXT_TYPE        <= EXT_ZERO;
          REG_WRITE_ENABLE<= '0';
          REG_DST         <= DST_RD;
          MEM_TO_REG      <= MEM_ALUOUT;
          JUMP_TYPE       <= JUMP_JR;
        when "001100" =>            -- syscall (0x0c)
          ALU_OP          <= ALU_ADD;
          EXT_TYPE        <= EXT_ZERO;
          REG_WRITE_ENABLE<= '0';
          REG_DST         <= DST_RD;
          MEM_TO_REG      <= MEM_ALUOUT;
          SYS_CALL        <= '1';
        when others =>
          ILLEGAL <= '1';
      end case;
    else
      -- Formato I o J: se decide solo por OP.
      case OP is
        when "001000" =>            -- addi (0x08)
          IS_ITYPE        <= '1';
          ALU_OP          <= ALU_ADD;
          EXT_TYPE        <= EXT_SIGN;
          REG_WRITE_ENABLE<= '1';
          REG_DST         <= DST_RT;
          MEM_TO_REG      <= MEM_ALUOUT;
        when "001001" =>            -- addiu (0x09)
          IS_ITYPE        <= '1';
          ALU_OP          <= ALU_ADD;
          EXT_TYPE        <= EXT_SIGN;
          REG_WRITE_ENABLE<= '1';
          REG_DST         <= DST_RT;
          MEM_TO_REG      <= MEM_ALUOUT;
        when "001010" =>            -- slti (0x0a)
          IS_ITYPE        <= '1';
          ALU_OP          <= ALU_SLT;
          EXT_TYPE        <= EXT_SIGN;
          REG_WRITE_ENABLE<= '1';
          REG_DST         <= DST_RT;
          MEM_TO_REG      <= MEM_ALUOUT;
        when "001100" =>            -- andi (0x0c)
          IS_ITYPE        <= '1';
          ALU_OP          <= ALU_AND;
          EXT_TYPE        <= EXT_ZERO;
          REG_WRITE_ENABLE<= '1';
          REG_DST         <= DST_RT;
          MEM_TO_REG      <= MEM_ALUOUT;
        when "001101" =>            -- ori (0x0d)
          IS_ITYPE        <= '1';
          ALU_OP          <= ALU_OR;
          EXT_TYPE        <= EXT_ZERO;
          REG_WRITE_ENABLE<= '1';
          REG_DST         <= DST_RT;
          MEM_TO_REG      <= MEM_ALUOUT;
        when "001111" =>            -- lui (0x0f)
          IS_ITYPE        <= '1';
          ALU_OP          <= ALU_LUI;
          EXT_TYPE        <= EXT_ZERO;
          REG_WRITE_ENABLE<= '1';
          REG_DST         <= DST_RT;
          MEM_TO_REG      <= MEM_ALUOUT;
          LUI_OP          <= '1';
        when "100000" =>            -- lb (0x20)
          IS_ITYPE        <= '1';
          ALU_OP          <= ALU_ADD;
          EXT_TYPE        <= EXT_SIGN;
          MEM_READ        <= '1';
          MEM_SIZE        <= SIZE_BYTE;
          MEM_SIGNED      <= '1';
          REG_WRITE_ENABLE<= '1';
          REG_DST         <= DST_RT;
          MEM_TO_REG      <= MEM_MDR;
        when "100011" =>            -- lw (0x23)
          IS_ITYPE        <= '1';
          ALU_OP          <= ALU_ADD;
          EXT_TYPE        <= EXT_SIGN;
          MEM_READ        <= '1';
          MEM_SIZE        <= SIZE_WORD;
          MEM_SIGNED      <= '0';
          REG_WRITE_ENABLE<= '1';
          REG_DST         <= DST_RT;
          MEM_TO_REG      <= MEM_MDR;
        when "100100" =>            -- lbu (0x24)
          IS_ITYPE        <= '1';
          ALU_OP          <= ALU_ADD;
          EXT_TYPE        <= EXT_SIGN;
          MEM_READ        <= '1';
          MEM_SIZE        <= SIZE_BYTE;
          MEM_SIGNED      <= '0';
          REG_WRITE_ENABLE<= '1';
          REG_DST         <= DST_RT;
          MEM_TO_REG      <= MEM_MDR;
        when "101000" =>            -- sb (0x28)
          IS_ITYPE        <= '1';
          ALU_OP          <= ALU_ADD;
          EXT_TYPE        <= EXT_SIGN;
          MEM_WRITE       <= '1';
          MEM_SIZE        <= SIZE_BYTE;
          MEM_SIGNED      <= '0';
          REG_WRITE_ENABLE<= '0';
          REG_DST         <= DST_RT;
          MEM_TO_REG      <= MEM_ALUOUT;
        when "101011" =>            -- sw (0x2b)
          IS_ITYPE        <= '1';
          ALU_OP          <= ALU_ADD;
          EXT_TYPE        <= EXT_SIGN;
          MEM_WRITE       <= '1';
          MEM_SIZE        <= SIZE_WORD;
          MEM_SIGNED      <= '0';
          REG_WRITE_ENABLE<= '0';
          REG_DST         <= DST_RT;
          MEM_TO_REG      <= MEM_ALUOUT;
        when "000100" =>            -- beq (0x04)
          IS_ITYPE        <= '1';
          ALU_OP          <= ALU_ADD;
          EXT_TYPE        <= EXT_BRANCH;
          REG_WRITE_ENABLE<= '0';
          REG_DST         <= DST_RT;
          MEM_TO_REG      <= MEM_ALUOUT;
          BRANCH_TYPE     <= BRANCH_BEQ;
        when "000101" =>            -- bne (0x05)
          IS_ITYPE        <= '1';
          ALU_OP          <= ALU_ADD;
          EXT_TYPE        <= EXT_BRANCH;
          REG_WRITE_ENABLE<= '0';
          REG_DST         <= DST_RT;
          MEM_TO_REG      <= MEM_ALUOUT;
          BRANCH_TYPE     <= BRANCH_BNE;
        when "000010" =>            -- j (0x02)
          IS_JTYPE        <= '1';
          ALU_OP          <= ALU_ADD;
          EXT_TYPE        <= EXT_ZERO;
          REG_WRITE_ENABLE<= '0';
          REG_DST         <= DST_RD;
          MEM_TO_REG      <= MEM_ALUOUT;
          JUMP_TYPE       <= JUMP_J;
        when "000011" =>            -- jal (0x03)
          IS_JTYPE        <= '1';
          ALU_OP          <= ALU_ADD;
          EXT_TYPE        <= EXT_ZERO;
          REG_WRITE_ENABLE<= '1';
          REG_DST         <= DST_R31;
          MEM_TO_REG      <= MEM_PC;
          JUMP_TYPE       <= JUMP_JAL;
        when others =>
          ILLEGAL <= '1';
      end case;
    end if;
  end process decodificar;

end architecture rtl;

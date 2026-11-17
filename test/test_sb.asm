# Diagnostico SB: escribe en los cuatro carriles y modifica un solo byte.
.data
buf: .space 8
.text
main:
    la   $s0, buf
    addi $t6, $zero, 0xaa
    sb   $t6, 0($s0)
    addi $t6, $zero, 0xbb
    sb   $t6, 1($s0)
    addi $t6, $zero, 0xcc
    sb   $t6, 2($s0)
    addi $t6, $zero, 0xdd
    sb   $t6, 3($s0)
    lw   $a0, 0($s0)       # esperado: ddccbbaa
    jal  imprimir_hex
    jal  nueva_linea

    lui  $t6, 0x1234
    ori  $t6, $t6, 0x5678
    sw   $t6, 4($s0)
    addi $t6, $zero, -1
    sb   $t6, 5($s0)
    lw   $a0, 4($s0)       # esperado: 12ff5678
    jal  imprimir_hex
    jal  nueva_linea

    addi $v0, $zero, 10
    syscall

# Imprime $a0 como 8 digitos hexadecimales y un espacio.
imprimir_hex:
    add  $t0, $a0, $zero
    addi $t1, $zero, 8
ih_bucle:
    srl  $t2, $t0, 28
    slti $t3, $t2, 10
    beq  $t3, $zero, ih_letra
    addi $a0, $t2, 48
    j    ih_imprime
ih_letra:
    addi $a0, $t2, 87
ih_imprime:
    addi $v0, $zero, 11
    syscall
    sll  $t0, $t0, 4
    addi $t1, $t1, -1
    bne  $t1, $zero, ih_bucle
    addi $a0, $zero, 32
    addi $v0, $zero, 11
    syscall
    jr   $ra

nueva_linea:
    addi $a0, $zero, 10
    addi $v0, $zero, 11
    syscall
    jr   $ra

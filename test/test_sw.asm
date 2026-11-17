# Diagnostico SW/LW: palabras completas y direcciones alineadas.
.data
buf: .space 12
.text
main:
    la   $s0, buf
    lui  $t0, 0x8070
    ori  $t0, $t0, 0xf00d
    sw   $t0, 0($s0)
    lui  $t1, 0x1234
    ori  $t1, $t1, 0x5678
    sw   $t1, 4($s0)
    addi $t2, $zero, -1
    sw   $t2, 8($s0)

    lw   $a0, 0($s0)
    jal  imprimir_hex
    lw   $a0, 4($s0)
    jal  imprimir_hex
    lw   $a0, 8($s0)
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

# Diagnostico de inmediatos: ADDI sign-extend; ANDI/ORI zero-extend; SLTI.
.text
main:
    addi $t0, $zero, -1
    add  $a0, $t0, $zero  # esperado: ffffffff
    jal  imprimir_hex

    andi $t1, $t0, 0xff09
    add  $a0, $t1, $zero  # esperado: 0000ff09
    jal  imprimir_hex

    ori  $t2, $zero, 0x8000
    add  $a0, $t2, $zero  # esperado: 00008000
    jal  imprimir_hex

    slti $t3, $t0, 0
    add  $a0, $t3, $zero  # esperado: 00000001
    jal  imprimir_hex

    slti $t4, $zero, -1
    add  $a0, $t4, $zero  # esperado: 00000000
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

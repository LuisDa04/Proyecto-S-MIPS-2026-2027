# Diagnostico de multiplicacion por sumas repetidas.
# Calcula 12*10=120 (0x78) y 13*12=156 (0x9c).
.text
main:
    addi $t0, $zero, 12
    addi $t1, $zero, 10
    add  $t2, $zero, $zero
mult1_loop:
    add  $t2, $t2, $t0
    addi $t1, $t1, -1
    bne  $t1, $zero, mult1_loop
    add  $a0, $t2, $zero
    jal  imprimir_hex

    addi $t0, $zero, 13
    addi $t1, $zero, 12
    add  $t2, $zero, $zero
mult2_loop:
    add  $t2, $t2, $t0
    addi $t1, $t1, -1
    bne  $t1, $zero, mult2_loop
    add  $a0, $t2, $zero
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

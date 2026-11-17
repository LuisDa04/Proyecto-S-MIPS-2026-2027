.text
main:
    # Preparar $s1 = -7 = 0xfffffff9
    addi $s1, $zero, -7

    # PRUEBA 1: comprobar que $s1 tiene el valor correcto
    add  $a0, $s1, $zero
    jal  imprimir_hex

    # PRUEBA 2: comprobar ANDI
    andi $a0, $s1, 0xff0f
    jal  imprimir_hex

    # PRUEBA 3: comprobar otro ANDI
    andi $a0, $s1, 0x000f
    jal  imprimir_hex

    # PRUEBA 4: comprobar ORI como control
    ori  $a0, $zero, 0x8000
    jal  imprimir_hex

    jal nueva_linea

    # Terminar
    addi $v0, $zero, 10
    syscall


# Imprime $a0 en hexadecimal
imprimir_hex:
    add  $t0, $a0, $zero
    addi $t1, $zero, 8

ih_bucle:
    srl  $t2, $t0, 28
    slti $t3, $t2, 10
    beq  $t3, $zero, ih_letra
    addi $a0, $t2, 48
    j ih_imprime

ih_letra:
    addi $a0, $t2, 87

ih_imprime:
    addi $v0, $zero, 11
    syscall
    sll $t0, $t0, 4
    addi $t1, $t1, -1
    bne $t1, $zero, ih_bucle

    addi $a0, $zero, 32
    addi $v0, $zero, 11
    syscall
    jr $ra

nueva_linea:
    addi $a0, $zero, 10
    addi $v0, $zero, 11
    syscall
    jr $ra
; matrix_ops.asm — Matrix-like operations with MUL/ADD/STORE patterns
; Simulates element-wise matrix operations with many fusible sequences
;
; Expected to discover: MUL_ADD, MUL_ADD_STORE, LOAD_MUL, etc.

; Initialize values
    LOAD R1, 3         ; matrix value a
    LOAD R2, 5         ; matrix value b
    LOAD R3, 7         ; matrix value c
    LOAD R4, 2         ; scalar multiplier
    LOAD R5, 1         ; scalar addend
    LOAD R10, 500      ; loop counter
    LOAD R0, 0         ; accumulator

loop:
    ; Operation 1: R0 = R1 * R4 + R5
    MOV R0, R1
    MUL R0, R4
    ADD R0, R5
    STORE R0, 200

    ; Operation 2: R0 = R2 * R4 + R5
    MOV R0, R2
    MUL R0, R4
    ADD R0, R5
    STORE R0, 201

    ; Operation 3: R0 = R3 * R4 + R5
    MOV R0, R3
    MUL R0, R4
    ADD R0, R5
    STORE R0, 202

    ; Operation 4: R0 = (R1 + R2) * R4
    MOV R0, R1
    ADD R0, R2
    MUL R0, R4
    STORE R0, 203

    ; Operation 5: R0 = (R2 + R3) * R4
    MOV R0, R2
    ADD R0, R3
    MUL R0, R4
    STORE R0, 204

    ; Decrement and loop
    DEC R10
    JNZ R10, loop

    HALT

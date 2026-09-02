; stress_test.asm — Maximally fusible patterns for stress testing the evolution engine
; Contains many repeated sequences across a large loop count.
;
; Expected to discover multiple fusion opportunities across different patterns.

; Initialize
    LOAD R1, 5
    LOAD R2, 10
    LOAD R3, 15
    LOAD R4, 20
    LOAD R5, 3
    LOAD R6, 7
    LOAD R15, 2000     ; loop counter

loop:
    ; Pattern A: LOAD ADD ADD STORE (×3)
    LOAD R0, 0
    ADD R0, R1
    ADD R0, R2
    STORE R0, 100

    LOAD R0, 0
    ADD R0, R3
    ADD R0, R4
    STORE R0, 101

    LOAD R0, 0
    ADD R0, R5
    ADD R0, R6
    STORE R0, 102

    ; Pattern B: MOV MUL ADD STORE (×2)
    MOV R0, R1
    MUL R0, R5
    ADD R0, R2
    STORE R0, 103

    MOV R0, R3
    MUL R0, R5
    ADD R0, R4
    STORE R0, 104

    ; Pattern C: SUB MUL STORE (×2)
    MOV R0, R2
    SUB R0, R1
    MUL R0, R5
    STORE R0, 105

    MOV R0, R4
    SUB R0, R3
    MUL R0, R5
    STORE R0, 106

    ; Pattern D: INC INC INC (repeated increments)
    INC R1
    INC R2
    INC R3

    ; Decrement counter and loop
    DEC R15
    JNZ R15, loop

    HALT

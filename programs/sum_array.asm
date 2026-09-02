; sum_array.asm — Sums an array of values using repeated LOAD/ADD/STORE patterns
; This program is designed to have highly fusible instruction sequences.
;
; Simulates: result = sum of 10 values, repeated 1000 times
; Expected to discover: LOAD_ADD_STORE, ADD_ADD, or similar fusions

; Initialize the "array" values in registers
    LOAD R1, 10        ; array[0] = 10
    LOAD R2, 20        ; array[1] = 20
    LOAD R3, 30        ; array[2] = 30
    LOAD R4, 40        ; array[3] = 40
    LOAD R5, 50        ; array[4] = 50
    LOAD R6, 60        ; array[5] = 60
    LOAD R7, 70        ; array[6] = 70
    LOAD R8, 80        ; array[7] = 80
    LOAD R9, 1000      ; loop counter
    LOAD R0, 0         ; accumulator (result)

loop:
    ; Sum all array values into R0
    ; This creates a repeated pattern: ADD ADD ADD ADD ADD ADD ADD ADD
    LOAD R0, 0
    ADD R0, R1
    ADD R0, R2
    ADD R0, R3
    ADD R0, R4
    ADD R0, R5
    ADD R0, R6
    ADD R0, R7
    ADD R0, R8
    STORE R0, 100      ; store result to memory[100]

    ; Decrement counter and loop
    DEC R9
    JNZ R9, loop

    HALT

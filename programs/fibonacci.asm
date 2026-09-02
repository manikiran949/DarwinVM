; fibonacci.asm — Computes Fibonacci numbers with repeated ADD patterns
; The inner loop has a very regular ADD/MOV pattern that should be fusible.
;
; Expected to discover: MOV_ADD or ADD_MOV patterns

; R0 = fib(n-2), R1 = fib(n-1), R2 = fib(n), R3 = counter, R4 = target
    LOAD R0, 0         ; fib(0) = 0
    LOAD R1, 1         ; fib(1) = 1
    LOAD R3, 2000      ; compute 2000 fibonacci iterations
    LOAD R2, 0         ; temp for fib(n)

loop:
    ; fib(n) = fib(n-1) + fib(n-2)
    MOV R2, R0
    ADD R2, R1

    ; Shift: fib(n-2) = fib(n-1), fib(n-1) = fib(n)
    MOV R0, R1
    MOV R1, R2

    ; Store current fibonacci number
    STORE R2, 300

    ; Decrement counter
    DEC R3
    JNZ R3, loop

    ; Store final result
    STORE R2, 301
    HALT

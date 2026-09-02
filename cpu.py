"""
Self-Evolving CPU — Core CPU Emulator

A register-based CPU with 16 general-purpose registers, configurable memory,
and the ability to dynamically register new (evolved) instructions at runtime.
"""

from dataclasses import dataclass, field
from typing import Callable, Optional
import time


@dataclass
class Instruction:
    """Represents a single CPU instruction."""
    opcode: str
    operands: list
    line_number: int = 0

    def __repr__(self):
        ops = ", ".join(str(o) for o in self.operands)
        return f"{self.opcode} {ops}" if ops else self.opcode


@dataclass
class InstructionMeta:
    """Metadata for a registered instruction (base or evolved)."""
    name: str
    handler: Callable
    is_evolved: bool = False
    constituent_opcodes: list = field(default_factory=list)
    creation_time: float = 0.0
    execution_count: int = 0
    description: str = ""


class CPUHaltException(Exception):
    """Raised when the CPU executes a HALT instruction."""
    pass


class CPUError(Exception):
    """General CPU execution error."""
    pass


class CPU:
    """
    A register-based CPU emulator.

    Features:
    - 16 general-purpose registers (R0–R15)
    - Program counter (PC) and flags register
    - Array-based memory (configurable size)
    - Dynamic instruction registration for evolved opcodes
    - Per-instruction execution counting
    """

    NUM_REGISTERS = 16
    DEFAULT_MEMORY_SIZE = 4096

    def __init__(self, memory_size: int = DEFAULT_MEMORY_SIZE):
        # Registers: R0–R15
        self.registers = [0] * self.NUM_REGISTERS
        # Program counter
        self.pc = 0
        # Flags: zero, negative, overflow
        self.flags = {"zero": False, "negative": False, "overflow": False}
        # Memory
        self.memory_size = memory_size
        self.memory = [0] * memory_size
        # Instruction dispatch table
        self.instruction_table: dict[str, InstructionMeta] = {}
        # Program loaded into CPU
        self.program: list[Instruction] = []
        # Label map: label_name -> instruction index
        self.labels: dict[str, int] = {}
        # Execution stats
        self.total_instructions_executed = 0
        self.execution_time = 0.0
        # Profiler callback (set by the profiler)
        self.profiler_callback: Optional[Callable] = None
        # Halted flag
        self.halted = False

        # Register all base instructions
        self._register_base_instructions()

    def _register_base_instructions(self):
        """Register the base instruction set."""
        base_instructions = [
            ("LOAD", self._exec_load, "Load immediate value or memory into register"),
            ("STORE", self._exec_store, "Store register value to memory"),
            ("ADD", self._exec_add, "Add two registers"),
            ("SUB", self._exec_sub, "Subtract two registers"),
            ("MUL", self._exec_mul, "Multiply two registers"),
            ("DIV", self._exec_div, "Integer divide two registers"),
            ("JUMP", self._exec_jump, "Unconditional jump to label/address"),
            ("JZ", self._exec_jz, "Jump if register is zero"),
            ("JNZ", self._exec_jnz, "Jump if register is not zero"),
            ("HALT", self._exec_halt, "Stop execution"),
            ("NOP", self._exec_nop, "No operation"),
            ("MOV", self._exec_mov, "Copy value from one register to another"),
            ("CMP", self._exec_cmp, "Compare two registers and set flags"),
            ("INC", self._exec_inc, "Increment register by 1"),
            ("DEC", self._exec_dec, "Decrement register by 1"),
        ]
        for name, handler, desc in base_instructions:
            self.register_instruction(name, handler, description=desc)

    def register_instruction(self, name: str, handler: Callable,
                             is_evolved: bool = False,
                             constituent_opcodes: list = None,
                             description: str = ""):
        """Register an instruction (base or evolved) in the dispatch table."""
        self.instruction_table[name] = InstructionMeta(
            name=name,
            handler=handler,
            is_evolved=is_evolved,
            constituent_opcodes=constituent_opcodes or [],
            creation_time=time.time(),
            execution_count=0,
            description=description,
        )

    def unregister_instruction(self, name: str):
        """Remove an evolved instruction from the dispatch table."""
        meta = self.instruction_table.get(name)
        if meta and meta.is_evolved:
            del self.instruction_table[name]

    def load_program(self, program: list[Instruction], labels: dict[str, int] = None):
        """Load a program into the CPU."""
        self.program = program
        self.labels = labels or {}
        self.reset()

    def reset(self):
        """Reset CPU state (registers, PC, flags, memory) but keep the program and instruction table."""
        self.registers = [0] * self.NUM_REGISTERS
        self.pc = 0
        self.flags = {"zero": False, "negative": False, "overflow": False}
        self.memory = [0] * self.memory_size
        self.total_instructions_executed = 0
        self.execution_time = 0.0
        self.halted = False
        self._pc_modified = False
        # Reset per-instruction execution counts
        for meta in self.instruction_table.values():
            meta.execution_count = 0

    def execute(self, max_instructions: int = 10_000_000) -> dict:
        """
        Execute the loaded program until HALT or max_instructions reached.

        Returns a dict with execution statistics.
        """
        self.halted = False
        start_time = time.perf_counter()

        try:
            while self.pc < len(self.program) and self.total_instructions_executed < max_instructions:
                if self.halted:
                    break
                self._step()
        except CPUHaltException:
            pass

        end_time = time.perf_counter()
        self.execution_time = end_time - start_time

        return {
            "total_instructions": self.total_instructions_executed,
            "execution_time": self.execution_time,
            "instructions_per_second": (
                self.total_instructions_executed / self.execution_time
                if self.execution_time > 0 else 0
            ),
            "registers": list(self.registers),
            "flags": dict(self.flags),
            "memory": list(self.memory),
        }

    def _step(self):
        """Fetch, decode, and execute one instruction."""
        if self.pc >= len(self.program):
            self.halted = True
            return

        instr = self.program[self.pc]
        meta = self.instruction_table.get(instr.opcode)

        if meta is None:
            raise CPUError(
                f"Unknown instruction '{instr.opcode}' at line {instr.line_number} (PC={self.pc})"
            )

        # Notify profiler before execution
        if self.profiler_callback:
            self.profiler_callback(instr)

        # Execute
        meta.handler(instr.operands)
        meta.execution_count += 1
        self.total_instructions_executed += 1

        # PC is advanced by the handler for jumps; otherwise auto-increment
        # We check if the handler already changed PC via a flag
        if not getattr(self, '_pc_modified', False):
            self.pc += 1
        self._pc_modified = False

    def _update_flags(self, value: int):
        """Update CPU flags based on the result value."""
        self.flags["zero"] = (value == 0)
        self.flags["negative"] = (value < 0)

    # ─── Operand Helpers ──────────────────────────────────────────────

    def _resolve_register(self, operand) -> int:
        """Resolve a register name (e.g., 'R0') to its index."""
        if isinstance(operand, str) and operand.upper().startswith("R"):
            try:
                idx = int(operand[1:])
                if 0 <= idx < self.NUM_REGISTERS:
                    return idx
            except ValueError:
                pass
        raise CPUError(f"Invalid register: {operand}")

    def _resolve_value(self, operand) -> int:
        """Resolve an operand to a value — either a register's content or an immediate."""
        if isinstance(operand, int):
            return operand
        if isinstance(operand, str):
            if operand.upper().startswith("R"):
                idx = self._resolve_register(operand)
                return self.registers[idx]
            try:
                return int(operand)
            except ValueError:
                pass
        raise CPUError(f"Cannot resolve value: {operand}")

    def _resolve_address(self, operand) -> int:
        """Resolve an operand to a memory address or jump target."""
        if isinstance(operand, int):
            return operand
        if isinstance(operand, str):
            # Check labels first
            if operand in self.labels:
                return self.labels[operand]
            try:
                return int(operand)
            except ValueError:
                pass
        raise CPUError(f"Cannot resolve address: {operand}")

    # ─── Base Instruction Implementations ─────────────────────────────

    def _exec_load(self, operands: list):
        """LOAD Rd, value  — Load immediate value into Rd.
           LOAD Rd, [addr] — Load from memory address into Rd."""
        if len(operands) < 2:
            raise CPUError("LOAD requires 2 operands: LOAD Rd, value")
        rd = self._resolve_register(operands[0])
        # Check for memory addressing mode [addr]
        op1 = operands[1]
        if isinstance(op1, str) and op1.startswith("[") and op1.endswith("]"):
            addr = self._resolve_value(op1[1:-1])
            if 0 <= addr < self.memory_size:
                self.registers[rd] = self.memory[addr]
            else:
                raise CPUError(f"Memory address out of bounds: {addr}")
        else:
            self.registers[rd] = self._resolve_value(op1)
        self._update_flags(self.registers[rd])

    def _exec_store(self, operands: list):
        """STORE Rs, addr — Store register value to memory address."""
        if len(operands) < 2:
            raise CPUError("STORE requires 2 operands: STORE Rs, addr")
        rs = self._resolve_register(operands[0])
        addr = self._resolve_value(operands[1])
        if 0 <= addr < self.memory_size:
            self.memory[addr] = self.registers[rs]
        else:
            raise CPUError(f"Memory address out of bounds: {addr}")

    def _exec_add(self, operands: list):
        """ADD Rd, Rs — Rd = Rd + Rs."""
        if len(operands) < 2:
            raise CPUError("ADD requires 2 operands: ADD Rd, Rs")
        rd = self._resolve_register(operands[0])
        val = self._resolve_value(operands[1])
        self.registers[rd] += val
        self._update_flags(self.registers[rd])

    def _exec_sub(self, operands: list):
        """SUB Rd, Rs — Rd = Rd - Rs."""
        if len(operands) < 2:
            raise CPUError("SUB requires 2 operands: SUB Rd, Rs")
        rd = self._resolve_register(operands[0])
        val = self._resolve_value(operands[1])
        self.registers[rd] -= val
        self._update_flags(self.registers[rd])

    def _exec_mul(self, operands: list):
        """MUL Rd, Rs — Rd = Rd * Rs."""
        if len(operands) < 2:
            raise CPUError("MUL requires 2 operands: MUL Rd, Rs")
        rd = self._resolve_register(operands[0])
        val = self._resolve_value(operands[1])
        self.registers[rd] *= val
        self._update_flags(self.registers[rd])

    def _exec_div(self, operands: list):
        """DIV Rd, Rs — Rd = Rd // Rs."""
        if len(operands) < 2:
            raise CPUError("DIV requires 2 operands: DIV Rd, Rs")
        rd = self._resolve_register(operands[0])
        val = self._resolve_value(operands[1])
        if val == 0:
            raise CPUError("Division by zero")
        self.registers[rd] //= val
        self._update_flags(self.registers[rd])

    def _exec_jump(self, operands: list):
        """JUMP label — Unconditional jump."""
        if len(operands) < 1:
            raise CPUError("JUMP requires 1 operand: JUMP target")
        target = self._resolve_address(operands[0])
        self.pc = target
        self._pc_modified = True

    def _exec_jz(self, operands: list):
        """JZ Rd, label — Jump if Rd is zero."""
        if len(operands) < 2:
            raise CPUError("JZ requires 2 operands: JZ Rd, target")
        rd = self._resolve_register(operands[0])
        if self.registers[rd] == 0:
            target = self._resolve_address(operands[1])
            self.pc = target
            self._pc_modified = True

    def _exec_jnz(self, operands: list):
        """JNZ Rd, label — Jump if Rd is not zero."""
        if len(operands) < 2:
            raise CPUError("JNZ requires 2 operands: JNZ Rd, target")
        rd = self._resolve_register(operands[0])
        if self.registers[rd] != 0:
            target = self._resolve_address(operands[1])
            self.pc = target
            self._pc_modified = True

    def _exec_halt(self, operands: list):
        """HALT — Stop execution."""
        self.halted = True
        raise CPUHaltException()

    def _exec_nop(self, operands: list):
        """NOP — No operation."""
        pass

    def _exec_mov(self, operands: list):
        """MOV Rd, Rs — Copy value from Rs to Rd."""
        if len(operands) < 2:
            raise CPUError("MOV requires 2 operands: MOV Rd, Rs")
        rd = self._resolve_register(operands[0])
        val = self._resolve_value(operands[1])
        self.registers[rd] = val
        self._update_flags(self.registers[rd])

    def _exec_cmp(self, operands: list):
        """CMP Ra, Rb — Compare Ra and Rb, set flags."""
        if len(operands) < 2:
            raise CPUError("CMP requires 2 operands: CMP Ra, Rb")
        val_a = self._resolve_value(operands[0])
        val_b = self._resolve_value(operands[1])
        result = val_a - val_b
        self._update_flags(result)

    def _exec_inc(self, operands: list):
        """INC Rd — Increment Rd by 1."""
        if len(operands) < 1:
            raise CPUError("INC requires 1 operand: INC Rd")
        rd = self._resolve_register(operands[0])
        self.registers[rd] += 1
        self._update_flags(self.registers[rd])

    def _exec_dec(self, operands: list):
        """DEC Rd — Decrement Rd by 1."""
        if len(operands) < 1:
            raise CPUError("DEC requires 1 operand: DEC Rd")
        rd = self._resolve_register(operands[0])
        self.registers[rd] -= 1
        self._update_flags(self.registers[rd])

    # ─── Introspection ────────────────────────────────────────────────

    def get_instruction_stats(self) -> list[dict]:
        """Get execution statistics for all instructions."""
        stats = []
        for name, meta in self.instruction_table.items():
            stats.append({
                "name": name,
                "is_evolved": meta.is_evolved,
                "execution_count": meta.execution_count,
                "constituent_opcodes": meta.constituent_opcodes,
                "description": meta.description,
            })
        return sorted(stats, key=lambda s: s["execution_count"], reverse=True)

    def get_evolved_instructions(self) -> list[InstructionMeta]:
        """Get all currently registered evolved instructions."""
        return [
            meta for meta in self.instruction_table.values()
            if meta.is_evolved
        ]

    def get_state_snapshot(self) -> dict:
        """Get a snapshot of the full CPU state."""
        return {
            "registers": list(self.registers),
            "pc": self.pc,
            "flags": dict(self.flags),
            "memory_used": sum(1 for v in self.memory if v != 0),
            "total_instructions": len(self.instruction_table),
            "evolved_instructions": len(self.get_evolved_instructions()),
            "instructions_executed": self.total_instructions_executed,
        }

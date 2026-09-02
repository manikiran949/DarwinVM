"""
Tests for the CPU emulator core.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from cpu import CPU, Instruction, CPUHaltException, CPUError


class TestCPURegisters:
    """Test register operations."""

    def test_initial_registers_are_zero(self):
        cpu = CPU()
        assert all(r == 0 for r in cpu.registers)

    def test_load_immediate(self):
        cpu = CPU()
        program = [
            Instruction("LOAD", ["R0", 42]),
            Instruction("HALT", []),
        ]
        cpu.load_program(program)
        cpu.execute()
        assert cpu.registers[0] == 42

    def test_load_multiple_registers(self):
        cpu = CPU()
        program = [
            Instruction("LOAD", ["R0", 10]),
            Instruction("LOAD", ["R1", 20]),
            Instruction("LOAD", ["R15", 999]),
            Instruction("HALT", []),
        ]
        cpu.load_program(program)
        cpu.execute()
        assert cpu.registers[0] == 10
        assert cpu.registers[1] == 20
        assert cpu.registers[15] == 999

    def test_mov(self):
        cpu = CPU()
        program = [
            Instruction("LOAD", ["R0", 42]),
            Instruction("MOV", ["R1", "R0"]),
            Instruction("HALT", []),
        ]
        cpu.load_program(program)
        cpu.execute()
        assert cpu.registers[1] == 42


class TestCPUArithmetic:
    """Test arithmetic instructions."""

    def test_add(self):
        cpu = CPU()
        program = [
            Instruction("LOAD", ["R0", 10]),
            Instruction("LOAD", ["R1", 20]),
            Instruction("ADD", ["R0", "R1"]),
            Instruction("HALT", []),
        ]
        cpu.load_program(program)
        cpu.execute()
        assert cpu.registers[0] == 30

    def test_sub(self):
        cpu = CPU()
        program = [
            Instruction("LOAD", ["R0", 50]),
            Instruction("LOAD", ["R1", 20]),
            Instruction("SUB", ["R0", "R1"]),
            Instruction("HALT", []),
        ]
        cpu.load_program(program)
        cpu.execute()
        assert cpu.registers[0] == 30

    def test_mul(self):
        cpu = CPU()
        program = [
            Instruction("LOAD", ["R0", 6]),
            Instruction("LOAD", ["R1", 7]),
            Instruction("MUL", ["R0", "R1"]),
            Instruction("HALT", []),
        ]
        cpu.load_program(program)
        cpu.execute()
        assert cpu.registers[0] == 42

    def test_div(self):
        cpu = CPU()
        program = [
            Instruction("LOAD", ["R0", 100]),
            Instruction("LOAD", ["R1", 7]),
            Instruction("DIV", ["R0", "R1"]),
            Instruction("HALT", []),
        ]
        cpu.load_program(program)
        cpu.execute()
        assert cpu.registers[0] == 14  # Integer division

    def test_div_by_zero_raises(self):
        cpu = CPU()
        program = [
            Instruction("LOAD", ["R0", 10]),
            Instruction("LOAD", ["R1", 0]),
            Instruction("DIV", ["R0", "R1"]),
            Instruction("HALT", []),
        ]
        cpu.load_program(program)
        with pytest.raises(CPUError, match="Division by zero"):
            cpu.execute()

    def test_inc(self):
        cpu = CPU()
        program = [
            Instruction("LOAD", ["R0", 41]),
            Instruction("INC", ["R0"]),
            Instruction("HALT", []),
        ]
        cpu.load_program(program)
        cpu.execute()
        assert cpu.registers[0] == 42

    def test_dec(self):
        cpu = CPU()
        program = [
            Instruction("LOAD", ["R0", 43]),
            Instruction("DEC", ["R0"]),
            Instruction("HALT", []),
        ]
        cpu.load_program(program)
        cpu.execute()
        assert cpu.registers[0] == 42


class TestCPUMemory:
    """Test memory operations."""

    def test_store_and_load_memory(self):
        cpu = CPU()
        program = [
            Instruction("LOAD", ["R0", 42]),
            Instruction("STORE", ["R0", 100]),
            Instruction("LOAD", ["R1", "[100]"]),
            Instruction("HALT", []),
        ]
        cpu.load_program(program)
        cpu.execute()
        assert cpu.memory[100] == 42
        assert cpu.registers[1] == 42


class TestCPUControlFlow:
    """Test control flow instructions."""

    def test_jump(self):
        cpu = CPU()
        program = [
            Instruction("LOAD", ["R0", 10]),
            Instruction("JUMP", ["end"]),
            Instruction("LOAD", ["R0", 99]),  # Should be skipped
            Instruction("HALT", []),           # index 3 = 'end'
        ]
        labels = {"end": 3}
        cpu.load_program(program, labels)
        cpu.execute()
        assert cpu.registers[0] == 10  # R0 should NOT be 99

    def test_jz_taken(self):
        cpu = CPU()
        program = [
            Instruction("LOAD", ["R0", 0]),
            Instruction("JZ", ["R0", "target"]),
            Instruction("LOAD", ["R1", 99]),  # Should be skipped
            Instruction("LOAD", ["R1", 42]),  # target
            Instruction("HALT", []),
        ]
        labels = {"target": 3}
        cpu.load_program(program, labels)
        cpu.execute()
        assert cpu.registers[1] == 42

    def test_jz_not_taken(self):
        cpu = CPU()
        program = [
            Instruction("LOAD", ["R0", 5]),
            Instruction("JZ", ["R0", "target"]),
            Instruction("LOAD", ["R1", 99]),  # Should execute
            Instruction("HALT", []),
            Instruction("LOAD", ["R1", 42]),  # target — should NOT execute
            Instruction("HALT", []),
        ]
        labels = {"target": 4}
        cpu.load_program(program, labels)
        cpu.execute()
        assert cpu.registers[1] == 99

    def test_jnz(self):
        cpu = CPU()
        program = [
            Instruction("LOAD", ["R0", 1]),
            Instruction("JNZ", ["R0", "target"]),
            Instruction("LOAD", ["R1", 99]),  # Should be skipped
            Instruction("LOAD", ["R1", 42]),  # target
            Instruction("HALT", []),
        ]
        labels = {"target": 3}
        cpu.load_program(program, labels)
        cpu.execute()
        assert cpu.registers[1] == 42

    def test_loop(self):
        """Test a simple loop that adds 1 ten times."""
        cpu = CPU()
        program = [
            Instruction("LOAD", ["R0", 0]),   # accumulator
            Instruction("LOAD", ["R1", 10]),   # counter
            # loop:
            Instruction("INC", ["R0"]),         # R0++
            Instruction("DEC", ["R1"]),         # R1--
            Instruction("JNZ", ["R1", "loop"]),
            Instruction("HALT", []),
        ]
        labels = {"loop": 2}
        cpu.load_program(program, labels)
        cpu.execute()
        assert cpu.registers[0] == 10
        assert cpu.registers[1] == 0


class TestCPUFlags:
    """Test flag updates."""

    def test_zero_flag(self):
        cpu = CPU()
        program = [
            Instruction("LOAD", ["R0", 1]),
            Instruction("DEC", ["R0"]),
            Instruction("HALT", []),
        ]
        cpu.load_program(program)
        cpu.execute()
        assert cpu.flags["zero"] is True

    def test_negative_flag(self):
        cpu = CPU()
        program = [
            Instruction("LOAD", ["R0", 0]),
            Instruction("DEC", ["R0"]),
            Instruction("HALT", []),
        ]
        cpu.load_program(program)
        cpu.execute()
        assert cpu.flags["negative"] is True


class TestCPUDynamicInstructions:
    """Test dynamic instruction registration."""

    def test_register_custom_instruction(self):
        cpu = CPU()

        def custom_double(operands):
            rd = cpu._resolve_register(operands[0])
            cpu.registers[rd] *= 2

        cpu.register_instruction("DOUBLE", custom_double, is_evolved=True,
                                 constituent_opcodes=["MUL"],
                                 description="Double a register")

        program = [
            Instruction("LOAD", ["R0", 21]),
            Instruction("DOUBLE", ["R0"]),
            Instruction("HALT", []),
        ]
        cpu.load_program(program)
        cpu.execute()
        assert cpu.registers[0] == 42

    def test_unregister_evolved_instruction(self):
        cpu = CPU()

        def noop(operands):
            pass

        cpu.register_instruction("EVOLVED_NOP", noop, is_evolved=True)
        assert "EVOLVED_NOP" in cpu.instruction_table

        cpu.unregister_instruction("EVOLVED_NOP")
        assert "EVOLVED_NOP" not in cpu.instruction_table

    def test_cannot_unregister_base_instruction(self):
        cpu = CPU()
        cpu.unregister_instruction("ADD")  # Should not remove it
        assert "ADD" in cpu.instruction_table


class TestCPUReset:
    """Test CPU reset."""

    def test_reset_clears_registers(self):
        cpu = CPU()
        cpu.registers[0] = 42
        cpu.reset()
        assert cpu.registers[0] == 0

    def test_reset_preserves_instruction_table(self):
        cpu = CPU()
        initial_count = len(cpu.instruction_table)
        cpu.reset()
        assert len(cpu.instruction_table) == initial_count

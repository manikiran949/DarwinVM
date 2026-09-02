"""
Tests for the Assembler / Parser.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from assembler import Assembler, AssemblerError, assemble


class TestAssemblerBasic:
    """Test basic assembly parsing."""

    def test_simple_instruction(self):
        program, labels = assemble("LOAD R0, 42\nHALT")
        assert len(program) == 2
        assert program[0].opcode == "LOAD"
        assert program[0].operands == ["R0", 42]
        assert program[1].opcode == "HALT"

    def test_uppercase_normalization(self):
        program, labels = assemble("load r0, 42\nhalt")
        assert program[0].opcode == "LOAD"
        assert program[0].operands == ["R0", 42]

    def test_comments_stripped(self):
        source = """
        ; This is a comment
        LOAD R0, 10  ; inline comment
        # Another comment style
        ADD R0, R1   # inline
        HALT
        """
        program, labels = assemble(source)
        assert len(program) == 3

    def test_empty_lines_skipped(self):
        source = """
        LOAD R0, 10

        ADD R0, R1

        HALT
        """
        program, labels = assemble(source)
        assert len(program) == 3


class TestAssemblerLabels:
    """Test label handling."""

    def test_label_resolution(self):
        source = """
        LOAD R0, 10
        loop:
        INC R0
        JUMP loop
        HALT
        """
        program, labels = assemble(source)
        assert "loop" in labels
        assert labels["loop"] == 1  # Points to INC instruction

    def test_multiple_labels(self):
        source = """
        start:
        LOAD R0, 0
        JUMP end
        middle:
        LOAD R0, 99
        end:
        HALT
        """
        program, labels = assemble(source)
        assert labels["start"] == 0
        assert labels["middle"] == 2
        assert labels["end"] == 3

    def test_duplicate_label_raises(self):
        source = """
        loop:
        LOAD R0, 10
        loop:
        HALT
        """
        with pytest.raises(AssemblerError, match="Duplicate label"):
            assemble(source)


class TestAssemblerOperands:
    """Test operand parsing."""

    def test_register_operands(self):
        program, _ = assemble("ADD R0, R15\nHALT")
        assert program[0].operands == ["R0", "R15"]

    def test_immediate_operands(self):
        program, _ = assemble("LOAD R0, 42\nHALT")
        assert program[0].operands == ["R0", 42]

    def test_negative_immediate(self):
        program, _ = assemble("LOAD R0, -5\nHALT")
        assert program[0].operands == ["R0", -5]

    def test_memory_address_operand(self):
        program, _ = assemble("LOAD R0, [100]\nHALT")
        assert program[0].operands == ["R0", "[100]"]

    def test_no_operands(self):
        program, _ = assemble("HALT")
        assert program[0].operands == []
        assert program[0].opcode == "HALT"

    def test_label_as_operand(self):
        source = """
        target:
        NOP
        JUMP target
        HALT
        """
        program, labels = assemble(source)
        # The JUMP operand should be "target" (string — resolved at runtime)
        assert program[1].operands == ["target"]

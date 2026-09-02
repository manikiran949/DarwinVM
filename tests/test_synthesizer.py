"""
Tests for the Synthesizer and Rewriter.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from cpu import CPU, Instruction
from pattern_detector import PatternCandidate
from synthesizer import Synthesizer
from rewriter import Rewriter


class TestSynthesizer:
    """Test instruction synthesis."""

    def test_synthesize_add_add(self):
        cpu = CPU()
        synthesizer = Synthesizer(cpu)

        candidate = PatternCandidate(
            opcodes=("ADD", "ADD"),
            frequency=5000,
        )
        synth = synthesizer.synthesize(candidate)

        assert synth.name == "ADD_ADD"
        assert "ADD_ADD" in cpu.instruction_table
        assert cpu.instruction_table["ADD_ADD"].is_evolved

    def test_fused_instruction_executes_correctly(self):
        """Verify that a fused ADD_ADD produces the same result as two separate ADDs."""
        # Baseline: separate instructions
        baseline_cpu = CPU()
        baseline_program = [
            Instruction("LOAD", ["R0", 10]),
            Instruction("LOAD", ["R1", 5]),
            Instruction("LOAD", ["R2", 3]),
            Instruction("ADD", ["R0", "R1"]),   # R0 = 15
            Instruction("ADD", ["R0", "R2"]),   # R0 = 18
            Instruction("HALT", []),
        ]
        baseline_cpu.load_program(baseline_program)
        baseline_cpu.execute()
        expected = baseline_cpu.registers[0]

        # Evolved: fused instruction
        evolved_cpu = CPU()
        synthesizer = Synthesizer(evolved_cpu)
        candidate = PatternCandidate(opcodes=("ADD", "ADD"), frequency=1000)
        synthesizer.synthesize(candidate)

        evolved_program = [
            Instruction("LOAD", ["R0", 10]),
            Instruction("LOAD", ["R1", 5]),
            Instruction("LOAD", ["R2", 3]),
            Instruction("ADD_ADD", ["R0", "R1", "|", "R0", "R2"]),
            Instruction("HALT", []),
        ]
        evolved_cpu.load_program(evolved_program)
        evolved_cpu.execute()

        assert evolved_cpu.registers[0] == expected

    def test_synthesize_mul_add_store(self):
        cpu = CPU()
        synthesizer = Synthesizer(cpu)

        candidate = PatternCandidate(
            opcodes=("MUL", "ADD", "STORE"),
            frequency=3000,
        )
        synth = synthesizer.synthesize(candidate)

        assert synth.name == "MUL_ADD_STORE"
        assert cpu.instruction_table["MUL_ADD_STORE"].constituent_opcodes == ["MUL", "ADD", "STORE"]


class TestRewriter:
    """Test program rewriting."""

    def test_simple_rewrite(self):
        rewriter = Rewriter()
        program = [
            Instruction("LOAD", ["R0", 10]),
            Instruction("ADD", ["R0", "R1"]),
            Instruction("ADD", ["R0", "R2"]),
            Instruction("STORE", ["R0", 100]),
            Instruction("HALT", []),
        ]
        labels = {}

        candidate = PatternCandidate(
            opcodes=("ADD", "ADD"),
            frequency=1000,
        )

        new_program, new_labels = rewriter.rewrite(program, labels, [candidate])

        # Should have replaced 2 ADDs with 1 ADD_ADD
        assert len(new_program) == 4  # LOAD + ADD_ADD + STORE + HALT
        assert new_program[1].opcode == "ADD_ADD"

    def test_rewrite_preserves_correctness(self):
        """Full integration: assemble → rewrite → execute and verify same result."""
        from assembler import assemble

        source = """
        LOAD R0, 10
        LOAD R1, 5
        LOAD R2, 3
        ADD R0, R1
        ADD R0, R2
        HALT
        """
        program, labels = assemble(source)

        # Baseline execution
        baseline_cpu = CPU()
        baseline_cpu.load_program(program, labels)
        baseline_cpu.execute()
        expected_r0 = baseline_cpu.registers[0]

        # Rewrite
        candidate = PatternCandidate(opcodes=("ADD", "ADD"), frequency=1000)
        rewriter = Rewriter()
        new_program, new_labels = rewriter.rewrite(program, labels, [candidate])

        # Evolved execution
        evolved_cpu = CPU()
        synthesizer = Synthesizer(evolved_cpu)
        synthesizer.synthesize(candidate)
        evolved_cpu.load_program(new_program, new_labels)
        evolved_cpu.execute()

        assert evolved_cpu.registers[0] == expected_r0

    def test_rewrite_with_labels(self):
        rewriter = Rewriter()
        program = [
            Instruction("LOAD", ["R9", 5]),
            # loop (index 1):
            Instruction("ADD", ["R0", "R1"]),
            Instruction("ADD", ["R0", "R2"]),
            Instruction("DEC", ["R9"]),
            Instruction("JNZ", ["R9", "loop"]),
            Instruction("HALT", []),
        ]
        labels = {"loop": 1}

        candidate = PatternCandidate(opcodes=("ADD", "ADD"), frequency=1000)
        new_program, new_labels = rewriter.rewrite(program, labels, [candidate])

        # loop label should still point to the correct instruction
        assert "loop" in new_labels
        # The ADD_ADD should be at the position loop points to
        loop_idx = new_labels["loop"]
        assert new_program[loop_idx].opcode == "ADD_ADD"

    def test_no_rewrite_when_no_match(self):
        rewriter = Rewriter()
        program = [
            Instruction("LOAD", ["R0", 10]),
            Instruction("SUB", ["R0", "R1"]),
            Instruction("HALT", []),
        ]
        labels = {}

        candidate = PatternCandidate(opcodes=("ADD", "ADD"), frequency=1000)
        new_program, new_labels = rewriter.rewrite(program, labels, [candidate])

        # No changes
        assert len(new_program) == 3
        assert new_program[0].opcode == "LOAD"
        assert new_program[1].opcode == "SUB"

    def test_count_replacements(self):
        rewriter = Rewriter()
        program = [
            Instruction("ADD", ["R0", "R1"]),
            Instruction("ADD", ["R0", "R2"]),
            Instruction("STORE", ["R0", 100]),
            Instruction("ADD", ["R0", "R1"]),
            Instruction("ADD", ["R0", "R2"]),
            Instruction("HALT", []),
        ]

        candidate = PatternCandidate(opcodes=("ADD", "ADD"), frequency=1000)
        counts = rewriter.count_replacements(program, [candidate])

        assert counts["ADD_ADD"] == 2

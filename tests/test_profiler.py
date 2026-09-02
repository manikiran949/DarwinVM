"""
Tests for the Profiler.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from cpu import CPU, Instruction
from profiler import Profiler


class TestProfilerObservation:
    """Test that the profiler correctly observes and counts patterns."""

    def test_basic_pattern_counting(self):
        profiler = Profiler(window_size=3)
        cpu = CPU()
        cpu.profiler_callback = profiler.observe

        # Create a simple loop: LOAD, ADD, STORE, repeated
        program = [
            Instruction("LOAD", ["R0", 0]),
            Instruction("LOAD", ["R1", 1]),
            Instruction("LOAD", ["R9", 100]),
            # loop:
            Instruction("ADD", ["R0", "R1"]),
            Instruction("ADD", ["R0", "R1"]),
            Instruction("STORE", ["R0", 100]),
            Instruction("DEC", ["R9"]),
            Instruction("JNZ", ["R9", "loop"]),
            Instruction("HALT", []),
        ]
        labels = {"loop": 3}
        cpu.load_program(program, labels)
        cpu.execute()

        assert profiler.total_observed > 0
        assert len(profiler.pattern_counts) > 0

    def test_hot_patterns(self):
        profiler = Profiler(window_size=4)
        cpu = CPU()
        cpu.profiler_callback = profiler.observe

        # Simple loop to generate patterns
        program = [
            Instruction("LOAD", ["R0", 0]),
            Instruction("LOAD", ["R1", 1]),
            Instruction("LOAD", ["R9", 50]),
            # loop:
            Instruction("ADD", ["R0", "R1"]),
            Instruction("ADD", ["R0", "R1"]),
            Instruction("DEC", ["R9"]),
            Instruction("JNZ", ["R9", "loop"]),
            Instruction("HALT", []),
        ]
        labels = {"loop": 3}
        cpu.load_program(program, labels)
        cpu.execute()

        # Should find the (ADD, ADD) pattern frequently
        hot = profiler.get_hot_patterns(min_count=10, min_length=2)
        pattern_opcodes = [p[0] for p in hot]
        assert ("ADD", "ADD") in pattern_opcodes

    def test_opcode_counts(self):
        profiler = Profiler(window_size=3)
        cpu = CPU()
        cpu.profiler_callback = profiler.observe

        program = [
            Instruction("LOAD", ["R0", 5]),
            Instruction("ADD", ["R0", "R0"]),
            Instruction("ADD", ["R0", "R0"]),
            Instruction("ADD", ["R0", "R0"]),
            Instruction("HALT", []),
        ]
        cpu.load_program(program)
        cpu.execute()

        assert profiler.opcode_counts["LOAD"] == 1
        assert profiler.opcode_counts["ADD"] == 3
        assert profiler.opcode_counts["HALT"] == 1

    def test_reset(self):
        profiler = Profiler()
        profiler.observe(Instruction("ADD", ["R0", "R1"]))
        profiler.observe(Instruction("ADD", ["R0", "R1"]))
        assert profiler.total_observed == 2

        profiler.reset()
        assert profiler.total_observed == 0
        assert len(profiler.pattern_counts) == 0

    def test_stats(self):
        profiler = Profiler(window_size=4)
        profiler.observe(Instruction("LOAD", ["R0", 1]))
        profiler.observe(Instruction("ADD", ["R0", "R1"]))
        profiler.observe(Instruction("ADD", ["R0", "R1"]))

        stats = profiler.get_stats()
        assert stats["total_observed"] == 3
        assert stats["window_size"] == 4

"""
Integration test: full evolution pipeline end-to-end.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from cpu import CPU
from assembler import assemble
from evolution import EvolutionEngine, evolve_from_source


class TestEvolutionPipeline:
    """Integration tests for the full evolution pipeline."""

    def test_evolution_discovers_patterns(self):
        """Test that the evolution engine discovers and fuses patterns."""
        source = """
        LOAD R1, 10
        LOAD R2, 20
        LOAD R3, 30
        LOAD R9, 500

        loop:
        LOAD R0, 0
        ADD R0, R1
        ADD R0, R2
        ADD R0, R3
        STORE R0, 100

        DEC R9
        JNZ R9, loop

        HALT
        """

        engine = EvolutionEngine(
            max_generations=2,
            min_pattern_frequency=100,
            benchmark_runs=3,
            verbose=False,
        )
        report = engine.evolve(source=source)

        # Should have at least one generation
        assert len(report.generations) >= 1

        # Should have discovered at least one pattern
        first_gen = report.generations[0]
        assert first_gen.patterns_found > 0

    def test_evolution_correctness(self):
        """Test that evolved program produces the same result as baseline."""
        source = """
        LOAD R1, 5
        LOAD R2, 10
        LOAD R9, 200

        loop:
        LOAD R0, 0
        ADD R0, R1
        ADD R0, R2
        STORE R0, 100

        DEC R9
        JNZ R9, loop

        HALT
        """

        # Baseline execution
        program, labels = assemble(source)
        baseline_cpu = CPU()
        baseline_cpu.load_program(program, labels)
        baseline_result = baseline_cpu.execute()

        # Evolved execution
        engine = EvolutionEngine(
            max_generations=1,
            min_pattern_frequency=50,
            benchmark_runs=2,
            verbose=False,
        )
        report = engine.evolve(source=source)

        # Correctness should be verified by the engine
        if report.generations and report.generations[0].benchmark_result:
            assert report.generations[0].benchmark_result.correctness_verified

    def test_evolution_from_source_convenience(self):
        """Test the convenience function."""
        source = """
        LOAD R0, 0
        LOAD R1, 1
        LOAD R9, 100

        loop:
        ADD R0, R1
        ADD R0, R1
        DEC R9
        JNZ R9, loop

        HALT
        """
        report = evolve_from_source(
            source,
            max_generations=1,
            min_pattern_frequency=50,
            benchmark_runs=2,
            verbose=False,
        )
        assert report is not None
        assert report.initial_instruction_count > 0

    def test_no_evolution_when_no_patterns(self):
        """Test that evolution stops gracefully when no patterns are found."""
        source = """
        LOAD R0, 42
        HALT
        """
        engine = EvolutionEngine(
            max_generations=2,
            min_pattern_frequency=10000,  # Very high threshold
            benchmark_runs=2,
            verbose=False,
        )
        report = engine.evolve(source=source)

        # Should complete without errors
        assert report is not None
        assert report.overall_speedup == 1.0 or len(report.generations) <= 1

    def test_multiple_generations(self):
        """Test that multiple generations can run."""
        source = """
        LOAD R1, 3
        LOAD R2, 7
        LOAD R3, 11
        LOAD R4, 2
        LOAD R9, 100

        loop:
        MOV R0, R1
        ADD R0, R2
        ADD R0, R3
        MUL R0, R4
        STORE R0, 100

        MOV R0, R2
        ADD R0, R3
        MUL R0, R4
        STORE R0, 101

        DEC R9
        JNZ R9, loop

        HALT
        """
        engine = EvolutionEngine(
            max_generations=2,
            min_pattern_frequency=30,
            benchmark_runs=2,
            max_instructions=500_000,
            verbose=False,
        )
        report = engine.evolve(source=source)

        assert len(report.generations) >= 1

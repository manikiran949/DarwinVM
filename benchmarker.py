"""
Self-Evolving CPU — Benchmarker

Measures performance of baseline vs. evolved CPU execution and maintains
a scorecard for each evolved instruction. Determines which instructions
provide real speedup and prunes the rest.
"""

import time
import copy
from cpu import CPU, Instruction
from assembler import assemble
from profiler import Profiler


class InstructionScore:
    """Performance scorecard for an evolved instruction."""

    def __init__(self, name: str, constituent_opcodes: list[str]):
        self.name = name
        self.constituent_opcodes = constituent_opcodes
        self.uses = 0
        self.speedup = 1.0
        self.kept = False
        self.baseline_time = 0.0
        self.evolved_time = 0.0
        self.instructions_saved = 0

    def __repr__(self):
        status = "✓ KEPT" if self.kept else "✗ PRUNED"
        return (
            f"{self.name}: uses={self.uses:,}, "
            f"speedup={self.speedup:.2f}x [{status}]"
        )

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "constituent_opcodes": self.constituent_opcodes,
            "uses": self.uses,
            "speedup": self.speedup,
            "kept": self.kept,
            "baseline_time": self.baseline_time,
            "evolved_time": self.evolved_time,
            "instructions_saved": self.instructions_saved,
        }


class BenchmarkResult:
    """Result of a benchmark run."""

    def __init__(self):
        self.baseline_time: float = 0.0
        self.evolved_time: float = 0.0
        self.baseline_instruction_count: int = 0
        self.evolved_instruction_count: int = 0
        self.overall_speedup: float = 1.0
        self.instruction_reduction: float = 0.0
        self.instruction_scores: list[InstructionScore] = []
        self.baseline_registers: list[int] = []
        self.evolved_registers: list[int] = []
        self.correctness_verified: bool = False

    @property
    def baseline_ips(self) -> float:
        """Baseline instructions per second."""
        if self.baseline_time > 0:
            return self.baseline_instruction_count / self.baseline_time
        return 0

    @property
    def evolved_ips(self) -> float:
        """Evolved instructions per second."""
        if self.evolved_time > 0:
            return self.evolved_instruction_count / self.evolved_time
        return 0

    def to_dict(self) -> dict:
        return {
            "baseline_time": self.baseline_time,
            "evolved_time": self.evolved_time,
            "baseline_instruction_count": self.baseline_instruction_count,
            "evolved_instruction_count": self.evolved_instruction_count,
            "overall_speedup": self.overall_speedup,
            "instruction_reduction": self.instruction_reduction,
            "correctness_verified": self.correctness_verified,
            "baseline_ips": self.baseline_ips,
            "evolved_ips": self.evolved_ips,
            "instruction_scores": [s.to_dict() for s in self.instruction_scores],
        }


class Benchmarker:
    """
    Benchmarks baseline vs. evolved CPU execution.

    Runs both versions, measures timing, verifies correctness (register
    states must match), and scores each evolved instruction.
    """

    def __init__(self, warmup_runs: int = 2, benchmark_runs: int = 5,
                 max_instructions: int = 10_000_000):
        self.warmup_runs = warmup_runs
        self.benchmark_runs = benchmark_runs
        self.max_instructions = max_instructions

    def benchmark(self, baseline_cpu: CPU, baseline_program: list[Instruction],
                  baseline_labels: dict[str, int],
                  evolved_cpu: CPU, evolved_program: list[Instruction],
                  evolved_labels: dict[str, int]) -> BenchmarkResult:
        """
        Run a full benchmark comparing baseline vs evolved execution.

        Args:
            baseline_cpu: CPU with only base instructions.
            baseline_program: Original program.
            baseline_labels: Original labels.
            evolved_cpu: CPU with evolved instructions registered.
            evolved_program: Rewritten program using evolved instructions.
            evolved_labels: Updated labels.

        Returns:
            BenchmarkResult with timing and correctness data.
        """
        result = BenchmarkResult()

        # ── Warmup ──
        for _ in range(self.warmup_runs):
            baseline_cpu.load_program(baseline_program, baseline_labels)
            baseline_cpu.execute(self.max_instructions)

            evolved_cpu.load_program(evolved_program, evolved_labels)
            evolved_cpu.execute(self.max_instructions)

        # ── Benchmark baseline ──
        baseline_times = []
        for _ in range(self.benchmark_runs):
            baseline_cpu.load_program(baseline_program, baseline_labels)
            stats = baseline_cpu.execute(self.max_instructions)
            baseline_times.append(stats["execution_time"])
            result.baseline_instruction_count = stats["total_instructions"]
            result.baseline_registers = stats["registers"]
            result.baseline_flags = stats["flags"]
            result.baseline_memory = stats["memory"]

        result.baseline_time = sum(baseline_times) / len(baseline_times)

        # ── Benchmark evolved ──
        evolved_times = []
        for _ in range(self.benchmark_runs):
            evolved_cpu.load_program(evolved_program, evolved_labels)
            stats = evolved_cpu.execute(self.max_instructions)
            evolved_times.append(stats["execution_time"])
            result.evolved_instruction_count = stats["total_instructions"]
            result.evolved_registers = stats["registers"]
            result.evolved_flags = stats["flags"]
            result.evolved_memory = stats["memory"]

        result.evolved_time = sum(evolved_times) / len(evolved_times)

        # ── Calculate metrics ──
        if result.evolved_time > 0:
            result.overall_speedup = result.baseline_time / result.evolved_time
        else:
            result.overall_speedup = float("inf")

        if result.baseline_instruction_count > 0:
            result.instruction_reduction = (
                1.0 - result.evolved_instruction_count / result.baseline_instruction_count
            ) * 100

        # ── Verify correctness ──
        result.correctness_verified = (
            result.baseline_registers == result.evolved_registers and
            result.baseline_flags == result.evolved_flags and
            result.baseline_memory == result.evolved_memory
        )

        # ── Score evolved instructions ──
        evolved_instructions = evolved_cpu.get_evolved_instructions()
        for meta in evolved_instructions:
            score = InstructionScore(
                name=meta.name,
                constituent_opcodes=meta.constituent_opcodes,
            )
            score.uses = meta.execution_count
            score.instructions_saved = score.uses * (len(meta.constituent_opcodes) - 1)

            # Estimate per-instruction speedup contribution
            if score.uses > 0 and result.baseline_instruction_count > 0:
                # Proportion of instructions this fusion accounts for
                proportion = (score.uses * len(meta.constituent_opcodes)) / result.baseline_instruction_count
                # Estimated speedup contribution
                score.speedup = 1.0 + proportion * (result.overall_speedup - 1.0) * 2
            else:
                score.speedup = 1.0

            score.baseline_time = result.baseline_time
            score.evolved_time = result.evolved_time
            score.kept = score.speedup > 1.0 and score.uses > 0

            result.instruction_scores.append(score)

        # Sort scores by speedup descending
        result.instruction_scores.sort(key=lambda s: s.speedup, reverse=True)

        return result

    def quick_benchmark(self, cpu: CPU, program: list[Instruction],
                        labels: dict[str, int], runs: int = 3) -> dict:
        """
        Quick benchmark of a single program execution.

        Returns:
            Dict with average time, instruction count, and IPS.
        """
        times = []
        total_instr = 0
        registers = []

        for _ in range(runs):
            cpu.load_program(program, labels)
            stats = cpu.execute(self.max_instructions)
            times.append(stats["execution_time"])
            total_instr = stats["total_instructions"]
            registers = stats["registers"]

        avg_time = sum(times) / len(times)
        return {
            "average_time": avg_time,
            "total_instructions": total_instr,
            "ips": total_instr / avg_time if avg_time > 0 else 0,
            "registers": registers,
        }

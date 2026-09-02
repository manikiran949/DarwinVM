"""
Self-Evolving CPU — Main CLI Entry Point

Usage:
    python main.py run <program.asm>          Run a program on the base CPU
    python main.py evolve <program.asm>       Run the full evolution pipeline
    python main.py benchmark <program.asm>    Benchmark base vs. evolved
    python main.py demo                       Run all demo programs
    python main.py list-instructions          List the base instruction set
"""

import sys
import os
import time
from cpu import CPU
from assembler import assemble_file
from profiler import Profiler
from evolution import EvolutionEngine, EvolutionReport
from benchmarker import Benchmarker
from dashboard import Dashboard


def print_header():
    """Print the project header."""
    print()
    print("╔══════════════════════════════════════════════════════════╗")
    print("║           🧬  SELF-EVOLVING CPU EMULATOR  🧬            ║")
    print("║                                                         ║")
    print("║  A CPU that adapts its instruction set to the workload  ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print()


def cmd_run(filepath: str):
    """Run a program on the base CPU."""
    print_header()
    print(f"  Running: {filepath}")
    print(f"  {'─' * 50}")

    program, labels = assemble_file(filepath)
    print(f"  Program size: {len(program)} instructions")
    print(f"  Labels: {list(labels.keys())}")
    print()

    cpu = CPU()
    cpu.load_program(program, labels)
    stats = cpu.execute()

    print(f"  ── Execution Results ──")
    print(f"  Instructions executed: {stats['total_instructions']:,}")
    print(f"  Execution time:        {stats['execution_time']:.4f}s")
    ips = stats['instructions_per_second']
    print(f"  Instructions/second:   {ips:,.0f}")
    print()
    print(f"  ── Register State ──")
    for i in range(CPU.NUM_REGISTERS):
        val = stats['registers'][i]
        if val != 0:
            print(f"  R{i:2d} = {val}")
    print()


def cmd_evolve(filepath: str, generations: int = 3, verbose: bool = True):
    """Run the full evolution pipeline."""
    print_header()

    engine = EvolutionEngine(
        max_generations=generations,
        profiler_window=5,
        min_pattern_frequency=200,
        min_pattern_length=2,
        max_pattern_length=5,
        top_k_patterns=10,
        benchmark_runs=5,
        max_instructions=10_000_000,
        verbose=verbose,
    )

    report = engine.evolve(filepath=filepath)

    # Print the dashboard
    dashboard = Dashboard()
    dashboard.print_evolution_report(report)


def cmd_benchmark(filepath: str):
    """Benchmark base vs. evolved."""
    print_header()
    print(f"  Benchmarking: {filepath}")
    print()

    # First evolve
    engine = EvolutionEngine(
        max_generations=3,
        min_pattern_frequency=200,
        benchmark_runs=7,
        verbose=False,
    )
    report = engine.evolve(filepath=filepath)

    # Print detailed benchmark
    dashboard = Dashboard()
    dashboard.print_benchmark_comparison(report)


def cmd_demo():
    """Run all demo programs."""
    print_header()
    print("  Running all demo programs through the evolution pipeline...")
    print()

    programs_dir = os.path.join(os.path.dirname(__file__), "programs")
    if not os.path.exists(programs_dir):
        print("  Error: programs/ directory not found.")
        return

    asm_files = sorted([
        f for f in os.listdir(programs_dir) if f.endswith(".asm")
    ])

    if not asm_files:
        print("  No .asm files found in programs/ directory.")
        return

    dashboard = Dashboard()

    for asm_file in asm_files:
        filepath = os.path.join(programs_dir, asm_file)
        print(f"{'═' * 60}")
        print(f"  📄 {asm_file}")
        print(f"{'═' * 60}")

        engine = EvolutionEngine(
            max_generations=3,
            min_pattern_frequency=200,
            benchmark_runs=5,
            verbose=True,
        )
        report = engine.evolve(filepath=filepath)
        dashboard.print_evolution_report(report)
        print()


def cmd_list_instructions():
    """List the base instruction set."""
    print_header()
    print("  ── Base Instruction Set ──")
    print()

    cpu = CPU()
    print(f"  {'Opcode':<12} {'Description'}")
    print(f"  {'─' * 12} {'─' * 45}")

    for name, meta in sorted(cpu.instruction_table.items()):
        print(f"  {name:<12} {meta.description}")

    print()
    print(f"  Total: {len(cpu.instruction_table)} instructions")
    print()


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1].lower()

    if command == "run":
        if len(sys.argv) < 3:
            print("Usage: python main.py run <program.asm>")
            sys.exit(1)
        cmd_run(sys.argv[2])

    elif command == "evolve":
        if len(sys.argv) < 3:
            print("Usage: python main.py evolve <program.asm>")
            sys.exit(1)
        generations = int(sys.argv[3]) if len(sys.argv) > 3 else 3
        cmd_evolve(sys.argv[2], generations=generations)

    elif command == "benchmark":
        if len(sys.argv) < 3:
            print("Usage: python main.py benchmark <program.asm>")
            sys.exit(1)
        cmd_benchmark(sys.argv[2])

    elif command == "demo":
        cmd_demo()

    elif command in ("list", "list-instructions", "instructions"):
        cmd_list_instructions()

    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()

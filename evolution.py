"""
Self-Evolving CPU — Evolution Engine (Orchestrator)

Orchestrates the full evolution pipeline:
  1. Execute program on the baseline CPU with profiling
  2. Detect hot instruction patterns
  3. Synthesize new instructions
  4. Rewrite the program
  5. Benchmark baseline vs. evolved
  6. Keep winners, discard losers
  7. Repeat for multiple generations

Produces a detailed evolution report.
"""

import time
import copy
from cpu import CPU, Instruction
from assembler import assemble, assemble_file
from profiler import Profiler
from pattern_detector import PatternDetector, PatternCandidate
from synthesizer import Synthesizer
from rewriter import Rewriter
from benchmarker import Benchmarker, BenchmarkResult


class GenerationReport:
    """Report for a single generation of evolution."""

    def __init__(self, generation: int):
        self.generation = generation
        self.timestamp = time.time()
        self.patterns_found: int = 0
        self.candidates_selected: int = 0
        self.instructions_synthesized: int = 0
        self.program_size_before: int = 0
        self.program_size_after: int = 0
        self.benchmark_result: BenchmarkResult = None
        self.new_instructions: list[dict] = []
        self.pruned_instructions: list[str] = []
        self.kept_instructions: list[str] = []

    def to_dict(self) -> dict:
        return {
            "generation": self.generation,
            "patterns_found": self.patterns_found,
            "candidates_selected": self.candidates_selected,
            "instructions_synthesized": self.instructions_synthesized,
            "program_size_before": self.program_size_before,
            "program_size_after": self.program_size_after,
            "new_instructions": self.new_instructions,
            "pruned_instructions": self.pruned_instructions,
            "kept_instructions": self.kept_instructions,
            "benchmark": self.benchmark_result.to_dict() if self.benchmark_result else None,
        }


class EvolutionReport:
    """Complete report across all generations."""

    def __init__(self):
        self.generations: list[GenerationReport] = []
        self.initial_instruction_count: int = 0
        self.final_instruction_count: int = 0
        self.initial_execution_time: float = 0.0
        self.final_execution_time: float = 0.0
        self.total_evolved_instructions: int = 0
        self.overall_speedup: float = 1.0
        self.all_discovered_instructions: list[dict] = []
        self.surviving_instructions: list[dict] = []

    def to_dict(self) -> dict:
        return {
            "initial_instruction_count": self.initial_instruction_count,
            "final_instruction_count": self.final_instruction_count,
            "initial_execution_time": self.initial_execution_time,
            "final_execution_time": self.final_execution_time,
            "total_evolved_instructions": self.total_evolved_instructions,
            "overall_speedup": self.overall_speedup,
            "all_discovered_instructions": self.all_discovered_instructions,
            "surviving_instructions": self.surviving_instructions,
            "generations": [g.to_dict() for g in self.generations],
        }


class EvolutionEngine:
    """
    Orchestrates the self-evolving CPU pipeline.

    Runs multiple generations of:
        profile → detect → synthesize → rewrite → benchmark → prune
    """

    def __init__(self,
                 max_generations: int = 3,
                 profiler_window: int = 5,
                 min_pattern_frequency: int = 500,
                 min_pattern_length: int = 2,
                 max_pattern_length: int = 5,
                 top_k_patterns: int = 10,
                 benchmark_runs: int = 5,
                 max_instructions: int = 10_000_000,
                 verbose: bool = True):
        self.max_generations = max_generations
        self.profiler_window = profiler_window
        self.min_pattern_frequency = min_pattern_frequency
        self.min_pattern_length = min_pattern_length
        self.max_pattern_length = max_pattern_length
        self.top_k_patterns = top_k_patterns
        self.benchmark_runs = benchmark_runs
        self.max_instructions = max_instructions
        self.verbose = verbose

    def evolve(self, source: str = None, filepath: str = None) -> EvolutionReport:
        """
        Run the full evolution pipeline.

        Provide either `source` (assembly text) or `filepath` (path to .asm file).

        Returns:
            EvolutionReport with all evolution data.
        """
        if filepath:
            program, labels = assemble_file(filepath)
        elif source:
            program, labels = assemble(source)
        else:
            raise ValueError("Provide either 'source' or 'filepath'")

        report = EvolutionReport()
        report.initial_instruction_count = self._count_base_instructions(CPU())

        # ── Initial baseline benchmark ──
        if self.verbose:
            print("=" * 60)
            print("  SELF-EVOLVING CPU — Evolution Pipeline")
            print("=" * 60)
            print()
            print(f"  Program size: {len(program)} instructions")
            print(f"  Max generations: {self.max_generations}")
            print()

        baseline_cpu = CPU()
        baseline_result = Benchmarker(
            benchmark_runs=self.benchmark_runs,
            max_instructions=self.max_instructions,
        ).quick_benchmark(baseline_cpu, program, labels)
        report.initial_execution_time = baseline_result["average_time"]

        if self.verbose:
            print(f"  Baseline: {baseline_result['total_instructions']:,} instructions "
                  f"in {baseline_result['average_time']:.4f}s "
                  f"({baseline_result['ips']:,.0f} IPS)")
            print()

        # Current state of the program and labels
        current_program = list(program)
        current_labels = dict(labels)
        all_candidates_ever = []
        # Track all previously synthesized instruction handlers for re-registration
        # Each entry: (name, handler, constituent_opcodes, description)
        prior_evolved_instructions = []

        # ── Evolution loop ──
        for gen in range(self.max_generations):
            gen_report = self._run_generation(
                generation=gen,
                original_program=program,
                original_labels=labels,
                current_program=current_program,
                current_labels=current_labels,
                prior_evolved_instructions=prior_evolved_instructions,
            )
            report.generations.append(gen_report)

            if gen_report.benchmark_result:
                bm = gen_report.benchmark_result
                # Only accept evolution if it's both faster AND correct
                if bm.overall_speedup > 1.0 and bm.correctness_verified:
                    current_program = gen_report._evolved_program
                    current_labels = gen_report._evolved_labels
                    all_candidates_ever.extend(gen_report.new_instructions)
                    # Carry forward kept evolved instruction handlers
                    if hasattr(gen_report, '_kept_handlers'):
                        prior_evolved_instructions.extend(gen_report._kept_handlers)
                else:
                    reason = "no speedup" if bm.overall_speedup <= 1.0 else "correctness mismatch"
                    if self.verbose:
                        print(f"  Generation {gen} rejected ({reason}). Stopping evolution.")
                    break

            if gen_report.candidates_selected == 0:
                if self.verbose:
                    print(f"  No new patterns found in generation {gen}. Stopping evolution.")
                break

        # ── Final report ──
        # Re-register all surviving evolved instructions
        # (We need to re-benchmark to get final stats)
        last_valid_bm = None
        for gen in reversed(report.generations):
            if gen.benchmark_result and gen.benchmark_result.overall_speedup > 1.0 and gen.benchmark_result.correctness_verified:
                last_valid_bm = gen.benchmark_result
                break
                
        if last_valid_bm:
            report.final_execution_time = last_valid_bm.evolved_time
            report.overall_speedup = last_valid_bm.overall_speedup
        else:
            report.final_execution_time = report.initial_execution_time
            report.overall_speedup = 1.0

        report.final_instruction_count = report.initial_instruction_count + len(all_candidates_ever)
        report.all_discovered_instructions = all_candidates_ever
        report.total_evolved_instructions = len(all_candidates_ever)

        return report

    def _run_generation(self, generation: int,
                        original_program: list[Instruction],
                        original_labels: dict[str, int],
                        current_program: list[Instruction],
                        current_labels: dict[str, int],
                        prior_evolved_instructions: list = None) -> GenerationReport:
        """Run a single generation of evolution."""
        gen_report = GenerationReport(generation)
        prior_evolved_instructions = prior_evolved_instructions or []

        if self.verbose:
            print(f"  ┌─ Generation {generation} {'─' * 40}")

        # Step 1: Profile execution
        if self.verbose:
            print(f"  │  Profiling execution...")
        profiler = Profiler(window_size=self.profiler_window)
        profile_cpu = CPU()
        # Re-register any previously evolved instructions so the CPU can run
        # programs that already use fused opcodes from prior generations
        for name, handler, constit, desc in prior_evolved_instructions:
            profile_cpu.register_instruction(
                name, handler, is_evolved=True,
                constituent_opcodes=constit, description=desc,
            )
        profile_cpu.profiler_callback = profiler.observe
        profile_cpu.load_program(current_program, current_labels)
        profile_cpu.execute(self.max_instructions)

        # Step 2: Detect hot patterns
        hot_patterns = profiler.get_hot_patterns(
            min_count=self.min_pattern_frequency,
            min_length=self.min_pattern_length,
            max_length=self.max_pattern_length,
        )
        gen_report.patterns_found = len(hot_patterns)

        if self.verbose:
            print(f"  │  Found {len(hot_patterns)} hot patterns")

        if not hot_patterns:
            if self.verbose:
                print(f"  └─ No patterns found. Skipping generation.")
            return gen_report

        # Step 3: Select candidates
        # Collect names of all previously evolved opcodes to exclude from patterns
        evolved_opcode_names = {name for name, _, _, _ in prior_evolved_instructions}
        detector = PatternDetector(
            min_frequency=self.min_pattern_frequency,
            min_length=self.min_pattern_length,
            max_length=self.max_pattern_length,
            top_k=self.top_k_patterns,
            evolved_opcodes=evolved_opcode_names,
        )
        candidates = detector.detect(hot_patterns)
        gen_report.candidates_selected = len(candidates)

        if self.verbose:
            print(f"  │  Selected {len(candidates)} candidates for synthesis:")
            for c in candidates:
                print(f"  │    {c.fused_name} (freq={c.frequency:,}, score={c.score:,})")

        if not candidates:
            if self.verbose:
                print(f"  └─ No viable candidates. Skipping generation.")
            return gen_report

        # Step 4: Synthesize new instructions
        evolved_cpu = CPU()
        # Re-register prior evolved instructions on the evolved CPU
        for name, handler, constit, desc in prior_evolved_instructions:
            evolved_cpu.register_instruction(
                name, handler, is_evolved=True,
                constituent_opcodes=constit, description=desc,
            )
        synthesizer = Synthesizer(evolved_cpu)
        synthesized = synthesizer.synthesize_all(candidates)
        gen_report.instructions_synthesized = len(synthesized)

        if self.verbose:
            print(f"  │  Synthesized {len(synthesized)} new instructions")

        # Step 5: Rewrite the program
        gen_report.program_size_before = len(current_program)
        rewriter = Rewriter()
        evolved_program, evolved_labels = rewriter.rewrite(
            current_program, current_labels, candidates
        )
        gen_report.program_size_after = len(evolved_program)

        if self.verbose:
            reduction = gen_report.program_size_before - gen_report.program_size_after
            print(f"  │  Program: {gen_report.program_size_before} → "
                  f"{gen_report.program_size_after} instructions "
                  f"(-{reduction})")

        # Step 6: Benchmark
        if self.verbose:
            print(f"  │  Benchmarking...")

        baseline_cpu = CPU()
        benchmarker = Benchmarker(
            benchmark_runs=self.benchmark_runs,
            max_instructions=self.max_instructions,
        )
        benchmark_result = benchmarker.benchmark(
            baseline_cpu=baseline_cpu,
            baseline_program=original_program,
            baseline_labels=original_labels,
            evolved_cpu=evolved_cpu,
            evolved_program=evolved_program,
            evolved_labels=evolved_labels,
        )
        gen_report.benchmark_result = benchmark_result

        if self.verbose:
            print(f"  │  Baseline:  {benchmark_result.baseline_time:.4f}s "
                  f"({benchmark_result.baseline_instruction_count:,} instructions)")
            print(f"  │  Evolved:   {benchmark_result.evolved_time:.4f}s "
                  f"({benchmark_result.evolved_instruction_count:,} instructions)")
            print(f"  │  Speedup:   {benchmark_result.overall_speedup:.2f}x")
            print(f"  │  Correct:   {'✓' if benchmark_result.correctness_verified else '✗ MISMATCH!'}")

        # Step 7: Score and prune
        for score in benchmark_result.instruction_scores:
            info = {
                "name": score.name,
                "opcodes": score.constituent_opcodes,
                "uses": score.uses,
                "speedup": score.speedup,
            }
            gen_report.new_instructions.append(info)

            if score.kept:
                gen_report.kept_instructions.append(score.name)
                if self.verbose:
                    print(f"  │  ✓ KEEP  {score.name}: "
                          f"uses={score.uses:,}, speedup={score.speedup:.2f}x")
            else:
                gen_report.pruned_instructions.append(score.name)
                evolved_cpu.unregister_instruction(score.name)
                if self.verbose:
                    print(f"  │  ✗ PRUNE {score.name}: "
                          f"uses={score.uses:,}, speedup={score.speedup:.2f}x")

        # Store the evolved program for potential next generation
        gen_report._evolved_program = evolved_program
        gen_report._evolved_labels = evolved_labels
        # Record kept evolved instruction handlers for future generations
        gen_report._kept_handlers = []
        for score in benchmark_result.instruction_scores:
            if score.kept:
                meta = evolved_cpu.instruction_table.get(score.name)
                if meta and meta.is_evolved:
                    gen_report._kept_handlers.append(
                        (meta.name, meta.handler, meta.constituent_opcodes, meta.description)
                    )

        if self.verbose:
            print(f"  └─ Generation {generation} complete")
            print()

        return gen_report

    def _count_base_instructions(self, cpu: CPU) -> int:
        """Count base (non-evolved) instructions in the CPU."""
        return sum(
            1 for meta in cpu.instruction_table.values()
            if not meta.is_evolved
        )


def evolve_from_file(filepath: str, **kwargs) -> EvolutionReport:
    """Convenience function to run evolution from a file."""
    engine = EvolutionEngine(**kwargs)
    return engine.evolve(filepath=filepath)


def evolve_from_source(source: str, **kwargs) -> EvolutionReport:
    """Convenience function to run evolution from source code."""
    engine = EvolutionEngine(**kwargs)
    return engine.evolve(source=source)

"""
Self-Evolving CPU — Dashboard

Terminal-based display for evolution results. Provides formatted tables,
ASCII art, and progress display for the evolution pipeline.

Uses only the Python standard library (no external dependencies required),
but leverages 'rich' if available for enhanced output.
"""

import sys
from evolution import EvolutionReport, GenerationReport


# Try to import rich for enhanced output; fall back to basic formatting
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    from rich import box
    HAS_RICH = True
except ImportError:
    HAS_RICH = False


class Dashboard:
    """
    Terminal dashboard for displaying evolution results.

    Automatically uses 'rich' for beautiful output if available,
    otherwise falls back to plain text with Unicode box-drawing.
    """

    def __init__(self):
        if HAS_RICH:
            self.console = Console()

    def print_evolution_report(self, report: EvolutionReport):
        """Print the full evolution report."""
        if HAS_RICH:
            self._rich_evolution_report(report)
        else:
            self._plain_evolution_report(report)

    def print_benchmark_comparison(self, report: EvolutionReport):
        """Print a detailed benchmark comparison."""
        if HAS_RICH:
            self._rich_benchmark(report)
        else:
            self._plain_benchmark(report)

    # ─── Rich Output (with 'rich' library) ────────────────────────────

    def _rich_evolution_report(self, report: EvolutionReport):
        console = self.console

        # Header
        console.print()
        console.print(Panel(
            "[bold cyan]🧬 EVOLUTION REPORT[/bold cyan]",
            box=box.DOUBLE,
            style="bright_blue",
        ))

        # Overview table
        overview = Table(title="Evolution Overview", box=box.ROUNDED)
        overview.add_column("Metric", style="cyan")
        overview.add_column("Before", style="red")
        overview.add_column("After", style="green")
        overview.add_column("Change", style="yellow")

        overview.add_row(
            "Instruction Set Size",
            str(report.initial_instruction_count),
            str(report.final_instruction_count),
            f"+{report.total_evolved_instructions} evolved",
        )
        overview.add_row(
            "Execution Time",
            f"{report.initial_execution_time:.4f}s",
            f"{report.final_execution_time:.4f}s",
            f"{report.overall_speedup:.2f}x speedup",
        )
        overview.add_row(
            "Generations",
            "0",
            str(len(report.generations)),
            "",
        )
        console.print(overview)
        console.print()

        # Discovered instructions table
        if report.all_discovered_instructions:
            instr_table = Table(
                title="Discovered Instructions",
                box=box.ROUNDED,
            )
            instr_table.add_column("Instruction", style="bright_green")
            instr_table.add_column("Constituent Opcodes", style="cyan")
            instr_table.add_column("Uses", justify="right", style="yellow")
            instr_table.add_column("Speedup", justify="right", style="magenta")

            for instr in report.all_discovered_instructions:
                opcodes_str = " → ".join(instr.get("opcodes", []))
                uses = f"{instr.get('uses', 0):,}"
                speedup = f"{instr.get('speedup', 1.0):.2f}x"
                instr_table.add_row(
                    instr["name"], opcodes_str, uses, speedup
                )

            console.print(instr_table)
            console.print()

        # Generation details
        for gen_report in report.generations:
            self._rich_generation_detail(gen_report)

        # Final summary
        self._rich_final_summary(report)

    def _rich_generation_detail(self, gen: GenerationReport):
        console = self.console

        if gen.benchmark_result:
            bm = gen.benchmark_result
            status = "[green]✓ PASS[/green]" if bm.correctness_verified else "[red]✗ FAIL[/red]"
            speedup_color = "green" if bm.overall_speedup > 1.0 else "red"

            detail = Table(
                title=f"Generation {gen.generation}",
                box=box.SIMPLE_HEAVY,
            )
            detail.add_column("Metric", style="cyan")
            detail.add_column("Value", style="white")

            detail.add_row("Patterns Found", str(gen.patterns_found))
            detail.add_row("Candidates Selected", str(gen.candidates_selected))
            detail.add_row("Instructions Synthesized", str(gen.instructions_synthesized))
            detail.add_row("Program Size", f"{gen.program_size_before} → {gen.program_size_after}")
            detail.add_row("Speedup", f"[{speedup_color}]{bm.overall_speedup:.2f}x[/{speedup_color}]")
            detail.add_row("Correctness", status)
            detail.add_row("Kept", ", ".join(gen.kept_instructions) or "—")
            detail.add_row("Pruned", ", ".join(gen.pruned_instructions) or "—")

            console.print(detail)
            console.print()

    def _rich_benchmark(self, report: EvolutionReport):
        console = self.console

        console.print()
        console.print(Panel(
            "[bold cyan]📊 BENCHMARK COMPARISON[/bold cyan]",
            box=box.DOUBLE,
            style="bright_blue",
        ))

        if not report.generations:
            console.print("[yellow]No evolution data available.[/yellow]")
            return

        last_gen = report.generations[-1]
        if not last_gen.benchmark_result:
            console.print("[yellow]No benchmark data available.[/yellow]")
            return

        bm = last_gen.benchmark_result

        # Comparison table
        comp = Table(title="Performance Comparison", box=box.ROUNDED)
        comp.add_column("", style="bold")
        comp.add_column("Baseline CPU", style="red", justify="right")
        comp.add_column("Evolved CPU", style="green", justify="right")

        comp.add_row(
            "Execution Time",
            f"{bm.baseline_time:.4f}s",
            f"{bm.evolved_time:.4f}s",
        )
        comp.add_row(
            "Instructions Executed",
            f"{bm.baseline_instruction_count:,}",
            f"{bm.evolved_instruction_count:,}",
        )
        comp.add_row(
            "Instructions/Second",
            f"{bm.baseline_ips:,.0f}",
            f"{bm.evolved_ips:,.0f}",
        )
        comp.add_row(
            "Instruction Reduction",
            "—",
            f"{bm.instruction_reduction:.1f}%",
        )

        console.print(comp)
        console.print()

        # Speedup result
        speedup = bm.overall_speedup
        color = "green" if speedup > 1.0 else "red"
        console.print(Panel(
            f"[bold {color}]Overall Speedup: {speedup:.2f}x[/bold {color}]",
            box=box.HEAVY,
        ))
        console.print()

        # Instruction scorecard
        if bm.instruction_scores:
            scores = Table(
                title="Instruction Scorecard",
                box=box.ROUNDED,
            )
            scores.add_column("Instruction", style="bright_green")
            scores.add_column("Uses", justify="right", style="yellow")
            scores.add_column("Speedup", justify="right")
            scores.add_column("Status", justify="center")

            for score in bm.instruction_scores:
                speedup_str = f"{score.speedup:.2f}x"
                if score.speedup > 1.0:
                    speedup_str = f"[green]{speedup_str}[/green]"
                else:
                    speedup_str = f"[red]{speedup_str}[/red]"

                status = "[green]✓ KEPT[/green]" if score.kept else "[red]✗ PRUNED[/red]"

                scores.add_row(
                    score.name,
                    f"{score.uses:,}",
                    speedup_str,
                    status,
                )

            console.print(scores)

        console.print()

    def _rich_final_summary(self, report: EvolutionReport):
        console = self.console

        speedup = report.overall_speedup
        if speedup >= 1.5:
            emoji = "🚀"
            msg = "Excellent evolution!"
        elif speedup >= 1.1:
            emoji = "✨"
            msg = "Good improvement!"
        elif speedup > 1.0:
            emoji = "📈"
            msg = "Marginal improvement."
        else:
            emoji = "📉"
            msg = "No improvement — workload may not benefit from fusion."

        summary_text = (
            f"[bold]{emoji} {msg}[/bold]\n\n"
            f"  Initial ISA:    {report.initial_instruction_count} instructions\n"
            f"  Evolved ISA:    {report.final_instruction_count} instructions "
            f"(+{report.total_evolved_instructions} new)\n"
            f"  Execution Time: {report.initial_execution_time:.4f}s → "
            f"{report.final_execution_time:.4f}s\n"
            f"  Overall:        [bold]{speedup:.2f}x[/bold] speedup"
        )

        color = "green" if speedup > 1.0 else "red"
        console.print(Panel(
            summary_text,
            title="[bold]Final Summary[/bold]",
            border_style=color,
            box=box.DOUBLE,
        ))
        console.print()

    # ─── Plain Text Output (no 'rich' library) ───────────────────────

    def _plain_evolution_report(self, report: EvolutionReport):
        print()
        print("╔══════════════════════════════════════════════════════╗")
        print("║            🧬 EVOLUTION REPORT 🧬                   ║")
        print("╚══════════════════════════════════════════════════════╝")
        print()

        # Overview
        print("  ── Evolution Overview ──")
        print(f"  ISA Size:       {report.initial_instruction_count} → "
              f"{report.final_instruction_count} "
              f"(+{report.total_evolved_instructions} evolved)")
        print(f"  Execution Time: {report.initial_execution_time:.4f}s → "
              f"{report.final_execution_time:.4f}s")
        print(f"  Speedup:        {report.overall_speedup:.2f}x")
        print(f"  Generations:    {len(report.generations)}")
        print()

        # Discovered instructions
        if report.all_discovered_instructions:
            print("  ── Discovered Instructions ──")
            print(f"  {'Instruction':<25} {'Opcodes':<30} {'Uses':>10} {'Speedup':>10}")
            print(f"  {'─' * 25} {'─' * 30} {'─' * 10} {'─' * 10}")
            for instr in report.all_discovered_instructions:
                name = instr["name"]
                opcodes = " → ".join(instr.get("opcodes", []))
                uses = f"{instr.get('uses', 0):,}"
                speedup = f"{instr.get('speedup', 1.0):.2f}x"
                print(f"  {name:<25} {opcodes:<30} {uses:>10} {speedup:>10}")
            print()

        # Generation details
        for gen in report.generations:
            self._plain_generation_detail(gen)

        # Final summary
        speedup = report.overall_speedup
        if speedup >= 1.5:
            msg = "🚀 Excellent evolution!"
        elif speedup >= 1.1:
            msg = "✨ Good improvement!"
        elif speedup > 1.0:
            msg = "📈 Marginal improvement."
        else:
            msg = "📉 No improvement."

        print(f"  ── Final Summary ──")
        print(f"  {msg}")
        print(f"  {report.initial_instruction_count} → "
              f"{report.final_instruction_count} instructions | "
              f"{report.overall_speedup:.2f}x speedup")
        print()

    def _plain_generation_detail(self, gen: GenerationReport):
        print(f"  ── Generation {gen.generation} ──")
        print(f"  Patterns found:    {gen.patterns_found}")
        print(f"  Candidates:        {gen.candidates_selected}")
        print(f"  Synthesized:       {gen.instructions_synthesized}")
        print(f"  Program size:      {gen.program_size_before} → {gen.program_size_after}")

        if gen.benchmark_result:
            bm = gen.benchmark_result
            correct = "✓" if bm.correctness_verified else "✗ MISMATCH"
            print(f"  Speedup:           {bm.overall_speedup:.2f}x")
            print(f"  Correctness:       {correct}")

        if gen.kept_instructions:
            print(f"  Kept:              {', '.join(gen.kept_instructions)}")
        if gen.pruned_instructions:
            print(f"  Pruned:            {', '.join(gen.pruned_instructions)}")
        print()

    def _plain_benchmark(self, report: EvolutionReport):
        print()
        print("╔══════════════════════════════════════════════════════╗")
        print("║          📊 BENCHMARK COMPARISON 📊                  ║")
        print("╚══════════════════════════════════════════════════════╝")
        print()

        if not report.generations or not report.generations[-1].benchmark_result:
            print("  No benchmark data available.")
            return

        bm = report.generations[-1].benchmark_result

        print(f"  {'Metric':<25} {'Baseline':>15} {'Evolved':>15}")
        print(f"  {'─' * 25} {'─' * 15} {'─' * 15}")
        print(f"  {'Execution Time':<25} {bm.baseline_time:>14.4f}s {bm.evolved_time:>14.4f}s")
        print(f"  {'Instructions':<25} {bm.baseline_instruction_count:>15,} {bm.evolved_instruction_count:>15,}")
        print(f"  {'IPS':<25} {bm.baseline_ips:>15,.0f} {bm.evolved_ips:>15,.0f}")
        print(f"  {'Reduction':<25} {'—':>15} {bm.instruction_reduction:>14.1f}%")
        print()
        print(f"  Overall Speedup: {bm.overall_speedup:.2f}x")
        print()

        if bm.instruction_scores:
            print(f"  ── Instruction Scorecard ──")
            print(f"  {'Instruction':<25} {'Uses':>10} {'Speedup':>10} {'Status':>10}")
            print(f"  {'─' * 25} {'─' * 10} {'─' * 10} {'─' * 10}")
            for score in bm.instruction_scores:
                status = "✓ KEPT" if score.kept else "✗ PRUNED"
                print(f"  {score.name:<25} {score.uses:>10,} {score.speedup:>9.2f}x {status:>10}")
            print()

"""
Self-Evolving CPU — Instruction Synthesizer

Creates new virtual opcodes from detected patterns. Generates Python functions
that execute the full sequence of base instructions in a single call, reducing
interpreter dispatch overhead.
"""

import time
from cpu import CPU, Instruction, InstructionMeta
from pattern_detector import PatternCandidate


class SynthesizedInstruction:
    """Represents a newly synthesized (evolved) instruction."""

    def __init__(self, name: str, constituent_opcodes: tuple[str, ...],
                 handler, description: str = ""):
        self.name = name
        self.constituent_opcodes = list(constituent_opcodes)
        self.handler = handler
        self.creation_time = time.time()
        self.description = description

    def __repr__(self):
        return f"SynthesizedInstruction({self.name}: {' → '.join(self.constituent_opcodes)})"


class Synthesizer:
    """
    Creates new CPU instructions by fusing sequences of base instructions.

    For a pattern like (LOAD, ADD, ADD, STORE), it generates a single function
    that executes all four operations, eliminating 3 dispatch cycles.

    The key insight: in an interpreted CPU, each instruction incurs overhead
    from the fetch-decode-dispatch loop. Fusing N instructions into 1 removes
    (N-1) rounds of that overhead.
    """

    def __init__(self, cpu: CPU):
        self.cpu = cpu
        self.synthesized: list[SynthesizedInstruction] = []

    def synthesize(self, candidate: PatternCandidate) -> SynthesizedInstruction:
        """
        Synthesize a new instruction from a pattern candidate.

        Args:
            candidate: The PatternCandidate to synthesize.

        Returns:
            A SynthesizedInstruction ready to be registered with the CPU.
        """
        opcodes = candidate.opcodes
        fused_name = candidate.fused_name

        # Check if already synthesized
        if fused_name in self.cpu.instruction_table:
            existing = self.cpu.instruction_table[fused_name]
            if existing.is_evolved:
                # Return existing
                return SynthesizedInstruction(
                    name=fused_name,
                    constituent_opcodes=opcodes,
                    handler=existing.handler,
                    description=existing.description,
                )

        # Build the fused handler
        handler = self._build_fused_handler(opcodes)
        description = f"Fused: {' → '.join(opcodes)} (freq={candidate.frequency:,})"

        synth = SynthesizedInstruction(
            name=fused_name,
            constituent_opcodes=opcodes,
            handler=handler,
            description=description,
        )
        self.synthesized.append(synth)

        # Register with the CPU
        self.cpu.register_instruction(
            name=fused_name,
            handler=handler,
            is_evolved=True,
            constituent_opcodes=list(opcodes),
            description=description,
        )

        return synth

    def _build_fused_handler(self, opcodes: tuple[str, ...]):
        """
        Build a fused handler function that executes a sequence of base instructions.

        The handler takes a flat list of all operands for all constituent instructions,
        and calls each base instruction's handler in sequence.

        Operand layout for the fused instruction:
            The operands are packed as: [n_ops_1, ops_1..., n_ops_2, ops_2..., ...]
            where n_ops_i is the number of operands for instruction i.

        Alternatively, for simplicity, we use a delimiter-based approach:
            operands = [op1_a, op1_b, "|", op2_a, op2_b, "|", op3_a]
            where "|" separates operand groups for each constituent instruction.
        """
        # Capture the base handlers for each opcode
        base_handlers = []
        for opcode in opcodes:
            meta = self.cpu.instruction_table.get(opcode)
            if meta is None:
                raise ValueError(f"Cannot synthesize: unknown base opcode '{opcode}'")
            base_handlers.append(meta.handler)

        num_instructions = len(opcodes)

        def fused_handler(operands: list):
            """
            Execute all constituent instructions in sequence.
            Operands are separated by '|' delimiter.
            """
            # Split operands by '|' delimiter
            groups = []
            current_group = []
            for op in operands:
                if op == "|":
                    groups.append(current_group)
                    current_group = []
                else:
                    current_group.append(op)
            groups.append(current_group)

            # Pad with empty groups if fewer delimiters than expected
            while len(groups) < num_instructions:
                groups.append([])

            # Execute each constituent instruction
            for handler, ops in zip(base_handlers, groups):
                handler(ops)

        return fused_handler

    def synthesize_all(self, candidates: list[PatternCandidate]) -> list[SynthesizedInstruction]:
        """Synthesize instructions for all candidates."""
        results = []
        for candidate in candidates:
            try:
                synth = self.synthesize(candidate)
                results.append(synth)
            except Exception as e:
                print(f"  ⚠ Failed to synthesize {candidate.fused_name}: {e}")
        return results

    def get_synthesized_list(self) -> list[dict]:
        """Get a summary of all synthesized instructions."""
        return [
            {
                "name": s.name,
                "opcodes": s.constituent_opcodes,
                "description": s.description,
            }
            for s in self.synthesized
        ]

"""
Self-Evolving CPU — Program Rewriter

Rewrites programs to use evolved (fused) instructions. Scans for occurrences
of fusible patterns in the instruction stream and replaces them with single
evolved opcodes. Correctly adjusts jump targets and labels after instruction
removal.
"""

from cpu import Instruction
from pattern_detector import PatternCandidate


class Rewriter:
    """
    Rewrites a program to use evolved instructions.

    Given a program and a set of fused patterns, scans the instruction stream
    for pattern matches and replaces them with the corresponding fused opcode.

    Handles:
    - Non-overlapping pattern replacement (greedy, longest-first)
    - Jump target adjustment after instructions are removed
    - Label remapping
    """

    def rewrite(self, program: list[Instruction], labels: dict[str, int],
                candidates: list[PatternCandidate]) -> tuple[list[Instruction], dict[str, int]]:
        """
        Rewrite a program to use fused instructions.

        Args:
            program: The original program (list of Instructions).
            labels: The label map (label_name -> instruction index).
            candidates: List of PatternCandidates that have been synthesized.

        Returns:
            (new_program, new_labels) — The rewritten program and updated label map.
        """
        if not candidates:
            return list(program), dict(labels)

        # Sort candidates by length descending (prefer longer fusions first)
        sorted_candidates = sorted(candidates, key=lambda c: c.length, reverse=True)

        # Build a mapping of which instructions get replaced
        # replaced[i] = True if instruction at index i is part of a fusion
        n = len(program)
        replaced = [False] * n
        # List of (start_index, length, fused_candidate) for each replacement
        replacements = []

        for candidate in sorted_candidates:
            pattern = candidate.opcodes
            pattern_len = len(pattern)

            i = 0
            while i <= n - pattern_len:
                # Check if any instruction in this range is already replaced
                if any(replaced[i + j] for j in range(pattern_len)):
                    i += 1
                    continue

                # Check if the pattern matches
                match = True
                for j in range(pattern_len):
                    if program[i + j].opcode != pattern[j]:
                        match = False
                        break

                if match:
                    # Check that no jump target points INTO the middle of this pattern
                    # (jumps to the start are OK — they'll be redirected to the fused instruction)
                    label_targets = set(labels.values())
                    middle_targets = set(range(i + 1, i + pattern_len))
                    if middle_targets & label_targets:
                        # A label points into the middle — cannot safely fuse this occurrence
                        i += 1
                        continue

                    # Mark as replaced
                    for j in range(pattern_len):
                        replaced[i + j] = True
                    replacements.append((i, pattern_len, candidate))
                    i += pattern_len
                else:
                    i += 1

        if not replacements:
            return list(program), dict(labels)

        # Sort replacements by start index
        replacements.sort(key=lambda r: r[0])

        # Build the new program
        new_program = []
        # Map: old_index -> new_index (for adjusting jump targets)
        index_map = {}
        old_idx = 0
        replacement_idx = 0

        while old_idx < n:
            if replacement_idx < len(replacements) and old_idx == replacements[replacement_idx][0]:
                start, length, candidate = replacements[replacement_idx]

                # Collect all operands with '|' separators
                all_operands = []
                for j in range(length):
                    if j > 0:
                        all_operands.append("|")
                    all_operands.extend(program[start + j].operands)

                # Create the fused instruction
                fused_instr = Instruction(
                    opcode=candidate.fused_name,
                    operands=all_operands,
                    line_number=program[start].line_number,
                )
                new_idx = len(new_program)
                new_program.append(fused_instr)

                # Map old indices to new
                for j in range(length):
                    index_map[start + j] = new_idx

                old_idx = start + length
                replacement_idx += 1
            else:
                index_map[old_idx] = len(new_program)
                new_program.append(Instruction(
                    opcode=program[old_idx].opcode,
                    operands=list(program[old_idx].operands),
                    line_number=program[old_idx].line_number,
                ))
                old_idx += 1

        # Remap labels
        new_labels = {}
        for label_name, old_target in labels.items():
            if old_target in index_map:
                new_labels[label_name] = index_map[old_target]
            elif old_target >= n:
                # Label pointed past the end — map to new end
                new_labels[label_name] = len(new_program)
            else:
                # Should not happen, but keep the original
                new_labels[label_name] = old_target

        # Update jump operands with new label targets
        # (Labels are resolved by name at runtime, so we just need to update the labels dict)

        return new_program, new_labels

    def count_replacements(self, program: list[Instruction],
                           candidates: list[PatternCandidate]) -> dict[str, int]:
        """
        Count how many times each pattern could be replaced (without actually rewriting).

        Useful for estimating the impact of fusion before committing.
        """
        counts = {}
        n = len(program)

        for candidate in candidates:
            pattern = candidate.opcodes
            pattern_len = len(pattern)
            count = 0

            i = 0
            while i <= n - pattern_len:
                match = all(
                    program[i + j].opcode == pattern[j]
                    for j in range(pattern_len)
                )
                if match:
                    count += 1
                    i += pattern_len  # Non-overlapping
                else:
                    i += 1

            counts[candidate.fused_name] = count

        return counts

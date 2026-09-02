"""
Self-Evolving CPU — Instruction Profiler

Observes CPU execution and records instruction sequence patterns using a
sliding window approach. Counts how many times each sub-sequence of
instructions appears during execution.
"""

from collections import Counter, deque
from cpu import Instruction


class Profiler:
    """
    Profiles CPU execution to discover frequently occurring instruction patterns.

    Uses a sliding window of the last N executed instructions and records all
    sub-sequences of length 2..N. Tracks pattern frequency with a Counter.

    Usage:
        profiler = Profiler(window_size=5)
        cpu.profiler_callback = profiler.observe
        cpu.execute()
        hot_patterns = profiler.get_hot_patterns(min_count=1000)
    """

    def __init__(self, window_size: int = 5):
        self.window_size = window_size
        # Sliding window of recently executed instruction opcodes
        self._window: deque[str] = deque(maxlen=window_size)
        # Detailed window with full instruction info for operand analysis
        self._detail_window: deque[Instruction] = deque(maxlen=window_size)
        # Count of each opcode sub-sequence (as tuple of opcode strings)
        self.pattern_counts: Counter = Counter()
        # Total instructions observed
        self.total_observed: int = 0
        # Individual opcode counts
        self.opcode_counts: Counter = Counter()

    def observe(self, instruction: Instruction):
        """
        Called by the CPU for each executed instruction.
        Records the opcode in the sliding window and updates pattern counts.
        """
        opcode = instruction.opcode
        self._window.append(opcode)
        self._detail_window.append(instruction)
        self.opcode_counts[opcode] += 1
        self.total_observed += 1

        # Extract all sub-sequences of length 2..window_size from the window
        window_list = list(self._window)
        window_len = len(window_list)

        for seq_len in range(2, min(window_len, self.window_size) + 1):
            # Only the most recent sub-sequence of this length
            seq = tuple(window_list[window_len - seq_len:])
            self.pattern_counts[seq] += 1

    def get_hot_patterns(self, min_count: int = 1000,
                         min_length: int = 2,
                         max_length: int = None) -> list[tuple[tuple[str, ...], int]]:
        """
        Return patterns that exceed the minimum occurrence count.

        Args:
            min_count: Minimum number of occurrences.
            min_length: Minimum sequence length.
            max_length: Maximum sequence length (None = no limit).

        Returns:
            List of (pattern_tuple, count) sorted by count descending.
        """
        results = []
        for pattern, count in self.pattern_counts.items():
            if count < min_count:
                continue
            if len(pattern) < min_length:
                continue
            if max_length is not None and len(pattern) > max_length:
                continue
            results.append((pattern, count))

        # Sort by count descending, then by pattern length descending (prefer longer fusions)
        results.sort(key=lambda x: (x[1], len(x[0])), reverse=True)
        return results

    def get_top_opcodes(self, n: int = 10) -> list[tuple[str, int]]:
        """Get the N most frequently executed individual opcodes."""
        return self.opcode_counts.most_common(n)

    def get_stats(self) -> dict:
        """Get profiling statistics summary."""
        return {
            "total_observed": self.total_observed,
            "unique_patterns": len(self.pattern_counts),
            "top_opcodes": self.get_top_opcodes(),
            "window_size": self.window_size,
        }

    def reset(self):
        """Reset all profiling data."""
        self._window.clear()
        self._detail_window.clear()
        self.pattern_counts.clear()
        self.opcode_counts.clear()
        self.total_observed = 0

"""
Self-Evolving CPU — Pattern Detector

Analyzes profiler data to find the best candidates for instruction fusion.
Filters out control-flow instructions and ranks candidates by a score
that combines frequency and sequence length.
"""

# Control-flow opcodes that cannot be safely fused
CONTROL_FLOW_OPCODES = {"JUMP", "JZ", "JNZ", "HALT"}


class PatternCandidate:
    """A candidate pattern for instruction fusion."""

    def __init__(self, opcodes: tuple[str, ...], frequency: int):
        self.opcodes = opcodes
        self.frequency = frequency
        self.length = len(opcodes)
        # Score: frequency * (length - 1) — more savings for longer patterns
        # (length - 1) because fusing N instructions into 1 saves (N-1) dispatch cycles
        self.score = frequency * (self.length - 1)
        # Name for the fused instruction
        self.fused_name = "_".join(opcodes)

    def __repr__(self):
        return (
            f"PatternCandidate({self.fused_name}, "
            f"freq={self.frequency:,}, score={self.score:,})"
        )


class PatternDetector:
    """
    Analyzes profiler output to find the best fusion candidates.

    Filters:
    - No control-flow instructions in the pattern
    - Minimum occurrence threshold
    - Minimum/maximum sequence length
    - Removes sub-patterns that are fully contained in longer, higher-scoring patterns

    Ranking:
    - Score = frequency × (sequence_length - 1)
    - Returns top-K candidates
    """

    def __init__(self, min_frequency: int = 1000, min_length: int = 2,
                 max_length: int = 5, top_k: int = 10,
                 evolved_opcodes: set = None):
        self.min_frequency = min_frequency
        self.min_length = min_length
        self.max_length = max_length
        self.top_k = top_k
        # Set of opcode names that are already evolved — patterns containing
        # these are excluded to prevent nesting fused handlers
        self.evolved_opcodes = evolved_opcodes or set()

    def detect(self, hot_patterns: list[tuple[tuple[str, ...], int]]) -> list[PatternCandidate]:
        """
        Analyze hot patterns and return fusion candidates.

        Args:
            hot_patterns: Output from Profiler.get_hot_patterns()

        Returns:
            List of PatternCandidate objects, sorted by score descending.
        """
        candidates = []

        for pattern, count in hot_patterns:
            # Filter: minimum length
            if len(pattern) < self.min_length:
                continue
            # Filter: maximum length
            if len(pattern) > self.max_length:
                continue
            # Filter: minimum frequency
            if count < self.min_frequency:
                continue
            # Filter: no control-flow instructions
            if any(op in CONTROL_FLOW_OPCODES for op in pattern):
                continue
            # Filter: no already-evolved instructions (prevent nested fusions)
            if self.evolved_opcodes and any(op in self.evolved_opcodes for op in pattern):
                continue
            # Filter: skip patterns that are just the same opcode repeated
            # (these are less interesting for fusion)
            # Actually, these CAN be useful (e.g., ADD ADD ADD → ADD_CHAIN)
            # So we keep them.

            candidates.append(PatternCandidate(
                opcodes=pattern,
                frequency=count,
            ))

        # Remove sub-patterns that are fully contained in longer patterns
        candidates = self._remove_subpatterns(candidates)

        # Sort by score descending
        candidates.sort(key=lambda c: c.score, reverse=True)

        # Return top-K
        return candidates[:self.top_k]

    def _remove_subpatterns(self, candidates: list[PatternCandidate]) -> list[PatternCandidate]:
        """
        Remove candidates that are strict sub-sequences of a higher-scoring candidate.
        This prevents creating both ADD_MUL and ADD_MUL_STORE when the longer one
        is better.
        """
        if not candidates:
            return candidates

        # Sort by length descending, then score descending
        sorted_candidates = sorted(
            candidates, key=lambda c: (c.length, c.score), reverse=True
        )

        kept = []
        for candidate in sorted_candidates:
            is_subpattern = False
            for kept_candidate in kept:
                if self._is_subsequence(candidate.opcodes, kept_candidate.opcodes):
                    # Only remove if the longer pattern has a better score
                    if kept_candidate.score >= candidate.score:
                        is_subpattern = True
                        break
            if not is_subpattern:
                kept.append(candidate)

        return kept

    def _is_subsequence(self, short: tuple, long: tuple) -> bool:
        """Check if 'short' is a contiguous sub-sequence of 'long'."""
        if len(short) >= len(long):
            return False
        short_len = len(short)
        for i in range(len(long) - short_len + 1):
            if long[i:i + short_len] == short:
                return True
        return False

"""
Self-Evolving CPU — Assembler / Parser

Parses assembly text into a list of Instruction objects.
Supports labels, comments, register names, immediate values, and memory addressing.
"""

from cpu import Instruction


class AssemblerError(Exception):
    """Error during assembly parsing."""
    pass


class Assembler:
    """
    Parses assembly source text into a program (list of Instructions).

    Syntax:
        ; this is a comment
        # this is also a comment
        label:
            OPCODE operand1, operand2

    Operands:
        R0–R15      — Register reference
        42          — Immediate integer
        -7          — Negative immediate
        [R0]        — Memory address from register (not yet used, reserved)
        [100]       — Memory address immediate
        label_name  — Jump target (resolved to instruction index)
    """

    def __init__(self):
        self.program: list[Instruction] = []
        self.labels: dict[str, int] = {}

    def parse(self, source: str) -> tuple[list[Instruction], dict[str, int]]:
        """
        Parse assembly source into a program.

        Returns:
            (program, labels) where program is a list of Instructions
            and labels maps label names to instruction indices.
        """
        self.program = []
        self.labels = {}

        lines = source.strip().split("\n")
        instruction_index = 0

        # First pass: collect labels and instructions
        raw_instructions = []
        for line_num, line in enumerate(lines, start=1):
            line = self._strip_comment(line).strip()
            if not line:
                continue

            # Check for label (ends with ':')
            if line.endswith(":"):
                label_name = line[:-1].strip()
                if not label_name:
                    raise AssemblerError(f"Empty label at line {line_num}")
                if label_name in self.labels:
                    raise AssemblerError(
                        f"Duplicate label '{label_name}' at line {line_num}"
                    )
                self.labels[label_name] = instruction_index
                continue

            # Parse instruction
            opcode, operands = self._parse_instruction_line(line, line_num)
            raw_instructions.append((opcode, operands, line_num))
            instruction_index += 1

        # Second pass: resolve label references in operands
        for opcode, operands, line_num in raw_instructions:
            resolved_operands = []
            for op in operands:
                resolved_operands.append(self._resolve_operand(op))
            self.program.append(Instruction(
                opcode=opcode,
                operands=resolved_operands,
                line_number=line_num,
            ))

        return self.program, self.labels

    def _strip_comment(self, line: str) -> str:
        """Remove comments from a line (anything after ; or #)."""
        for char in (";", "#"):
            idx = line.find(char)
            if idx >= 0:
                line = line[:idx]
        return line

    def _parse_instruction_line(self, line: str, line_num: int) -> tuple[str, list]:
        """Parse a single instruction line into (opcode, operand_list)."""
        # Split on whitespace to get opcode and the rest
        parts = line.split(None, 1)
        if not parts:
            raise AssemblerError(f"Empty instruction at line {line_num}")

        opcode = parts[0].upper()

        if len(parts) == 1:
            return opcode, []

        # Parse operands (comma-separated)
        operand_str = parts[1]
        operands = [op.strip() for op in operand_str.split(",")]
        operands = [op for op in operands if op]  # Remove empty strings

        return opcode, operands

    def _resolve_operand(self, operand: str):
        """
        Resolve a single operand string into the appropriate type.

        - Register names (R0–R15) stay as strings
        - Integer literals become ints
        - Memory addresses [N] stay as strings
        - Label names stay as strings (resolved by CPU at runtime)
        """
        op = operand.strip()

        # Memory addressing [addr]
        if op.startswith("[") and op.endswith("]"):
            return op  # Keep as string, CPU handles it

        # Register
        if op.upper().startswith("R") and len(op) >= 2:
            try:
                reg_num = int(op[1:])
                if 0 <= reg_num <= 15:
                    return op.upper()
            except ValueError:
                pass

        # Integer literal
        try:
            return int(op)
        except ValueError:
            pass

        # Must be a label or unknown — keep as string
        return op


def assemble(source: str) -> tuple[list[Instruction], dict[str, int]]:
    """Convenience function to assemble source code."""
    return Assembler().parse(source)


def assemble_file(filepath: str) -> tuple[list[Instruction], dict[str, int]]:
    """Assemble from a file path."""
    with open(filepath, "r") as f:
        source = f.read()
    return assemble(source)

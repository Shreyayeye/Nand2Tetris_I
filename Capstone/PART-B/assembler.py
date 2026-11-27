#!/usr/bin/env python3
"""A two-pass assembler for the Hack assembly language.

Usage:
    python assembler.py Box.asm
    python assembler.py programs/Add.asm -o output/Add.hack
    python assembler.py Box.asm --symbols my_symbols.txt

Default behaviour:
    * The .hack file is written beside the input .asm file.
    * symbols.txt is written beside this script (the capstone folder).

The implementation follows the official Nand2Tetris Hack specification:
    A-instruction: 0vvvvvvvvvvvvvvv  (15-bit value)
    C-instruction: 111a cccccc dd jjj
"""

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Official Hack lookup tables
# ---------------------------------------------------------------------------

# Predefined symbols from the Hack language specification.
PREDEFINED_SYMBOLS: Dict[str, int] = {
    "SP": 0,
    "LCL": 1,
    "ARG": 2,
    "THIS": 3,
    "THAT": 4,
    "R0": 0,
    "R1": 1,
    "R2": 2,
    "R3": 3,
    "R4": 4,
    "R5": 5,
    "R6": 6,
    "R7": 7,
    "R8": 8,
    "R9": 9,
    "R10": 10,
    "R11": 11,
    "R12": 12,
    "R13": 13,
    "R14": 14,
    "R15": 15,
    "SCREEN": 16384,
    "KBD": 24576,
}

# Each value already contains the 7-bit pattern "a c1 c2 c3 c4 c5 c6".
COMP_TABLE: Dict[str, str] = {
    # a = 0: use the A register.
    "0": "0101010",
    "1": "0111111",
    "-1": "0111010",
    "D": "0001100",
    "A": "0110000",
    "!D": "0001101",
    "!A": "0110001",
    "-D": "0001111",
    "-A": "0110011",
    "D+1": "0011111",
    "A+1": "0110111",
    "D-1": "0001110",
    "A-1": "0110010",
    "D+A": "0000010",
    "D-A": "0010011",
    "A-D": "0000111",
    "D&A": "0000000",
    "D|A": "0010101",
    # a = 1: use M (Memory[A]).
    "M": "1110000",
    "!M": "1110001",
    "-M": "1110011",
    "M+1": "1110111",
    "M-1": "1110010",
    "D+M": "1000010",
    "D-M": "1010011",
    "M-D": "1000111",
    "D&M": "1000000",
    "D|M": "1010101",
}

DEST_TABLE: Dict[str, str] = {
    "": "000",
    "M": "001",
    "D": "010",
    "MD": "011",
    "A": "100",
    "AM": "101",
    "AD": "110",
    "AMD": "111",
}

JUMP_TABLE: Dict[str, str] = {
    "": "000",
    "JGT": "001",
    "JEQ": "010",
    "JGE": "011",
    "JLT": "100",
    "JNE": "101",
    "JLE": "110",
    "JMP": "111",
}

# Hack symbols may contain letters, digits, _, ., $ and :, but not start
# with a digit.  This matches the official assembler's symbol rules.
SYMBOL_RE = re.compile(r"^[A-Za-z_$.:][A-Za-z0-9_$.:]*$")
DECIMAL_RE = re.compile(r"^[0-9]+$")
C_CHAR_RE = re.compile(r"^[A-Z0-9!+\-&|;=]+$")

MAX_A_VALUE = 32767  # A-instruction values are 15 bits.


class AssemblerError(Exception):
    """A user-friendly assembly error, optionally tied to a source line."""

    def __init__(self, message: str, line: Optional[int] = None) -> None:
        self.message = message
        self.line = line
        super().__init__(self.format_message())

    def format_message(self) -> str:
        """Return the message shown to the user."""
        if self.line is None:
            return self.message
        return "line {}: {}".format(self.line, self.message)


# ---------------------------------------------------------------------------
# Pass 1: cleaning and symbol discovery
# ---------------------------------------------------------------------------


def clean_source(input_path: Path) -> List[Tuple[int, str]]:
    """Read an .asm file and return (source_line_number, instruction) pairs.

    Comments starting with // are removed, blank lines are skipped, and
    leading/trailing whitespace is stripped.  Original line numbers are kept
    so errors can point at the real source line.
    """
    try:
        text = input_path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as exc:
        raise AssemblerError(
            "input file is not valid UTF-8 text: {}".format(exc)
        ) from None
    except OSError as exc:
        raise AssemblerError("cannot read {}: {}".format(input_path, exc)) from None

    cleaned: List[Tuple[int, str]] = []
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.split("//", 1)[0].strip()
        if line:
            cleaned.append((line_number, line))
    return cleaned


def validate_symbol(name: str, line_number: int, kind: str) -> None:
    """Validate a label or variable name."""
    if not SYMBOL_RE.match(name):
        raise AssemblerError(
            "invalid {} name '{}'. Symbols may contain letters, digits, _, "
            "., $ and : and cannot start with a digit.".format(kind, name),
            line_number,
        )


def first_pass(
    instructions: List[Tuple[int, str]]
) -> Tuple[Dict[str, int], Dict[str, int]]:
    """Find every label and return (symbol_table, labels).

    Label declarations do not generate machine code, so they do not advance
    the ROM address.  Variables are allocated later, during pass 2.
    """
    symbol_table = dict(PREDEFINED_SYMBOLS)
    labels: Dict[str, int] = {}
    rom_address = 0

    for line_number, text in instructions:
        if text.startswith("("):
            if not text.endswith(")") or len(text) < 3:
                raise AssemblerError(
                    "malformed label '{}'. Use (LABEL_NAME).".format(text),
                    line_number,
                )
            name = text[1:-1]
            validate_symbol(name, line_number, "label")
            if name in symbol_table:
                raise AssemblerError(
                    "symbol '{}' is defined more than once.".format(name),
                    line_number,
                )
            symbol_table[name] = rom_address
            labels[name] = rom_address
        else:
            # Both A- and C-instructions occupy exactly one ROM word.
            rom_address += 1

    if rom_address > 32768:
        raise AssemblerError(
            "program has {} instructions; Hack ROM holds at most 32768.".format(
                rom_address
            )
        )

    return symbol_table, labels


# ---------------------------------------------------------------------------
# Pass 2: machine-code generation
# ---------------------------------------------------------------------------


def assemble_a_instruction(
    text: str,
    line_number: int,
    symbol_table: Dict[str, int],
    variables: Dict[str, int],
) -> str:
    """Translate @value into a 16-bit A-instruction."""
    value_text = text[1:].strip()
    if not value_text:
        raise AssemblerError("A-instruction is missing a value.", line_number)

    if DECIMAL_RE.match(value_text):
        value = int(value_text, 10)
        if value > MAX_A_VALUE:
            raise AssemblerError(
                "A-instruction value {} is too large; maximum is {}.".format(
                    value, MAX_A_VALUE
                ),
                line_number,
            )
    else:
        validate_symbol(value_text, line_number, "symbol")
        if value_text not in symbol_table:
            # New variable: allocate the next free RAM address, starting at 16.
            address = 16 + len(variables)
            symbol_table[value_text] = address
            variables[value_text] = address
        value = symbol_table[value_text]

    return format(value, "016b")


def encode_dest(dest_name: str, line_number: int, text: str) -> str:
    """Encode the dest field in any order (the official assembler allows it).

    The official Pong.asm contains ``DM=M+1`` even though the textbook table
    spells the same destination ``MD``.  Therefore the destination is treated
    as an unordered set of the letters A, D and M, with no duplicates.
    """
    if (
        any(character not in "ADM" for character in dest_name)
        or len(set(dest_name)) != len(dest_name)
    ):
        raise AssemblerError(
            "invalid destination '{}' in '{}'. Valid destinations: {}.".format(
                dest_name,
                text,
                ", ".join(key for key in DEST_TABLE if key),
            ),
            line_number,
        )
    return (
        ("1" if "A" in dest_name else "0")
        + ("1" if "D" in dest_name else "0")
        + ("1" if "M" in dest_name else "0")
    )


def assemble_c_instruction(text: str, line_number: int) -> str:
    """Translate dest=comp;jump into a 16-bit C-instruction."""
    if any(character.isspace() for character in text):
        raise AssemblerError(
            "unexpected whitespace in C-instruction '{}'; Hack instructions "
            "cannot contain spaces.".format(text),
            line_number,
        )
    if not C_CHAR_RE.match(text):
        raise AssemblerError(
            "invalid character in C-instruction '{}'.".format(text), line_number
        )
    if text.count(";") > 1:
        raise AssemblerError(
            "too many ';' characters in C-instruction '{}'.".format(text),
            line_number,
        )
    if text.count("=") > 1:
        raise AssemblerError(
            "too many '=' characters in C-instruction '{}'.".format(text),
            line_number,
        )

    if ";" in text:
        left_side, jump_name = text.split(";", 1)
        if not jump_name:
            raise AssemblerError("empty jump field in '{}'.".format(text), line_number)
    else:
        left_side, jump_name = text, ""

    if "=" in left_side:
        dest_name, comp_name = left_side.split("=", 1)
        if not dest_name:
            raise AssemblerError("empty destination field in '{}'.".format(text), line_number)
        if not comp_name:
            raise AssemblerError("empty computation field in '{}'.".format(text), line_number)
    else:
        dest_name, comp_name = "", left_side

    if comp_name not in COMP_TABLE:
        raise AssemblerError(
            "invalid computation '{}'. Valid computations: {}.".format(
                comp_name, ", ".join(sorted(COMP_TABLE))
            ),
            line_number,
        )
    dest_bits = encode_dest(dest_name, line_number, text)
    if jump_name not in JUMP_TABLE:
        raise AssemblerError(
            "invalid jump '{}'. Valid jumps: {}.".format(
                jump_name, ", ".join(key for key in JUMP_TABLE if key)
            ),
            line_number,
        )

    return (
        "111"
        + COMP_TABLE[comp_name]
        + dest_bits
        + JUMP_TABLE[jump_name]
    )


def second_pass(
    instructions: List[Tuple[int, str]], symbol_table: Dict[str, int]
) -> Tuple[List[str], Dict[str, int]]:
    """Generate machine code and discover variables.

    Returns (machine_code, variables).  symbol_table is extended in place
    when new variables are found.
    """
    machine_code: List[str] = []
    variables: Dict[str, int] = {}

    for line_number, text in instructions:
        if text.startswith("("):
            continue  # Labels produce no machine code.
        if text.startswith("@"):
            machine_code.append(
                assemble_a_instruction(text, line_number, symbol_table, variables)
            )
        else:
            machine_code.append(assemble_c_instruction(text, line_number))

    for binary in machine_code:
        if len(binary) != 16 or any(bit not in "01" for bit in binary):
            raise AssemblerError("internal error: invalid machine word '{}'.".format(binary))

    return machine_code, variables


# ---------------------------------------------------------------------------
# Output files
# ---------------------------------------------------------------------------


def write_hack_file(output_path: Path, machine_code: List[str]) -> None:
    """Write one 16-bit binary word per line."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with output_path.open("w", encoding="utf-8", newline="\n") as output_file:
            for binary in machine_code:
                output_file.write(binary + "\n")
    except OSError as exc:
        raise AssemblerError("cannot write {}: {}".format(output_path, exc)) from None


def write_symbols_file(
    symbols_path: Path,
    program_name: str,
    labels: Dict[str, int],
    variables: Dict[str, int],
) -> None:
    """Write a readable symbol report with labels and variables separated.

    This is the personalised feature required for K = 87 (K mod 3 = 0).
    """
    symbols_path.parent.mkdir(parents=True, exist_ok=True)

    label_lines = [
        "{} -> {}".format(name, address)
        for name, address in sorted(labels.items(), key=lambda item: (item[1], item[0]))
    ]
    variable_lines = [
        "{} -> {}".format(name, address)
        for name, address in sorted(variables.items(), key=lambda item: (item[1], item[0]))
    ]
    predefined_lines = [
        "{} -> {}".format(name, address)
        for name, address in PREDEFINED_SYMBOLS.items()
    ]

    report = [
        "SYMBOL TABLE",
        "============",
        "",
        "Program: {}".format(program_name),
        "Generated by: assembler.py",
        "Labels do not occupy ROM addresses; variables start at RAM address 16.",
        "",
        "Labels:",
    ]
    report.extend(label_lines if label_lines else ["  (none)"])
    report.extend(["", "Variables:"])
    report.extend(variable_lines if variable_lines else ["  (none)"])
    report.extend(
        [
            "",
            "Predefined symbols (reference):",
        ]
    )
    # Keep the predefined list readable by placing four entries per line.
    for start in range(0, len(predefined_lines), 4):
        report.append("  " + " | ".join(predefined_lines[start : start + 4]))
    report.append("")

    try:
        with symbols_path.open("w", encoding="utf-8", newline="\n") as symbol_file:
            symbol_file.write("\n".join(report))
    except OSError as exc:
        raise AssemblerError("cannot write {}: {}".format(symbols_path, exc)) from None


# ---------------------------------------------------------------------------
# Public API and command line interface
# ---------------------------------------------------------------------------


def assemble(
    input_path: Path, output_path: Path, symbols_path: Path
) -> Dict[str, object]:
    """Assemble one program and return a small statistics dictionary."""
    instructions = clean_source(input_path)
    symbol_table, labels = first_pass(instructions)
    machine_code, variables = second_pass(instructions, symbol_table)

    write_hack_file(output_path, machine_code)
    write_symbols_file(symbols_path, input_path.name, labels, variables)

    return {
        "instructions": len(machine_code),
        "labels": len(labels),
        "variables": len(variables),
    }


def build_argument_parser() -> argparse.ArgumentParser:
    """Create the command-line parser."""
    parser = argparse.ArgumentParser(
        description="Assemble a Hack .asm program into a 16-bit .hack file."
    )
    parser.add_argument("input", help="path to the source .asm file")
    parser.add_argument(
        "-o",
        "--output",
        help="output .hack path (default: beside the input file, with .hack suffix)",
    )
    parser.add_argument(
        "-s",
        "--symbols",
        help="symbol report path (default: symbols.txt beside assembler.py)",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """Command-line entry point. Returns a process exit code."""
    args = build_argument_parser().parse_args(argv)
    input_path = Path(args.input)

    if not input_path.is_file():
        print("error: input file not found: {}".format(input_path), file=sys.stderr)
        return 1

    output_path = (
        Path(args.output) if args.output else input_path.with_suffix(".hack")
    )
    symbols_path = (
        Path(args.symbols)
        if args.symbols
        else Path(__file__).resolve().parent / "symbols.txt"
    )

    try:
        stats = assemble(input_path, output_path, symbols_path)
    except AssemblerError as exc:
        print("error: {}".format(exc), file=sys.stderr)
        return 1
    except OSError as exc:
        print("error: {}".format(exc), file=sys.stderr)
        return 1

    print(
        "Assembled {} -> {} ({} instructions, {} labels, {} variables)".format(
            input_path,
            output_path,
            stats["instructions"],
            stats["labels"],
            stats["variables"],
        )
    )
    print("Symbol table written to {}".format(symbols_path))
    return 0


if __name__ == "__main__":
    sys.exit(main())

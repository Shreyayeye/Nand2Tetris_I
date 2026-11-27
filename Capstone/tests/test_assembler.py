"""Unit tests for assembler.py.

Run from the capstone folder with:

    python -m unittest discover -s tests -v
"""

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
# The assembler lives in PART-C in the organised repository layout; older
# flat copies keep it beside the tests folder's parent.
sys.path.insert(0, str(ROOT / "PART-C"))

import assembler  # noqa: E402  (import after sys.path adjustment)


class AssemblerTestCase(unittest.TestCase):
    """Shared helpers for assembler tests."""

    def assemble_text(self, source, output_name="prog.hack", symbols_name="symbols.txt"):
        """Assemble source text in a temporary folder and return output text."""
        temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_directory.cleanup)
        folder = Path(temporary_directory.name)
        source_path = folder / "prog.asm"
        output_path = folder / output_name
        symbols_path = folder / symbols_name
        source_path.write_text(source, encoding="utf-8")
        assembler.assemble(source_path, output_path, symbols_path)
        return output_path.read_text(encoding="utf-8"), symbols_path.read_text(
            encoding="utf-8"
        )


class TestEncoding(AssemblerTestCase):
    """Verify the official Hack encoding tables."""

    def test_add_program_known_encoding(self):
        output, _ = self.assemble_text("@2\nD=A\n@3\nD=D+A\n@0\nM=D\n")
        self.assertEqual(
            output,
            "0000000000000010\n"
            "1110110000010000\n"
            "0000000000000011\n"
            "1110000010010000\n"
            "0000000000000000\n"
            "1110001100001000\n",
        )

    def test_every_comp_mnemonic_is_16_bits(self):
        for mnemonic, bits in assembler.COMP_TABLE.items():
            with self.subTest(comp=mnemonic):
                output, _ = self.assemble_text("{}\n".format(mnemonic))
                word = output.strip()
                self.assertEqual(len(word), 16)
                self.assertTrue(word.startswith("111"))
                self.assertEqual(word[3:10], bits)
                self.assertEqual(word[10:], "000000")

    def test_destination_order_is_accepted(self):
        """Official Pong.asm contains DM=M+1 as well as MD=M+1."""
        reordered, _ = self.assemble_text("DM=M+1\n")
        canonical, _ = self.assemble_text("MD=M+1\n")
        self.assertEqual(reordered, canonical)

    def test_a_instruction_limits(self):
        output, _ = self.assemble_text("@0\n@32767\n")
        self.assertEqual(output, "0000000000000000\n0111111111111111\n")

    def test_predefined_symbols(self):
        output, _ = self.assemble_text("@SP\n@R15\n@SCREEN\n@KBD\n")
        self.assertEqual(
            output,
            "0000000000000000\n"
            "0000000000001111\n"
            "0100000000000000\n"
            "0110000000000000\n",
        )


class TestErrors(AssemblerTestCase):
    """Verify that bad input gives clear errors with source line numbers."""

    def assert_error_contains(self, source, expected):
        with self.assertRaises(assembler.AssemblerError) as context:
            self.assemble_text(source)
        message = str(context.exception)
        self.assertIn(expected, message)
        self.assertIn("line", message)

    def test_empty_a_instruction(self):
        self.assert_error_contains("@\n", "line 1")

    def test_out_of_range_a_instruction(self):
        self.assert_error_contains("@32768\n", "line 1")

    def test_invalid_a_symbol(self):
        self.assert_error_contains("@bad-name\n", "line 1")

    def test_malformed_label(self):
        self.assert_error_contains("(LOOP\nD=A\n", "line 1")

    def test_invalid_label_name(self):
        self.assert_error_contains("(BAD LABEL)\n", "line 1")

    def test_duplicate_label(self):
        self.assert_error_contains("(LOOP)\n(LOOP)\n", "line 2")

    def test_whitespace_inside_c_instruction(self):
        self.assert_error_contains("D = A\n", "line 1")

    def test_invalid_comp(self):
        self.assert_error_contains("D=A+B\n", "line 1")

    def test_invalid_dest(self):
        self.assert_error_contains("X=A\n", "line 1")

    def test_invalid_jump(self):
        self.assert_error_contains("D;JXX\n", "line 1")

    def test_empty_fields(self):
        self.assert_error_contains("D=\n", "line 1")

    def test_line_number_after_comments(self):
        self.assert_error_contains("// comment\n\nD;JMP;\n", "line 3")


class TestSymbolsFile(AssemblerTestCase):
    """Verify labels, variables and the personalised symbols.txt report."""

    def test_labels_and_variables_are_grouped(self):
        source = (
            "@i\n"
            "M=1\n"
            "(LOOP)\n"
            "@i\n"
            "M=M-1\n"
            "D=M\n"
            "@LOOP\n"
            "D;JGT\n"
        )
        _, report = self.assemble_text(source)
        self.assertIn("SYMBOL TABLE", report)
        self.assertIn("Labels:", report)
        self.assertIn("Variables:", report)
        self.assertIn("LOOP -> 2", report)
        self.assertIn("i -> 16", report)


class TestOfficialPrograms(AssemblerTestCase):
    """Compare symbolic programs with their official symbol-less versions."""

    def compare_with_symbol_less(self, symbolic_name, symbol_less_name):
        programs_dir = ROOT / "programs"
        if not programs_dir.is_dir():
            programs_dir = ROOT / "PART-B"
        symbolic_path = programs_dir / symbolic_name
        symbol_less_path = ROOT / "tests" / "reference" / symbol_less_name
        if not symbolic_path.is_file() or not symbol_less_path.is_file():
            self.skipTest("official comparison files are not available")

        with tempfile.TemporaryDirectory() as temporary_directory:
            folder = Path(temporary_directory)
            symbolic_output = folder / "symbolic.hack"
            symbol_less_output = folder / "symbol_less.hack"
            dummy_symbols = folder / "symbols.txt"

            assembler.assemble(symbolic_path, symbolic_output, dummy_symbols)
            assembler.assemble(symbol_less_path, symbol_less_output, dummy_symbols)

            first = symbolic_output.read_text(encoding="utf-8")
            second = symbol_less_output.read_text(encoding="utf-8")
            self.assertEqual(first, second)

    def test_max_matches_official_symbol_less_version(self):
        self.compare_with_symbol_less("Max.asm", "MaxL.asm")

    def test_rect_matches_official_symbol_less_version(self):
        self.compare_with_symbol_less("Rect.asm", "RectL.asm")

    def test_pong_matches_official_symbol_less_version(self):
        self.compare_with_symbol_less("Pong.asm", "PongL.asm")


if __name__ == "__main__":
    unittest.main()

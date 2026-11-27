"""Lightweight static checks for the HDL and generated machine code.

These checks do NOT replace the official Nand2Tetris Hardware Simulator.
They only catch common structural mistakes (missing chip name, unbalanced
braces, missing parts) when the simulator is not installed.

Run from the capstone folder with:

    python -m unittest discover -s tests -v
"""

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SCREEN = 16384
START_ROW = 87
START_ADDRESS = 19168
HEIGHT = 20
WORDS_PER_ROW = 4


class TestHDLFiles(unittest.TestCase):
    """Check the structure of the three required chip files."""

    def read_hdl(self, filename):
        path = ROOT / filename
        if not path.is_file():
            path = ROOT / "PART-A" / filename
        self.assertTrue(path.is_file(), "{} is missing".format(filename))
        return path.read_text(encoding="utf-8")

    def assert_valid_structure(self, filename, chip_name, required_parts):
        text = self.read_hdl(filename)
        self.assertIn("CHIP {} {{".format(chip_name), text)
        self.assertEqual(text.count("{"), text.count("}"), "unbalanced braces")
        self.assertIn("IN", text)
        self.assertIn("OUT", text)
        self.assertIn("PARTS:", text)
        for part in required_parts:
            self.assertIn(part, text, "{} is missing from {}".format(part, filename))

    def test_cpu_structure(self):
        self.assert_valid_structure(
            "CPU.hdl",
            "CPU",
            ["ARegister", "DRegister", "ALU", "PC", "Mux16", "instruction[15]"],
        )

    def test_memory_structure(self):
        self.assert_valid_structure(
            "Memory.hdl",
            "Memory",
            ["RAM16K", "Screen", "Keyboard", "DMux4Way", "Mux4Way16", "address[13..14]"],
        )

    def test_computer_structure(self):
        self.assert_valid_structure(
            "Computer.hdl", "Computer", ["ROM32K", "CPU(", "Memory(", "pc"]
        )


class TestPersonalisedCalculations(unittest.TestCase):
    """Verify the numbers used by Box.asm."""

    def test_k_calculations(self):
        k = 87
        self.assertEqual(k % 3, 0)
        self.assertEqual(k % 4, 3)

    def test_start_address(self):
        self.assertEqual(SCREEN + 32 * START_ROW, START_ADDRESS)

    def test_box_dimensions(self):
        self.assertEqual(HEIGHT, 20)
        self.assertEqual(WORDS_PER_ROW, 4)
        self.assertEqual(HEIGHT * WORDS_PER_ROW, 80)

    def test_last_address_inside_screen(self):
        last_row = START_ROW + HEIGHT - 1
        last_address = SCREEN + 32 * last_row + (WORDS_PER_ROW - 1)
        self.assertEqual(last_address, 19779)
        self.assertLess(last_address, SCREEN + 8192)

    def test_box_asm_uses_constants(self):
        source_path = ROOT / "Box.asm"
        if not source_path.is_file():
            source_path = ROOT / "PART-C" / "Box.asm"
        source = source_path.read_text(encoding="utf-8")
        for token in ("@19168", "@20", "@4", "@32", "@KBD", "(DRAW_WORD)", "(CLEAR_WORD)"):
            self.assertIn(token, source)


class TestMachineCodeWidth(unittest.TestCase):
    """Every generated .hack line must be exactly 16 binary digits."""

    def test_all_hack_files(self):
        box_hack = ROOT / "Box.hack"
        if not box_hack.is_file():
            box_hack = ROOT / "PART-C" / "Box.hack"
        paths = [box_hack] + sorted((ROOT / "output").glob("*.hack"))
        self.assertEqual(len(paths), 5, "expected Box.hack and four output files")
        for path in paths:
            with self.subTest(path=path.name):
                lines = [
                    line.strip()
                    for line in path.read_text(encoding="utf-8").splitlines()
                    if line.strip()
                ]
                self.assertTrue(lines, "{} is empty".format(path.name))
                for line in lines:
                    self.assertEqual(len(line), 16)
                    self.assertTrue(set(line).issubset({"0", "1"}))


if __name__ == "__main__":
    unittest.main()

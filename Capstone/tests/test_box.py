"""Functional test for Box.hack using a small reference Hack interpreter.

This is NOT the official Nand2Tetris CPU Emulator.  It is an independent
Python model of the Hack instruction set, used here to verify that Box.hack
writes exactly the intended 20 x 4 screen words and nothing else.

Run from the capstone folder with:

    python -m unittest discover -s tests -v
"""

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Box.hack is generated inside PART-C in the organised repository layout.
BOX_HACK = ROOT / "PART-C" / "Box.hack"
if not BOX_HACK.is_file():
    BOX_HACK = ROOT / "Box.hack"

SCREEN = 16384
SCREEN_END = 24575
KBD = 24576

START_ROW = 87
HEIGHT = 20
WORDS_PER_ROW = 4


class HackVM:
    """A minimal, faithful interpreter for 16-bit Hack machine code."""

    def __init__(self, rom):
        self.rom = rom
        self.ram = [0] * (KBD + 1)
        self.a = 0
        self.d = 0
        self.pc = 0
        self.keyboard = 0
        self.writes = []  # (address, value) pairs for screen writes

    @staticmethod
    def alu(x, y, zx, nx, zy, ny, f, no):
        """Implement the Hack ALU truth table."""
        if zx:
            x = 0
        if nx:
            x = (~x) & 0xFFFF
        if zy:
            y = 0
        if ny:
            y = (~y) & 0xFFFF
        if f:
            result = (x + y) & 0xFFFF
        else:
            result = x & y
        if no:
            result = (~result) & 0xFFFF

        zero = result == 0
        negative = bool(result & 0x8000)
        return result, zero, negative

    def step(self):
        """Execute one instruction."""
        if self.pc >= len(self.rom):
            raise RuntimeError("program counter ran past the end of ROM")

        instruction = self.rom[self.pc]

        if not instruction & 0x8000:
            # A-instruction: 0vvvvvvvvvvvvvvv
            self.a = instruction & 0x7FFF
            self.pc += 1
            return

        # C-instruction: 111a cccccc dd jjj
        a_bit = (instruction >> 12) & 1
        zx = (instruction >> 11) & 1
        nx = (instruction >> 10) & 1
        zy = (instruction >> 9) & 1
        ny = (instruction >> 8) & 1
        f = (instruction >> 7) & 1
        no = (instruction >> 6) & 1
        dest_bits = (instruction >> 3) & 0x7
        j1 = (instruction >> 2) & 1
        j2 = (instruction >> 1) & 1
        j3 = instruction & 1

        old_a = self.a
        y = self.ram[old_a] if a_bit else old_a
        if a_bit and old_a == KBD:
            y = self.keyboard

        result, zero, negative = self.alu(self.d, y, zx, nx, zy, ny, f, no)

        # In the real CPU, M is addressed by the OLD value of A, while a
        # destination that includes A updates A for the following instruction.
        if dest_bits & 0x4:
            self.a = result
        if dest_bits & 0x2:
            self.d = result
        if dest_bits & 0x1:
            self.ram[old_a] = result
            if SCREEN <= old_a <= SCREEN_END:
                self.writes.append((old_a, result))

        jump = (
            (j1 and negative)
            or (j2 and zero)
            or (j3 and not negative and not zero)
        )
        self.pc = self.a if jump else self.pc + 1


def load_rom(path):
    """Read a .hack file into a list of 16-bit integers."""
    words = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        if len(line) != 16 or any(bit not in "01" for bit in line):
            raise AssertionError("invalid machine word on line {}".format(line_number))
        words.append(int(line, 2))
    return words


def expected_box_addresses():
    """The exact 80 screen words that belong to the personalised box."""
    return {
        SCREEN + 32 * (START_ROW + row) + column
        for row in range(HEIGHT)
        for column in range(WORDS_PER_ROW)
    }


class TestBoxHack(unittest.TestCase):
    """Check keyboard behaviour and the drawn/cleared screen region."""

    def setUp(self):
        self.assertTrue(BOX_HACK.is_file(), "Box.hack has not been generated")
        self.rom = load_rom(BOX_HACK)
        self.expected = expected_box_addresses()

    @staticmethod
    def run_steps(vm, keyboard_value, steps):
        vm.keyboard = keyboard_value
        for _ in range(steps):
            vm.step()

    def test_idle_keyboard_does_not_write(self):
        vm = HackVM(self.rom)
        self.run_steps(vm, 0, 2000)
        self.assertEqual(vm.writes, [], "no key should leave the screen untouched")

    def test_press_draws_exact_box_and_release_clears_it(self):
        vm = HackVM(self.rom)

        # Settle with the key released.
        self.run_steps(vm, 0, 500)
        self.assertEqual(vm.writes, [])

        # Press a key.  Any non-zero value is treated as "pressed".
        self.run_steps(vm, 65, 3000)
        drawn = dict(vm.writes)
        self.assertEqual(
            set(drawn), self.expected, "draw must cover exactly the 80 box words"
        )
        self.assertTrue(
            all(value == 0xFFFF for value in drawn.values()),
            "every drawn word must be black (0xFFFF)",
        )

        # Release the key.  The same words must be cleared, with no extra writes.
        vm.writes = []
        self.run_steps(vm, 0, 3000)
        cleared = dict(vm.writes)
        self.assertEqual(
            set(cleared), self.expected, "clear must cover exactly the 80 box words"
        )
        self.assertTrue(
            all(value == 0 for value in cleared.values()),
            "every cleared word must be white (0)",
        )

        # Press again to confirm the program keeps responding after a clear.
        vm.writes = []
        self.run_steps(vm, 1, 3000)
        redrawn = dict(vm.writes)
        self.assertEqual(set(redrawn), self.expected)
        self.assertTrue(all(value == 0xFFFF for value in redrawn.values()))

    def test_box_stays_inside_screen_memory(self):
        vm = HackVM(self.rom)
        self.run_steps(vm, 65, 3000)
        for address, _ in vm.writes:
            self.assertTrue(SCREEN <= address <= SCREEN_END)
            self.assertIn(address, self.expected)


if __name__ == "__main__":
    unittest.main()

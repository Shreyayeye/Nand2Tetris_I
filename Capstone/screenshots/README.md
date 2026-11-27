# Screenshot inventory

The following genuine screenshots are included in this folder. Each was captured from the Nand2Tetris Web IDE, a terminal/editor, or the CPU Emulator; none were drawn or fabricated.

| File | What it shows |
|---|---|
| `01_cpu_test_passed.png` | Hardware Simulator running `CPU.tst`; message: *Simulation successful: The output file is identical to the compare file* |
| `02_memory_test_passed.png` | Hardware Simulator running `Memory.tst`; same success message |
| `03_computer_add_test_passed.png` | Hardware Simulator running `ComputerAdd.tst`; 17 steps; same success message |
| `04_computer_max_test_passed.png` | Hardware Simulator running `ComputerMax.tst`; 30 steps; same success message |
| `05_computer_rect_test_passed.png` | Hardware Simulator running `ComputerRect.tst`; 69 steps; same success message |
| `06_assembler_execution.png` | Terminal: initial wrong-directory error, then `cd PART-C` and `python assembler.py Box.asm` (99 instructions, 7 labels, 6 variables) |
| `07_symbols_txt.png` | Generated `symbols.txt` with separate Labels and Variables sections |
| `09_box_released.png` | CPU Emulator with `Box.hack` loaded after key release (box area cleared) |

The report `Capstone_Report.pdf` references the included images as S1–S7 and S9. The pressed-state emulator view is intentionally omitted; key-press behaviour is evidenced by the Python reference interpreter in `tests/test_box.py` instead.

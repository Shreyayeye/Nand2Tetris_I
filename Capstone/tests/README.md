# Testing

## 1. Automated Python tests (actually run)

From the `Capstone` folder:

```powershell
python -m unittest discover -s tests -v
```

Current result: **33 tests passed** (`OK`).

| Test file | What it checks | Result |
|---|---|---|
| `test_assembler.py` | Official comp/dest/jump encoding, A-instruction limits, predefined symbols, line-numbered errors, `symbols.txt` grouping, comparison with official symbol-less programs | Passed |
| `test_box.py` | Runs `Box.hack` in a small Python reference Hack interpreter; no writes while idle, exactly 80 black words on press, exactly 80 white words on release, no writes outside the box | Passed |
| `test_hdl_static.py` | HDL structure, personalised address calculations, 16-bit width of every generated `.hack` file | Passed |

The test scripts now locate sources in the organised `PART-A`, `PART-B` and `PART-C` folders (and still support an older flat layout). During report preparation, the missing generated files `output/Add.hack`, `output/Max.hack`, `output/Rect.hack` and `output/Pong.hack` were produced with `assembler.py`; the suite then passed 33/33.

The official assembler executable was not available, so a direct comparison against it was not performed. Instead, symbolic `Max.asm`, `Rect.asm` and `Pong.asm` were assembled and compared byte-for-byte with the official symbol-less `*L.asm` files in `tests/reference/`; all three comparisons passed.

## 2. Official HDL tests (actually run in the Nand2Tetris Web IDE)

The scripts in `tests/official-hdl-tests/` were executed in the Nand2Tetris Web IDE Hardware Simulator. Each ended with *Simulation successful: The output file is identical to the compare file*:

| Script | Evidence |
|---|---|
| `CPU.tst` | `screenshots/01_cpu_test_passed.png` |
| `Memory.tst` | `screenshots/02_memory_test_passed.png` |
| `ComputerAdd.tst` | `screenshots/03_computer_add_test_passed.png` |
| `ComputerMax.tst` | `screenshots/04_computer_max_test_passed.png` |
| `ComputerRect.tst` | `screenshots/05_computer_rect_test_passed.png` |

To repeat manually: install the tools from <https://www.nand2tetris.org/software>, copy `CPU.hdl`, `Memory.hdl` and `Computer.hdl` from `PART-A/` beside the `.tst` files, then run each script in the Hardware Simulator.

## 3. Box.hack verification

`Box.hack` was checked with the Python reference interpreter in `test_box.py` and loaded in the Nand2Tetris CPU Emulator (`screenshots/09_box_released.png` shows the cleared state). Key-press drawing is verified by the interpreter tests; an emulator screenshot of the pressed state is not included in this submission.

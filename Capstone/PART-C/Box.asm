// Box.asm
// Roll Number: 2501010187
// Personal number K = 87; K mod 3 = 0, K mod 4 = 3.
//
// Draws a black rectangle while any keyboard key is held down and clears
// the same rectangle when the key is released.
//
// Personalised box geometry:
//   SCREEN          = 16384
//   start row       = 87
//   start address   = SCREEN + 32 * 87 = 19168
//   height          = 20 rows (87 .. 106)
//   width           = 64 pixels = 4 screen words per row
//   colour          = 0xFFFF (black) when pressed, 0x0000 (white) when released
//
// A screen row is 32 words apart, so the program uses two nested loops:
//   outer loop: 20 rows, advancing the row address by 32
//   inner loop: 4 words, advancing the word address by 1

// state = 0 means "box is currently cleared"; state = 1 means "box is drawn".
@0
D=A
@state
M=D

(KEY_CHECK)
// Read the keyboard and normalise any non-zero key code to 1.
@KBD
D=M
@KEY_RELEASED
D;JEQ            // if key == 0, D is already 0
D=1              // any pressed key becomes logical 1
(KEY_RELEASED)
@key
M=D

// If the logical key state has not changed, keep polling the keyboard.
@key
D=M
@state
D=D-M            // D = key - state
@KEY_CHECK
D;JEQ            // no change -> nothing to draw or clear

// Remember the new state before redrawing.
@key
D=M
@state
M=D

@state
D=M
@CLEAR_BOX
D;JEQ            // state == 0 -> clear the box

// ------------------------------------------------------------------
// DRAW: 20 rows x 4 words, starting at screen address 19168
// ------------------------------------------------------------------
@19168
D=A
@row
M=D

@20
D=A
@rowCount
M=D

(DRAW_ROW)
@row
D=M
@word
M=D              // word = first screen address of this row

@4
D=A
@wordCount
M=D

(DRAW_WORD)
@word
A=M              // A = screen word address
M=-1             // write 0xFFFF (all 16 pixels black)
@word
M=M+1            // next word in the same row
@wordCount
M=M-1
D=M
@DRAW_WORD
D;JGT

@32
D=A
@row
M=D+M            // move to the same column in the next screen row
@rowCount
M=M-1
D=M
@DRAW_ROW
D;JGT

@KEY_CHECK
0;JMP

// ------------------------------------------------------------------
// CLEAR: same 80 screen words, writing 0x0000 (white)
// ------------------------------------------------------------------
(CLEAR_BOX)
@19168
D=A
@row
M=D

@20
D=A
@rowCount
M=D

(CLEAR_ROW)
@row
D=M
@word
M=D              // word = first screen address of this row

@4
D=A
@wordCount
M=D

(CLEAR_WORD)
@word
A=M              // A = screen word address
M=0              // write 0x0000 (all 16 pixels white)
@word
M=M+1
@wordCount
M=M-1
D=M
@CLEAR_WORD
D;JGT

@32
D=A
@row
M=D+M            // move to the same column in the next screen row
@rowCount
M=M-1
D=M
@CLEAR_ROW
D;JGT

@KEY_CHECK
0;JMP

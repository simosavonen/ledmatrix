import random
from datetime import datetime

from ..canvas import Canvas
from .base import Mode

"""AI-played Tetris: the board takes up the right half of the screen, score
and the next piece live on the left. The AI picks a target rotation/column
for each piece using a simple board-quality heuristic, then - like a real
player - rotates and shifts it sideways one step at a time while it keeps
falling under gravity, instead of teleporting it straight into place."""

STEP_INTERVAL = 0.15

COLS = 10
ROWS = 16
CELL = 2
BOARD_X = 32 + (32 - COLS * CELL) // 2
BOARD_Y = (32 - ROWS * CELL) // 2

SPAWN_COL = COLS // 2 - 2

BORDER_COLOR = (20, 20, 28)
SCORE_COLOR = (230, 230, 240)

SCORE_TABLE = [0, 100, 300, 500, 800]

# rotation states as (row, col) offsets within a 4x4 box
PIECES = {
    "I": [
        [(1, 0), (1, 1), (1, 2), (1, 3)],
        [(0, 2), (1, 2), (2, 2), (3, 2)],
    ],
    "O": [
        [(0, 1), (0, 2), (1, 1), (1, 2)],
    ],
    "T": [
        [(0, 1), (1, 0), (1, 1), (1, 2)],
        [(0, 1), (1, 1), (1, 2), (2, 1)],
        [(1, 0), (1, 1), (1, 2), (2, 1)],
        [(0, 1), (1, 0), (1, 1), (2, 1)],
    ],
    "S": [
        [(0, 1), (0, 2), (1, 0), (1, 1)],
        [(0, 1), (1, 1), (1, 2), (2, 2)],
    ],
    "Z": [
        [(0, 0), (0, 1), (1, 1), (1, 2)],
        [(0, 2), (1, 1), (1, 2), (2, 1)],
    ],
    "J": [
        [(0, 0), (1, 0), (1, 1), (1, 2)],
        [(0, 1), (0, 2), (1, 1), (2, 1)],
        [(1, 0), (1, 1), (1, 2), (2, 2)],
        [(0, 1), (1, 1), (2, 0), (2, 1)],
    ],
    "L": [
        [(0, 2), (1, 0), (1, 1), (1, 2)],
        [(0, 1), (1, 1), (2, 1), (2, 2)],
        [(1, 0), (1, 1), (1, 2), (2, 0)],
        [(0, 0), (0, 1), (1, 1), (2, 1)],
    ],
}

PIECE_COLORS = {
    "I": (60, 200, 220),
    "O": (230, 210, 60),
    "T": (170, 80, 210),
    "S": (80, 200, 100),
    "Z": (220, 60, 60),
    "J": (70, 110, 230),
    "L": (230, 150, 40),
}

HEIGHT_W = -0.51
LINES_W = 0.76
HOLES_W = -0.36
BUMP_W = -0.18


class TetrisMode(Mode):
    name = "tetris"

    def __init__(self):
        self._board: list[list[tuple | None]] = []
        self._score = 0
        self._piece_type = ""
        self._piece_rot = 0
        self._piece_row = 0
        self._piece_col = 0
        self._target_rot = 0
        self._target_col = 0
        self._next_type = ""
        self._last_step: datetime | None = None

    def reset(self) -> None:
        self._board = []
        self._last_step = None

    def _new_board(self) -> None:
        self._board = [[None for _ in range(COLS)] for _ in range(ROWS)]
        self._seed_clutter()
        self._score = 0
        self._next_type = random.choice(list(PIECES))
        self._spawn_piece()

    def _seed_clutter(self) -> None:
        # Start mid-game rather than on an empty field: pre-fill a messy
        # stack in the bottom rows, well clear of the spawn area.
        clutter_rows = random.randint(4, 7)
        fill_chance = random.uniform(0.45, 0.65)
        colors = list(PIECE_COLORS.values())
        for r in range(ROWS - clutter_rows, ROWS):
            filled_cols = [c for c in range(COLS) if random.random() < fill_chance]
            if len(filled_cols) >= COLS:
                filled_cols.pop(random.randrange(COLS))  # never start with an already-complete row
            for c in filled_cols:
                self._board[r][c] = random.choice(colors)

    def _cells(self, piece_type: str, rotation: int) -> list[tuple[int, int]]:
        states = PIECES[piece_type]
        return states[rotation % len(states)]

    def _can_place(self, piece_type: str, rotation: int, row: int, col: int) -> bool:
        for dr, dc in self._cells(piece_type, rotation):
            r, c = row + dr, col + dc
            if c < 0 or c >= COLS or r < 0 or r >= ROWS:
                return False
            if self._board[r][c] is not None:
                return False
        return True

    def _drop_row(self, piece_type: str, rotation: int, col: int) -> int | None:
        if not self._can_place(piece_type, rotation, 0, col):
            return None
        row = 0
        while self._can_place(piece_type, rotation, row + 1, col):
            row += 1
        return row

    def _score_board(self, board: list[list]) -> float:
        heights = []
        holes = 0
        for c in range(COLS):
            filled_seen = False
            col_height = 0
            col_holes = 0
            for r in range(ROWS):
                if board[r][c] is not None:
                    if not filled_seen:
                        col_height = ROWS - r
                        filled_seen = True
                elif filled_seen:
                    col_holes += 1
            heights.append(col_height)
            holes += col_holes
        aggregate_height = sum(heights)
        bumpiness = sum(abs(heights[i] - heights[i + 1]) for i in range(COLS - 1))
        lines = sum(1 for r in range(ROWS) if all(board[r][c] is not None for c in range(COLS)))
        return HEIGHT_W * aggregate_height + LINES_W * lines + HOLES_W * holes + BUMP_W * bumpiness

    def _best_placement(self, piece_type: str) -> tuple[int, int]:
        best = None
        best_score = float("-inf")
        for rotation in range(len(PIECES[piece_type])):
            for col in range(-1, COLS + 1):
                row = self._drop_row(piece_type, rotation, col)
                if row is None:
                    continue
                trial = [r[:] for r in self._board]
                for dr, dc in self._cells(piece_type, rotation):
                    trial[row + dr][col + dc] = PIECE_COLORS[piece_type]
                score = self._score_board(trial)
                if score > best_score:
                    best_score = score
                    best = (rotation, col)
        return best if best is not None else (0, SPAWN_COL)

    def _spawn_piece(self) -> None:
        self._piece_type = self._next_type
        self._next_type = random.choice(list(PIECES))
        self._piece_rot = 0
        self._piece_row = 0
        self._piece_col = SPAWN_COL
        if not self._can_place(self._piece_type, 0, 0, SPAWN_COL):
            self._new_board()
            return
        self._target_rot, self._target_col = self._best_placement(self._piece_type)

    def _lock_piece(self) -> None:
        color = PIECE_COLORS[self._piece_type]
        for dr, dc in self._cells(self._piece_type, self._piece_rot):
            r, c = self._piece_row + dr, self._piece_col + dc
            if 0 <= r < ROWS and 0 <= c < COLS:
                self._board[r][c] = color

        full_rows = [r for r in range(ROWS) if all(self._board[r][c] is not None for c in range(COLS))]
        for r in full_rows:
            del self._board[r]
            self._board.insert(0, [None for _ in range(COLS)])
        self._score += SCORE_TABLE[min(len(full_rows), 4)]
        self._spawn_piece()

    def _step(self) -> None:
        if self._piece_rot != self._target_rot:
            next_rot = (self._piece_rot + 1) % len(PIECES[self._piece_type])
            if self._can_place(self._piece_type, next_rot, self._piece_row, self._piece_col):
                self._piece_rot = next_rot
        elif self._piece_col != self._target_col:
            step = 1 if self._target_col > self._piece_col else -1
            next_col = self._piece_col + step
            if self._can_place(self._piece_type, self._piece_rot, self._piece_row, next_col):
                self._piece_col = next_col

        if self._can_place(self._piece_type, self._piece_rot, self._piece_row + 1, self._piece_col):
            self._piece_row += 1
        else:
            self._lock_piece()

    def render(self, canvas: Canvas, now: datetime) -> None:
        if not self._board or self._last_step is None:
            self._new_board()
            self._last_step = now

        if (now - self._last_step).total_seconds() >= STEP_INTERVAL:
            self._last_step = now
            self._step()

        canvas.clear((0, 0, 0))

        for x in range(BOARD_X - 1, BOARD_X + COLS * CELL + 1):
            canvas.set_pixel(x, BOARD_Y - 1, BORDER_COLOR)
            canvas.set_pixel(x, BOARD_Y + ROWS * CELL, BORDER_COLOR)
        for y in range(BOARD_Y - 1, BOARD_Y + ROWS * CELL + 1):
            canvas.set_pixel(BOARD_X - 1, y, BORDER_COLOR)
            canvas.set_pixel(BOARD_X + COLS * CELL, y, BORDER_COLOR)

        for r in range(ROWS):
            for c in range(COLS):
                color = self._board[r][c]
                if color is None:
                    continue
                self._draw_cell(canvas, BOARD_X + c * CELL, BOARD_Y + r * CELL, color)

        piece_color = PIECE_COLORS[self._piece_type]
        for dr, dc in self._cells(self._piece_type, self._piece_rot):
            r, c = self._piece_row + dr, self._piece_col + dc
            if 0 <= r < ROWS and 0 <= c < COLS:
                self._draw_cell(canvas, BOARD_X + c * CELL, BOARD_Y + r * CELL, piece_color)

        score_text = str(self._score)
        canvas.draw_text(2, 2, score_text, SCORE_COLOR, scale=1)

        next_color = PIECE_COLORS[self._next_type]
        for dr, dc in self._cells(self._next_type, 0):
            self._draw_cell(canvas, 4 + dc * CELL, 14 + dr * CELL, next_color)

        canvas.bloom()

    def _draw_cell(self, canvas: Canvas, x: int, y: int, color) -> None:
        for yy in range(y, y + CELL):
            for xx in range(x, x + CELL):
                canvas.set_pixel(xx, yy, color)

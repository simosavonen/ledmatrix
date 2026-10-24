from PIL import Image

from . import font as fontmod

Color = tuple[int, int, int]


class Canvas:
    """A 64x32 RGB frame buffer that display backends know how to show."""

    def __init__(self, width: int = 64, height: int = 32):
        self.width = width
        self.height = height
        self.image = Image.new("RGB", (width, height), (0, 0, 0))

    def clear(self, color: Color = (0, 0, 0)) -> None:
        self.image.paste(color, (0, 0, self.width, self.height))

    def set_pixel(self, x: int, y: int, color: Color) -> None:
        if 0 <= x < self.width and 0 <= y < self.height:
            self.image.putpixel((x, y), color)

    def get_pixel(self, x: int, y: int) -> Color:
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.image.getpixel((x, y))
        return (0, 0, 0)

    def draw_hline(self, y: int, x0: int, x1: int, color: Color) -> None:
        for x in range(x0, x1):
            self.set_pixel(x, y, color)

    def draw_glyph(self, x: int, y: int, char: str, color: Color, scale: int = 1) -> int:
        """Draws one character at (x, y), returns the width consumed (incl. gap)."""
        rows = fontmod.glyph(char)
        for row_idx, row in enumerate(rows):
            for col_idx, cell in enumerate(row):
                if cell != "#":
                    continue
                for sy in range(scale):
                    for sx in range(scale):
                        self.set_pixel(
                            x + col_idx * scale + sx,
                            y + row_idx * scale + sy,
                            color,
                        )
        return fontmod.GLYPH_WIDTH * scale + scale  # one scaled column of gap

    def draw_text(self, x: int, y: int, text: str, color: Color, scale: int = 1) -> int:
        cursor = x
        for char in text:
            cursor += self.draw_glyph(cursor, y, char, color, scale)
        return cursor - x

    def text_width(self, text: str, scale: int = 1) -> int:
        glyph_w = fontmod.GLYPH_WIDTH * scale + scale
        return glyph_w * len(text) - scale if text else 0

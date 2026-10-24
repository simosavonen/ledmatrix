from PIL import Image, ImageChops, ImageFilter

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

    def blend_pixel(self, x: int, y: int, color: Color, alpha: float) -> None:
        """Mixes `color` into the existing pixel by `alpha` (0..1 coverage)."""
        if alpha <= 0:
            return
        if alpha >= 1:
            self.set_pixel(x, y, color)
            return
        if not (0 <= x < self.width and 0 <= y < self.height):
            return
        bg = self.get_pixel(x, y)
        blended = tuple(int(bg[i] * (1 - alpha) + color[i] * alpha) for i in range(3))
        self.set_pixel(x, y, blended)

    def draw_dot(self, cx: float, cy: float, radius: float, color: Color) -> None:
        """Soft, anti-aliased circular dot at a sub-pixel position - for a
        moving object, this makes it slide smoothly instead of jumping
        between whole pixels and looking like it only 'scraped' a cell."""
        x0, x1 = int(cx - radius - 1), int(cx + radius + 2)
        y0, y1 = int(cy - radius - 1), int(cy + radius + 2)
        for y in range(y0, y1):
            for x in range(x0, x1):
                dist = ((x + 0.5 - cx) ** 2 + (y + 0.5 - cy) ** 2) ** 0.5
                coverage = max(0.0, min(1.0, radius + 0.5 - dist))
                if coverage > 0:
                    self.blend_pixel(x, y, color, coverage)

    def draw_vbar_aa(self, x: int, width: int, y0: float, y1: float, color: Color) -> None:
        """A `width`-column-wide vertical bar spanning the float range
        [y0, y1), with anti-aliased top/bottom edges so it slides smoothly."""
        top, bottom = int(y0) - 1, int(y1) + 1
        for y in range(max(0, top), bottom + 1):
            coverage = max(0.0, min(y + 1, y1) - max(y, y0))
            coverage = max(0.0, min(1.0, coverage))
            if coverage <= 0:
                continue
            for xx in range(x, x + width):
                self.blend_pixel(xx, y, color, coverage)

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

    def bloom(self, radius: float = 1.2, strength: float = 0.55) -> None:
        """Blurs a dimmed copy of the frame and screen-blends it back in, so
        lit pixels bleed softly into their neighbors instead of looking like
        flat, hard-edged blocks. Cheap - fine to call every frame."""
        if strength <= 0:
            return
        blurred = self.image.filter(ImageFilter.GaussianBlur(radius))
        if strength < 1.0:
            blurred = blurred.point(lambda p: int(p * strength))
        self.image = ImageChops.screen(self.image, blurred)

    def text_width(self, text: str, scale: int = 1) -> int:
        glyph_w = fontmod.GLYPH_WIDTH * scale + scale
        return glyph_w * len(text) - scale if text else 0

"""Image helpers: slicing tall strips into tiles and typesetting English back onto a page."""
from collections.abc import Iterator

from PIL import Image, ImageDraw, ImageFont

from .schemas import Region

FONT_CANDIDATES = [
    "ComicNeue-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "DejaVuSans-Bold.ttf",
]


def prepare(img: Image.Image, max_width: int) -> Image.Image:
    img = img.convert("RGB")
    if img.width > max_width:
        h = round(img.height * max_width / img.width)
        img = img.resize((max_width, h), Image.LANCZOS)
    return img


def slice_image(img: Image.Image, slice_height: int) -> Iterator[tuple[int, Image.Image]]:
    """Yield (y_offset, tile). Tiles have equal height so no sliver is left at the end."""
    n = max(1, -(-img.height // slice_height))
    step = -(-img.height // n)
    for i in range(n):
        y0 = i * step
        yield y0, img.crop((0, y0, img.width, min(img.height, y0 + step)))


def load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in FONT_CANDIDATES:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default(size)


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, max_w: float) -> list[str]:
    lines: list[str] = []
    for para in text.split("\n"):
        line = ""
        for word in para.split():
            trial = f"{line} {word}".strip()
            if draw.textlength(trial, font=font) > max_w and line:
                lines.append(line)
                line = word
            else:
                line = trial
        lines.append(line)
    return lines


def _background(img: Image.Image, x0: int, y0: int, x1: int, y1: int) -> tuple[int, int, int]:
    pts = []
    for i in range(7):
        t = i / 6
        pts += [(x0 + (x1 - x0) * t, y0), (x0 + (x1 - x0) * t, y1), (x0, y0 + (y1 - y0) * t), (x1, y0 + (y1 - y0) * t)]
    px = [img.getpixel((min(img.width - 1, max(0, round(x))), min(img.height - 1, max(0, round(y))))) for x, y in pts]
    return tuple(round(sum(c[i] for c in px) / len(px)) for i in range(3))  # type: ignore[return-value]


def render_page(img: Image.Image, regions: list[Region]) -> Image.Image:
    """Cover each region with its local background colour and typeset the English text."""
    out = img.copy()
    draw = ImageDraw.Draw(out)
    for r in regions:
        x, y, w, h = r.box[0] * img.width, r.box[1] * img.height, r.box[2] * img.width, r.box[3] * img.height
        pad = max(3, min(w, h) * 0.06)
        x0, y0 = max(0, x - pad), max(0, y - pad)
        x1, y1 = min(img.width, x + w + pad), min(img.height, y + h + pad)
        bg = _background(img, x0, y0, x1, y1)
        draw.rounded_rectangle((x0, y0, x1, y1), radius=min(x1 - x0, y1 - y0) * 0.25, fill=bg)
        ink = (17, 17, 17) if (0.299 * bg[0] + 0.587 * bg[1] + 0.114 * bg[2]) > 140 else (255, 255, 255)
        iw, ih = (x1 - x0) * 0.88, (y1 - y0) * 0.86
        size = int(min(40, ih * 0.6))
        while size > 8:
            font = load_font(size)
            lines = _wrap(draw, r.english, font, iw)
            if len(lines) * size * 1.15 <= ih and all(draw.textlength(l, font=font) <= iw for l in lines):
                break
            size -= 1
        font = load_font(size)
        lines = _wrap(draw, r.english, font, iw)
        top = (y0 + y1) / 2 - len(lines) * size * 1.15 / 2
        for i, line in enumerate(lines):
            draw.text(((x0 + x1) / 2, top + i * size * 1.15), line, font=font, fill=ink, anchor="ma")
    return out

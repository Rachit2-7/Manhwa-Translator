"""Command-line usage: python -m app.cli page.jpg -o page_en.png"""
import argparse
import asyncio
import io
from pathlib import Path

from PIL import Image

from .config import settings
from .imaging import prepare, render_page
from .schemas import TranslateOptions
from .translator import translate_image


def main() -> None:
    ap = argparse.ArgumentParser(description="Translate a Korean manhwa page to English.")
    ap.add_argument("image", type=Path)
    ap.add_argument("-o", "--output", type=Path, default=None)
    ap.add_argument("--glossary", default="")
    ap.add_argument("--sfx", action="store_true", help="also typeset sound effects")
    args = ap.parse_args()

    result = asyncio.run(translate_image(args.image.read_bytes(), TranslateOptions(glossary=args.glossary, include_sfx=args.sfx)))
    page = prepare(Image.open(io.BytesIO(args.image.read_bytes())), settings.max_width)
    out = args.output or args.image.with_name(args.image.stem + "_en.png")
    render_page(page, result.regions).save(out)
    print(f"{len(result.regions)} regions translated across {result.tiles} tile(s) -> {out}")


if __name__ == "__main__":
    main()

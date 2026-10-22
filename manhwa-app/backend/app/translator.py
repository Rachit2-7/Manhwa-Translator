"""Vision translation: detect text regions in a manga page and translate them with Claude."""
import asyncio
import base64
import io
import json
import logging
import re

from anthropic import AsyncAnthropic
from PIL import Image

from .config import settings
from .imaging import prepare, slice_image
from .schemas import Region, TranslateOptions, TranslateResponse

log = logging.getLogger("translator")

PROMPT = """You are a professional Korean-to-English manga/manhwa/webtoon translator and typesetter.
The attached image is a raw Korean scan (or a vertical slice of one).
Find every piece of Korean text worth translating: speech bubbles, thought bubbles, narration boxes, captions, signs{sfx}.
Ignore watermarks, site logos and credits.
For each region return a tight bounding box as integers on a 0-1000 scale relative to THIS image: [left, top, width, height].
Translate in this style: {style}. Keep lines short enough to fit the bubble, keep names consistent, add no commentary.{glossary}
Reading order: top to bottom, right to left within a row for speech.
Return ONLY JSON in exactly this shape:
{{"regions":[{{"box":[l,t,w,h],"korean":"original","english":"translation","type":"speech|thought|narration|sfx|sign"}}]}}
If there is no Korean text, return {{"regions":[]}}."""


def build_prompt(opts: TranslateOptions) -> str:
    return PROMPT.format(
        sfx=", and sound effects" if opts.include_sfx else "",
        style=opts.style,
        glossary=f"\nGlossary to follow:\n{opts.glossary}" if opts.glossary.strip() else "",
    )


def parse_regions(text: str) -> list[dict]:
    """Extract the JSON object from a model reply, tolerating markdown fences and chatter."""
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        raise ValueError("no JSON object in model reply")
    data = json.loads(match.group(0))
    regions = data.get("regions")
    if not isinstance(regions, list):
        raise ValueError("'regions' missing or not a list")
    return regions


def _jpeg_b64(tile: Image.Image) -> str:
    buf = io.BytesIO()
    tile.save(buf, "JPEG", quality=88)
    return base64.b64encode(buf.getvalue()).decode()


async def _translate_tile(client: AsyncAnthropic, tile: Image.Image, prompt: str, retries: int = 1) -> list[dict]:
    content = [
        {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": _jpeg_b64(tile)}},
        {"type": "text", "text": prompt},
    ]
    for attempt in range(retries + 1):
        resp = await client.messages.create(
            model=settings.model, max_tokens=settings.max_tokens, messages=[{"role": "user", "content": content}]
        )
        text = "".join(b.text for b in resp.content if b.type == "text")
        try:
            return parse_regions(text)
        except (ValueError, json.JSONDecodeError) as exc:
            log.warning("bad model JSON (attempt %d): %s", attempt + 1, exc)
    raise ValueError("model did not return valid JSON")


async def translate_image(data: bytes, opts: TranslateOptions, client: AsyncAnthropic | None = None) -> TranslateResponse:
    img = prepare(Image.open(io.BytesIO(data)), settings.max_width)
    client = client or AsyncAnthropic(api_key=settings.anthropic_api_key)
    prompt = build_prompt(opts)
    tiles = list(slice_image(img, settings.slice_height))
    sem = asyncio.Semaphore(settings.concurrency)

    async def run(tile: Image.Image) -> list[dict]:
        async with sem:
            return await _translate_tile(client, tile, prompt)

    results = await asyncio.gather(*(run(t) for _, t in tiles))
    regions: list[Region] = []
    for (y0, tile), raw in zip(tiles, results):
        for r in raw:
            try:
                l, t, w, h = (float(v) for v in r["box"][:4])
                kind = r.get("type", "speech")
                if kind == "sfx" and not opts.include_sfx:
                    continue
                if not r.get("english"):
                    continue
                regions.append(
                    Region(
                        box=[l / 1000, (y0 + t / 1000 * tile.height) / img.height, w / 1000, h / 1000 * tile.height / img.height],
                        korean=str(r.get("korean", "")),
                        english=str(r["english"]),
                        type=kind if kind in {"speech", "thought", "narration", "sfx", "sign"} else "speech",
                    )
                )
            except (KeyError, TypeError, ValueError):
                log.warning("skipping malformed region: %r", r)
    return TranslateResponse(width=img.width, height=img.height, tiles=len(tiles), model=settings.model, regions=regions)

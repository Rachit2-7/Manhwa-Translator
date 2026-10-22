import logging
from pathlib import Path

import anthropic
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.staticfiles import StaticFiles
from PIL import UnidentifiedImageError

from .config import settings
from .schemas import TranslateOptions, TranslateResponse
from .translator import translate_image

logging.basicConfig(level=logging.INFO)
app = FastAPI(title="Manhwa Translation Engine", version="1.0.0")


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok", "model": settings.model, "api_key_configured": bool(settings.anthropic_api_key)}


@app.post("/api/translate", response_model=TranslateResponse)
async def translate(
    image: UploadFile = File(...),
    style: str = Form(TranslateOptions().style),
    glossary: str = Form(""),
    include_sfx: bool = Form(False),
) -> TranslateResponse:
    if not settings.anthropic_api_key:
        raise HTTPException(503, "ANTHROPIC_API_KEY is not configured on the server.")
    if not (image.content_type or "").startswith("image/"):
        raise HTTPException(415, "Upload must be an image.")
    data = await image.read()
    if len(data) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, f"Image exceeds {settings.max_upload_mb} MB.")
    try:
        return await translate_image(data, TranslateOptions(style=style, glossary=glossary, include_sfx=include_sfx))
    except UnidentifiedImageError:
        raise HTTPException(400, "Could not read the image.")
    except anthropic.RateLimitError:
        raise HTTPException(429, "Upstream rate limit hit, retry shortly.")
    except anthropic.AuthenticationError:
        raise HTTPException(503, "The configured Anthropic API key was rejected.")
    except anthropic.APIError as exc:
        raise HTTPException(502, f"Upstream model error: {exc.__class__.__name__}")
    except ValueError as exc:
        raise HTTPException(502, str(exc))


FRONTEND = Path(__file__).resolve().parents[2] / "frontend"
if FRONTEND.exists():
    app.mount("/", StaticFiles(directory=FRONTEND, html=True), name="frontend")

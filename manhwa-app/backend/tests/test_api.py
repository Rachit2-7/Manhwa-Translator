import io

from fastapi.testclient import TestClient
from PIL import Image

from app import main
from app.schemas import Region, TranslateResponse

client = TestClient(main.app)


def _png():
    buf = io.BytesIO()
    Image.new("RGB", (50, 50)).save(buf, "PNG")
    return buf.getvalue()


def test_health():
    assert client.get("/api/health").json()["status"] == "ok"


def test_translate_requires_key(monkeypatch):
    monkeypatch.setattr(main.settings, "anthropic_api_key", "")
    r = client.post("/api/translate", files={"image": ("a.png", _png(), "image/png")})
    assert r.status_code == 503


def test_translate_rejects_non_image(monkeypatch):
    monkeypatch.setattr(main.settings, "anthropic_api_key", "k")
    r = client.post("/api/translate", files={"image": ("a.txt", b"hi", "text/plain")})
    assert r.status_code == 415


def test_translate_happy_path(monkeypatch):
    monkeypatch.setattr(main.settings, "anthropic_api_key", "k")

    async def fake(data, opts):
        return TranslateResponse(width=50, height=50, tiles=1, model="m", regions=[Region(box=[0, 0, 1, 1], english="Hi")])

    monkeypatch.setattr(main, "translate_image", fake)
    r = client.post("/api/translate", files={"image": ("a.png", _png(), "image/png")}, data={"include_sfx": "true"})
    assert r.status_code == 200 and r.json()["regions"][0]["english"] == "Hi"

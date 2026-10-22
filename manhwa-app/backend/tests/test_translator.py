import asyncio
import io
from types import SimpleNamespace

import pytest
from PIL import Image

from app.schemas import TranslateOptions
from app.translator import build_prompt, parse_regions, translate_image


def test_parse_handles_fences_and_chatter():
    text = 'Sure!\n```json\n{"regions":[{"box":[1,2,3,4],"english":"Hi"}]}\n```'
    assert parse_regions(text)[0]["english"] == "Hi"


def test_parse_rejects_garbage():
    with pytest.raises(ValueError):
        parse_regions("no json here")


def test_prompt_includes_glossary_and_sfx():
    p = build_prompt(TranslateOptions(glossary="서준 = Seojun", include_sfx=True))
    assert "Seojun" in p and "sound effects" in p


class FakeClient:
    """Mimics AsyncAnthropic.messages.create, returning one region per tile."""

    def __init__(self, replies):
        self.replies, self.calls = list(replies), 0
        self.messages = SimpleNamespace(create=self.create)

    async def create(self, **_):
        self.calls += 1
        text = self.replies.pop(0)
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=text)])


def _png(w=200, h=300):
    buf = io.BytesIO()
    Image.new("RGB", (w, h), "white").save(buf, "PNG")
    return buf.getvalue()


def test_translate_maps_boxes_and_filters_sfx():
    reply = '{"regions":[{"box":[100,200,300,100],"korean":"안녕","english":"Hello","type":"speech"},' \
            '{"box":[0,0,10,10],"english":"BOOM","type":"sfx"}]}'
    res = asyncio.run(translate_image(_png(), TranslateOptions(), client=FakeClient([reply])))
    assert len(res.regions) == 1
    assert res.regions[0].box == pytest.approx([0.1, 0.2, 0.3, 0.1])


def test_retry_on_bad_json():
    client = FakeClient(["oops", '{"regions":[]}'])
    res = asyncio.run(translate_image(_png(), TranslateOptions(), client=client))
    assert client.calls == 2 and res.regions == []

from typing import Literal

from pydantic import BaseModel, Field

RegionType = Literal["speech", "thought", "narration", "sfx", "sign"]


class Region(BaseModel):
    """One piece of text on a page. `box` is [x, y, w, h] as fractions (0-1) of the full image."""

    box: list[float] = Field(min_length=4, max_length=4)
    korean: str = ""
    english: str
    type: RegionType = "speech"


class TranslateOptions(BaseModel):
    style: str = "natural, fluent English that reads like a published webtoon localisation"
    glossary: str = ""
    include_sfx: bool = False


class TranslateResponse(BaseModel):
    width: int
    height: int
    tiles: int
    model: str
    regions: list[Region]

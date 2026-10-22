from PIL import Image

from app.imaging import render_page, slice_image
from app.schemas import Region


def test_slices_cover_whole_image_without_slivers():
    img = Image.new("RGB", (100, 3100))
    tiles = list(slice_image(img, 1500))
    assert sum(t.height for _, t in tiles) == 3100
    assert len(tiles) == 3 and tiles[1][0] == tiles[0][1].height


def test_render_changes_region_pixels():
    img = Image.new("RGB", (400, 400), (200, 30, 30))
    r = Region(box=[0.25, 0.25, 0.5, 0.3], english="Hello there, world")
    out = render_page(img, [r])
    assert out.size == img.size and out.tobytes() != img.tobytes()

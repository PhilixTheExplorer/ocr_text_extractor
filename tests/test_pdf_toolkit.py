from collections.abc import Callable
from pathlib import Path

import pytest

from lexo.domain.models import CropBox, TextKind
from lexo.domain.ranges import PageRanges
from lexo.pdf.pymupdf_toolkit import PyMuPdfToolkit

MakePdf = Callable[[Path, int], Path]


@pytest.fixture
def tk() -> PyMuPdfToolkit:
    return PyMuPdfToolkit()


def test_inspect(tk: PyMuPdfToolkit, make_pdf: MakePdf, tmp_path: Path) -> None:
    info = tk.inspect(make_pdf(tmp_path / "a.pdf", 3))
    assert info.page_count == 3
    assert info.has_text_layer is True


def test_page_count(tk: PyMuPdfToolkit, make_pdf: MakePdf, tmp_path: Path) -> None:
    assert tk.page_count(make_pdf(tmp_path / "a.pdf", 4)) == 4


def test_extract(tk: PyMuPdfToolkit, make_pdf: MakePdf, tmp_path: Path) -> None:
    pdf = make_pdf(tmp_path / "a.pdf", 5)
    out = tk.extract_pages(pdf, PageRanges.parse("2-3,5"), tmp_path / "out.pdf")
    assert tk.inspect(out).page_count == 3


def test_extract_empty_selection(tk: PyMuPdfToolkit, make_pdf: MakePdf, tmp_path: Path) -> None:
    pdf = make_pdf(tmp_path / "a.pdf", 2)
    with pytest.raises(ValueError):
        tk.extract_pages(pdf, PageRanges.parse("9-10"), tmp_path / "out.pdf")


def test_reorder_respects_order(tk: PyMuPdfToolkit, make_pdf: MakePdf, tmp_path: Path) -> None:
    pdf = make_pdf(tmp_path / "a.pdf", 4)
    out = tk.reorder(pdf, [2, 0, 3, 1], tmp_path / "out.pdf")
    pages = tk.extract_text_layer(out, PageRanges.parse("1-"))
    assert [p.text.strip() for p in pages] == ["Page 3", "Page 1", "Page 4", "Page 2"]


def test_reorder_rejects_non_permutation(
    tk: PyMuPdfToolkit, make_pdf: MakePdf, tmp_path: Path
) -> None:
    pdf = make_pdf(tmp_path / "a.pdf", 3)
    with pytest.raises(ValueError):
        tk.reorder(pdf, [0, 1], tmp_path / "out.pdf")


def test_split_every(tk: PyMuPdfToolkit, make_pdf: MakePdf, tmp_path: Path) -> None:
    pdf = make_pdf(tmp_path / "a.pdf", 5)
    parts = tk.split(pdf, every=2, out_dir=tmp_path / "parts")
    assert [tk.inspect(p).page_count for p in parts] == [2, 2, 1]


def test_split_at(tk: PyMuPdfToolkit, make_pdf: MakePdf, tmp_path: Path) -> None:
    pdf = make_pdf(tmp_path / "a.pdf", 6)
    parts = tk.split(pdf, at=[3, 5], out_dir=tmp_path / "parts")
    assert [tk.inspect(p).page_count for p in parts] == [2, 2, 2]


def test_split_requires_one_mode(tk: PyMuPdfToolkit, make_pdf: MakePdf, tmp_path: Path) -> None:
    pdf = make_pdf(tmp_path / "a.pdf", 3)
    with pytest.raises(ValueError):
        tk.split(pdf)
    with pytest.raises(ValueError):
        tk.split(pdf, every=2, at=[2])


def test_crop_shrinks_page(tk: PyMuPdfToolkit, make_pdf: MakePdf, tmp_path: Path) -> None:
    pdf = make_pdf(tmp_path / "a.pdf", 1)
    before = tk.inspect(pdf).page_sizes[0]
    out = tk.crop(pdf, CropBox(left=0.1, top=0.1, right=0.9, bottom=0.9), tmp_path / "c.pdf")
    after = tk.inspect(out).page_sizes[0]
    assert after[0] < before[0]
    assert after[1] < before[1]


def test_crop_twice_insets_within_visible_region(
    tk: PyMuPdfToolkit, make_pdf: MakePdf, tmp_path: Path
) -> None:
    pdf = make_pdf(tmp_path / "a.pdf", 1)
    box = CropBox(left=0.1, top=0.1, right=0.9, bottom=0.9)
    once = tk.crop(pdf, box, tmp_path / "c1.pdf")
    twice = tk.crop(once, box, tmp_path / "c2.pdf")

    import pymupdf

    src = pymupdf.open(pdf)
    media = src[0].rect
    src.close()
    result = pymupdf.open(twice)
    cb = result[0].cropbox
    result.close()

    # Two nested 10% insets: 0.1 + 0.1*0.8 = 0.18 in, 0.82 out.
    assert cb.x0 == pytest.approx(media.width * 0.18)
    assert cb.x1 == pytest.approx(media.width * 0.82)
    assert cb.y0 == pytest.approx(media.height * 0.18)
    assert cb.y1 == pytest.approx(media.height * 0.82)


def test_crop_trims_same_visible_edge_under_any_rotation(
    tk: PyMuPdfToolkit, make_pdf: MakePdf, tmp_path: Path
) -> None:
    """Pages alternating /Rotate 90 and 270 must crop identically, not mirrored."""
    import pymupdf

    pdf = make_pdf(tmp_path / "a.pdf", 4)
    doc = pymupdf.open(pdf)
    for i in range(doc.page_count):
        doc[i].set_rotation(270 if i % 2 == 0 else 90)
    doc.save(tmp_path / "rot.pdf")
    doc.close()

    src = pymupdf.open(tmp_path / "rot.pdf")
    # Trim 20% off the top as the user sees it.
    out = tk.crop(tmp_path / "rot.pdf", CropBox(0.0, 0.2, 1.0, 1.0), tmp_path / "c.pdf")
    result = pymupdf.open(out)

    for i in range(result.page_count):
        want = src[i].rect
        want = pymupdf.Rect(want.x0, want.y0 + 0.2 * want.height, want.x1, want.y1)
        expected = src[i].get_pixmap(dpi=72, clip=want)
        actual = result[i].get_pixmap(dpi=72)
        assert (actual.width, actual.height) == (expected.width, expected.height)
        assert actual.samples == expected.samples, f"page {i} cropped the wrong edge"

    src.close()
    result.close()


def test_rotate(tk: PyMuPdfToolkit, make_pdf: MakePdf, tmp_path: Path) -> None:
    pdf = make_pdf(tmp_path / "a.pdf", 2)
    out = tk.rotate(pdf, 90, tmp_path / "r.pdf")
    assert tk.inspect(out).page_count == 2


def test_rotate_rejects_non_multiple(tk: PyMuPdfToolkit, make_pdf: MakePdf, tmp_path: Path) -> None:
    pdf = make_pdf(tmp_path / "a.pdf", 1)
    with pytest.raises(ValueError):
        tk.rotate(pdf, 45, tmp_path / "r.pdf")


def test_merge(tk: PyMuPdfToolkit, make_pdf: MakePdf, tmp_path: Path) -> None:
    a = make_pdf(tmp_path / "a.pdf", 2)
    b = make_pdf(tmp_path / "b.pdf", 3)
    out = tk.merge([a, b], tmp_path / "m.pdf")
    assert tk.inspect(out).page_count == 5


def test_split_spreads(tk: PyMuPdfToolkit, make_pdf: MakePdf, tmp_path: Path) -> None:
    pdf = make_pdf(tmp_path / "a.pdf", 2)
    src_w = tk.inspect(pdf).page_sizes[0][0]
    out = tk.split_spreads(pdf, tmp_path / "spread.pdf", ratio=0.5)
    info = tk.inspect(out)
    assert info.page_count == 4
    assert info.page_sizes[0][0] == pytest.approx(src_w / 2, abs=1.0)


def test_split_spreads_bad_ratio(tk: PyMuPdfToolkit, make_pdf: MakePdf, tmp_path: Path) -> None:
    pdf = make_pdf(tmp_path / "a.pdf", 1)
    with pytest.raises(ValueError):
        tk.split_spreads(pdf, tmp_path / "x.pdf", ratio=1.5)


def test_render_jpeg(tk: PyMuPdfToolkit, make_pdf: MakePdf, tmp_path: Path) -> None:
    # Pages render as JPEG (not PNG) so dense scans stay small enough for Drive
    # upload and Google OCR; the mimetype travels with the image.
    pdf = make_pdf(tmp_path / "a.pdf", 2)
    images = list(tk.render(pdf, PageRanges.parse("1-2"), dpi=72))
    assert len(images) == 2
    assert all(img.image_bytes[:3] == b"\xff\xd8\xff" for img in images)
    assert all(img.mimetype == "image/jpeg" for img in images)


def test_ocr_render_dpi_caps_huge_pages() -> None:
    from lexo.pdf.pymupdf_toolkit import _MAX_OCR_EDGE_PX, _ocr_render_dpi

    # A normal-size page keeps the requested dpi.
    assert _ocr_render_dpi(612, 792, 300) == 300
    # A very large page (points) is rendered at a lower dpi so its longest edge
    # does not exceed the cap.
    eff = _ocr_render_dpi(1894, 2632, 300)
    assert eff < 300
    assert round(2632 / 72 * eff) <= _MAX_OCR_EDGE_PX


def test_extract_text_layer(tk: PyMuPdfToolkit, make_pdf: MakePdf, tmp_path: Path) -> None:
    pdf = make_pdf(tmp_path / "a.pdf", 2)
    pages = tk.extract_text_layer(pdf, PageRanges.parse("1-2"))
    assert len(pages) == 2
    assert all(p.kind == TextKind.DIGITAL for p in pages)
    assert "Page 1" in pages[0].text


def test_glyph_soup_text_layer_routes_to_ocr() -> None:
    from lexo.pdf.pymupdf_toolkit import _is_glyph_soup

    # A legacy non-Unicode font reports its text as Private Use Area glyph ids.
    pua_soup = "".join(chr(0xF000 + (i % 0x100)) for i in range(50))
    assert _is_glyph_soup(pua_soup) is True
    assert _is_glyph_soup("ပထမ စာမျက်နှာ") is False  # real Burmese Unicode
    assert _is_glyph_soup("Page 1") is False
    assert _is_glyph_soup("   \n\t ") is False

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


def test_render_png(tk: PyMuPdfToolkit, make_pdf: MakePdf, tmp_path: Path) -> None:
    pdf = make_pdf(tmp_path / "a.pdf", 2)
    images = list(tk.render(pdf, PageRanges.parse("1-2"), dpi=72))
    assert len(images) == 2
    assert all(img.image_bytes[:4] == b"\x89PNG" for img in images)


def test_extract_text_layer(tk: PyMuPdfToolkit, make_pdf: MakePdf, tmp_path: Path) -> None:
    pdf = make_pdf(tmp_path / "a.pdf", 2)
    pages = tk.extract_text_layer(pdf, PageRanges.parse("1-2"))
    assert len(pages) == 2
    assert all(p.kind == TextKind.DIGITAL for p in pages)
    assert "Page 1" in pages[0].text

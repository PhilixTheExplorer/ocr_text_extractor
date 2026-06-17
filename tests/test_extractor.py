from collections.abc import Callable
from pathlib import Path

from lexo.domain.ranges import PageRanges
from lexo.text.extractor import TextExtractor

MakePdf = Callable[[Path, int], Path]


def test_extract_all_pages(make_pdf: MakePdf, tmp_path: Path) -> None:
    doc = TextExtractor().extract(make_pdf(tmp_path / "a.pdf", 3))
    assert doc.page_count == 3
    assert len(doc.pages) == 3
    assert doc.has_text
    assert "Page 1" in doc.pages[0].text


def test_extract_subset(make_pdf: MakePdf, tmp_path: Path) -> None:
    doc = TextExtractor().extract(make_pdf(tmp_path / "a.pdf", 5), PageRanges.parse("2-3"))
    assert [p.index for p in doc.pages] == [1, 2]
    assert doc.page_count == 5

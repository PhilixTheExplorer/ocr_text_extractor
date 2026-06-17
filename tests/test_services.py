from collections.abc import Callable
from pathlib import Path

from lexo.infra.settings import Settings
from lexo.pdf.pymupdf_toolkit import PyMuPdfToolkit
from lexo.services import LexoService

MakePdf = Callable[[Path, int], Path]


def _service() -> LexoService:
    return LexoService(Settings(), PyMuPdfToolkit())


def test_extract(make_pdf: MakePdf, tmp_path: Path) -> None:
    svc = _service()
    doc = svc.extract(make_pdf(tmp_path / "a.pdf", 2))
    assert doc.page_count == 2
    assert doc.has_text


def test_export_markdown(make_pdf: MakePdf, tmp_path: Path) -> None:
    svc = _service()
    doc = svc.extract(make_pdf(tmp_path / "a.pdf", 1))
    assert svc.export(doc, "markdown").startswith("---\n")

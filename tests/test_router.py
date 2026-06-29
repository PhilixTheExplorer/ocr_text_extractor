import asyncio
from collections.abc import Callable
from pathlib import Path

from helpers import FakeProvider
from lexo.domain.events import Event, PageCompleted, RunCompleted, RunStarted
from lexo.domain.models import TextKind
from lexo.pdf.pymupdf_toolkit import PyMuPdfToolkit
from lexo.pipeline.engine import OcrEngine
from lexo.pipeline.router import OcrRouter

MakePdf = Callable[[Path, int], Path]


def test_digital_pdf_skips_ocr(make_pdf: MakePdf, tmp_path: Path) -> None:
    provider = FakeProvider(text="OCR")
    router = OcrRouter(PyMuPdfToolkit(), OcrEngine(provider, retry_base_delay=0))
    doc = asyncio.run(router.process_pdf(make_pdf(tmp_path / "a.pdf", 2)))
    assert provider.calls == 0
    assert "Page 1" in doc.pages[0].text


def test_force_ocr_uses_provider(make_pdf: MakePdf, tmp_path: Path) -> None:
    provider = FakeProvider(text="OCR")
    router = OcrRouter(PyMuPdfToolkit(), OcrEngine(provider, retry_base_delay=0), dpi=72)
    doc = asyncio.run(router.process_pdf(make_pdf(tmp_path / "a.pdf", 2), force_ocr=True))
    assert provider.calls == 2
    assert doc.pages[0].text.startswith("OCR")


def test_batches_render_and_emit_single_run(make_pdf: MakePdf, tmp_path: Path) -> None:
    events: list[Event] = []
    provider = FakeProvider(text="OCR")
    router = OcrRouter(
        PyMuPdfToolkit(),
        OcrEngine(provider, concurrency=1, retry_base_delay=0),
        dpi=72,
        batch_size=1,  # force one page per batch -> 3 engine.run calls
    )
    doc = asyncio.run(
        router.process_pdf(make_pdf(tmp_path / "a.pdf", 3), force_ocr=True, on_event=events.append)
    )
    assert provider.calls == 3
    assert all(page.text.startswith("OCR") for page in doc.pages)
    # Batching must still look like a single run to subscribers.
    assert sum(isinstance(e, RunStarted) for e in events) == 1
    assert sum(isinstance(e, RunCompleted) for e in events) == 1


def test_page_completed_text_is_postprocessed(make_pdf: MakePdf, tmp_path: Path) -> None:
    events: list[Event] = []
    provider = FakeProvider(text="OCR")
    router = OcrRouter(PyMuPdfToolkit(), OcrEngine(provider, retry_base_delay=0), dpi=72)
    doc = asyncio.run(
        router.process_pdf(
            make_pdf(tmp_path / "a.pdf", 2),
            force_ocr=True,
            postprocessor=str.upper,
            on_event=events.append,
        )
    )
    streamed = {e.page_index: e.text for e in events if isinstance(e, PageCompleted)}
    # The text on each event matches the post-processed text the router stores.
    assert streamed == {page.index: page.text for page in doc.pages}
    assert all(text == text.upper() for text in streamed.values())


def test_pdf_is_hashed_once_across_batches(
    make_pdf: MakePdf, tmp_path: Path, monkeypatch: object
) -> None:
    import lexo.pdf.pymupdf_toolkit as toolkit_mod
    import lexo.pipeline.router as router_mod

    calls = {"router": 0, "toolkit": 0}
    real = router_mod.sha256_file

    def counting(key: str):
        def wrapper(path: Path) -> str:
            calls[key] += 1
            return real(path)

        return wrapper

    monkeypatch.setattr(router_mod, "sha256_file", counting("router"))  # type: ignore[attr-defined]
    monkeypatch.setattr(toolkit_mod, "sha256_file", counting("toolkit"))  # type: ignore[attr-defined]

    router = OcrRouter(
        PyMuPdfToolkit(),
        OcrEngine(FakeProvider(text="OCR"), concurrency=1, retry_base_delay=0),
        dpi=72,
        batch_size=1,  # 4 pages -> 4 batches; each would re-hash if not threaded through
    )
    doc = asyncio.run(router.process_pdf(make_pdf(tmp_path / "a.pdf", 4), force_ocr=True))
    # One hash total: the router computes the doc id once and passes it to render.
    assert calls == {"router": 1, "toolkit": 0}
    assert len(doc.pages) == 4


def test_ocr_failure_marks_page_failed(make_pdf: MakePdf, tmp_path: Path) -> None:
    provider = FakeProvider(fail_times=99)
    router = OcrRouter(
        PyMuPdfToolkit(),
        OcrEngine(provider, max_retries=1, retry_base_delay=0),
        dpi=72,
    )
    doc = asyncio.run(router.process_pdf(make_pdf(tmp_path / "a.pdf", 1), force_ocr=True))
    assert doc.pages[0].kind == TextKind.FAILED
    assert doc.pages[0].error == "transient failure"

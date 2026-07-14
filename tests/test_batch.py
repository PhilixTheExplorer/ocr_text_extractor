import asyncio
from pathlib import Path

from lexo.batch import (
    BatchEvent,
    BatchOcrConfig,
    BatchStatus,
    collect_pdf_inputs,
    run_batch_ocr,
)
from lexo.domain.models import ExtractedDoc, PageText, TextKind


class FakeService:
    async def ocr(self, path: Path, **kwargs: object) -> ExtractedDoc:
        return ExtractedDoc(
            "id", path.name, 1, [PageText(0, f"text from {path.stem}", TextKind.SCANNED)]
        )

    def export(self, doc: ExtractedDoc, fmt: str) -> str:
        assert fmt == "text"
        return doc.pages[0].text + "\n"


def test_batch_writes_skips_and_reports_missing(tmp_path: Path) -> None:
    source = tmp_path / "pdfs"
    output = tmp_path / "txt"
    source.mkdir()
    output.mkdir()
    (source / "part006.pdf").write_bytes(b"pdf")
    (source / "part007.pdf").write_bytes(b"pdf")
    (output / "part007.txt").write_text("existing", encoding="utf-8")
    events: list[BatchEvent] = []
    config = BatchOcrConfig(
        sources=(source / "part006.pdf", source / "part007.pdf", source / "missing.pdf"),
        output_dir=output,
    )

    summary = asyncio.run(run_batch_ocr(FakeService(), config, on_event=events.append))  # type: ignore[arg-type]

    assert summary.written == 1
    assert summary.skipped == 1
    assert summary.failed == 1
    assert (output / "part006.txt").read_text(encoding="utf-8") == "text from part006\n"
    assert [event.status for event in events] == [
        BatchStatus.STARTED,
        BatchStatus.WRITTEN,
        BatchStatus.SKIPPED,
        BatchStatus.MISSING,
    ]


def test_collect_pdf_inputs_expands_folders_and_deduplicates(tmp_path: Path) -> None:
    folder = tmp_path / "pdfs"
    folder.mkdir()
    first = folder / "a.pdf"
    second = folder / "B.PDF"
    first.write_bytes(b"pdf")
    second.write_bytes(b"pdf")
    (folder / "notes.txt").write_text("ignore", encoding="utf-8")

    assert collect_pdf_inputs([folder, first]) == (first, second)

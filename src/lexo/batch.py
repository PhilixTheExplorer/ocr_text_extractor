"""Reusable multi-PDF batch OCR use case.

The CLI and GUI are adapters around this module; input collection, resume
behaviour, OCR, and UTF-8 export live in one place.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from lexo.infra.auth_google import AuthError
from lexo.pipeline.engine import CancellationToken, Cancelled
from lexo.services import LexoService


class BatchStatus(StrEnum):
    STARTED = "started"
    WRITTEN = "written"
    SKIPPED = "skipped"
    MISSING = "missing"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class BatchOcrConfig:
    sources: tuple[Path, ...]
    output_dir: Path
    lang: str | None = None
    force_ocr: bool = True
    overwrite: bool = False

    def __post_init__(self) -> None:
        if not self.sources:
            raise ValueError("choose at least one PDF")
        output_names = [source.with_suffix(".txt").name.casefold() for source in self.sources]
        if len(output_names) != len(set(output_names)):
            raise ValueError("PDF filenames must be unique when exporting to one folder")

    @property
    def total(self) -> int:
        return len(self.sources)

    def output_for(self, source: Path) -> Path:
        return self.output_dir / source.with_suffix(".txt").name


def collect_pdf_inputs(inputs: Iterable[Path]) -> tuple[Path, ...]:
    """Expand files and non-recursive directories into a stable PDF list."""
    sources: list[Path] = []
    for item in inputs:
        if item.is_dir():
            sources.extend(
                sorted(
                    (path for path in item.iterdir() if path.suffix.lower() == ".pdf"),
                    key=lambda path: path.name.casefold(),
                )
            )
        elif item.is_file() and item.suffix.lower() == ".pdf":
            sources.append(item)
        else:
            raise ValueError(f"not a PDF file or directory: {item}")

    unique: list[Path] = []
    seen: set[str] = set()
    for source in sources:
        key = str(source.resolve()).casefold()
        if key not in seen:
            seen.add(key)
            unique.append(source)
    if not unique:
        raise ValueError("no PDF files found")
    return tuple(unique)


@dataclass(frozen=True, slots=True)
class BatchEvent:
    position: int
    total: int
    source: Path
    output: Path
    status: BatchStatus
    message: str = ""


@dataclass(frozen=True, slots=True)
class BatchSummary:
    written: int = 0
    skipped: int = 0
    failed: int = 0


BatchEventSink = Callable[[BatchEvent], None]


async def run_batch_ocr(
    service: LexoService,
    config: BatchOcrConfig,
    *,
    on_event: BatchEventSink | None = None,
    token: CancellationToken | None = None,
) -> BatchSummary:
    """OCR multiple PDFs, continuing after per-file failures."""
    emit = on_event or (lambda _event: None)
    cancellation = token or CancellationToken()
    config.output_dir.mkdir(parents=True, exist_ok=True)
    written = skipped = failed = 0

    for position, source in enumerate(config.sources, start=1):
        cancellation.check()
        output = config.output_for(source)

        if not source.is_file():
            failed += 1
            emit(
                BatchEvent(
                    position,
                    config.total,
                    source,
                    output,
                    BatchStatus.MISSING,
                    "PDF not found",
                )
            )
            continue
        if output.exists() and not config.overwrite:
            skipped += 1
            emit(
                BatchEvent(
                    position,
                    config.total,
                    source,
                    output,
                    BatchStatus.SKIPPED,
                    "TXT already exists",
                )
            )
            continue

        emit(
            BatchEvent(position, config.total, source, output, BatchStatus.STARTED)
        )
        try:
            doc = await service.ocr(
                source,
                provider="google",
                lang=config.lang,
                force_ocr=config.force_ocr,
                token=cancellation,
            )
            if doc.failed_pages:
                pages = ", ".join(str(page.index + 1) for page in doc.failed_pages)
                raise RuntimeError(f"OCR failed on page(s): {pages}")
            output.write_text(service.export(doc, "text"), encoding="utf-8")
        except (AuthError, Cancelled):
            raise
        except Exception as exc:
            failed += 1
            emit(
                BatchEvent(
                    position,
                    config.total,
                    source,
                    output,
                    BatchStatus.FAILED,
                    str(exc),
                )
            )
            continue

        written += 1
        emit(
            BatchEvent(position, config.total, source, output, BatchStatus.WRITTEN)
        )

    return BatchSummary(written=written, skipped=skipped, failed=failed)

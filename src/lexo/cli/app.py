"""Lexo CLI entry point.

Commands: ``info``, ``check-update``, ``extract``, ``ocr``, ``pdf {info,extract,
split,crop,rotate,merge,split-spread}``, ``login``, ``logout``, ``gui``.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import NoReturn

import typer

from lexo import __version__
from lexo.domain.events import Event, PageCompleted, PageFailed
from lexo.domain.models import CropBox
from lexo.domain.ranges import PageRanges
from lexo.export import EXTENSIONS
from lexo.infra import paths
from lexo.pdf.pymupdf_toolkit import PyMuPdfToolkit
from lexo.services import LexoService
from lexo.update import UpdateCheckError, check_update_available

app = typer.Typer(
    name="lexo",
    help="Lexo (Local EXtraction & OCR) - a local-first desktop document OCR tool.",
    no_args_is_help=True,
    add_completion=False,
)
pdf_app = typer.Typer(
    help="PDF operations (no OCR): info, extract, split, crop, rotate, merge, split-spread.",
    no_args_is_help=True,
)
app.add_typer(pdf_app, name="pdf")

_toolkit = PyMuPdfToolkit()


def _fail(exc: Exception) -> NoReturn:
    typer.echo(f"error: {exc}", err=True)
    raise typer.Exit(1)


# top level
def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"lexo {__version__}")
        raise typer.Exit()


@app.callback()
def main_callback(
    version: bool = typer.Option(
        False,
        "--version",
        "-V",
        help="Show version and exit.",
        callback=_version_callback,
        is_eager=True,
    ),
) -> None:
    """Lexo command-line interface."""


@app.command()
def info() -> None:
    """Show version and where Lexo stores its data."""
    typer.echo(f"lexo {__version__}")
    typer.echo(f"data dir:   {paths.data_dir()}")
    typer.echo(f"config dir: {paths.config_dir()}")


@app.command("check-update")
def check_update_cmd() -> None:
    """Check PyPI for a newer Lexo release."""
    try:
        status = check_update_available()
    except UpdateCheckError as exc:
        _fail(exc)

    if status.update_available:
        typer.echo(
            f"Update available: lexo {status.latest_version} (current: {status.current_version})"
        )
        typer.echo(status.package_url)
    else:
        typer.echo(f"Lexo is up to date ({status.current_version})")


# pdf
@pdf_app.command("info")
def pdf_info(
    pdf: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True),
) -> None:
    """Inspect a PDF: page count, text layer, page size."""
    di = _toolkit.inspect(pdf)
    typer.echo(f"file:           {pdf}")
    typer.echo(f"pages:          {di.page_count}")
    typer.echo(f"has text layer: {di.has_text_layer}")
    if di.page_sizes:
        w, h = di.page_sizes[0]
        typer.echo(f"page 1 size:    {w:.0f} x {h:.0f} pt")


@pdf_app.command()
def extract(
    pdf: Path = typer.Argument(..., exists=True, dir_okay=False),
    pages: str = typer.Option(
        ..., "--pages", "-p", help='Pages: all/odd/even or a range, e.g. "1-3,7,10-"'
    ),
    out: Path = typer.Option(..., "--out", "-o", help="Output PDF path"),
) -> None:
    """Extract a page range into a new PDF."""
    try:
        result = _toolkit.extract_pages(pdf, PageRanges.parse(pages), out)
    except Exception as exc:
        _fail(exc)
    typer.echo(f"✓ wrote {result}")


@pdf_app.command()
def split(
    pdf: Path = typer.Argument(..., exists=True, dir_okay=False),
    every: int | None = typer.Option(None, "--every", help="Pages per chunk"),
    at: str | None = typer.Option(
        None, "--at", help="1-based pages that start a new file, e.g. 4,7"
    ),
    out_dir: Path | None = typer.Option(None, "--out-dir", help="Output dir (default: alongside)"),
) -> None:
    """Split a PDF by chunk size (--every) or at page boundaries (--at)."""
    try:
        at_list = [int(x) for x in at.split(",")] if at else None
    except ValueError as exc:
        _fail(exc)
    try:
        results = _toolkit.split(pdf, every=every, at=at_list, out_dir=out_dir)
    except Exception as exc:
        _fail(exc)
    for p in results:
        typer.echo(f"✓ {p}")


@pdf_app.command()
def crop(
    pdf: Path = typer.Argument(..., exists=True, dir_okay=False),
    out: Path = typer.Option(..., "--out", "-o"),
    top: float = typer.Option(0.0, "--top", help="Percent to trim from the top"),
    bottom: float = typer.Option(0.0, "--bottom", help="Percent to trim from the bottom"),
    left: float = typer.Option(0.0, "--left", help="Percent to trim from the left"),
    right: float = typer.Option(0.0, "--right", help="Percent to trim from the right"),
    pages: str | None = typer.Option(None, "--pages", "-p", help="Limit to a page range"),
) -> None:
    """Crop margins off pages (percent per edge) - e.g. strip headers/footers before OCR."""
    box = CropBox(left=left / 100, top=top / 100, right=1 - right / 100, bottom=1 - bottom / 100)
    ranges = PageRanges.parse(pages) if pages else None
    try:
        if box.left >= box.right or box.top >= box.bottom:
            raise ValueError("crop removes the entire page")
        result = _toolkit.crop(pdf, box, out, ranges)
    except Exception as exc:
        _fail(exc)
    typer.echo(f"✓ wrote {result}")


@pdf_app.command()
def rotate(
    pdf: Path = typer.Argument(..., exists=True, dir_okay=False),
    out: Path = typer.Option(..., "--out", "-o"),
    degrees: int = typer.Option(90, "--degrees", "-d", help="Multiple of 90"),
    pages: str | None = typer.Option(None, "--pages", "-p", help="Limit to a page range"),
) -> None:
    """Rotate pages by a multiple of 90 degrees."""
    ranges = PageRanges.parse(pages) if pages else None
    try:
        result = _toolkit.rotate(pdf, degrees, out, ranges)
    except Exception as exc:
        _fail(exc)
    typer.echo(f"✓ wrote {result}")


@pdf_app.command()
def merge(
    pdfs: list[Path] = typer.Argument(..., help="Input PDFs, in order"),
    out: Path = typer.Option(..., "--out", "-o"),
) -> None:
    """Merge multiple PDFs into one."""
    for p in pdfs:
        if not p.exists():
            _fail(FileNotFoundError(p))
    try:
        result = _toolkit.merge(pdfs, out)
    except Exception as exc:
        _fail(exc)
    typer.echo(f"✓ wrote {result}")


@pdf_app.command("split-spread")
def split_spread(
    pdf: Path = typer.Argument(..., exists=True, dir_okay=False),
    out: Path = typer.Option(..., "--out", "-o"),
    ratio: float = typer.Option(0.5, "--ratio", help="Split position, 0.05 to 0.95"),
) -> None:
    """Split each two-up page into two pages (left half, then right half)."""
    try:
        result = _toolkit.split_spreads(pdf, out, ratio=ratio)
    except Exception as exc:
        _fail(exc)
    typer.echo(f"✓ wrote {result}")


# text extraction
@app.command("extract")
def extract_text(
    pdf: Path = typer.Argument(..., exists=True, dir_okay=False),
    pages: str | None = typer.Option(None, "--pages", "-p", help="Limit to a page range"),
    fmt: str = typer.Option("text", "--format", "-f", help="text, markdown, or jsonl"),
    out: Path | None = typer.Option(None, "--out", "-o", help="Output file (default: stdout)"),
) -> None:
    """Extract embedded text from a digital PDF."""
    if fmt not in EXTENSIONS:
        _fail(ValueError(f"unknown format: {fmt} (choose from {', '.join(EXTENSIONS)})"))
    svc = LexoService.create()
    ranges = PageRanges.parse(pages) if pages else None
    try:
        doc = svc.extract(pdf, ranges)
        content = svc.export(doc, fmt)
    except Exception as exc:
        _fail(exc)
    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(content, encoding="utf-8")
        typer.echo(f"wrote {out} ({len(doc.pages)} pages)")
    else:
        typer.echo(content)
    failures = doc.failed_pages
    if failures:
        typer.echo(f"OCR failed on {len(failures)} page(s)", err=True)
        raise typer.Exit(1)
    if not doc.has_text:
        typer.echo("note: no embedded text found; this looks scanned (try `lexo ocr`)", err=True)


@app.command("login")
def login_cmd() -> None:
    """Authenticate with Google (opens a browser) and store the token in the OS keychain."""
    from lexo.infra import auth_google

    try:
        auth_google.login()
    except Exception as exc:
        _fail(exc)
    typer.echo("logged in; token stored in your OS keychain")


@app.command("logout")
def logout_cmd() -> None:
    """Sign out of Google (remove the stored token)."""
    from lexo.infra import auth_google

    auth_google.logout()
    typer.echo("logged out; token removed from your OS keychain")


def _ocr_progress(event: Event) -> None:
    if isinstance(event, PageCompleted):
        typer.echo(f"  page {event.page_index + 1} done", err=True)
    elif isinstance(event, PageFailed):
        typer.echo(f"  page {event.page_index + 1} failed: {event.error}", err=True)


@app.command("ocr")
def ocr_cmd(
    path: Path = typer.Argument(..., exists=True, dir_okay=False, help="PDF or image"),
    pages: str | None = typer.Option(None, "--pages", "-p", help="Limit to a page range"),
    lang: str | None = typer.Option(None, "--lang", help="OCR language (default: my)"),
    fmt: str = typer.Option("text", "--format", "-f", help="text, markdown, or jsonl"),
    out: Path | None = typer.Option(None, "--out", "-o", help="Output file (default: stdout)"),
    force_ocr: bool = typer.Option(False, "--force-ocr", help="OCR even pages with a text layer"),
) -> None:
    """OCR a scanned PDF or image into text."""
    if fmt not in EXTENSIONS:
        _fail(ValueError(f"unknown format: {fmt} (choose from {', '.join(EXTENSIONS)})"))
    svc = LexoService.create()
    ranges = PageRanges.parse(pages) if pages else None
    try:
        doc = asyncio.run(
            svc.ocr(
                path,
                provider="google",
                lang=lang,
                force_ocr=force_ocr,
                ranges=ranges,
                on_event=_ocr_progress,
            )
        )
        content = svc.export(doc, fmt)
    except Exception as exc:
        _fail(exc)

    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(content, encoding="utf-8")
        typer.echo(f"wrote {out} ({len(doc.pages)} pages)")
    else:
        typer.echo(content)

    failed = doc.failed_pages
    if failed:
        nums = ", ".join(str(p.index + 1) for p in failed)
        typer.echo(f"warning: {len(failed)}/{len(doc.pages)} page(s) failed OCR: {nums}", err=True)
        raise typer.Exit(1)


@app.command("gui")
def gui_cmd() -> None:
    """Launch the Lexo desktop app."""
    from lexo.gui.app import run

    run()


def main() -> None:
    # Force UTF-8 console output - Windows defaults to cp1252, which can't
    # encode Burmese (or even a ✓). Essential for a Myanmar-script tool.
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8")
            except (ValueError, OSError):
                pass
    app()


if __name__ == "__main__":
    main()

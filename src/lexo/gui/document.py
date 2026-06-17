"""The working-copy document model and its editing operations.

This is the GUI's document model, kept free of Qt so it can be reasoned about
and tested on its own. Opening a file copies it into a private temp directory;
every edit (rotate, crop, split, append, extract, remove) is applied to that
working copy through the `PdfToolkit` (PDFs) or Pillow (images), so the original
file on disk is untouched until `save`. Editing methods raise on failure and
return whether the edit was *structural* (changed page count or order), which
the UI uses to decide how much to rebuild.
"""

from __future__ import annotations

import os
import shutil
import tempfile
from collections.abc import Callable
from pathlib import Path

from lexo.domain.models import CropBox, PageText, TextKind
from lexo.domain.ranges import PageRanges
from lexo.ports.pdf_toolkit import PdfToolkit


class WorkingDocument:
    def __init__(
        self,
        toolkit: PdfToolkit,
        workdir: Path,
        source: Path,
        kind: str,
        work_path: Path | None,
        work_images: list[Path],
    ) -> None:
        self.toolkit = toolkit
        self.workdir = workdir
        self.source = source
        self.kind = kind
        self.work_path = work_path
        self.work_images = work_images
        self.dirty = False
        self._pdf_pages = 0
        if kind == "pdf" and work_path is not None:
            self._pdf_pages = toolkit.page_count(work_path)

    @classmethod
    def open(
        cls, toolkit: PdfToolkit, parent_dir: Path, paths: list[Path], kind: str
    ) -> WorkingDocument:
        workdir = Path(tempfile.mkdtemp(dir=parent_dir))
        if kind == "pdf":
            work = workdir / paths[0].name
            shutil.copyfile(paths[0], work)
            return cls(toolkit, workdir, paths[0], kind, work, [])
        images: list[Path] = []
        for i, src in enumerate(paths):
            dst = workdir / f"{i:03d}_{src.name}"
            shutil.copyfile(src, dst)
            images.append(dst)
        work = images[0] if len(images) == 1 else None
        return cls(toolkit, workdir, paths[0], kind, work, images)

    # identity

    @property
    def is_pdf(self) -> bool:
        return self.kind == "pdf"

    @property
    def is_image_set(self) -> bool:
        return self.kind == "images" and len(self.work_images) > 1

    @property
    def page_count(self) -> int:
        return self._pdf_pages if self.is_pdf else len(self.work_images)

    # reading

    def render_target(self, index: int) -> tuple[Path, str, int]:
        """Return (path, render-kind, render-index) for rendering one page."""
        if self.is_pdf:
            assert self.work_path is not None
            return self.work_path, "pdf", index
        return self.work_images[index], "images", 0

    def scan_pages(self) -> list[PageText]:
        """The page model: digital text per page for PDFs, scanned for images."""
        if self.is_pdf:
            assert self.work_path is not None
            return self.toolkit.extract_text_layer(
                self.work_path, PageRanges.parse("1-"), detect_scanned=True
            )
        return [
            PageText(index=i, text="", kind=TextKind.SCANNED) for i in range(len(self.work_images))
        ]

    def ocr_path(self, current_index: int) -> Path:
        if self.is_pdf:
            assert self.work_path is not None
            return self.work_path
        return self.work_images[current_index]

    # editing - returns True if the edit changed page count/order

    def rotate(self, rows: list[int] | None, degrees: int) -> bool:
        if self.is_pdf:
            self._apply(lambda src, out: self.toolkit.rotate(src, degrees, out, self._ranges(rows)))
        else:
            self._edit_images(self._rows_or_all(rows), lambda im: im.rotate(-degrees, expand=True))
        return False

    def crop(self, rows: list[int] | None, box: CropBox) -> bool:
        if self.is_pdf:
            self._apply(lambda src, out: self.toolkit.crop(src, box, out, self._ranges(rows)))
        else:
            self._edit_images(self._rows_or_all(rows), lambda im: _crop_image(im, box))
        return False

    def remove(self, rows: list[int]) -> bool:
        drop = set(rows)
        remaining = [i for i in range(self.page_count) if i not in drop]
        if not remaining:
            raise ValueError("cannot remove every page")
        if self.is_pdf:
            ranges = PageRanges.parse(",".join(str(i + 1) for i in remaining))
            self._apply(lambda src, out: self.toolkit.extract_pages(src, ranges, out))
        else:
            self.work_images = [self.work_images[i] for i in remaining]
            self.dirty = True
        return True

    def reorder(self, order: list[int]) -> bool:
        if sorted(order) != list(range(self.page_count)):
            raise ValueError("reorder needs a permutation of all page indices")
        if self.is_pdf:
            self._apply(lambda src, out: self.toolkit.reorder(src, order, out))
        else:
            self.work_images = [self.work_images[i] for i in order]
            self.dirty = True
        return True

    def split_spreads(self, ratio: float) -> bool:
        self._apply(lambda src, out: self.toolkit.split_spreads(src, out, ratio=ratio))
        return True

    def append(self, extra: list[Path]) -> bool:
        self._apply(lambda src, out: self.toolkit.merge([src, *extra], out))
        return True

    def split(self, every: int, out_dir: Path | None) -> list[Path]:
        """Write the document out as multiple files; does not change the working copy."""
        assert self.work_path is not None
        return self.toolkit.split(self.work_path, every=every, out_dir=out_dir)

    def extract(self, rows: list[int], target: Path) -> None:
        """PDF: write selected pages to `target` (a file). Images: copy to `target` (a folder)."""
        if self.is_pdf:
            assert self.work_path is not None
            ranges = PageRanges.parse(",".join(str(r + 1) for r in rows))
            self.toolkit.extract_pages(self.work_path, ranges, target)
        else:
            for row in rows:
                src = self.work_images[row]
                shutil.copyfile(src, target / _display_name(src))

    # saving

    def save(self, target: Path | None = None) -> None:
        """Overwrite the source (target None) or write a copy to `target`."""
        work = self.work_path or self.work_images[0]
        dest = target or self.source
        shutil.copyfile(work, dest)
        if target is not None:
            self.source = target
        self.dirty = False

    def save_images(self, folder: Path) -> None:
        for src in self.work_images:
            shutil.copyfile(src, folder / _display_name(src))
        self.dirty = False

    def cleanup(self) -> None:
        shutil.rmtree(self.workdir, ignore_errors=True)

    # internals

    def _ranges(self, rows: list[int] | None) -> PageRanges | None:
        if rows is None:
            return None
        return PageRanges.parse(",".join(str(r + 1) for r in rows))

    def _rows_or_all(self, rows: list[int] | None) -> list[int]:
        return list(range(self.page_count)) if rows is None else rows

    def _apply(self, op: Callable[[Path, Path], object]) -> None:
        assert self.work_path is not None
        out = self.workdir / ("_edit_" + self.work_path.name)
        try:
            op(self.work_path, out)
        except Exception:
            out.unlink(missing_ok=True)
            raise
        os.replace(out, self.work_path)
        self.dirty = True
        self._pdf_pages = self.toolkit.page_count(self.work_path)

    def _edit_images(self, rows: list[int], transform: Callable[[object], object]) -> None:
        from PIL import Image

        for row in rows:
            path = self.work_images[row]
            with Image.open(path) as im:
                result = transform(im)
            result.save(path)
        self.dirty = True


def _crop_image(im: object, box: CropBox) -> object:
    w, h = im.size  # type: ignore[attr-defined]
    return im.crop(  # type: ignore[attr-defined]
        (int(box.left * w), int(box.top * h), int(box.right * w), int(box.bottom * h))
    )


def _display_name(work_path: Path) -> str:
    """Strip the 'NNN_' ordering prefix added to image working copies."""
    return work_path.name.split("_", 1)[-1]

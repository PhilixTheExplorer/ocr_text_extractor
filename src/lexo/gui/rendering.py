"""Shared page rendering for the desktop app.

Renders a PDF page or an image to a base64 PNG at a bounded size. Used by the
pages strip (small thumbnails), the page preview (large view), and the crop
dialog, so every surface shows the same pixels.
"""

from __future__ import annotations

import base64
import io
from pathlib import Path
from typing import Any


def render_pdf_page_from_doc(doc: Any, index: int, max_w: int, max_h: int) -> tuple[str, int, int]:
    import pymupdf

    page = doc[index]
    rect = page.rect
    zoom = min(max_w / rect.width, max_h / rect.height)
    pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom))
    return base64.b64encode(pix.tobytes("png")).decode(), pix.width, pix.height


def render_page(
    path: Path, kind: str, max_w: int, max_h: int, index: int = 0
) -> tuple[str, int, int]:
    """Return (base64 PNG, width, height) scaled to fit within max_w x max_h.

    For kind == "pdf", `index` selects the page; for images, `path` is the
    image and `index` is ignored.
    """
    if kind == "pdf":
        import pymupdf

        doc = pymupdf.open(path)
        try:
            return render_pdf_page_from_doc(doc, index, max_w, max_h)
        finally:
            doc.close()

    from PIL import Image

    with Image.open(path) as image:
        w, h = image.size
        scale = min(max_w / w, max_h / h, 1.0)
        disp = image.convert("RGB").resize((max(1, int(w * scale)), max(1, int(h * scale))))
    buffer = io.BytesIO()
    disp.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode(), disp.width, disp.height

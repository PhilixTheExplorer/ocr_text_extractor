"""Plain text export: page bodies joined by blank lines."""

from __future__ import annotations

from lexo.domain.models import ExtractedDoc


def to_text(doc: ExtractedDoc) -> str:
    parts = [page.text.strip() for page in doc.pages if page.text.strip()]
    return "\n\n".join(parts).strip() + "\n"

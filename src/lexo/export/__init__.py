"""Export sinks. Plain text is the default; Markdown and JSONL are also offered."""

from __future__ import annotations

from lexo.domain.models import ExtractedDoc
from lexo.export.jsonl import to_jsonl
from lexo.export.markdown import to_markdown
from lexo.export.text import to_text

EXTENSIONS = {"text": ".txt", "markdown": ".md", "jsonl": ".jsonl"}


def render(doc: ExtractedDoc, fmt: str, metadata: dict[str, object] | None = None) -> str:
    if fmt == "markdown":
        return to_markdown(doc, metadata)
    if fmt == "text":
        return to_text(doc)
    if fmt == "jsonl":
        return to_jsonl(doc)
    raise ValueError(f"unknown format: {fmt}")


__all__ = ["EXTENSIONS", "render", "to_jsonl", "to_markdown", "to_text"]

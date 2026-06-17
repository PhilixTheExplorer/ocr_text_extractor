"""Markdown export with YAML frontmatter. The default export format."""

from __future__ import annotations

from datetime import UTC, datetime

from lexo.domain.models import ExtractedDoc, TextKind


def _scalar(value: object) -> str:
    # Minimal YAML scalar: numbers bare, everything else quoted and escaped.
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int | float):
        return str(value)
    s = str(value).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{s}"'


def to_markdown(doc: ExtractedDoc, metadata: dict[str, object] | None = None) -> str:
    front: dict[str, object] = {
        "source": doc.source_name,
        "doc_id": doc.doc_id,
        "page_count": doc.page_count,
        "extracted_at": datetime.now(UTC).isoformat(),
    }
    if metadata:
        front.update(metadata)

    lines = ["---"]
    lines += [f"{key}: {_scalar(val)}" for key, val in front.items()]
    lines += ["---", ""]

    for page in doc.pages:
        lines.append(f"## Page {page.index + 1}")
        lines.append("")
        body = page.text.strip()
        if page.kind == TextKind.FAILED:
            message = page.error or "unknown error"
            lines.append(f"(OCR failed on this page: {message})")
        else:
            lines.append(body if body else "(no text layer on this page; OCR needed)")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"

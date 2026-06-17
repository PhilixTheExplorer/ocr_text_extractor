"""JSON Lines export, one record per page. Suited for NLP and LLM ingestion."""

from __future__ import annotations

import json

from lexo.domain.models import ExtractedDoc


def to_jsonl(doc: ExtractedDoc) -> str:
    lines = []
    for page in doc.pages:
        record = {
            "doc_id": doc.doc_id,
            "source": doc.source_name,
            "page": page.index + 1,
            "kind": page.kind.value,
            "text": page.text,
        }
        if page.error:
            record["error"] = page.error
        # ensure_ascii=False keeps Burmese (and other non-ASCII) readable.
        lines.append(json.dumps(record, ensure_ascii=False))
    return "\n".join(lines) + "\n"

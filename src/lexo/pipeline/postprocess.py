"""Post-process OCR text. Burmese-aware and safe for other scripts too."""

from __future__ import annotations

from lexo.text.burmese import clean_text, normalize_unicode


def postprocess(text: str) -> str:
    return _drop_leading_rule(clean_text(normalize_unicode(text)))


def _drop_leading_rule(text: str) -> str:
    lines = text.splitlines()
    while lines and _is_underscore_rule(lines[0]):
        lines.pop(0)
    return "\n".join(lines).strip()


def _is_underscore_rule(line: str) -> bool:
    stripped = line.strip()
    return len(stripped) >= 3 and set(stripped) == {"_"}

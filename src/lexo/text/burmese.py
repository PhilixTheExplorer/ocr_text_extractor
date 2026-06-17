"""Burmese (Myanmar script) text handling.

Two jobs that v1 got wrong or skipped:
1. Unicode NFC normalization for consistent storage.
2. ZWSP-safe cleaning: U+200B (zero width space) marks Burmese word and line
   breaks and must be preserved, while real control characters are dropped.
"""

from __future__ import annotations

import re
import unicodedata

ZWSP = chr(0x200B)


def normalize_unicode(text: str) -> str:
    return unicodedata.normalize("NFC", text)


def clean_text(text: str) -> str:
    """Normalize whitespace without destroying Burmese structure.

    Preserves newlines and ZWSP, drops other control/format characters,
    collapses runs of spaces and tabs, and trims trailing space per line.
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    kept: list[str] = []
    for ch in text:
        if ch in ("\n", "\t", ZWSP):
            kept.append(ch)
        elif unicodedata.category(ch).startswith("C"):
            # Other control or format characters: drop them.
            continue
        else:
            kept.append(ch)
    text = "".join(kept)

    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n")]
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

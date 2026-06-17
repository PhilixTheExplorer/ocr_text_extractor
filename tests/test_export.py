import json

import pytest

from lexo.domain.models import ExtractedDoc, PageText, TextKind
from lexo.export import render, to_jsonl, to_markdown, to_text


def _doc() -> ExtractedDoc:
    return ExtractedDoc(
        doc_id="abc",
        source_name="a.pdf",
        page_count=2,
        pages=[
            PageText(0, "Hello world", TextKind.DIGITAL),
            PageText(1, "Second page", TextKind.DIGITAL),
        ],
    )


def test_markdown_frontmatter_and_pages() -> None:
    md = to_markdown(_doc())
    assert md.startswith("---\n")
    assert 'source: "a.pdf"' in md
    assert "page_count: 2" in md
    assert "## Page 1" in md
    assert "Hello world" in md


def test_text_joins_pages() -> None:
    assert to_text(_doc()).strip() == "Hello world\n\nSecond page"


def test_jsonl_one_record_per_page_unicode() -> None:
    doc = ExtractedDoc("id", "f.pdf", 1, [PageText(0, "မြန်မာ", TextKind.DIGITAL)])
    record = json.loads(to_jsonl(doc).strip())
    assert record["text"] == "မြန်မာ"
    assert record["page"] == 1
    assert record["kind"] == "digital"


def test_failed_page_exports_error_marker() -> None:
    doc = ExtractedDoc(
        "id",
        "f.pdf",
        1,
        [PageText(0, "", TextKind.FAILED, error="boom")],
    )
    assert "OCR failed on this page: boom" in to_markdown(doc)
    assert json.loads(to_jsonl(doc).strip())["error"] == "boom"


def test_render_dispatch_and_unknown() -> None:
    assert render(_doc(), "text").strip() == "Hello world\n\nSecond page"
    with pytest.raises(ValueError):
        render(_doc(), "pptx")

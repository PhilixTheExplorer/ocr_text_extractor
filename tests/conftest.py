from pathlib import Path

import pymupdf
import pytest


@pytest.fixture
def make_pdf():
    def _make(path: Path, pages: int) -> Path:
        doc = pymupdf.open()
        for i in range(pages):
            page = doc.new_page()
            page.insert_text((72, 72), f"Page {i + 1}")
        doc.save(path)
        doc.close()
        return path

    return _make

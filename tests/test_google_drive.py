from lexo.providers.google_drive import _strip_export_title


def test_strip_export_title_removes_temp_doc_name_only() -> None:
    assert _strip_export_title("lexo-ocr-0\n\nBody\n", "lexo-ocr-0") == "Body\n"
    assert _strip_export_title("Real title\nBody\n", "lexo-ocr-0") == "Real title\nBody\n"

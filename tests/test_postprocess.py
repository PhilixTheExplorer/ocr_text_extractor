from lexo.pipeline.postprocess import postprocess


def test_postprocess_removes_leading_underscore_rule() -> None:
    assert postprocess("________________\nOCR text") == "OCR text"

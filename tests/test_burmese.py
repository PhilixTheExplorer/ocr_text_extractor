import unicodedata

from lexo.text.burmese import ZWSP, clean_text, normalize_unicode


def test_clean_preserves_zwsp() -> None:
    assert ZWSP in clean_text(f"foo{ZWSP}bar")


def test_clean_drops_control_keeps_newline() -> None:
    out = clean_text("a\x00b\nc")
    assert "\x00" not in out
    assert "\n" in out


def test_clean_collapses_spaces_and_tabs() -> None:
    assert clean_text("a    b\t\tc") == "a b c"


def test_normalize_nfc() -> None:
    decomposed = unicodedata.normalize("NFD", "é")
    assert normalize_unicode(decomposed) == "é"

import pytest

from lexo.domain.ranges import PageRanges


def test_single_and_list() -> None:
    assert PageRanges.parse("1,3,5").resolve(10) == [0, 2, 4]


def test_closed_range() -> None:
    assert PageRanges.parse("2-4").resolve(10) == [1, 2, 3]


def test_open_end() -> None:
    assert PageRanges.parse("8-").resolve(10) == [7, 8, 9]


def test_open_start() -> None:
    assert PageRanges.parse("-3").resolve(10) == [0, 1, 2]


def test_mixed_and_dedup() -> None:
    assert PageRanges.parse("1-3,2,7,10-").resolve(10) == [0, 1, 2, 6, 9]


def test_clamps_to_total() -> None:
    assert PageRanges.parse("5-100").resolve(6) == [4, 5]


def test_all_keyword() -> None:
    assert PageRanges.parse("all").resolve(4) == [0, 1, 2, 3]


def test_odd_keyword() -> None:
    # 1-based odd pages 1, 3, 5 -> 0-based 0, 2, 4.
    assert PageRanges.parse("odd").resolve(6) == [0, 2, 4]


def test_even_keyword() -> None:
    # 1-based even pages 2, 4, 6 -> 0-based 1, 3, 5.
    assert PageRanges.parse("even").resolve(6) == [1, 3, 5]


def test_keywords_are_case_insensitive() -> None:
    assert PageRanges.parse("ODD").resolve(5) == [0, 2, 4]


def test_keyword_combines_with_ranges() -> None:
    assert PageRanges.parse("odd,2").resolve(4) == [0, 1, 2]


@pytest.mark.parametrize("bad", ["", "0", "5-2", "a-b", "  ", "evens"])
def test_invalid(bad: str) -> None:
    with pytest.raises(ValueError):
        PageRanges.parse(bad)

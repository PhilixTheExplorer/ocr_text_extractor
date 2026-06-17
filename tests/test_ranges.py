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


@pytest.mark.parametrize("bad", ["", "0", "5-2", "a-b", "  "])
def test_invalid(bad: str) -> None:
    with pytest.raises(ValueError):
        PageRanges.parse(bad)

from lexo.gui.window.editing import reorder_for_move


def test_move_single_up() -> None:
    assert reorder_for_move(5, {2}, -1) == [0, 2, 1, 3, 4]


def test_move_single_down() -> None:
    assert reorder_for_move(5, {2}, 1) == [0, 1, 3, 2, 4]


def test_move_block_up_keeps_relative_order() -> None:
    assert reorder_for_move(5, {2, 3}, -1) == [0, 2, 3, 1, 4]


def test_move_block_down_keeps_relative_order() -> None:
    assert reorder_for_move(5, {1, 2}, 1) == [0, 3, 1, 2, 4]


def test_move_up_at_top_is_noop() -> None:
    assert reorder_for_move(5, {0, 1}, -1) is None


def test_move_down_at_bottom_is_noop() -> None:
    assert reorder_for_move(5, {3, 4}, 1) is None


def test_move_empty_selection_is_noop() -> None:
    assert reorder_for_move(5, set(), -1) is None


def test_move_non_contiguous_block_up() -> None:
    # Pages 1 and 3 each slide up past their unselected neighbour.
    assert reorder_for_move(5, {1, 3}, -1) == [1, 0, 3, 2, 4]

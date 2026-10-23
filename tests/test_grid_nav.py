"""Grid moves by row, which keys the grid acts on, the order thumbnails load in,
and the thumbnail size steps."""
from PySide6.QtCore import Qt

from tail_tagger.ui.grid_nav import (TILE_MAX, TILE_MIN, key_action, load_order, row_step,
                                     step_tile_size)


def test_down_moves_one_row_same_column():
    assert row_step(1, count=10, columns=4, rows=1) == 5


def test_up_moves_one_row_same_column():
    assert row_step(5, count=10, columns=4, rows=-1) == 1


def test_up_from_first_row_stays():
    assert row_step(2, count=10, columns=4, rows=-1) == 2


def test_down_from_last_row_stays():
    assert row_step(9, count=10, columns=4, rows=1) == 9


def test_down_into_short_last_row_lands_on_last():
    # Row 2 holds only images 8 and 9, so nothing sits under image 7
    assert row_step(7, count=10, columns=4, rows=1) == 9


def test_g_toggles_in_both_views():
    assert key_action(Qt.Key_G, grid_showing=False, typing=False, has_images=True) == "toggle"
    assert key_action(Qt.Key_G, grid_showing=True, typing=False, has_images=True) == "toggle"


def test_grid_keys_only_while_grid_shows():
    for key in (Qt.Key_Up, Qt.Key_Down, Qt.Key_Return, Qt.Key_Enter):
        assert key_action(key, grid_showing=False, typing=False, has_images=True) is None
    assert key_action(Qt.Key_Up, grid_showing=True, typing=False, has_images=True) == "up"
    assert key_action(Qt.Key_Down, grid_showing=True, typing=False, has_images=True) == "down"
    assert key_action(Qt.Key_Return, grid_showing=True, typing=False, has_images=True) == "open"
    assert key_action(Qt.Key_Enter, grid_showing=True, typing=False, has_images=True) == "open"


def test_typing_blocks_every_grid_key():
    for key in (Qt.Key_G, Qt.Key_Up, Qt.Key_Down, Qt.Key_Return):
        assert key_action(key, grid_showing=True, typing=True, has_images=True) is None


def test_no_images_blocks_every_grid_key():
    for key in (Qt.Key_G, Qt.Key_Up, Qt.Key_Down, Qt.Key_Return):
        assert key_action(key, grid_showing=True, typing=False, has_images=False) is None


def test_other_keys_do_nothing():
    assert key_action(Qt.Key_Left, grid_showing=True, typing=False, has_images=True) is None


def test_load_order_visible_then_ahead_then_behind():
    assert load_order(10, 12, count=100, ahead=2) == [10, 11, 12, 13, 14, 8, 9]


def test_load_order_clips_to_folder():
    assert load_order(0, 2, count=4, ahead=3) == [0, 1, 2, 3]


def test_tile_size_steps_and_clamps():
    assert step_tile_size(350, 1) == 390
    assert step_tile_size(350, -1) == 310
    assert step_tile_size(TILE_MAX, 1) == TILE_MAX
    assert step_tile_size(TILE_MIN, -3) == TILE_MIN

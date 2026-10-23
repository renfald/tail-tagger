"""Where a dragged tag lands. The white drop line and the final index are worked out from
row positions, which is easy to get off by one and hard to spot by eye."""
from tail_tagger.ui.tag_rows import final_index, insertion_point

ROW_HEIGHT = 23  # A tag row, as the list draws it
PITCH = ROW_HEIGHT + 1  # Rows have a 1 px gap above them


def rows(*data_indexes):
    """Visible rows stacked from the top of the list, as (top, bottom, data_index)."""
    result = []
    for slot, index in enumerate(data_indexes):
        top = 1 + slot * PITCH
        result.append((top, top + ROW_HEIGHT - 1, index))
    return result


def middle(row):
    top, bottom, _ = row
    return (top + bottom) // 2


def test_cursor_in_top_half_of_row_drops_before_it():
    shown = rows(0, 1, 2)
    line_y, index = insertion_point(shown, middle(shown[1]), total=3)
    assert (line_y, index) == (shown[1][0], 1)


def test_cursor_near_bottom_of_row_drops_after_it():
    shown = rows(0, 1, 2)
    line_y, index = insertion_point(shown, shown[1][1] - 5, total=3)
    assert (line_y, index) == (shown[2][0], 2)


def test_cursor_below_last_row_drops_at_end():
    shown = rows(0, 1, 2)
    line_y, index = insertion_point(shown, 500, total=3)
    assert (line_y, index) == (shown[2][1], 3)


def test_empty_list_drops_at_start():
    assert insertion_point([], 50, total=0) == (0, 0)


def test_grabbing_a_tag_and_moving_sideways_puts_it_back():
    # Tag 1 is grabbed and leaves the list, so tag 2 slides up under the cursor.
    # The cursor is still where the grab started (the middle of slot 1), which
    # must drop the tag back where it came from rather than below tag 2.
    shown = rows(0, 2, 3)
    _, index = insertion_point(shown, middle(shown[1]), total=4)
    assert final_index(index, original_index=1) == 1


def test_moving_down_lands_one_slot_up_from_the_line():
    # Insert indexes still count the dragged tag's old slot, so moving down shifts back one
    assert final_index(3, original_index=0) == 2


def test_moving_up_lands_at_the_line():
    assert final_index(0, original_index=2) == 0

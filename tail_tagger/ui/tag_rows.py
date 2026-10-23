"""Plain helpers for drawing and reordering tag rows: colors, text width, and drop position."""
from tail_tagger.ui.theme import TAG_CATEGORY_COLORS

STAR_SIZE = 22  # The favorite star shown at the right of a hovered known tag
TEXT_MARGIN = 3  # Padding around the name inside the tag box
DROP_LINE_OFFSET = 10  # The drop line moves past a row once the cursor is this close to its bottom
DRAG_THRESHOLD = 8  # Pixels the mouse must move with the button down before a press becomes a drag


def tag_colors(category, is_known, selected, dim_on_select):
    """Returns (background, text, stripe) colors for a tag row."""
    # Get category color, defaulting to '9' (unknown) if category is not found
    category_color = TAG_CATEGORY_COLORS.get(category, TAG_CATEGORY_COLORS["9"])

    if not is_known:
        # Unknown tags always use the invalid stripe, whatever their selection
        return "#552121", "#855252", TAG_CATEGORY_COLORS["6"]
    if dim_on_select and selected:
        return "#242424", "#888888", category_color
    return "#353535", "white", category_color


def text_width(row_width, is_known):
    """Width available for a tag's name in a row of row_width."""
    available = row_width - 1  # Safe buffer for the list's margins
    # For known tags, account for star icon space whether visible or not, so the
    # text doesn't jump when the star appears. Unknown tags never show a star.
    if is_known:
        available -= STAR_SIZE
    available -= 2 * TEXT_MARGIN
    # Apply a small buffer to ensure text doesn't touch edges
    return available - 1


def insertion_point(rows, y, total):
    """Where a dragged tag would land for a cursor at y.

    rows are the visible rows in order as (top, bottom, data_index), with bottom inclusive.
    Returns (line_y, insert_index); insert_index still counts the dragged tag's own slot.
    """
    for top, bottom, data_index in rows:
        # The line moves below a row once the cursor gets within DROP_LINE_OFFSET of its bottom
        if y < bottom - DROP_LINE_OFFSET:
            return top, data_index
    if rows:
        return rows[-1][1], total
    return 0, 0


def final_index(insert_index, original_index):
    """The tag's index after the move. insert_index counts its old slot, so moving down shifts back one."""
    if insert_index > original_index:
        return insert_index - 1
    return insert_index

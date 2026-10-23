"""Plain helpers for the grid view: moving by rows, which keys act, load order, tile size."""
from PySide6.QtCore import Qt

TILE_DEFAULT = 350  # Tile size in pixels when the app starts
TILE_MIN = 120
TILE_MAX = 520
TILE_STEP = 40  # Pixels added or removed per Ctrl+wheel notch


def row_step(index, count, columns, rows):
    """The index one row up (rows=-1) or down (rows=1) from index, in the same column.

    Returns index unchanged when there is no row in that direction. Moving down into a
    last row that is too short to have this column lands on the last image.
    """
    target = index + rows * columns
    if rows < 0:
        return target if target >= 0 else index
    last_row = (count - 1) // columns
    if target // columns > last_row:
        return index
    return min(target, count - 1)


def key_action(key, grid_showing, typing, has_images):
    """What a key press does for the grid: "toggle", "up", "down", "open", or None.

    Nothing happens while the user types in a text box, or when there are no images.
    G works in both views; the others only while the grid is showing.
    """
    if typing or not has_images:
        return None
    if key == Qt.Key_G:
        return "toggle"
    if not grid_showing:
        return None
    if key == Qt.Key_Up:
        return "up"
    if key == Qt.Key_Down:
        return "down"
    if key in (Qt.Key_Return, Qt.Key_Enter):
        return "open"
    return None


def load_order(first, last, count, ahead):
    """Indexes to load thumbnails for: the visible ones first..last, then ahead after
    them, then ahead before them. Clipped to the folder, with no repeats."""
    order = list(range(first, last + 1))
    order += range(last + 1, last + 1 + ahead)
    order += range(first - ahead, first)
    result = []
    for index in order:
        if 0 <= index < count and index not in result:
            result.append(index)
    return result


def step_tile_size(size, notches):
    """The tile size after notches of Ctrl+wheel, kept between TILE_MIN and TILE_MAX."""
    return max(TILE_MIN, min(TILE_MAX, size + notches * TILE_STEP))

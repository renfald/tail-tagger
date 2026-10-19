"""List rules for the current image's tags and for favorites.

Plain functions on tag names, with no Qt. MainWindow calls these to work out the new
order, then applies the result to TagData objects, saves, and refreshes panels.
Every function returns a new list and leaves its inputs unchanged.
"""

from typing import Callable

IsVisible = Callable[[str], bool]


def toggle_name(order: list[str], name: str) -> list[str]:
    """Removes every occurrence of name if present, otherwise appends it."""
    if name in order:
        return [n for n in order if n != name]
    return order + [name]


def append_names(order: list[str], names: list[str]) -> list[str]:
    """Appends each name not already in order, keeping the given order, once each."""
    result = list(order)
    for name in names:
        if name not in result:
            result.append(name)
    return result


def move_name(order: list[str], name: str, index: int) -> list[str]:
    """Moves name to index, clamped to the valid range. Unchanged if name is absent."""
    if name not in order:
        return list(order)
    result = [n for n in order if n != name]
    index = max(0, min(index, len(result)))
    result.insert(index, name)
    return result


def visible_favorites(all_names: list[str], is_visible: IsVisible) -> list[str]:
    """Favorites shown for the current tag source, in order, each name once."""
    result = []
    for name in all_names:
        if name not in result and is_visible(name):
            result.append(name)
    return result


def move_favorite_name(all_names: list[str], is_visible: IsVisible, name: str, new_visible_index: int) -> list[str]:
    """Moves a favorite to new_visible_index within the visible favorites.

    The moved name is placed in front of the next visible favorite, or after the previous
    one when it ends up last, so favorites hidden by the tag source keep their positions.
    """
    visible = visible_favorites(all_names, is_visible)
    if name not in visible or len(visible) < 2:
        return list(all_names)

    visible_after = move_name(visible, name, new_visible_index)
    pos = visible_after.index(name)
    rest = [n for n in all_names if n != name]
    if pos + 1 < len(visible_after):
        insert_at = rest.index(visible_after[pos + 1])
    else:
        insert_at = rest.index(visible_after[pos - 1]) + 1
    rest.insert(insert_at, name)
    return rest

from tail_tagger.tag_state import (toggle_name, append_names, move_name,
                                   visible_favorites, move_favorite_name)

E621 = {"e1", "e2", "e3"}.__contains__


def test_toggle_appends_and_removes():
    assert toggle_name(["a", "b"], "c") == ["a", "b", "c"]
    assert toggle_name(["a", "b"], "a") == ["b"]


def test_toggle_removes_every_copy():
    assert toggle_name(["a", "b", "a"], "a") == ["b"]


def test_append_skips_present_and_repeats():
    assert append_names(["a"], ["b", "a", "c", "b"]) == ["a", "b", "c"]


def test_move_name():
    assert move_name(["a", "b", "c"], "a", 2) == ["b", "c", "a"]
    assert move_name(["a", "b", "c"], "c", 0) == ["c", "a", "b"]
    assert move_name(["a", "b", "c"], "a", 99) == ["b", "c", "a"]
    assert move_name(["a", "b"], "z", 0) == ["a", "b"]


def test_inputs_not_mutated():
    order = ["a", "b"]
    toggle_name(order, "a")
    append_names(order, ["c"])
    move_name(order, "a", 1)
    assert order == ["a", "b"]


def test_visible_favorites_filters_and_dedupes():
    assert visible_favorites(["e1", "d1", "e2", "e1"], E621) == ["e1", "e2"]


def test_move_favorite_between_visible():
    assert move_favorite_name(["e1", "d1", "e2", "d2", "e3"], E621, "e3", 1) == ["e1", "d1", "e3", "e2", "d2"]


def test_move_favorite_to_end():
    assert move_favorite_name(["e1", "d1", "e2", "d2", "e3"], E621, "e1", 2) == ["d1", "e2", "d2", "e3", "e1"]


def test_move_favorite_keeps_other_source_order():
    shared = {"s1", "s2", "e1"}.__contains__
    result = move_favorite_name(["s1", "d1", "s2", "e1"], shared, "e1", 0)
    assert result == ["e1", "s1", "d1", "s2"]


def test_move_favorite_noops():
    assert move_favorite_name(["e1", "d1"], E621, "d1", 0) == ["e1", "d1"]
    assert move_favorite_name(["e1", "d1"], E621, "e1", 0) == ["e1", "d1"]


def test_move_favorite_collapses_duplicates():
    assert move_favorite_name(["e1", "e2", "e1"], E621, "e1", 1) == ["e2", "e1"]

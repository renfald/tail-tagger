import random
import re
from collections import defaultdict
from collections.abc import Mapping
from itertools import chain
from functools import cache
from sys import intern
from typing import Callable, Iterable, TextIO, cast

from ._compat import Self

import torch
from torch import Tensor

__all__ = (
    "TAG_CATEGORIES",
    "Label", "Rewriter",
    "parse_aliases", "parse_list", "parse_expandable_list"
)

TAG_CATEGORIES = [
    "general",
    "artist",
    "contributor",
    "copyright",
    "character",
    "species",
    "invalid",
    "meta",
    "lore",
]

COLOR_PREFIXES = (
    "black_",
    "blue_",
    "brown_",
    "green_",
    "grey_",
    "orange_",
    "pink_",
    "purple_",
    "red_",
    "tan_",
    "teal_",
    "white_",
    "yellow_",

    "dark_",
    "darkened_",
    "light_",
    "blonde_",

    "monotone_",
    "two_tone_",
    "countershad",
    "reverse_countershad",
    "multicolored_",

    "camo_",
    "cosmic_",
    "mottled_",
    "plaid_",
    "pride_color_",
    "rainbow_",
)

COLOR_EXCEPTIONS = (
    "_background",
    "_border",
    "_outline",

    "_bars",
    "_flag",

    "dark_room",
    "light_beam",
    "light_bulb",
    "rainbow_symbol",
    "tan_line",
)

class Label:
    __slots__ = ("label", "category", "implies", "implied_by", "validation")

    def __init__(
        self,
        label: str, category: str,
        implies: Iterable[str] = (),
        validation: Tensor | None = None,
        *,
        implied_by: Iterable[str] = ()
    ):
        self.label = intern(label)
        self.category = intern(category)
        self.implies = [intern(impl) for impl in implies]
        self.validation = validation
        self.implied_by = [intern(impl) for impl in implied_by]

    def __str__(self) -> str:
        return self.label

    @property
    @cache
    def subcategory(self) -> str | None:
        if (
            self.category == "meta"
            and self.label in ("safe", "questionable", "explicit")
        ):
            return "rating"

        if (
            self.category == "general"
            and self.label.startswith(COLOR_PREFIXES)
            and not self.label.endswith(COLOR_EXCEPTIONS)
        ):
            return "color"

        return None

    @staticmethod
    def init_graph(labels: dict[str, "Label"] | Iterable["Label"]) -> dict[str, "Label"]:
        if not isinstance(labels, dict):
            labels = {
                label.label: label
                for label in labels
            }

        for label in labels.values():
            for implied in label.implies:
                if (implied_label := labels.get(implied)) is not None:
                    implied_label.implied_by.append(label.label)

        return labels

    @staticmethod
    def expand_list(
        value: Iterable[tuple[str, bool]] | TextIO | str,
        labels: Mapping[str, "Label"] | Iterable["Label"]
    ) -> set[str]:
        if isinstance(value, (TextIO, str)):
            value = parse_expandable_list(value)

        expanded: set[str] = set()
        def _expand(label: str) -> None:
            if (label_obj := cast(Mapping, labels).get(label)) is None:
                return

            for label in label_obj.implied_by:
                expanded.add(label)
                _expand(label)

        for label, expand in value:
            if expand:
                if not isinstance(labels, Mapping):
                    labels = {
                        label.label: label
                        for label in labels
                        if label.implied_by
                    }

                _expand(label)
            else:
                expanded.add(label)

        return expanded

class Rewriter(dict[str, str]):
    __slots__ = ("rewrite_fn", "separator")

    def __init__(
        self,
        rewrite_fn: Callable[[Label], str],
        separator: str = ", ",
        labels: Iterable[Label] | None = None,
        *,
        check: bool = True,
    ) -> None:
        super().__init__()

        self.rewrite_fn = rewrite_fn
        self.separator = separator

        if labels is not None:
            self.add(labels)

            if check:
                self.check()

    def add(self, labels: Iterable[Label]) -> None:
        for label in labels:
            if label.label not in self:
                self[label.label] = self.rewrite_fn(label)

    def check(self) -> None:
        if (conflicts := self.conflicts(self.items())):
            raise ValueError("Conflicting rewritten tags: " + "; ".join(
                " ".join(repr(key) for key in keys) + f" > {repr(value)}"
                for keys, value in conflicts
            ))

    def rewrite(self, labels: Iterable[str]) -> Iterable[str]:
        for label in labels:
            yield self[label]

    def rewrite_join(
        self, labels: Iterable[str], *,
        prefix: str | None = "",
        shuffle: bool = False
    ) -> str:
        return self.join(
            self.rewrite(labels), sep=self.separator,
            prefix=prefix, shuffle=shuffle
        )

    def unjoin(self, labels: str) -> Iterable[str]:
        return self.split(labels, self.separator)

    @staticmethod
    def join(
        labels: Iterable[str], *,
        sep: str = ", ",
        prefix: str | None = "",
        shuffle: bool = False
    ) -> str:
        if shuffle:
            labels = list(labels)
            random.shuffle(labels)

        if prefix and (prefix_labels := Rewriter.split(prefix, sep)):
            labels = chain(prefix_labels, filter(lambda label: label not in prefix_labels, labels))

        return str.join(sep, labels)

    @staticmethod
    def split(labels: str, sep: str = ",") -> Iterable[str]:
        if sep in ("", " "):
            return labels.split()

        return filter(bool, re.split(rf"\s*(?:{re.escape(sep.strip() or sep)}|[\t\r\n])\s*", labels))

    @staticmethod
    def create(
        labels: Iterable[Label] | None = None,
        *,
        aliases: Mapping[str, str] | str | None = None,
        prefixes: Mapping[str, str] | str | None = None,
        separator: str | None = None,
        spaces: bool = True,
        escape: bool = False,
    ) -> "Rewriter":
        if aliases is None:
            aliases = {}
        elif isinstance(aliases, str):
            aliases = dict(parse_aliases(aliases))

        if prefixes is None:
            prefixes = {}
        elif isinstance(prefixes, str):
            prefixes = dict(parse_aliases(prefixes))

        trans: dict[int, str] = {}
        if spaces:
            trans[ord("_")] = " "

        if escape:
            trans[ord("(")] = r"\("
            trans[ord(")")] = r"\)"
            trans[ord(":")] = r"\:"

        def rewrite(label: Label) -> str:
            rewritten = label.label

            if (alias := aliases.get(rewritten)) is not None:
                rewritten = alias

            if (prefix := prefixes.get(label.category)) is not None:
                rewritten = prefix + rewritten

            if trans:
                rewritten = rewritten.translate(trans)

            return rewritten

        if separator is None:
            separator = ", " if spaces else " "

        return Rewriter(rewrite, separator, labels)

    @staticmethod
    def conflicts(mapping: Iterable[tuple[str, str]]) -> list[tuple[list[str], str]]:
        reverse: dict[str, list[str]] = defaultdict(list)
        conflicts: list[tuple[list[str], str]] = []
        for k, v in mapping:
            bucket = reverse[v]
            bucket.append(k)
            if len(bucket) == 2:
                conflicts.append((bucket, v))

        return conflicts

def parse_list(value: TextIO | str) -> Iterable[str]:
    if not isinstance(value, str):
        value = value.read()

    for line in value.splitlines():
        yield from re.split(r"(?:^| |\t)#", line, maxsplit=1)[0].split()

def parse_expandable_list(value: TextIO | str, *, strict: bool = False) -> Iterable[tuple[str, bool]]:
    if not isinstance(value, str):
        value = value.read()

    for idx, line in enumerate(value.splitlines()):
        for label in re.split(r"(?:^| |\t)#", line, maxsplit=1)[0].split():
            if label.startswith("~~"):
                if len(label) > 2:
                    yield (label[2:], True)
                elif strict:
                    raise ValueError(f"Stray '~~' on line {idx+1}.")
            elif label.startswith("~"):
                if len(label) > 1:
                    label = label[1:]
                    yield (label, False)
                    yield (label, True)
                elif strict:
                    raise ValueError(f"Stray '~' on line {idx+1}.")
            else:
                yield (label[1:], False)

def parse_aliases(value: TextIO | str) -> Iterable[tuple[str, str]]:
    if not isinstance(value, str):
        value = value.read()

    for idx, line in enumerate(value.splitlines()):
        line = re.split(r"(?:^| |\t)#", line, maxsplit=1)[0]

        parts = line.split()
        match len(parts):
            case 0:
                pass
            case 2:
                yield tuple(parts) # type: ignore
            case _:
                raise ValueError(f"Invalid alias on line {idx+1}: {repr(line)}")

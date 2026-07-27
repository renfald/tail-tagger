from collections.abc import Mapping
from dataclasses import dataclass
from functools import cache
from itertools import islice
from math import log
from typing import Callable, Iterable, Iterator, Sequence, Literal, TextIO, TypeAlias
import re

import torch
from torch import Tensor

from .label import Label

__all__ = (
    "IMPLICATION_MODES", "DEFAULT_METRIC",
    "Metric", "MetricLike", "Operator",
    "Calibration",
    "ExclusiveGroup", "FilterLabels", "FilterResults", "QualifyResults", "SortResults",
    "InheritImplications", "ConstrainImplications", "RemoveImplications",
    "min_pr", "f_score", "csi", "simple_slider",
    "log_interval", "interval_exp",
    "parse_metric",
)

IMPLICATION_MODES = (
    "preserve",
    "inherit",
    "constrain",
    "enforce",
    "remove",
    "constrain-remove",
    "enforce-inherit",
    "enforce-constrain",
    "enforce-remove",
    "off"
)

Metric: TypeAlias = Callable[[Tensor], Tensor]
MetricLike: TypeAlias = Metric | Iterable[float] | float | str
Operator: TypeAlias = Callable[["Calibration", dict[str, float]], None]

TP = 0
FP = 1
TN = 2
FN = 3

def min_precision(inner: Metric, min_precision: float) -> Metric:
    if not 0.0 <= min_precision <= 1.0:
        raise ValueError("min_precision must be between 0.0 and 1.0, inclusive")

    if min_precision == 0.0:
        return inner

    @torch.inference_mode()
    def _min_precision(matrix: Tensor) -> Tensor:
        p = matrix[..., TP] / (matrix[..., TP] + matrix[..., FP])
        return torch.where(p >= min_precision, inner(matrix), float("-inf"))

    return _min_precision

def f_score(beta: float = 1.0) -> Metric:
    if beta <= 0.0:
        raise ValueError("beta must be positive")

    w_fn = beta * beta
    w_tp = 1.0 + w_fn

    @torch.inference_mode()
    def _f_score(matrix: Tensor) -> Tensor:
        wtp = matrix[..., TP] * w_tp
        return (wtp / (
            wtp +
            matrix[..., FP] +
            matrix[..., FN] * w_fn
        )).nan_to_num_()

    return _f_score

def csi(w_fp: float = 1.0) -> Metric:
    if w_fp <= 0.0:
        raise ValueError("w_fp must be positive")

    @torch.inference_mode()
    def _csi(matrix: Tensor) -> Tensor:
        return (matrix[..., TP] / (
            matrix[..., TP] +
            matrix[..., FP] * w_fp +
            matrix[..., FN]
        )).nan_to_num_()

    return _csi

DEFAULT_METRIC = min_precision(f_score(1.0), 0.1)

_EMPTY: frozenset = frozenset()

def log_interval(value: float, scale: float) -> float:
    assert 0.0 <= value <= 1.0
    assert scale > 0.0

    return scale**(1.0 - 2 * value)

def interval_exp(value: float, scale: float, *, clamp: bool = False) -> float:
    assert scale > 0.0

    value = (1.0 - log(value, scale)) / 2

    if clamp:
        value = min(max(value, 0.0), 1.0)

    return value

def simple_slider(
    value: float,
    min_precision: float = 0.1,
    metric: Callable[[float], Metric] = f_score,
    scale: float = 4.0
) -> Metric:
    return globals()["min_precision"](metric(log_interval(value, scale)), min_precision)

def parse_metric(value: str) -> Metric:
    if value == "default":
        return DEFAULT_METRIC

    if (match := re.fullmatch(r"(f|csi)([0-9]+\.[0-9]+)?(?:@(0\.[0-9]+))?", value)) is None:
        raise ValueError("Invalid metric.")

    metric, arg_s, prec_s = match.groups()

    arg = float(arg_s) if arg_s else 1.0
    prec = float(prec_s) if prec_s else 0.0

    metric_fn: Callable[[float], Metric]
    match metric:
        case "f":
            metric_fn = f_score
        case "csi":
            metric_fn = csi
        case _:
            raise AssertionError

    return min_precision(metric_fn(arg), prec)

class CalibrationProxy(Mapping[str, Label]):
    __slots__ = ("calibration",)

    def __init__(self, calibration: "Calibration") -> None:
        self.calibration = calibration

    def __getitem__(self, key: str) -> Label:
        return self.calibration[key][0]

    def __iter__(self) -> Iterator[str]:
        return iter(self.calibration)

    def __len__(self) -> int:
        return len(self.calibration)

class Calibration(dict[str, tuple[Label, float]]):
    __slots__ = ()

    def __init__(self, labels: Iterable[Label], metric: MetricLike) -> None:
        if callable(metric):
            super().__init__(
                (label.label, (label, self.calibrate_label(label, metric)[0]))
                for label in labels
            )
        elif isinstance(metric, str):
            metric = parse_metric(metric)
            super().__init__(
                (label.label, (label, self.calibrate_label(label, metric)[0]))
                for label in labels
            )
        elif isinstance(metric, float):
            super().__init__(
                (label.label, (label, metric))
                for label in labels
            )
        else:
            super().__init__(
                (label.label, (label, threshold))
                for label, threshold in zip(labels, metric, strict=True)
            )

    def __setitem__(self, key: str, value: Metric | float | None) -> None: # type: ignore[override]
        label = self[key][0]

        if value is None:
            value = float("inf")
        elif callable(value):
            value = self.calibrate_label(label, value)[0]

        super().__setitem__(label.label, (label, value))

    def __delitem__(self, key: str) -> None:
        super().__setitem__(key, (self[key][0], float("inf")))

    def labels(self) -> Iterable[Label]:
        for label, _ in self.values():
            yield label

    def thresholds(self) -> Iterable[float]:
        for _, threshold in self.values():
            yield threshold

    def as_thresholds(self) -> list[float]:
        return list(self.thresholds())

    def get_threshold(self, label: str) -> float:
        return self[label][1]

    def labels_proxy(self) -> CalibrationProxy:
        return CalibrationProxy(self)

    def classify_output(
        self, output: Tensor,
        *,
        implications: str = "off",
        exclude_labels: set[str] | frozenset[str] | str | None = _EMPTY,
        exclude_categories: set[str] | frozenset[str] | str | None = _EMPTY,
        exclusive_groups: Iterable["ExclusiveGroup"] | str = (),
        sort: bool = True,
    ) -> dict[str, float]:
        if isinstance(exclude_labels, str):
            exclude_labels = Label.expand_list(exclude_labels, self.labels_proxy())

        if isinstance(exclude_categories, str):
            exclude_categories = set(exclude_categories.split())

        if isinstance(exclusive_groups, str):
            exclusive_groups = ExclusiveGroup.parse_file(exclusive_groups)

        return self.apply_to_output(output,
            self.default_operators(
                implications=implications,
                exclude_labels=exclude_labels,
                exclude_categories=exclude_categories,
                post_qualify=exclusive_groups,
                sort=sort,
            )
        )

    def classify_outputs(
        self, outputs: Tensor,
        *,
        implications: str = "off",
        exclude_labels: set[str] | frozenset[str] | str | None = _EMPTY,
        exclude_categories: set[str] | frozenset[str] | str | None = _EMPTY,
        exclusive_groups: Sequence["ExclusiveGroup"] | str = (),
        sort: bool = True,
    ) -> list[dict[str, float]]:
        if isinstance(exclude_labels, str):
            exclude_labels = Label.expand_list(exclude_labels, self.labels_proxy())

        if isinstance(exclude_categories, str):
            exclude_categories = set(exclude_categories.split())

        if isinstance(exclusive_groups, str):
            exclusive_groups = list(ExclusiveGroup.parse_file(exclusive_groups))

        return list(self.apply_to_outputs(outputs,
            list(self.default_operators(
                implications=implications,
                exclude_labels=exclude_labels,
                exclude_categories=exclude_categories,
                post_qualify=exclusive_groups,
                sort=sort,
            ))
        ))

    def apply_to_output(self, output: Tensor, operators: Iterable[Operator]) -> dict[str, float]:
        if output.shape != (len(self),):
            raise ValueError(f"Output tensor has shape {output.shape}, not ({len(self)}).")

        results = {
            label: prob
            for label, prob in zip(self.keys(), output.tolist())
        }

        for op in operators:
            op(self, results)

        return results

    def apply_to_outputs(self, outputs: Tensor, operators: Sequence[Operator]) -> Iterable[dict[str, float]]:
        match outputs.ndim:
            case 1:
                yield self.apply_to_output(outputs, operators)
            case 2:
                for output in outputs.unbind(0):
                    yield self.apply_to_output(output, operators)
            case _:
                raise ValueError(f"Outputs tensor has {outputs.ndim} dimensions, but expected 1 or 2.")

    @staticmethod
    def default_operators(
        implications: str = "off",
        exclude_labels: set[str] | frozenset[str] | None = _EMPTY,
        exclude_categories: set[str] | frozenset[str] | None = _EMPTY,
        post_qualify: Iterable[Operator] = (),
        sort: bool = False,
    ) -> Iterable[Operator]:
        if implications in ("preserve", "inherit", "constrain"):
            yield QualifyImplications
        elif implications in ("enforce", "enforce-inherit", "enforce-constrain", "enforce-remove"):
            yield EnforceImplications
        elif implications in ("remove", "constrain-remove", "off"):
            yield ThresholdResults
        else:
            raise ValueError("Invalid implications mode.")

        yield from post_qualify

        if exclude_labels or exclude_categories:
            if exclude_labels is None:
                exclude_labels = _EMPTY
            if exclude_categories is None:
                exclude_categories = _EMPTY

            yield FilterLabels(lambda label: (
                label.category not in exclude_categories
                and label.subcategory not in exclude_categories
                and label.label not in exclude_labels
            ))

        if implications in ("inherit", "enforce-inherit"):
            yield InheritImplications
        elif implications in ("constrain", "constrain-remove", "enforce-constrain"):
            yield ConstrainImplications

        if implications in ("remove", "constrain-remove", "enforce-remove"):
            yield RemoveImplications

        if sort:
            yield SortResults

    @staticmethod
    def calibrate_labels(labels: Iterable[Label], metric: Metric) -> Iterable[float]:
        for label in labels:
            yield Calibration.calibrate_label(label, metric)[0]

    @staticmethod
    def calibrate_label(label: Label, metric: Metric) -> tuple[float, float | None]:
        if label.validation is None:
            raise ValueError(f"Label {repr(label.label)} is missing validation data for calibration.")

        return Calibration.calibrate(label.validation, metric)

    @torch.inference_mode()
    @staticmethod
    def calibrate(validation: Tensor, metric: Metric) -> tuple[float, float | None]:
        best_score, best_idx = metric(validation).max(0)

        score_val = best_score.item()
        if score_val == float("-inf"):
            return float("inf"), None

        best_threshold = (best_idx.item() + 1) / (validation.size(0) + 1)
        return Calibration.bf16_threshold(best_threshold), score_val

    @cache
    @staticmethod
    def bf16_threshold(value: float) -> float:
        return (
            torch.tensor(value, device="cpu", dtype=torch.float32)
            .logit_()
            .to(dtype=torch.bfloat16)
            .to(dtype=torch.float32)
            .sigmoid_()
            .item()
        )

@dataclass(eq=False, match_args=False, slots=True)
class ExclusiveGroup:
    group: Sequence[str]
    requirements: Sequence[str] = ()
    exceptions: Sequence[str] = ()

    def __call__(self, calibration: "Calibration", results: dict[str, float]) -> None:
        for requirement in self.requirements:
            if results.get(requirement, float("-inf")) < calibration.get_threshold(requirement):
                return

        for exception in self.exceptions:
            if results.get(exception, float("-inf")) >= calibration.get_threshold(exception):
                return

        best_label: str | None = None
        best_prob = float("-inf")
        for label in self.group:
            if (prob := results.get(label)) is None:
                continue

            if prob <= best_prob:
                del results[label]
                _remove_antecedents(results, label, calibration)
                continue

            if best_label is not None:
                results.pop(best_label, None) # malformed group could have removed best label
                _remove_antecedents(results, best_label, calibration)

            best_label = label
            best_prob = prob

    @staticmethod
    def parse(value: Sequence[str] | str) -> "ExclusiveGroup":
        parts = value.split() if isinstance(value, str) else value

        split_idx = 0
        for idx, part in enumerate(parts):
            if part.endswith(":"):
                split_idx = idx + 1
            elif not part:
                raise ValueError(f"Item {idx+1} is empty.")

        requirements: list[str] = []
        exceptions: list[str] = []
        if split_idx:
            for idx, part in enumerate(islice(parts, split_idx)):
                if part.endswith(":"):
                    if len(part) == 1:
                        continue

                    part = part[:-1]

                if part.startswith("!"):
                    if len(part) == 1:
                        raise ValueError(f"Item {idx+1} is empty.")

                    exceptions.append(part[1:])
                else:
                    requirements.append(part)

        group: list[str] = []
        for part in islice(parts, split_idx, None):
            if part not in group:
                group.append(part)

        if len(group) < 2:
            raise ValueError(f"At least two distinct items are required.")

        return ExclusiveGroup(group, requirements, exceptions)

    @staticmethod
    def parse_file(value: TextIO | str) -> Iterable["ExclusiveGroup"]:
        if not isinstance(value, str):
            value = value.read()

        for idx, line in enumerate(value.splitlines()):
            line = re.split(r"(?:^| |\t)#", line, maxsplit=1)[0]
            if (parts := line.split()):
                try:
                    yield ExclusiveGroup.parse(parts)
                except ValueError as ex:
                    raise ValueError(f"Invalid group on line {idx+1}: {ex}") from ex

class FilterLabels:
    def __init__(self, filter_fn: Callable[[Label], bool]) -> None:
        self.filter_fn = filter_fn

    def __call__(self, calibration: Calibration, results: dict[str, float]) -> None:
        for label in list(results.keys()):
            if not self.filter_fn(calibration[label][0]):
                del results[label]

def QualifyImplications(calibration: Calibration, results: dict[str, float]) -> None:
    qualified: set[str] = set()
    for label, prob in results.items():
        if prob >= calibration.get_threshold(label):
            _qualify_label(qualified, label, calibration)

    for label in calibration.keys():
        if label not in qualified:
            results.pop(label, None)

def EnforceImplications(calibration: Calibration, results: dict[str, float]) -> None:
    for label, threshold in calibration.values():
        if results.get(label.label, float("-inf")) < threshold:
            del results[label.label]
            _remove_antecedents(results, label.label, calibration)

def ThresholdResults(calibration: Calibration, results: dict[str, float]) -> None:
    for label, threshold in calibration.values():
        if results.get(label.label, float("-inf")) < threshold:
            del results[label.label]

def InheritImplications(calibration: Calibration, results: dict[str, float]) -> None:
    for result, prob in results.items():
        _inherit_implications(results, result, prob, calibration)

def ConstrainImplications(calibration: Calibration, results: dict[str, float]) -> None:
    for result, prob in results.items():
        _constrain_implications(results, result, prob, calibration)

def RemoveImplications(calibration: Calibration, results: dict[str, float]) -> None:
    for result in list(results.keys()):
        _remove_consequents(results, result, calibration)

def SortResults(calibration: Calibration, results: dict[str, float]) -> None:
    values = sorted(results.items(), key=lambda item: (-item[1], item[0]))
    results.clear()
    results.update(values)

def _qualify_label(
    qualified: set[str], label: str,
    labels: dict[str, tuple[Label, float]]
) -> None:
    if (label_info := labels.get(label)) is None:
        return

    if label in qualified:
        return

    qualified.add(label)

    for consequent in label_info[0].implies:
        _qualify_label(qualified, consequent, labels)

def _inherit_implications(
    outputs: dict[str, float],
    antecedent: str, prob: float,
    labels: dict[str, tuple[Label, float]]
) -> None:
    if (label := labels.get(antecedent)) is None:
        return

    for consequent in label[0].implies:
        if outputs.get(consequent, float("+inf")) < prob:
            outputs[consequent] = prob

        _inherit_implications(outputs, consequent, prob, labels)

def _constrain_implications(
    outputs: dict[str, float],
    consequent: str, prob: float,
    labels: dict[str, tuple[Label, float]]
) -> None:
    if (label := labels.get(consequent)) is None:
        return

    for antecedent in label[0].implied_by:
        if outputs.get(antecedent, float("-inf")) > prob:
            outputs[antecedent] = prob

        _constrain_implications(outputs, antecedent, prob, labels)

def _remove_antecedents(
    outputs: dict[str, float], consequent: str,
    labels: dict[str, tuple[Label, float]]
) -> None:
    if (label := labels.get(consequent)) is None:
        return

    for antecedent in label[0].implied_by:
        outputs.pop(antecedent, None)
        _remove_antecedents(outputs, antecedent, labels)

def _remove_consequents(
    outputs: dict[str, float], antecedent: str,
    labels: dict[str, tuple[Label, float]]
) -> None:
    if (label := labels.get(antecedent)) is None:
        return

    for consequent in label[0].implies:
        outputs.pop(consequent, None)
        _remove_consequents(outputs, consequent, labels)


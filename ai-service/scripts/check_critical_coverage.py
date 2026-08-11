"""Enforce branch-aware coverage for the production-critical modules.

The regular pytest coverage threshold protects the repository as a whole.  This
small command adds the second contract required by the training runbook: a
critical module cannot hide an uncovered branch behind a healthy global average.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

CRITICAL_THRESHOLDS: dict[str, float] = {
    "src/ai_service/training/checkpoint.py": 90.0,
    "src/ai_service/evaluation/report.py": 90.0,
    "src/ai_service/export/bundle.py": 90.0,
    "src/ai_service/evaluation/release.py": 90.0,
    "src/ai_service/training/trainer.py": 85.0,
    "src/ai_service/training/pipeline.py": 85.0,
}


@dataclass(frozen=True)
class CoverageResult:
    path: str
    observed: float
    required: float

    @property
    def passed(self) -> bool:
        return self.observed + 1e-12 >= self.required


def _normalise_path(path: str) -> str:
    """Return the repository-relative source path used by the threshold map."""

    normalised = path.replace("\\", "/")
    marker = "src/ai_service/"
    if marker in normalised:
        normalised = normalised[normalised.index(marker) :]
    return normalised.lstrip("./")


def _selected_thresholds(selected_paths: Collection[str] | None) -> dict[str, float]:
    if selected_paths is None:
        return dict(CRITICAL_THRESHOLDS)

    selected: dict[str, float] = {}
    for path in selected_paths:
        canonical = _normalise_path(path)
        if canonical not in CRITICAL_THRESHOLDS:
            raise ValueError(f"unknown critical coverage path: {path}")
        selected[canonical] = CRITICAL_THRESHOLDS[canonical]
    if not selected:
        raise ValueError("--only requires at least one critical coverage path")
    return {path: selected[path] for path in CRITICAL_THRESHOLDS if path in selected}


def evaluate_critical_coverage(
    coverage_document: Mapping[str, object],
    *,
    selected_paths: Collection[str] | None = None,
) -> tuple[CoverageResult, ...]:
    """Validate selected critical files from a coverage.py JSON document.

    ``summary.percent_covered`` is intentionally used here.  When coverage.py
    runs with ``--cov-branch`` that value includes the branch denominator and
    is therefore the value the release gate must enforce.
    """

    meta = coverage_document.get("meta")
    if not isinstance(meta, Mapping) or meta.get("branch_coverage") is not True:
        raise ValueError("coverage document must have meta.branch_coverage=true")

    files = coverage_document.get("files")
    if not isinstance(files, Mapping):
        raise ValueError("coverage document has no files mapping")

    thresholds = _selected_thresholds(selected_paths)
    indexed: dict[str, Mapping[str, object]] = {}
    for raw_path, payload in files.items():
        if not isinstance(raw_path, str) or not isinstance(payload, Mapping):
            continue
        indexed[_normalise_path(raw_path)] = payload

    results: list[CoverageResult] = []
    for path, required in thresholds.items():
        payload = indexed.get(path)
        if payload is None:
            raise ValueError(f"coverage document is missing {path}")
        summary = payload.get("summary")
        if not isinstance(summary, Mapping):
            raise ValueError(f"coverage document has no summary for {path}")
        observed = summary.get("percent_covered")
        if isinstance(observed, bool) or not isinstance(observed, (int, float)):
            raise ValueError(f"invalid percent_covered for {path}")
        results.append(CoverageResult(path, float(observed), required))
    return tuple(results)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("coverage_json", type=Path)
    parser.add_argument(
        "--only",
        dest="selected_paths",
        action="append",
        help="enforce one critical path; may be repeated (default: all paths)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        with args.coverage_json.open("r", encoding="utf-8") as handle:
            document = json.load(handle)
        results = evaluate_critical_coverage(document, selected_paths=args.selected_paths)
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        print(f"critical coverage: FAIL ({exc})", file=sys.stderr)
        return 1

    print("path\tobserved\trequired\tresult")
    for result in results:
        status = "PASS" if result.passed else "FAIL"
        print(f"{result.path}\t{result.observed:.2f}%\t{result.required:.2f}%\t{status}")
    return 0 if all(result.passed for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())

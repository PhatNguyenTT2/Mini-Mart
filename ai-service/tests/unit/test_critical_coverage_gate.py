from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest

_SCRIPT = Path(__file__).parents[2] / "scripts" / "check_critical_coverage.py"
_SPEC = importlib.util.spec_from_file_location("critical_coverage", _SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _MODULE
_SPEC.loader.exec_module(_MODULE)


CRITICAL = tuple(_MODULE.CRITICAL_THRESHOLDS)


def _document(
    *,
    observed: dict[str, float] | None = None,
    branch_coverage: bool = True,
    paths: tuple[str, ...] = CRITICAL,
) -> dict[str, Any]:
    values = observed or {
        path: threshold for path, threshold in _MODULE.CRITICAL_THRESHOLDS.items()
    }
    return {
        "meta": {"branch_coverage": branch_coverage},
        "files": {path: {"summary": {"percent_covered": values[path]}} for path in paths},
    }


def test_critical_coverage_gate_accepts_all_exact_thresholds() -> None:
    results = _MODULE.evaluate_critical_coverage(_document())

    assert len(results) == 6
    assert all(result.passed for result in results)


def test_critical_coverage_gate_rejects_one_file_below_threshold() -> None:
    observed = {path: threshold for path, threshold in _MODULE.CRITICAL_THRESHOLDS.items()}
    observed["src/ai_service/training/pipeline.py"] = 84.99

    results = _MODULE.evaluate_critical_coverage(_document(observed=observed))

    assert not next(
        result for result in results if result.path == "src/ai_service/training/pipeline.py"
    ).passed


def test_critical_coverage_gate_rejects_missing_critical_file() -> None:
    paths = tuple(path for path in CRITICAL if not path.endswith("pipeline.py"))

    with pytest.raises(ValueError, match=r"pipeline\.py"):
        _MODULE.evaluate_critical_coverage(_document(paths=paths))


def test_critical_coverage_gate_rejects_statement_only_document() -> None:
    with pytest.raises(ValueError, match="branch_coverage"):
        _MODULE.evaluate_critical_coverage(_document(branch_coverage=False))


def test_critical_coverage_gate_normalizes_windows_paths() -> None:
    windows = {
        path.replace("/", "\\"): threshold
        for path, threshold in _MODULE.CRITICAL_THRESHOLDS.items()
    }
    document = {
        "meta": {"branch_coverage": True},
        "files": {
            path: {"summary": {"percent_covered": threshold}} for path, threshold in windows.items()
        },
    }

    results = _MODULE.evaluate_critical_coverage(
        document,
    )

    assert all(result.passed for result in results)


def test_critical_coverage_gate_only_enforces_selected_paths() -> None:
    observed = {path: threshold for path, threshold in _MODULE.CRITICAL_THRESHOLDS.items()}
    observed["src/ai_service/training/pipeline.py"] = 40.0

    results = _MODULE.evaluate_critical_coverage(
        _document(observed=observed),
        selected_paths=["src/ai_service/training/checkpoint.py"],
    )

    assert [result.path for result in results] == ["src/ai_service/training/checkpoint.py"]
    assert results[0].passed


def test_critical_coverage_gate_rejects_unknown_selected_path() -> None:
    with pytest.raises(ValueError, match="unknown critical coverage path"):
        _MODULE.evaluate_critical_coverage(
            _document(), selected_paths=["src/ai_service/not-critical.py"]
        )

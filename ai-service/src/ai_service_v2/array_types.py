"""Shared NumPy array type surface compatible with the sealed runtime."""

from __future__ import annotations

from typing import Any, TypeAlias

from numpy.typing import NDArray

Array: TypeAlias = NDArray[Any]

__all__ = ["Array"]

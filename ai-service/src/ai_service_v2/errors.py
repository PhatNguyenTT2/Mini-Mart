"""Explicit error types for fail-closed contract seams."""

from __future__ import annotations


class ContractError(ValueError):
    """A serialized or in-memory contract violates a required invariant."""


class IntegrityError(ContractError):
    """A byte, hash, provenance, or artifact-integrity check failed."""


class ProtocolError(ContractError):
    """A split, candidate, masking, or evaluation protocol is invalid."""


class ScoreError(ContractError):
    """A model supplied scores that cannot be evaluated safely."""

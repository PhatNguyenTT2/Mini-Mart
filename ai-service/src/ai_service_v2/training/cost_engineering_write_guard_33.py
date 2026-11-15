"""Fail-closed prospective writing prohibition; no historical accounting credit."""

import re
from pathlib import Path

from ai_service_v2.errors import IntegrityError
from ai_service_v2.training.cost_runtime_custody import reject_reparse_path


def engineering_withdrawal_marker(namespace: Path) -> Path:
    return namespace.parent / (namespace.name + ".future-write-withdrawal.json")


def reject_withdrawn_engineering_root(namespace: Path) -> None:
    reject_reparse_path(namespace)
    for root in (namespace, *namespace.parents):
        marker = engineering_withdrawal_marker(root)
        reject_reparse_path(marker)
        if marker.exists():
            raise IntegrityError("BOUNDED_ENGINEERING_FUTURE_WRITE_WITHDRAWN")
        current = root.with_name(root.name + ".current-quarantine.json") if root.name else None
        if current is not None:
            reject_reparse_path(current)
            if current.exists():
                raise IntegrityError("BOUNDED_CURRENT_ROOT_QUARANTINED")
    index = (
        Path(__file__).resolve().parents[4]
        / "research/hybrid-recsys-v5/06_venue_readiness/07_local_v5_validation/00_control"
        / "cost_optimization_01/optimization_closure_03/current_quarantine_index_52.json"
    )
    reject_reparse_path(index)
    if index.exists():
        reject_quarantined_path(namespace, index_path=index)


def reject_quarantined_path(namespace: Path, *, index_path: Path) -> None:
    """Prohibition is effective even before a publication companion exists."""
    from ai_service_v2.training.cost_residual_inspection_48 import _control

    if ".." in namespace.parts:
        raise IntegrityError("BOUNDED_CURRENT_QUARANTINE_PATH")
    namespace = namespace.absolute()
    reject_reparse_path(namespace)
    reject_reparse_path(index_path)
    _, index = _control(index_path)
    if (
        type(index) is not dict
        or set(index)
        != {"schema_version", "authority_sha256", "receipt", "deny_paths", "root_identities"}
        or index["schema_version"] != "mp2-current-quarantine-index/1.0"
        or type(index["deny_paths"]) is not list
        or not index["deny_paths"]
        or type(index["root_identities"]) is not list
        or not index["root_identities"]
        or type(index["authority_sha256"]) is not str
        or not re.fullmatch(r"[0-9a-f]{64}", index["authority_sha256"])
        or type(index["receipt"]) is not str
        or not Path(index["receipt"]).is_absolute()
        or ".." in Path(index["receipt"]).parts
    ):
        raise IntegrityError("BOUNDED_CURRENT_QUARANTINE_INDEX_IN_DOUBT")
    identities: set[tuple[int, int]] = set()
    for identity_row in index["root_identities"]:
        if (
            type(identity_row) is not dict
            or set(identity_row) != {"device", "file_id"}
            or any(type(value) is not int or value < 0 for value in identity_row.values())
        ):
            raise IntegrityError("BOUNDED_CURRENT_QUARANTINE_INDEX_IN_DOUBT")
        key = (identity_row["device"], identity_row["file_id"])
        if key in identities:
            raise IntegrityError("BOUNDED_CURRENT_QUARANTINE_INDEX_IN_DOUBT")
        identities.add(key)
    paths: list[Path] = []
    for name in index["deny_paths"]:
        if type(name) is not str or not Path(name).is_absolute() or ".." in Path(name).parts:
            raise IntegrityError("BOUNDED_CURRENT_QUARANTINE_INDEX_IN_DOUBT")
        paths.append(Path(name))
    if any(namespace == root or namespace.is_relative_to(root) for root in paths):
        raise IntegrityError("BOUNDED_CURRENT_ROOT_QUARANTINED")
    for candidate in (namespace, *namespace.parents):
        if not candidate.exists():
            continue
        observed = candidate.stat()
        if (observed.st_dev, observed.st_ino) in identities:
            raise IntegrityError("BOUNDED_CURRENT_ROOT_QUARANTINED")

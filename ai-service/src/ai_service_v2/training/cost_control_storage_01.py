"""Bounded filesystem admission; no scientific or historical-payload authority."""

from __future__ import annotations

import ctypes
import os
import re
import shutil
import stat
import threading
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from ai_service_v2.errors import IntegrityError
from ai_service_v2.hashing import canonical_json_bytes, canonical_json_sha256, sha256_file
from ai_service_v2.training.cost_reference_metadata_01 import validate_inventory
from ai_service_v2.training.cost_runtime_custody import (
    read_canonical_json,
    reject_reparse_path,
    write_exclusive_json,
)

STORAGE_CAP_BYTES = 50_000_000_000
SAFETY_BYTES = 1_073_741_824
_ROOT_CATEGORIES = {
    "RUNTIME_CACHE",
    "INPUT_MATERIALIZATION",
    "RETAINED_CUSTODY",
    "PROJECT_CONTROLS",
    "VERIFICATION_OUTPUT",
    "PROJECT_ARTIFACTS",
    "INSTALLED_DEPENDENCY",
}


def _allocated_size(path: Path, info: os.stat_result) -> int:
    if os.name != "nt":
        return max(info.st_size, getattr(info, "st_blocks", 0) * 512)
    api = ctypes.WinDLL("kernel32", use_last_error=True)
    function = api.GetCompressedFileSizeW
    function.argtypes = [ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_ulong)]
    function.restype = ctypes.c_ulong
    high = ctypes.c_ulong()
    ctypes.set_last_error(0)
    low = function("\\\\?\\" + str(path.absolute()), ctypes.byref(high))
    if low == 0xFFFFFFFF and ctypes.get_last_error():
        raise IntegrityError("STORAGE_ALLOCATION_SIZE_UNAVAILABLE")
    return int(max(info.st_size, (high.value << 32) | low))


def capacity_census(
    root: Path, *, approved_aliases: Mapping[str, str] | None = None
) -> dict[str, Any]:
    """Enumerate file metadata only; never follow or silently discard reparse entries."""
    reject_reparse_path(root)
    if not root.is_dir():
        raise IntegrityError("STORAGE_ROOT_MISSING")
    root = root.resolve()
    admitted = {} if approved_aliases is None else dict(approved_aliases)
    physical: dict[tuple[int, int], tuple[int, int]] = {}
    aliases: list[dict[str, str]] = []
    directories = [root]
    entries = 0
    while directories:
        directory = directories.pop()
        with os.scandir(directory) as iterator:
            for entry in iterator:
                path = Path(entry.path)
                info = path.lstat()
                relative = path.relative_to(root).as_posix()
                if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
                    target = admitted.get(relative)
                    if target is None:
                        raise IntegrityError("STORAGE_REPARSE_UNAPPROVED")
                    target_path = root / target
                    reject_reparse_path(target_path)
                    if (
                        not target_path.is_relative_to(root)
                        or target_path.resolve() != target_path
                        or not target_path.exists()
                        or path.resolve() != target_path
                    ):
                        raise IntegrityError("STORAGE_REPARSE_TARGET_DRIFT")
                    aliases.append({"path": relative, "target": target})
                elif stat.S_ISDIR(info.st_mode):
                    directories.append(path)
                elif stat.S_ISREG(info.st_mode):
                    if not info.st_ino:
                        raise IntegrityError("STORAGE_FILE_ID_UNAVAILABLE")
                    entries += 1
                    identity = (info.st_dev, info.st_ino)
                    value = (info.st_size, _allocated_size(path, info))
                    if identity in physical and physical[identity] != value:
                        raise IntegrityError("STORAGE_CENSUS_CHANGED_DURING_READ")
                    physical[identity] = value
                else:
                    raise IntegrityError("STORAGE_UNKNOWN_ENTRY")
    aliases.sort(key=lambda row: row["path"])
    if {row["path"] for row in aliases} != set(admitted):
        raise IntegrityError("STORAGE_ALIAS_ROSTER_DRIFT")
    return {
        "schema_version": "mp2-cost-storage-census/1.0",
        "root": str(root),
        "logical_unique_bytes": sum(value[0] for value in physical.values()),
        "charged_unique_bytes": sum(value[1] for value in physical.values()),
        "unique_files": len(physical),
        "file_entries": entries,
        "aliases": aliases,
        "scope": "FILESYSTEM_METADATA_ONLY_NOT_PAYLOAD_REPLAY",
        "payload_bytes_certified": False,
    }


def size(value: object) -> int:
    if type(value) is not int or value < 0:
        raise IntegrityError("STORAGE_SIZE_UNKNOWN_OR_NONCANONICAL")
    return value


def storage_root_inventory(roots: list[dict[str, Any]]) -> dict[str, Any]:
    """Bind an explicit root/alias roster; callers must classify all project outputs."""
    from ai_service_v2.training.cost_bounded_io_01 import allocation_unit

    if type(roots) is not list or not 1 <= len(roots) <= 512:
        raise IntegrityError("STORAGE_ROOT_INVENTORY_ROSTER")
    rows = []
    names: set[str] = set()
    for row in roots:
        if (
            type(row) is not dict
            or set(row) != {"root", "category", "aliases"}
            or type(row["root"]) is not str
            or type(row["category"]) is not str
            or row["category"] not in _ROOT_CATEGORIES
            or type(row["aliases"]) is not dict
        ):
            raise IntegrityError("STORAGE_ROOT_INVENTORY_ROSTER")
        root = Path(row["root"])
        reject_reparse_path(root)
        if (
            not root.is_absolute()
            or str(root.resolve()) != row["root"]
            or not (root.is_dir() or root.is_file())
        ):
            raise IntegrityError("STORAGE_ROOT_IDENTITY")
        if str(root).casefold() in names:
            raise IntegrityError("STORAGE_ROOT_DUPLICATE")
        names.add(str(root).casefold())
        info = root.stat()
        if not info.st_ino:
            raise IntegrityError("STORAGE_ROOT_IDENTITY_UNAVAILABLE")
        aliases: dict[str, str] = {}
        identities: dict[str, dict[str, int]] = {}
        kind = "DIRECTORY" if stat.S_ISDIR(info.st_mode) else "FILE"
        if kind == "FILE" and row["aliases"]:
            raise IntegrityError("STORAGE_FILE_ALIAS_ROSTER")
        for name, target in row["aliases"].items():
            if type(name) is not str or type(target) is not str:
                raise IntegrityError("STORAGE_ALIAS_ROSTER_DRIFT")
            name, target = safe_name(name), safe_name(target)
            link, destination = root / name, root / target
            reject_reparse_path(destination)
            linked = link.lstat()
            if (
                not (
                    stat.S_ISLNK(linked.st_mode) or getattr(linked, "st_file_attributes", 0) & 0x400
                )
                or not destination.is_relative_to(root)
                or not destination.exists()
                or link.resolve() != destination
                or not linked.st_ino
            ):
                raise IntegrityError("STORAGE_REPARSE_TARGET_DRIFT")
            aliases[name] = target
            identities[name] = {"device": linked.st_dev, "file_id": linked.st_ino}
        rows.append(
            {
                "root": str(root),
                "category": row["category"],
                "kind": kind,
                "device": info.st_dev,
                "file_id": info.st_ino,
                "allocation_unit_bytes": allocation_unit(root),
                "aliases": dict(sorted(aliases.items())),
                "alias_identities": dict(sorted(identities.items())),
            }
        )
    return {
        "schema_version": "mp2-cost-storage-root-inventory/1.0",
        "roots": sorted(rows, key=lambda row: row["root"].casefold()),
        "scope": "EXPLICIT_CLASSIFIED_MP2_OUTPUT_ROOTS_NOT_AUTOMATIC_DISCOVERY",
        "scientific_execution_authorized": False,
    }


def reservation_candidate_census(inventory: dict[str, Any]) -> dict[str, Any]:
    """Inventory ledger path metadata, never infer claims from JSON filenames."""
    if type(inventory) is not dict or type(inventory.get("roots")) is not list:
        raise IntegrityError("STORAGE_ROOT_INVENTORY_BINDING")
    expected = storage_root_inventory(
        [
            {key: row[key] for key in ("root", "category", "aliases")}
            for row in inventory["roots"]
            if type(row) is dict and {"root", "category", "aliases"}.issubset(row)
        ]
    )
    if inventory != expected:
        raise IntegrityError("STORAGE_ROOT_INVENTORY_BINDING")

    def scan() -> list[dict[str, Any]]:
        candidates: dict[str, dict[str, Any]] = {}
        for row in expected["roots"]:
            root = Path(row["root"])
            pending = [root] if row["kind"] == "DIRECTORY" else []
            while pending:
                directory = pending.pop()
                reject_reparse_path(directory)
                with os.scandir(directory) as entries:
                    for entry in entries:
                        path = Path(entry.path)
                        info = path.lstat()
                        if (
                            stat.S_ISLNK(info.st_mode)
                            or getattr(info, "st_file_attributes", 0) & 0x400
                        ):
                            relative = path.relative_to(root).as_posix()
                            target = row["aliases"].get(relative)
                            if target is None or path.resolve() != root / target:
                                raise IntegrityError("STORAGE_REPARSE_TARGET_DRIFT")
                            continue
                        if stat.S_ISDIR(info.st_mode):
                            pending.append(path)
                        elif (
                            stat.S_ISREG(info.st_mode)
                            and path.name == "reserve.json"
                            and "bounded-ledger" in path.parts
                        ):
                            # Presence is not canonicality, custody, or settlement validity.
                            settled = path.parent / "settled.json"
                            reject_reparse_path(settled)
                            candidates[str(path)] = {
                                "path": str(path),
                                "device": info.st_dev,
                                "file_id": info.st_ino,
                                "bytes": info.st_size,
                                "mtime_ns": info.st_mtime_ns,
                                "links": info.st_nlink,
                                "settlement_candidate_present": settled.is_file(),
                            }
        return [candidates[name] for name in sorted(candidates)]

    before = scan()
    after = scan()
    if before != after:
        raise IntegrityError("STORAGE_RESERVATION_CANDIDATES_CHANGED_DURING_READ")
    return {
        "schema_version": "mp2-cost-reservation-candidate-census/1.0",
        "root_inventory_sha256": canonical_json_sha256(inventory),
        "candidates": after,
        "candidate_count": len(after),
        "unsettled_candidate_count": sum(not row["settlement_candidate_present"] for row in after),
        "scope": "FILESYSTEM_METADATA_ONLY_NOT_CONTROL_OR_RESERVATION_QUALIFICATION",
        "candidate_bytes_read": False,
        "reservation_bindings_certified": False,
        "unmaterialized_balance_bytes": None,
        "complete_storage_admission_pass": False,
    }


def execution_census(inventory: dict[str, Any]) -> dict[str, Any]:
    """Two stable metadata passes; deduplicate physical files across declared roots."""
    if type(inventory) is not dict or type(inventory.get("roots")) is not list:
        raise IntegrityError("STORAGE_ROOT_INVENTORY_BINDING")
    expected = storage_root_inventory(
        [
            {key: row[key] for key in ("root", "category", "aliases")}
            for row in inventory["roots"]
            if type(row) is dict and {"root", "category", "aliases"}.issubset(row)
        ]
    )
    if inventory != expected:
        raise IntegrityError("STORAGE_ROOT_INVENTORY_BINDING")

    return _execution_census(expected["roots"], inventory)


def execution_census_pages(inventories: list[dict[str, Any]]) -> dict[str, Any]:
    """Current explicit inventory pages, with one global physical-identity census.

    Historical inventories keep their512-root reader. Paging does not sum
    independent censuses, which would count cross-page hardlinks twice.
    """
    if type(inventories) is not list or not 1 <= len(inventories) <= 8:
        raise IntegrityError("STORAGE_CENSUS_PAGE_ROSTER")
    if len(canonical_json_bytes({"inventories": inventories})) > 8 * 1024 * 1024:
        raise IntegrityError("STORAGE_CENSUS_PAGE_DOCUMENT_BOUND")
    roots: list[dict[str, Any]] = []
    names: set[str] = set()
    for inventory in inventories:
        if type(inventory) is not dict or type(inventory.get("roots")) is not list:
            raise IntegrityError("STORAGE_ROOT_INVENTORY_BINDING")
        expected = storage_root_inventory(
            [
                {key: row[key] for key in ("root", "category", "aliases")}
                for row in inventory["roots"]
                if type(row) is dict and {"root", "category", "aliases"}.issubset(row)
            ]
        )
        if inventory != expected:
            raise IntegrityError("STORAGE_ROOT_INVENTORY_BINDING")
        for row in expected["roots"]:
            name = row["root"].casefold()
            if name in names:
                raise IntegrityError("STORAGE_ROOT_DUPLICATE")
            names.add(name)
            roots.append(row)
    binding = {"schema_version": "mp2-cost-storage-census-pages/1.0", "inventories": inventories}
    result = _execution_census(sorted(roots, key=lambda row: row["root"].casefold()), binding)
    result["schema_version"] = "mp2-cost-storage-census/1.2"
    result["inventory_page_count"] = len(inventories)
    return result


def _execution_census(
    checked_roots: list[dict[str, Any]], inventory: dict[str, Any]
) -> dict[str, Any]:
    def scan() -> tuple[
        dict[tuple[int, int], tuple[int, int, int, int]], list[dict[str, Any]], dict[str, Any]
    ]:
        physical: dict[tuple[int, int], tuple[int, int, int, int]] = {}
        summaries = []
        volumes: dict[str, Any] = {}
        for row in checked_roots:
            root = Path(row["root"])
            unit = row["allocation_unit_bytes"]
            pending = [root] if row["kind"] == "DIRECTORY" else []
            seen_aliases: set[str] = set()
            entries = 0
            entry_roster: list[list[Any]] = []
            if row["kind"] == "FILE":
                info = root.lstat()
                if not stat.S_ISREG(info.st_mode):
                    raise IntegrityError("STORAGE_ROOT_IDENTITY")
                identity = (info.st_dev, info.st_ino)
                allocated = _allocated_size(root, info)
                value = (
                    info.st_size,
                    (allocated + unit - 1) // unit * unit,
                    info.st_mtime_ns,
                    info.st_nlink,
                )
                if identity in physical and physical[identity] != value:
                    raise IntegrityError("STORAGE_CENSUS_CHANGED_DURING_READ")
                physical[identity] = value
                entries = 1
                entry_roster.append([".", "FILE", info.st_dev, info.st_ino])
            while pending:
                directory = pending.pop()
                reject_reparse_path(directory)
                with os.scandir(directory) as iterator:
                    for entry in iterator:
                        path = Path(entry.path)
                        info = path.lstat()
                        relative = path.relative_to(root).as_posix()
                        entry_roster.append(
                            [
                                relative,
                                info.st_mode,
                                info.st_dev,
                                info.st_ino,
                            ]
                        )
                        if (
                            stat.S_ISLNK(info.st_mode)
                            or getattr(info, "st_file_attributes", 0) & 0x400
                        ):
                            target = row["aliases"].get(relative)
                            if target is None:
                                raise IntegrityError("STORAGE_REPARSE_UNAPPROVED")
                            destination = root / target
                            reject_reparse_path(destination)
                            if (
                                path.resolve() != destination
                                or not destination.exists()
                                or {"device": info.st_dev, "file_id": info.st_ino}
                                != row["alias_identities"][relative]
                            ):
                                raise IntegrityError("STORAGE_REPARSE_TARGET_DRIFT")
                            seen_aliases.add(relative)
                        elif stat.S_ISDIR(info.st_mode):
                            pending.append(path)
                        elif stat.S_ISREG(info.st_mode):
                            if not info.st_ino:
                                raise IntegrityError("STORAGE_FILE_ID_UNAVAILABLE")
                            identity = (info.st_dev, info.st_ino)
                            allocated = _allocated_size(path, info)
                            value = (
                                info.st_size,
                                (allocated + unit - 1) // unit * unit,
                                info.st_mtime_ns,
                                info.st_nlink,
                            )
                            if identity in physical and physical[identity] != value:
                                raise IntegrityError("STORAGE_CENSUS_CHANGED_DURING_READ")
                            physical[identity] = value
                            entries += 1
                        else:
                            raise IntegrityError("STORAGE_UNKNOWN_ENTRY")
            if seen_aliases != set(row["aliases"]):
                raise IntegrityError("STORAGE_ALIAS_ROSTER_DRIFT")
            if (root.stat().st_dev, root.stat().st_ino) != (row["device"], row["file_id"]):
                raise IntegrityError("STORAGE_ROOT_IDENTITY")
            summaries.append(
                {
                    "root": str(root),
                    "category": row["category"],
                    "kind": row["kind"],
                    "file_entries": entries,
                    "entry_roster_sha256": canonical_json_sha256({"entries": sorted(entry_roster)}),
                }
            )
            key = str(row["device"])
            free = shutil.disk_usage(root).free
            previous = volumes.get(key, {"free_bytes": free})
            volumes[key] = {"free_bytes": min(free, previous["free_bytes"]), "volume": root.anchor}
        return physical, summaries, volumes

    first, roots, first_volumes = scan()
    second, final_roots, volumes = scan()
    if first != second or roots != final_roots:
        raise IntegrityError("STORAGE_CENSUS_CHANGED_DURING_READ")
    for key, row in volumes.items():
        row["free_bytes"] = min(row["free_bytes"], first_volumes[key]["free_bytes"])
        row["charged_unique_bytes"] = sum(
            value[1] for identity, value in second.items() if str(identity[0]) == key
        )
    return {
        "schema_version": "mp2-cost-storage-census/1.1",
        "scope": "FILESYSTEM_METADATA_ONLY_NOT_PAYLOAD_REPLAY",
        "payload_bytes_certified": False,
        "root_inventory_sha256": canonical_json_sha256(inventory),
        "logical_unique_bytes": sum(value[0] for value in second.values()),
        "charged_unique_bytes": sum(value[1] for value in second.values()),
        "unique_files": len(second),
        "file_entries": sum(row["file_entries"] for row in roots),
        "roots": roots,
        "volumes": volumes,
        "reservation_balances_included": False,
    }


def observe_current_storage_aliases(
    inventory_binding: dict[str, Any],
    *,
    lane: Path,
    protected_reference_binding: dict[str, Any],
) -> dict[str, Any]:
    """Observe only fixed aliases; absence is not disposal or accounting credit."""
    from ai_service_v2.training.cost_residual_inspection_48 import _control
    from ai_service_v2.training.cost_runtime_custody import exclusive_lane

    if threading.current_thread() is not threading.main_thread():
        raise IntegrityError("STORAGE_ALIAS_OBSERVATION_BACKGROUND_THREAD")
    observed, inventory = _control(Path(inventory_binding["path"]))
    protected_bound, graph = _control(Path(protected_reference_binding["path"]))
    if (
        observed != inventory_binding
        or type(inventory) is not dict
        or inventory.get("schema_version") != "mp2-cost-storage-root-inventory/1.0"
        or type(inventory.get("roots")) is not list
        or protected_bound != protected_reference_binding
        or type(graph) is not dict
        or graph.get("schema_version") != "mp2-current-protected-reference-graph/1.0"
        or type(graph.get("reference_paths")) is not list
    ):
        raise IntegrityError("STORAGE_ALIAS_OBSERVATION_BINDING")
    protected = []
    for name in graph["reference_paths"]:
        if type(name) is not str or not Path(name).is_absolute() or ".." in Path(name).parts:
            raise IntegrityError("STORAGE_ALIAS_PROTECTED_PATH")
        protected.append(Path(name))

    def observe() -> tuple[dict[str, Any], list[dict[str, Any]]]:
        roots, absent = [], []
        for row in inventory["roots"]:
            root = Path(row["root"])
            reject_reparse_path(root)
            info = root.stat()
            if (info.st_dev, info.st_ino) != (row["device"], row["file_id"]):
                raise IntegrityError("STORAGE_ALIAS_ROOT_DRIFT")
            if set(row["aliases"]) != set(row["alias_identities"]):
                raise IntegrityError("STORAGE_ALIAS_HISTORY_ROSTER")
            active = {}
            for name, target in row["aliases"].items():
                link, destination = root / safe_name(name), root / safe_name(target)
                reject_reparse_path(destination)
                try:
                    linked = link.lstat()
                except FileNotFoundError:
                    for reference in protected:
                        if any(
                            path == reference
                            or path.is_relative_to(reference)
                            or reference.is_relative_to(path)
                            for path in (link, destination)
                        ):
                            raise IntegrityError("STORAGE_PROTECTED_ALIAS_MISSING") from None
                    absent.append(
                        {
                            "root": str(root),
                            "path": str(link),
                            "target": str(destination),
                            "historical_identity": row["alias_identities"][name],
                            "state": "ABSENT_TWO_PASS_OBSERVATION_PENDING",
                            "target_state": "PRESENT_COUNTED_IN_CENSUS"
                            if destination.exists()
                            else "ABSENT_CURRENT_METADATA_ONLY",
                            "historical_pointer_retained": True,
                            "prohibition_required": True,
                        }
                    )
                    continue
                if (
                    {"device": linked.st_dev, "file_id": linked.st_ino}
                    != row["alias_identities"][name]
                    or not (
                        stat.S_ISLNK(linked.st_mode)
                        or getattr(linked, "st_file_attributes", 0) & 0x400
                    )
                    or link.resolve() != destination
                    or not destination.exists()
                ):
                    raise IntegrityError("STORAGE_ALIAS_RESURRECTION_OR_DRIFT")
                active[name] = target
            roots.append({"root": str(root), "category": row["category"], "aliases": active})
        current = storage_root_inventory(roots)
        for old, new in zip(inventory["roots"], current["roots"], strict=True):
            for name in ("root", "category", "kind", "device", "file_id", "allocation_unit_bytes"):
                if old[name] != new[name]:
                    raise IntegrityError("STORAGE_ALIAS_INVENTORY_DRIFT")
        return current, absent

    with exclusive_lane(lane):
        first, absent = observe()
        census = execution_census(first)
        second, final_absent = observe()
        if first != second or absent != final_absent:
            raise IntegrityError("STORAGE_ALIAS_OBSERVATION_UNSTABLE")
        if (
            _control(Path(inventory_binding["path"]))[0] != inventory_binding
            or _control(Path(protected_reference_binding["path"]))[0] != protected_reference_binding
        ):
            raise IntegrityError("STORAGE_ALIAS_OBSERVATION_FINAL_DRIFT")
        for row in absent:
            row["state"] = "ABSENT_TWO_STABLE_METADATA_PASSES"
        return {
            "schema_version": "mp2-current-storage-alias-observation/1.0",
            "predecessor_inventory": inventory_binding,
            "protected_reference_binding": protected_reference_binding,
            "current_inventory": first,
            "absent_aliases": absent,
            "census": census,
            "protected_reference_coverage_qualified": False,
            "scope": "OBSERVATION_ONLY_REQUIRES_SEPARATE_COMPLETE_GRAPH_AND_CURRENT_ACCOUNTING",
            "allocated_bytes_released": 0,
            "complete_storage_admission_pass": False,
            "scientific_execution_authorized": False,
        }


def storage_admission(
    projected_peak_bytes: object, *, free_bytes: object, current_bytes: object = 0
) -> dict[str, Any]:
    peak, free, current = size(projected_peak_bytes), size(free_bytes), size(current_bytes)
    if peak < current:
        raise IntegrityError("STORAGE_PEAK_BELOW_CURRENT")
    admitted = (11 * peak + 9) // 10 + SAFETY_BYTES
    if admitted > STORAGE_CAP_BYTES:
        raise IntegrityError("STORAGE_CAP_50GB_EXCEEDED")
    if admitted - current > free:
        raise IntegrityError("STORAGE_FREE_SPACE_INSUFFICIENT")
    return {
        "schema_version": "mp2-cost-storage-admission/1.0",
        "state": "STORAGE_ADMISSION_PASS_NON_AUTHORIZING",
        "storage_cap_bytes": STORAGE_CAP_BYTES,
        "current_bytes": current,
        "projected_peak_bytes": peak,
        "admitted_peak_bytes": admitted,
        "free_bytes": free,
        "scope": "WHOLE_RUNTIME_CACHE_PEAK_NOT_LIFETIME_WRITES",
        "scientific_execution_authorized": False,
    }


def storage_admission_current(
    projected_peak_bytes: object,
    *,
    policy_binding: dict[str, Any],
    free_bytes: object,
    current_bytes: object = 0,
) -> dict[str, Any]:
    """Prospective 80 GB policy, without changing historical admission/replay."""
    from ai_service_v2.training.cost_residual_inspection_48 import _control

    observed, policy = _control(Path(policy_binding["path"]))
    if (
        observed != policy_binding
        or type(policy) is not dict
        or set(policy)
        != {
            "schema_version",
            "scope",
            "storage_cap_bytes",
            "amendment",
            "scientific_execution_authorized",
        }
        or policy["schema_version"] != "mp2-current-storage-policy/1.0"
        or policy["scope"] != "CURRENT_MP2_ONLY"
        or type(policy["storage_cap_bytes"]) is not int
        or policy["storage_cap_bytes"] != 80000000000
        or policy["scientific_execution_authorized"] is not False
        or type(policy["amendment"]) is not dict
    ):
        raise IntegrityError("STORAGE_CURRENT_POLICY_BINDING")
    amendment, _ = _control(Path(policy["amendment"]["path"]))
    if amendment != policy["amendment"]:
        raise IntegrityError("STORAGE_CURRENT_AMENDMENT_DRIFT")
    peak, free, current = size(projected_peak_bytes), size(free_bytes), size(current_bytes)
    if peak < current:
        raise IntegrityError("STORAGE_PEAK_BELOW_CURRENT")
    admitted = (11 * peak + 9) // 10 + SAFETY_BYTES
    if admitted > policy["storage_cap_bytes"]:
        raise IntegrityError("STORAGE_CAP_80GB_EXCEEDED")
    if admitted - current > free:
        raise IntegrityError("STORAGE_FREE_SPACE_INSUFFICIENT")
    return {
        "schema_version": "mp2-cost-storage-admission/1.1",
        "state": "STORAGE_ADMISSION_PASS_NON_AUTHORIZING",
        "storage_cap_bytes": policy["storage_cap_bytes"],
        "current_bytes": current,
        "projected_peak_bytes": peak,
        "admitted_peak_bytes": admitted,
        "free_bytes": free,
        "policy_binding": observed,
        "scope": "WHOLE_RUNTIME_CACHE_PEAK_NOT_LIFETIME_WRITES",
        "scientific_execution_authorized": False,
    }


def current_storage_policy_controls(authority: dict[str, Any]) -> dict[Path, str]:
    """Declare both prospective controls before a metadata reader opens either."""
    if "current_storage_policy" not in authority:
        return {}
    bundle = authority["current_storage_policy"]
    if (
        authority.get("scientific_execution_authorized") is not False
        or type(bundle) is not dict
        or set(bundle) != {"policy_binding", "amendment_binding"}
    ):
        raise IntegrityError("STORAGE_CURRENT_AUTHORITY_POLICY")
    paths: dict[Path, str] = {}
    for name in ("policy_binding", "amendment_binding"):
        bound = bundle[name]
        if (
            type(bound) is not dict
            or set(bound) != {"path", "device", "file_id", "bytes", "sha256"}
            or type(bound["path"]) is not str
            or not Path(bound["path"]).is_absolute()
            or Path(bound["path"]).suffix.lower() not in {".json", ".md"}
            or any(
                type(bound[key]) is not int or bound[key] < 0
                for key in ("device", "file_id", "bytes")
            )
            or not 0 < bound["bytes"] <= 8 * 1024**2
            or type(bound["sha256"]) is not str
            or re.fullmatch(r"[0-9a-f]{64}", bound["sha256"]) is None
        ):
            raise IntegrityError("STORAGE_CURRENT_AUTHORITY_BINDING")
        path = Path(bound["path"])
        reject_reparse_path(path)
        if path.resolve() in {previous.resolve() for previous in paths}:
            raise IntegrityError("STORAGE_CURRENT_AUTHORITY_DUPLICATE_CONTROL")
        paths[path] = "BOUND_CURRENT_STORAGE_POLICY_CONTROL_ONLY"
    return paths


def storage_admission_for_authority(
    projected_peak_bytes: object,
    *,
    authority: dict[str, Any],
    free_bytes: object,
    current_bytes: object = 0,
) -> dict[str, Any]:
    """Only an explicit bound policy selects cap80; absent policy preserves cap50."""
    if not current_storage_policy_controls(authority):
        return storage_admission(
            projected_peak_bytes, free_bytes=free_bytes, current_bytes=current_bytes
        )
    from ai_service_v2.training.cost_residual_inspection_48 import _control

    bundle = authority["current_storage_policy"]
    observed, policy = _control(Path(bundle["policy_binding"]["path"]))
    if (
        observed != bundle["policy_binding"]
        or type(policy) is not dict
        or policy.get("amendment") != bundle["amendment_binding"]
    ):
        raise IntegrityError("STORAGE_CURRENT_AUTHORITY_POLICY_DRIFT")
    return storage_admission_current(
        projected_peak_bytes,
        policy_binding=bundle["policy_binding"],
        free_bytes=free_bytes,
        current_bytes=current_bytes,
    )


def safe_name(value: str) -> str:
    from ai_service_v2.training.cost_closure_postmeasurement_03 import safe_relative

    return safe_relative(value)


class StorageReservation:
    """A lane owner reserves bounded writes, including partial/staging bytes."""

    def __init__(
        self, cache: Path, namespace: Path, *, approved_aliases: Mapping[str, str] | None = None
    ) -> None:
        from ai_service_v2.training.cost_engineering_write_guard_33 import (
            reject_withdrawn_engineering_root,
        )

        reject_withdrawn_engineering_root(namespace)
        reject_reparse_path(namespace)
        if not namespace.resolve().is_relative_to(cache.resolve()) or namespace == cache:
            raise IntegrityError("STORAGE_NAMESPACE_OUTSIDE_CACHE")
        self.cache = cache
        self.namespace = namespace
        self.aliases = approved_aliases
        self.lock = threading.RLock()

    def _pending(self, directory: Path) -> int:
        reject_reparse_path(directory)
        if not directory.exists():
            return 0
        total = 0
        for path in directory.iterdir():
            if not re.fullmatch(r"[a-z0-9-]{1,100}\.json", path.name):
                raise IntegrityError("STORAGE_RESERVATION_ROSTER")
            row = read_canonical_json(path)
            expected = storage_admission(
                row["projected_peak_bytes"],
                current_bytes=row["current_bytes"],
                free_bytes=row["free_bytes"],
            )
            amount = size(row["reserved_bytes"])
            if (
                row != {**expected, "operation_id": path.stem, "reserved_bytes": amount}
                or row["projected_peak_bytes"] - row["current_bytes"] < amount
            ):
                raise IntegrityError("STORAGE_RESERVATION_DRIFT")
            total += amount
        return total

    def reserve(self, operation_id: str, additional_bytes: object) -> dict[str, Any]:
        from ai_service_v2.training.cost_engineering_write_guard_33 import (
            reject_withdrawn_engineering_root,
        )

        if not re.fullmatch(r"[a-z0-9-]{1,100}", operation_id):
            raise IntegrityError("STORAGE_RESERVATION_ID")
        with self.lock:
            reject_withdrawn_engineering_root(self.namespace)
            amount = size(additional_bytes)
            directory = self.namespace / "storage-reservations"
            pending = self._pending(directory)
            census = capacity_census(self.cache, approved_aliases=self.aliases)
            current = census["charged_unique_bytes"]
            admission = storage_admission(
                current + pending + amount,
                current_bytes=current,
                free_bytes=shutil.disk_usage(self.cache).free,
            )
            reject_withdrawn_engineering_root(self.namespace)
            directory.mkdir(exist_ok=True)
            receipt = {**admission, "operation_id": operation_id, "reserved_bytes": amount}
            write_exclusive_json(directory / f"{operation_id}.json", receipt)
            return receipt


class ArtifactLifecycle:
    """Delete only newly owned, custodied and unretained bytes in an active unit."""

    def __init__(self, namespace: Path, *, guard: Path, binding_sha256: str) -> None:
        from ai_service_v2.training.cost_engineering_write_guard_33 import (
            reject_withdrawn_engineering_root,
        )

        reject_withdrawn_engineering_root(namespace)
        reject_reparse_path(namespace)
        reject_reparse_path(guard)
        self.root = namespace.resolve()
        self.guard = guard.resolve()
        if not self.guard.is_relative_to(self.root) or not re.fullmatch(
            r"[0-9a-f]{64}", binding_sha256
        ):
            raise IntegrityError("LIFECYCLE_FOREIGN_GUARD")
        document = read_canonical_json(guard)
        if document.get("binding_sha256") != binding_sha256:
            raise IntegrityError("LIFECYCLE_GUARD_BINDING")
        self.binding = binding_sha256
        self.guard_sha256 = sha256_file(guard)
        self.directory = self.root / "lifecycle"
        reject_reparse_path(self.directory)
        if not self.directory.exists():
            self._active()
            self.directory.mkdir()

    def _active(self) -> None:
        from ai_service_v2.training.cost_engineering_write_guard_33 import (
            reject_withdrawn_engineering_root,
        )

        reject_withdrawn_engineering_root(self.root)
        if sha256_file(self.guard) != self.guard_sha256:
            raise IntegrityError("LIFECYCLE_GUARD_DRIFT")
        if any(
            path.exists()
            for path in (
                self.guard.parent / "completion_authority.json",
                self.guard.parent / "failure.json",
                self.guard.parent.parent / "terminal_failure.json",
                self.root / "terminal_failure.json",
            )
        ):
            raise IntegrityError("LIFECYCLE_UNIT_TERMINAL")

    def _path(self, group: str, suffix: str) -> Path:
        if not re.fullmatch(r"[a-z0-9-]{1,100}", group):
            raise IntegrityError("LIFECYCLE_GROUP_ID")
        return self.directory / f"{group}.{suffix}.json"

    def _rows(self, rows: list[dict[str, Any]]) -> None:
        if not validate_inventory(rows):
            raise IntegrityError("LIFECYCLE_EMPTY_PAYLOAD")
        for row in rows:
            name = safe_name(row["path"])
            path = self.root / name
            reject_reparse_path(path)
            if (
                not path.resolve().is_relative_to(self.root)
                or path == self.guard
                or path.suffix.lower() not in {".bin", ".pt", ".npy"}
                or name.split("/")[0]
                in {"lifecycle", "journal", "storage-reservations", "children"}
                or not path.is_file()
                or path.stat().st_nlink != 1
                or path.stat().st_size != row["bytes"]
                or sha256_file(path) != row["sha256"]
            ):
                raise IntegrityError("LIFECYCLE_PAYLOAD_OWNERSHIP_OR_BYTES")

    def custody(
        self, group: str, rows: list[dict[str, Any]], *, protected_paths: list[str] | None = None
    ) -> dict[str, Any]:
        self._active()
        self._rows(rows)
        protected = [] if protected_paths is None else protected_paths
        if len(set(protected)) != len(protected) or not set(protected) <= {
            row["path"] for row in rows
        }:
            raise IntegrityError("LIFECYCLE_RETAINED_ROSTER")
        receipt = {
            "schema_version": "mp2-cost-artifact-custody/1.0",
            "binding_sha256": self.binding,
            "guard_sha256": self.guard_sha256,
            "group": group,
            "artifacts": rows,
            "protected_paths": sorted(protected),
        }
        write_exclusive_json(self._path(group, "custody"), receipt)
        return receipt

    def _retentions(self) -> list[tuple[Path, dict[str, Any]]]:
        results = []
        for index, path in enumerate(sorted(self.directory.glob("retention-*.json")), 1):
            value = read_canonical_json(path)
            if (
                path.name != f"retention-{index:06d}.json"
                or set(value)
                != {"schema_version", "index", "groups", "selection_sha256", "guard_sha256"}
                or value["schema_version"] != "mp2-cost-retention/1.0"
                or type(value["index"]) is not int
                or value["index"] != index
                or value["guard_sha256"] != self.guard_sha256
                or not isinstance(value["groups"], list)
                or any(not isinstance(group, str) for group in value["groups"])
                or value["groups"] != sorted(set(value["groups"]))
                or not isinstance(value["selection_sha256"], str)
                or not re.fullmatch(r"[0-9a-f]{64}", value["selection_sha256"])
            ):
                raise IntegrityError("LIFECYCLE_RETENTION_DRIFT")
            for group in value["groups"]:
                self._path(group, "custody")
            results.append((path, value))
        return results

    def retain(self, groups: list[str], *, selection_sha256: str) -> dict[str, Any]:
        """Bind the caller's validated native selection; never select a winner here."""
        self._active()
        if (
            not groups
            or len(set(groups)) != len(groups)
            or not isinstance(selection_sha256, str)
            or not re.fullmatch(r"[0-9a-f]{64}", selection_sha256)
        ):
            raise IntegrityError("LIFECYCLE_RETENTION_SCHEMA")
        for group in groups:
            if self.replay(group)["state"] != "RETAINED_BYTES_VERIFIED":
                raise IntegrityError("LIFECYCLE_DISPOSED_CANNOT_BE_RETAINED")
        index = len(self._retentions()) + 1
        receipt = {
            "schema_version": "mp2-cost-retention/1.0",
            "index": index,
            "groups": sorted(groups),
            "selection_sha256": selection_sha256,
            "guard_sha256": self.guard_sha256,
        }
        write_exclusive_json(self.directory / f"retention-{index:06d}.json", receipt)
        return receipt

    def dispose(self, group: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
        self._active()
        custody_path = self._path(group, "custody")
        if not custody_path.exists():
            raise IntegrityError("LIFECYCLE_CUSTODY_REQUIRED")
        if self.replay(group)["state"] != "RETAINED_BYTES_VERIFIED":
            raise IntegrityError("LIFECYCLE_ALREADY_DISPOSED")
        custody = read_canonical_json(custody_path)
        if custody["artifacts"] != rows or custody["guard_sha256"] != self.guard_sha256:
            raise IntegrityError("LIFECYCLE_CUSTODY_DRIFT")
        retentions = self._retentions()
        if custody["protected_paths"] or (retentions and group in retentions[-1][1]["groups"]):
            raise IntegrityError("LIFECYCLE_RETAINED_PAYLOAD")
        self._rows(rows)
        intent = {
            "schema_version": "mp2-cost-disposal-intent/1.0",
            "custody_sha256": sha256_file(custody_path),
            "guard_sha256": self.guard_sha256,
            "artifacts": rows,
            "retention_sha256": sha256_file(retentions[-1][0]) if retentions else None,
        }
        write_exclusive_json(self._path(group, "intent"), intent)
        for row in rows:
            self._active()
            path = self.root / row["path"]
            reject_reparse_path(path)
            if path.stat().st_nlink != 1 or sha256_file(path) != row["sha256"]:
                raise IntegrityError("LIFECYCLE_DISPOSAL_TARGET_DRIFT")
            path.unlink()
            if path.exists():
                raise IntegrityError("LIFECYCLE_DISPOSAL_READBACK")
        result = {
            "schema_version": "mp2-cost-disposal/1.0",
            "state": "DISPOSED_AFTER_CUSTODY_METADATA_VERIFIED",
            "intent_sha256": canonical_json_sha256(intent),
            "custody_sha256": sha256_file(custody_path),
            "raw_bytes_currently_certified": False,
        }
        write_exclusive_json(self._path(group, "disposed"), result)
        return self.replay(group)

    def replay(self, group: str) -> dict[str, Any]:
        if sha256_file(self.guard) != self.guard_sha256:
            raise IntegrityError("LIFECYCLE_GUARD_DRIFT")
        custody_path = self._path(group, "custody")
        custody = read_canonical_json(custody_path)
        if (
            set(custody)
            != {
                "schema_version",
                "binding_sha256",
                "guard_sha256",
                "group",
                "artifacts",
                "protected_paths",
            }
            or custody["schema_version"] != "mp2-cost-artifact-custody/1.0"
            or custody["group"] != group
            or custody["binding_sha256"] != self.binding
            or custody["guard_sha256"] != self.guard_sha256
            or not isinstance(custody["protected_paths"], list)
            or any(not isinstance(name, str) for name in custody["protected_paths"])
            or custody["protected_paths"] != sorted(set(custody["protected_paths"]))
        ):
            raise IntegrityError("LIFECYCLE_CUSTODY_DRIFT")
        validate_inventory(custody["artifacts"])
        if not set(custody["protected_paths"]) <= {row["path"] for row in custody["artifacts"]}:
            raise IntegrityError("LIFECYCLE_CUSTODY_DRIFT")
        intent_path = self._path(group, "intent")
        disposed_path = self._path(group, "disposed")
        if intent_path.exists() or disposed_path.exists():
            if not intent_path.exists() or not disposed_path.exists():
                raise IntegrityError("LIFECYCLE_PARTIAL_DISPOSAL_IN_DOUBT")
            intent = read_canonical_json(intent_path)
            disposed = read_canonical_json(disposed_path)
            if (
                set(intent)
                != {
                    "schema_version",
                    "custody_sha256",
                    "guard_sha256",
                    "artifacts",
                    "retention_sha256",
                }
                or set(disposed)
                != {
                    "schema_version",
                    "state",
                    "intent_sha256",
                    "custody_sha256",
                    "raw_bytes_currently_certified",
                }
                or intent["schema_version"] != "mp2-cost-disposal-intent/1.0"
                or disposed["schema_version"] != "mp2-cost-disposal/1.0"
                or disposed["state"] != "DISPOSED_AFTER_CUSTODY_METADATA_VERIFIED"
                or intent["artifacts"] != custody["artifacts"]
                or intent["custody_sha256"] != sha256_file(custody_path)
                or intent["guard_sha256"] != self.guard_sha256
                or disposed["intent_sha256"] != canonical_json_sha256(intent)
                or disposed["custody_sha256"] != sha256_file(custody_path)
                or disposed["raw_bytes_currently_certified"] is not False
                or custody["protected_paths"]
                or any(
                    (self.root / safe_name(row["path"])).exists() for row in custody["artifacts"]
                )
            ):
                raise IntegrityError("LIFECYCLE_DISPOSAL_DRIFT")
            if intent["retention_sha256"] is not None:
                matches = [
                    value
                    for path, value in self._retentions()
                    if sha256_file(path) == intent["retention_sha256"]
                ]
                if len(matches) != 1 or group in matches[0]["groups"]:
                    raise IntegrityError("LIFECYCLE_DISPOSAL_RETENTION_DRIFT")
            return disposed
        self._rows(custody["artifacts"])
        return {"state": "RETAINED_BYTES_VERIFIED", "raw_bytes_currently_certified": True}

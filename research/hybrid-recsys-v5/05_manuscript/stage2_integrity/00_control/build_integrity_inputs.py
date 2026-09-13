#!/usr/bin/env python3
"""Build the immutable Stage 2.5 manuscript and bibliography inputs."""

from __future__ import annotations

import hashlib
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[5]
STAGE2 = REPO_ROOT / "research/hybrid-recsys-v5/05_manuscript/stage2_write"
STAGE25 = REPO_ROOT / "research/hybrid-recsys-v5/05_manuscript/stage2_integrity"

MASTER = STAGE2 / "03_draft/master_draft_stage2.tex"
FRAGMENT = STAGE2 / "03_draft/introduction_related_work_stage2.tex"
BIBLIOGRAPHY = STAGE2 / "04_citations/refs_stage2.bib"

OUTPUT_MASTER = STAGE25 / "03_compile/master_draft_stage2_5.tex"
OUTPUT_BIBLIOGRAPHY = STAGE25 / "03_compile/refs_stage2_5.bib"

EXPECTED = {
    MASTER: "8fa271e44b7d1be5fb5ef14921d3b568180e175032268b8120aba438694d6f93",
    FRAGMENT: "338b55f4a330cae9d9a9ba87136e734979a90eeeff9b6ac0f81debe13ff8ac72",
    BIBLIOGRAPHY: "5a93f0868b19f8ebdc8647435b151193a898b67e843db0a6ef3ece27cd9a7fbd",
}

INPUT_MARKER = b"\\input{introduction_related_work_stage2}"
OLD_BIB_MARKER = b"\\bibliography{../04_citations/refs_stage2}"
NEW_BIB_MARKER = b"\\bibliography{refs_stage2_5}"
OLD_CHENG_TITLE = b"title = {Wide and Deep Learning for Recommender Systems}"
NEW_CHENG_TITLE = b"title = {Wide \\& Deep Learning for Recommender Systems}"
GEOMETRY_PACKAGE = b"\\usepackage[margin=1in]{geometry}"
PORTABLE_PAGE_LAYOUT = b"""\\setlength{\\textwidth}{6.5in}
\\setlength{\\oddsidemargin}{0in}
\\setlength{\\evensidemargin}{0in}
\\setlength{\\textheight}{9in}
\\setlength{\\topmargin}{-0.5in}"""
FLOAT_PACKAGE = b"\\usepackage{float}\n"
FORCED_TABLE = b"\\begin{table}[H]"
PORTABLE_TABLE = b"\\begin{table}[htbp]"
ANCHOR_KIND_REWRITES = (
    (b"<!--anchor:figure:", b"<!--anchor:section:", 7),
    (b"<!--anchor:table:", b"<!--anchor:section:", 5),
)


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def locked_read(path: Path) -> bytes:
    raw = path.read_bytes()
    actual = sha256(raw)
    if actual != EXPECTED[path]:
        raise RuntimeError(f"input hash mismatch for {path}: {actual}")
    raw.decode("utf-8", errors="strict")
    if raw.startswith(b"\xef\xbb\xbf"):
        raise RuntimeError(f"UTF-8 BOM is forbidden: {path}")
    return raw


def replace_once(raw: bytes, old: bytes, new: bytes, label: str) -> bytes:
    count = raw.count(old)
    if count != 1:
        raise RuntimeError(f"expected exactly one {label}, found {count}")
    return raw.replace(old, new, 1)


def normalize_anchor_kinds(raw: bytes) -> bytes:
    for old, new, expected_count in ANCHOR_KIND_REWRITES:
        actual_count = raw.count(old)
        if actual_count != expected_count:
            raise RuntimeError(
                f"expected {expected_count} markers for {old!r}, found {actual_count}"
            )
        raw = raw.replace(old, new)
    return raw


def main() -> None:
    master = locked_read(MASTER)
    fragment = locked_read(FRAGMENT)
    bibliography = locked_read(BIBLIOGRAPHY)

    expanded = replace_once(master, INPUT_MARKER, fragment.rstrip(b"\n"), "input marker")
    expanded = replace_once(
        expanded, GEOMETRY_PACKAGE, PORTABLE_PAGE_LAYOUT, "geometry package"
    )
    expanded = replace_once(expanded, FLOAT_PACKAGE, b"", "float package")
    expanded = replace_once(expanded, FORCED_TABLE, PORTABLE_TABLE, "forced table")
    expanded = replace_once(
        expanded, OLD_BIB_MARKER, NEW_BIB_MARKER, "bibliography marker"
    )
    expanded = normalize_anchor_kinds(expanded)
    corrected_bibliography = replace_once(
        bibliography, OLD_CHENG_TITLE, NEW_CHENG_TITLE, "Cheng title"
    )

    OUTPUT_MASTER.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_MASTER.write_bytes(expanded)
    OUTPUT_BIBLIOGRAPHY.write_bytes(corrected_bibliography)

    print(f"master_bytes={len(expanded)}")
    print(f"master_sha256={sha256(expanded)}")
    print(f"bibliography_bytes={len(corrected_bibliography)}")
    print(f"bibliography_sha256={sha256(corrected_bibliography)}")


if __name__ == "__main__":
    main()

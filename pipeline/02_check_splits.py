"""Stage 2: check a regenerated bundle against the reference export before sealing TEST.

TRAIN and VAL must be byte-identical to the reference export (only TEST is redrawn). For TEST it
reports counts and overlap only; it parses no label and computes no metric.

Usage: python 02_check_splits.py --generated <bundle dir> --reference <reference export dir>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from common import split_of


def split_lines(path: Path) -> dict[str, list[bytes]]:
    splits: dict[str, list[bytes]] = {"train": [], "val": [], "test": []}
    with path.open("rb") as stream:
        for line in stream:
            name = split_of(line)
            if name:
                splits[name].append(line)
    return splits


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--generated", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    args = parser.parse_args()
    new = split_lines(args.generated / "events.jsonl")
    old = split_lines(args.reference / "events.jsonl")
    passed = True
    for name in ("train", "val"):
        same = new[name] == old[name]
        passed = passed and same
        print(f"{name}: {len(new[name])} events, identical to reference: {same}")
    shared = len(set(new["test"]) & set(old["test"]))
    print(f"test: {len(new['test'])} events; reference {len(old['test'])}; identical rows {shared}")
    for name in ("baskets.jsonl", "items.jsonl", "users.jsonl"):
        print(
            f"{name} identical:",
            (args.generated / name).read_bytes() == (args.reference / name).read_bytes(),
        )
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()

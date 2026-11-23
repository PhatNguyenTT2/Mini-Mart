"""Stage 3: move the regenerated TEST events into custody and delete the rest of the bundle.

Writes ``<work_root>/custody/test_source_events.jsonl`` and ``custody_receipt.json`` (event count and
SHA-256). Stage 6 refuses to open TEST if the file no longer matches the receipt. Parses no label
and computes no metric.

Usage: python 03_seal_test.py --config <cfg> --generated <bundle dir> --reseed <int>
"""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import common


def main() -> None:
    parser = common.parser(__doc__.splitlines()[0])
    parser.add_argument("--generated", type=Path, required=True)
    parser.add_argument("--reseed", type=int, required=True, help="seed used to redraw TEST")
    args = parser.parse_args()
    config = common.load_config(args.config)
    config.custody_root.mkdir(parents=True, exist_ok=False)
    digest, count = hashlib.sha256(), 0
    with (
        (args.generated / "events.jsonl").open("rb") as source,
        config.sealed_test.open("wb") as target,
    ):
        for line in source:
            if common.split_of(line) == "test":
                target.write(line)
                digest.update(line)
                count += 1
    receipt = {
        "reseed": args.reseed,
        "test_events": count,
        "test_source_sha256": digest.hexdigest(),
        "metrics_computed": False,
    }
    (config.custody_root / "custody_receipt.json").write_text(
        json.dumps(receipt, indent=1), encoding="utf-8"
    )
    shutil.rmtree(args.generated)
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()

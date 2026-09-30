"""Create a reproducible manifest for a labeled JSONL dataset."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any


def build_manifest(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    records = [
        json.loads(line)
        for line in raw.decode("utf-8").splitlines()
        if line.strip()
    ]
    labels = Counter(record.get("label") for record in records)
    bot_families = sorted(
        {
            str(record["bot_family"])
            for record in records
            if record.get("label") == "bot" and record.get("bot_family")
        }
    )
    return {
        "schema_version": "dataset-v0.1",
        "source": str(path),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "samples": len(records),
        "class_counts": {
            "human": labels.get("human", 0),
            "bot": labels.get("bot", 0),
        },
        "bot_families": bot_families,
        "raw_trajectory_included": any("points" in record for record in records),
        "metadata_coverage": (
            sum(bool(record.get("collection_context")) for record in records)
            / len(records)
            if records
            else 0
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    manifest = build_manifest(args.dataset)
    rendered = json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()

"""Remove stationary human collection windows from a JSONL dataset."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


def path_distance(points: list[dict[str, float]]) -> float:
    return sum(
        math.hypot(right["x"] - left["x"], right["y"] - left["y"])
        for left, right in zip(points, points[1:])
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--min-distance-pixels", type=float, default=100)
    args = parser.parse_args()
    kept = 0
    dropped = 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.source.open(encoding="utf-8-sig") as source, args.output.open(
        "w", encoding="utf-8"
    ) as output:
        for line in source:
            if not line.strip():
                continue
            record = json.loads(line)
            distance = path_distance(record.get("points", []))
            if distance < args.min_distance_pixels:
                dropped += 1
                continue
            record.setdefault("collection_context", {})["path_distance_pixels"] = round(
                distance, 2
            )
            output.write(json.dumps(record, ensure_ascii=False) + "\n")
            kept += 1
    print(f"Kept {kept} sessions; dropped {dropped} stationary sessions.")


if __name__ == "__main__":
    main()

"""Generate deterministic labeled bot letter sessions for the first prototype."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


def path_for(kind: str, n: int = 120) -> list[dict[str, float]]:
    points = []
    for i in range(n):
        u = i / (n - 1)
        if kind == "line":
            x, y = u, u
        elif kind == "bezier":
            x = 3 * (1 - u) ** 2 * u + u**3
            y = 3 * (1 - u) * u**2 + u**3
        else:
            x = u
            y = 0.5 + 0.45 * math.sin(u * math.pi * 2)
        points.append({"x": x, "y": y, "t": i * 1000 / 60})
    return points


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples-per-kind", type=int, default=20)
    parser.add_argument("--output", type=Path, default=Path("datasets/raw/bot-letters.jsonl"))
    args = parser.parse_args()
    if args.samples_per_kind < 1:
        parser.error("--samples-per-kind must be positive")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    kinds = ("line", "bezier", "sine")
    with args.output.open("w", encoding="utf-8") as handle:
        for kind in kinds:
            for index in range(args.samples_per_kind):
                handle.write(json.dumps({
                    "label": "bot",
                    "webdriver": True,
                    "pow_ok": True,
                    "bot_family": kind,
                    "letter": "A",
                    "points": path_for(kind),
                }) + "\n")
    print(f"Bot dataset written: {args.output} ({len(kinds) * args.samples_per_kind} sessions)")


if __name__ == "__main__":
    main()

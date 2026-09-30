"""Create a consistent SQLite audit backup without stopping the API."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=Path("data/audit.sqlite3"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not args.source.is_file():
        raise SystemExit(f"audit database not found: {args.source}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    source = sqlite3.connect(args.source)
    target = sqlite3.connect(args.output)
    try:
        source.backup(target)
    finally:
        target.close()
        source.close()
    print(f"Audit backup written: {args.output}")


if __name__ == "__main__":
    main()

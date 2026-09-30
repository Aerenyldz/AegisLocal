"""Create a hash-pinned manifest for an ONNX model artifact."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("model", type=Path)
    parser.add_argument("--version", required=True)
    parser.add_argument("--dataset-manifest", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not args.model.is_file():
        parser.error(f"model does not exist: {args.model}")
    dataset_hash = None
    if args.dataset_manifest:
        dataset = json.loads(args.dataset_manifest.read_text(encoding="utf-8"))
        dataset_hash = dataset.get("sha256")
    manifest = {
        "schema_version": "model-manifest-v0.1",
        "model_version": args.version,
        "model_path": str(args.model),
        "model_sha256": hashlib.sha256(args.model.read_bytes()).hexdigest(),
        "dataset_sha256": dataset_hash,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "promotion": "manual_only",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()

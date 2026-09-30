"""Check measured release gates before enabling a pilot enforcement policy."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("evaluation", type=Path)
    parser.add_argument("--load-report", type=Path)
    args = parser.parse_args()
    evaluation = json.loads(args.evaluation.read_text(encoding="utf-8"))
    failures: list[str] = []
    if not evaluation.get("model_release_allowed"):
        failures.append("model_release_allowed is false")
    if evaluation.get("status") != "ready_for_comparison":
        failures.append("dataset status is not ready_for_comparison")
    operating = evaluation.get("operating_point", {})
    if operating.get("fpr") is None or operating["fpr"] > 0.02:
        failures.append("human FPR must be <= 2%")
    if operating.get("tpr") is None or operating["tpr"] < 0.85:
        failures.append("bot TPR must be >= 85%")
    if evaluation.get("roc_auc") is None or evaluation["roc_auc"] < 0.85:
        failures.append("ROC-AUC must be >= 0.85")
    if args.load_report:
        load = json.loads(args.load_report.read_text(encoding="utf-8"))
        if load.get("error_rate", 1) > 0.01:
            failures.append("load-test error rate must be <= 1%")
    result = {"ready_for_pilot": not failures, "failures": failures}
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

"""Run a bounded local API smoke/load test and print latency metrics."""

from __future__ import annotations

import argparse
import json
import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def call(url: str, timeout: float) -> tuple[float, int | str]:
    started = time.perf_counter()
    try:
        with urlopen(Request(url, method="GET"), timeout=timeout) as response:
            response.read()
            status: int | str = response.status
    except HTTPError as error:
        status = error.code
    except (URLError, TimeoutError) as error:
        status = type(error).__name__
    return (time.perf_counter() - started) * 1000, status


def percentile(values: list[float], percentile_value: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, round((len(ordered) - 1) * percentile_value))
    return ordered[index]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8000/health")
    parser.add_argument("--requests", type=int, default=100)
    parser.add_argument("--workers", type=int, default=10)
    parser.add_argument(
        "--timeout",
        type=float,
        default=10,
        help="per-request timeout in seconds (default: 10)",
    )
    args = parser.parse_args()
    if args.requests < 1 or args.workers < 1:
        parser.error("requests and workers must be positive")

    # Warm the server before measuring concurrency so import/startup latency is
    # not incorrectly reported as request failure.
    _, warmup_status = call(args.url, args.timeout)
    if warmup_status != 200:
        raise SystemExit(f"load smoke failed: warm-up returned {warmup_status}")

    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = list(pool.map(lambda _: call(args.url, args.timeout), range(args.requests)))
    elapsed = time.perf_counter() - started
    latencies = [latency for latency, status in results if isinstance(status, int)]
    if not latencies:
        raise SystemExit("load smoke failed: no HTTP responses received")
    successful = sum(status == 200 for _, status in results)
    report = {
        "url": args.url,
        "requests": args.requests,
        "workers": args.workers,
        "successful": successful,
        "errors": args.requests - successful,
        "error_rate": (args.requests - successful) / args.requests,
        "throughput_rps": args.requests / elapsed if elapsed else 0,
        "latency_ms": {
            "min": min(latencies),
            "mean": statistics.mean(latencies),
            "p50": percentile(latencies, 0.50),
            "p95": percentile(latencies, 0.95),
            "max": max(latencies),
        },
    }
    print(json.dumps(report, indent=2))
    if report["error_rate"] > 0.01:
        raise SystemExit("load smoke failed: error rate exceeds 1%")


if __name__ == "__main__":
    main()

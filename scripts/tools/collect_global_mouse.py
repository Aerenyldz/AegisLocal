"""Collect global Windows pointer movement into local labeled JSONL windows.

Only screen coordinates and monotonic elapsed time are collected. Clicks,
keyboard input, active-window metadata, screenshots, and network uploads are
intentionally out of scope.
"""

from __future__ import annotations

import argparse
import ctypes
import json
import math
import platform
import time
from ctypes import wintypes
from pathlib import Path


class Point(ctypes.Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]


def cursor_position() -> tuple[int, int]:
    point = Point()
    if not ctypes.windll.user32.GetCursorPos(ctypes.byref(point)):
        raise ctypes.WinError()
    return point.x, point.y


def collect(
    *,
    duration_minutes: float,
    window_seconds: float,
    sample_hz: float,
    min_points: int,
    min_distance_pixels: float,
    output: Path,
) -> int:
    if platform.system() != "Windows":
        raise RuntimeError("Global mouse collection currently supports Windows only")
    if duration_minutes <= 0 or window_seconds <= 0 or sample_hz <= 0:
        raise ValueError("duration, window size, and sample rate must be positive")

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("", encoding="utf-8")
    duration_seconds = duration_minutes * 60
    interval = 1 / sample_hz
    started = time.monotonic()
    next_sample = started
    window_started = started
    points: list[dict[str, float]] = []
    sessions = 0

    def flush_window() -> None:
        nonlocal points, sessions, window_started
        distance = sum(
            math.hypot(right["x"] - left["x"], right["y"] - left["y"])
            for left, right in zip(points, points[1:])
        )
        if len(points) >= min_points and distance >= min_distance_pixels:
            record = {
                "label": "human",
                "webdriver": False,
                "collection_context": {
                    "collector": "global-windows-pointer",
                    "platform": platform.platform(aliased=True),
                    "sample_hz": sample_hz,
                    "window_seconds": window_seconds,
                    "path_distance_pixels": round(distance, 2),
                },
                "points": points,
            }
            with output.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            sessions += 1
        points = []
        window_started = time.monotonic()

    print("Global mouse collection started.")
    print("Only pointer coordinates are read; Ctrl+C stops and saves the last window.")
    print(f"Duration: {duration_minutes:g} minutes | Output: {output}")
    try:
        while time.monotonic() - started < duration_seconds:
            now = time.monotonic()
            x, y = cursor_position()
            points.append(
                {
                    "x": float(x),
                    "y": float(y),
                    "t": (now - started) * 1000,
                }
            )
            if now - window_started >= window_seconds:
                flush_window()
                print(f"Saved windows: {sessions}")
            next_sample += interval
            time.sleep(max(0, next_sample - time.monotonic()))
    except KeyboardInterrupt:
        print("\nStopping collection...")
    finally:
        flush_window()

    print(f"Finished. Saved {sessions} sessions to {output}")
    return sessions


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--duration-minutes", type=float, default=15)
    parser.add_argument("--window-seconds", type=float, default=30)
    parser.add_argument("--sample-hz", type=float, default=30)
    parser.add_argument("--min-points", type=int, default=80)
    parser.add_argument("--min-distance-pixels", type=float, default=100)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("datasets/raw/human-global.jsonl"),
    )
    args = parser.parse_args()
    if args.min_points < 8:
        parser.error("--min-points must be at least 8")
    collect(
        duration_minutes=args.duration_minutes,
        window_seconds=args.window_seconds,
        sample_hz=args.sample_hz,
        min_points=args.min_points,
        min_distance_pixels=args.min_distance_pixels,
        output=args.output,
    )


if __name__ == "__main__":
    main()

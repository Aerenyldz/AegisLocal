"""
Playwright bot probe against local AegisLocal API.

Install: pip install playwright httpx && playwright install chromium
Run:    python scripts/bot_playwright.py
"""

from __future__ import annotations

import asyncio
import math
import os
import sys

import httpx

try:
    from playwright.async_api import async_playwright
except ImportError:
    print("Install playwright: pip install playwright && playwright install chromium")
    sys.exit(1)

API = os.environ.get("AEGIS_API", "http://127.0.0.1:8000")


def bezier_points(n: int = 100) -> list[dict]:
    """Overly smooth cubic Bezier — typical automation path."""
    p0, p1, p2, p3 = (50, 50), (200, 40), (220, 300), (400, 280)
    pts = []
    for i in range(n):
        u = i / (n - 1)
        x = (
            (1 - u) ** 3 * p0[0]
            + 3 * (1 - u) ** 2 * u * p1[0]
            + 3 * (1 - u) * u**2 * p2[0]
            + u**3 * p3[0]
        )
        y = (
            (1 - u) ** 3 * p0[1]
            + 3 * (1 - u) ** 2 * u * p1[1]
            + 3 * (1 - u) * u**2 * p2[1]
            + u**3 * p3[1]
        )
        pts.append({"x": x, "y": y, "t": i * (1000 / 60)})
    return pts


async def main() -> None:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        await page.goto("about:blank")
        webdriver = await page.evaluate("() => navigator.webdriver === true")
        await browser.close()

    points = bezier_points()
    payload = {
        "session_id": "botplaywright01",
        "points": points,
        "webdriver": webdriver,
        "fingerprint": {"source": "playwright-bot"},
    }
    async with httpx.AsyncClient(base_url=API, timeout=30.0) as client:
        health = await client.get("/health")
        health.raise_for_status()
        res = await client.post("/v1/analyze/mouse", json=payload)
        res.raise_for_status()
        data = res.json()

    print("webdriver:", webdriver)
    print("decision:", data["decision"])
    print("risk_score:", data["risk_score"])
    print("label:", data["label"])
    print("reasons:")
    for r in data["reasons"]:
        print(" -", r)
    print("xai:", data["xai"])


if __name__ == "__main__":
    asyncio.run(main())

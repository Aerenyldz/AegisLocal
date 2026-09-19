# AegisLocal — Doğrulama ve Test Stratejisi

## 1. Yerel Ortam Smoke

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

```bash
pytest backend/tests -q
curl http://127.0.0.1:8000/health
```

Demo sayfası: `scripts/demo.html` (backend CORS debug=True ile).

## 2. Katman Testleri

| Katman | Araç | Başarı kriteri |
|--------|------|----------------|
| FFT özellik | `pytest` sentetik insan/bot yörüngeleri | Bot skor > insan skor (ortalama) |
| PoW | Rust `cargo test` + API `/v1/pow/*` | Geçerli proof kabul; replay red |
| Rate limit | Burst script | 429 sonrası |
| SDK | Manuel demo + Playwright | ≥8 nokta sonrası analyze 200 |

## 3. Bot otomasyonu (Playwright)

`scripts/bot_playwright.py` — düz Bézier benzeri hareket + stealth bayrakları.

Beklenen MVP davranışı:
- `navigator.webdriver` true ise risk↑
- Aşırı düzgün path → `path_too_smooth` / `low_tremor_energy`
- Karar çoğunlukla `soft_challenge` veya `deny`

## 4. İnsan davranışı simülasyonu

`scripts/human_sim.py` — fizyolojik tremor (8–12 Hz) + velocity jitter + Fitts benzeri hız profili.

Beklenen: `allow` veya düşük `gray`; XAI’de `tremor_present`.

## 5. Senaryo Matrisi

| # | Senaryo | Beklenen karar |
|---|---------|----------------|
| S1 | Gerçek kullanıcı, normal form | allow |
| S2 | Playwright düz lineTo | deny / soft_challenge |
| S3 | Puppeteer-stealth + Bezier | soft_challenge (≥) |
| S4 | PoW yok / sahte digest | deny (pow_failed) |
| S5 | Rate flood | 429 |
| S6 | Motor engelli (WASM off) | JS PoW ile allow path |
| S7 | Physics challenge replay | invalid |

## 6. Metrikler (Phase 5’e taşınır)

- TPR / FPR (bot tespit / insan yanlış pozitif)
- p50/p95 analyze latency
- PoW solve ms (WASM vs JS)
- Challenge completion rate

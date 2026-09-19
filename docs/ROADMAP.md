# AegisLocal — 20 Haftalık Uygulama Yol Haritası

5 faz · haftalık sprint · DoD kriterleri.

---

## Faz 1 — Araştırma & Veri Altyapısı (Hafta 1–4)

| Hafta | Sprint hedefi | Deliverables | Definition of Done |
|------|----------------|--------------|--------------------|
| **1** | Telemetri şeması + etik onay | JSON schema (`points`, fingerprint), KVKK DPIA taslağı, raw-retention opt-in bayrağı | Schema CI’de validate; gizlilik notu README’de |
| **2** | İnsan çeşitlilik toplama | Gönüllü kayıt UI / script, cihaz/OS etiketleri, `datasets/raw` pipeline | ≥200 insan oturumu (lab) veya sentetik+gerçek karışık seed set |
| **3** | Bot corpus | Playwright / Puppeteer-Stealth / Selenium / düz `fetch` botları | Her bot ailesi için ≥50 yörünge; etiket `bot_family` |
| **4** | Baseline FFT analizi | Özellik notebook + istatistik rapor; insan vs bot tremor_ratio dağılımı | ROC-AUC ≥0.85 lab setinde; özellik dökümanı merge |

**Faz 1 çıkış kapısı:** Etiketli dataset v0.1 + FFT özellik sözlüğü onaylandı.

---

## Faz 2 — Kriptografi / PoW (Hafta 5–8)

| Hafta | Sprint hedefi | Deliverables | DoD |
|------|----------------|--------------|-----|
| **5** | Rust PoW + WASM build | `pow-wasm` `wasm-pack`, JS fallback parity testleri | Aynı challenge → WASM/JS aynı digest; unit test yeşil |
| **6** | Dinamik zorluk | Risk’e göre difficulty 12–22; p95 latency telemetry | Medyan WASM çözüm <50ms @diff≤16 mid-tier CPU |
| **7** | Nonce / replay | Redis single-use, TTL, clock skew toleransı | Replay saldırısı testleri fail; rate-limit entegre |
| **8** | A11y politikası | WASM kapalı / motor engeli → JS PoW veya WCAG challenge | WCAG 2.2 AA checklist; ekran okuyucu senaryosu geçer |

**Faz 2 çıkış kapısı:** PoW prod-ready; fallback + a11y belgelenmiş.

---

## Faz 3 — AI / ONNX Motoru (Hafta 9–12)

| Hafta | Sprint hedefi | Deliverables | DoD |
|------|----------------|--------------|-----|
| **9** | Isolation Forest train | scikit-learn → ONNX export; `OnnxScorer` canlı | Model artifact + hash; inference <5ms CPU |
| **10** | Sequence model | GRU/LSTM kısa pencere (hız/ivme); ensemble | Ensemble ≥ baseline FFT; false-positive <2% insan set |
| **11** | XAI risk matrisi | Feature contribution + reasons API; Grafana panel | Her yanıtta `xai` + `reasons`; dashboard mock |
| **12** | Drift & retraining | Incremental pipeline, shadow mode, drift alarm | Haftalık retrain dry-run; drift eşiği dokümante |

**Faz 3 çıkış kapısı:** ONNX ensemble + XAI + shadow deploy.

---

## Faz 4 — Physics Canvas (Hafta 13–16)

| Hafta | Sprint hedefi | Deliverables | DoD |
|------|----------------|--------------|-----|
| **13** | Canvas fizik motoru | Yerçekimi + rüzgar; seed’li deterministik sim | Seed replay sunucu tarafı eşleşir |
| **14** | Etkileşim doğrulama | Trajectory hash, süre, fizik tutarlılık skorları | Bot script’leri >80% fail; insan >95% pass |
| **15** | Replay-attack koruması | Single-use + HMAC token + timing bounds | Kayıtlı trajectory yeniden gönderilemez |
| **16** | Gri bölge orkestrasyon | soft_challenge akışını SDK’ya bağla | E2E: gray → canvas → allow/deny |

**Faz 4 çıkış kapısı:** Gri bölge challenge production path tamam.

---

## Faz 5 — Dağıtım / Docker / Ops (Hafta 17–20)

| Hafta | Sprint hedefi | Deliverables | DoD |
|------|----------------|--------------|-----|
| **17** | Docker Compose | API + Redis + Postgres + Prometheus | `docker compose up` tek komutla ayakta |
| **18** | Rate-limit & reputation | Sliding window + opsiyonel AbuseIPDB/MaxMind | Air-gap’te reputation kapalı; limit testleri |
| **19** | Ops dashboard | React: bot/insan oranı, XAI, PoW latency | Canlı metrikler; alert kuralları |
| **20** | Hardening & release | Threat model, load test, v1.0 runbook | 1k RPS smoke; security checklist imzalı |

**Faz 5 çıkış kapısı:** On-prem v1.0 release candidate.

---

## Kritik Yol Bağımlılıkları

```
Dataset (F1) ──► FFT/ONNX (F3)
     │
PoW (F2) ──────► Orkestrasyon (F4) ──► Deploy (F5)
Reputation/RL (F5) ◄── Botnet riski (sürekli)
```

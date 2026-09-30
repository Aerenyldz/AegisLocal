# AegisLocal

%100 yerel (on-premise), KVKK/GDPR uyumlu davranışsal Bot Defense Gateway.

Amaç bir CAPTCHA klonu olmak değil: kurumun kendi trafiğine göre çalışan,
kararını açıklayan ve dış servise veri göndermeyen yerel risk motoru.

MVP ürün planı: [docs/MVP_PRODUCT_PLAN.md](docs/MVP_PRODUCT_PLAN.md)

Login entegrasyonu: [docs/LOGIN_INTEGRATION.md](docs/LOGIN_INTEGRATION.md)

Docker ile API + Redis + yerel audit persistence çalıştırma:
[docs/DEPLOYMENT_RUNBOOK.md](docs/DEPLOYMENT_RUNBOOK.md)

Kontrollü pilot ve v1.0 çıkış adımları:
[docs/PILOT_RUNBOOK.md](docs/PILOT_RUNBOOK.md)

---

## Prototip nasıl açılır?

Windows'ta doğrudan proje klasöründeki `BASLAT_AEGISLOCAL.bat` dosyasına çift
tıklayabilirsiniz. Bu dosya backend'i, demo web sunucusunu ve demo ekranını
otomatik açar.

Mevcut demo, MVP'nin risk motoru ve challenge katmanını gösterir. Ürünleşme
sırası `SDK → risk engine → policy engine → enforcement → audit/training`
şeklindedir; demo tek başına nihai ürün değildir.

### 1) API’yi başlat (zorunlu)

PowerShell:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
# İlk seferde venv yoksa:
#   python -m venv .venv
#   .\.venv\Scripts\Activate.ps1
#   pip install -r requirements.txt

uvicorn app.main:app --reload --port 8000
```

Veya kökten kısayol:

```powershell
cd <proje-klasoru>
.\AegisLocal.bat
```

Hazır olduğunda:

| Ne | Adres |
|----|--------|
| Sağlık | http://127.0.0.1:8000/health |
| API docs (Swagger) | http://127.0.0.1:8000/docs |
| Analiz endpoint | `POST /v1/analyze/mouse` |

### 2) Tarayıcı demosu (asıl prototip UI)

API ayaktayken `scripts\web\demo.html` dosyasını tarayıcıda aç:

- Explorer’da dosyaya çift tık, veya
- Chrome/Edge adres çubuğuna yapıştır:

```
http://127.0.0.1:5500/demo.html
```

Sonra pad üzerinde fareyi hareket ettir (≥8 nokta) → **Analiz Et**.

### 3) İsteğe bağlı script testleri

Yeni bir terminalde (API çalışırken):

```powershell
cd C:\Users\ahmet\OneDrive\Desktop\AegisLocal\backend
.\.venv\Scripts\Activate.ps1
python ..\scripts\tools\human_sim.py
python ..\scripts\tools\bot_playwright.py   # önce: pip install playwright && playwright install chromium
python -m pytest -q
```

---

## Doğrulama

Backend MVP testleri proje kökünden çalıştırılabilir:

```powershell
python -m pytest -q
```

Release kapısını ölçülmüş dataset ve yük testi çıktısı üzerinden çalıştır:

```powershell
python scripts\tools\release_check.py `
  datasets\processed\phase3-labeled-v0.1-clean.evaluation.json `
  --load-report artifacts\load-report.json
```

Bu komut başarısızsa enforcement pilotu başlatılmamalıdır. Dataset ve load
raporu henüz oluşturulmadıysa bu beklenen bir durumdur.

---

## Proje yapısı (kısa)

```
AegisLocal/
├── backend/          # FastAPI + FFT skor (prototip kalbi)
├── client-sdk/       # TypeScript telemetri SDK
├── pow-wasm/         # Rust PoW (WASM)
├── scripts/
│   ├── launchers/    # API, demo ve collector başlatıcıları
│   ├── tools/        # Simülasyon, dataset ve release araçları
│   └── web/          # Demo ve operator ekranları
├── docs/             # Mimari, roadmap, test
└── infra/docker/     # API + Redis Compose deployment
```

Detay: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) · [docs/ROADMAP.md](docs/ROADMAP.md) · [docs/TEST_STRATEGY.md](docs/TEST_STRATEGY.md)

## Lisans

Proprietary — kurum içi / on-premise dağıtım.

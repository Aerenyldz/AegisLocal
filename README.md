# AegisLocal

%100 yerel (on-premise), KVKK/GDPR uyumlu davranışsal Bot Defense Gateway.

Amaç bir CAPTCHA klonu olmak değil: kurumun kendi trafiğine göre çalışan,
kararını açıklayan ve dış servise veri göndermeyen yerel risk motoru.

MVP ürün planı: [docs/MVP_PRODUCT_PLAN.md](docs/MVP_PRODUCT_PLAN.md)

Login entegrasyonu: [docs/LOGIN_INTEGRATION.md](docs/LOGIN_INTEGRATION.md)

Docker ile API + Redis + yerel audit persistence çalıştırma:
[docs/DEPLOYMENT_RUNBOOK.md](docs/DEPLOYMENT_RUNBOOK.md)

---

## Prototip nasıl açılır?

Mevcut demo, MVP'nin risk motoru ve challenge katmanını gösterir. Ürünleşme
sırası `SDK → risk engine → policy engine → enforcement → audit/training`
şeklindedir; demo tek başına nihai ürün değildir.

### 1) API’yi başlat (zorunlu)

PowerShell:

```powershell
cd C:\Users\ahmet\OneDrive\Desktop\AegisLocal\backend
.\.venv\Scripts\Activate.ps1
# İlk seferde venv yoksa:
#   python -m venv .venv
#   .\.venv\Scripts\Activate.ps1
#   pip install -r requirements.txt

uvicorn app.main:app --reload --port 8000
```

Veya kökten kısayol:

```powershell
cd C:\Users\ahmet\OneDrive\Desktop\AegisLocal
.\scripts\start-api.ps1
```

Hazır olduğunda:

| Ne | Adres |
|----|--------|
| Sağlık | http://127.0.0.1:8000/health |
| API docs (Swagger) | http://127.0.0.1:8000/docs |
| Analiz endpoint | `POST /v1/analyze/mouse` |

### 2) Tarayıcı demosu (asıl prototip UI)

API ayaktayken `scripts\demo.html` dosyasını tarayıcıda aç:

- Explorer’da dosyaya çift tık, veya
- Chrome/Edge adres çubuğuna yapıştır:

```
file:///C:/Users/ahmet/OneDrive/Desktop/AegisLocal/scripts/demo.html
```

Sonra pad üzerinde fareyi hareket ettir (≥8 nokta) → **Analiz Et**.

### 3) İsteğe bağlı script testleri

Yeni bir terminalde (API çalışırken):

```powershell
cd C:\Users\ahmet\OneDrive\Desktop\AegisLocal\backend
.\.venv\Scripts\Activate.ps1
python ..\scripts\human_sim.py
python ..\scripts\bot_playwright.py   # önce: pip install playwright && playwright install chromium
pytest tests -q
```

---

## GitHub’a ekleme

Repo `git init` ile hazır; `.gitignore` venv / node_modules / target dışlar.

**1. İlk commit** (henüz yapılmadı — istersen benim yapmamı söyle):

```powershell
cd C:\Users\ahmet\OneDrive\Desktop\AegisLocal
git add .
git commit -m "Initial AegisLocal MVP: SDK, FFT API, PoW, docs"
```

**2. GitHub’da boş repo oluştur** (web: New repository → isim: `AegisLocal` → Create).  
Ardından (kullanıcı adını değiştir):

```powershell
git remote add origin https://github.com/<KULLANICI>/AegisLocal.git
git branch -M main
git push -u origin main
```

`GitHub CLI` (`gh`) kuruluysa alternatif: `gh repo create AegisLocal --private --source=. --remote=origin --push`

---

## Proje yapısı (kısa)

```
AegisLocal/
├── backend/          # FastAPI + FFT skor (prototip kalbi)
├── client-sdk/       # TypeScript telemetri SDK
├── pow-wasm/         # Rust PoW (WASM)
├── scripts/
│   ├── demo.html     # Tarayıcı prototipi  ← buradan aç
│   ├── start-api.ps1
│   ├── human_sim.py
│   └── bot_playwright.py
├── docs/             # Mimari, roadmap, test
└── infra/docker/     # API + Redis Compose deployment
```

Detay: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) · [docs/ROADMAP.md](docs/ROADMAP.md) · [docs/TEST_STRATEGY.md](docs/TEST_STRATEGY.md)

## Lisans

Proprietary — kurum içi / on-premise dağıtım.

# Labeled dataset schema

The evaluation pipeline reads UTF-8 JSONL files. Each non-empty line is one
mouse session and must contain:

```json
{
  "label": "human",
  "webdriver": false,
  "pow_ok": true,
  "points": [
    {"x": 120.0, "y": 80.0, "t": 0.0},
    {"x": 121.0, "y": 81.0, "t": 16.7}
  ]
}
```

Audit'ten üretilen snapshot'lar ham trajectory içermez; yalnızca türetilmiş
feature'lar ve operatör etiketi taşır. Bu snapshot model eğitimi için değil,
önce özellik-temelli değerlendirme ve etiket kalitesi kontrolü için kullanılır:

```powershell
Invoke-WebRequest http://127.0.0.1:8001/v1/audit/export -OutFile datasets\processed\audit-labeled.jsonl
```

Bu dosya doğrudan offline değerlendirilebilir:

```powershell
$env:PYTHONPATH="backend"
python scripts\tools\evaluate_dataset.py datasets\processed\audit-labeled.jsonl
```

Export'taki `risk_score` kullanılır; ham trajectory olmadığı için feature'lar
yeniden çıkarılmaz. Bir insan ve bir bot sınıfı yoksa sonuç
`insufficient_classes` olur. En az 20 örnek ve her sınıfta en az 10 örnek olmadan model yayını
`model_release_allowed: false` kalır.

Etiketleme API'si yalnızca `human`, `bot` veya `uncertain` kabul eder.
`uncertain` eğitim export'una dahil edilmez.

`label` is the ground-truth class (`human` or `bot`). `webdriver` and `pow_ok`
are optional signals used by the current scorer. A session needs at least
eight points; raw files remain local and are intentionally ignored by Git.
Letter challenge records may additionally include `letter` and `bot_family`.
Collection records may include a privacy-safe `collection_context` object with
browser family, platform, touch capability and pointer type. It must not
contain a user agent string, IP address, account identifier or form value.

Run an evaluation from the repository root:

```powershell
$env:PYTHONPATH="backend"
python scripts\tools\evaluate_dataset.py datasets\raw\labeled.jsonl
```

The output reports class counts, mean risk, ROC-AUC, TPR, FPR and accuracy.
Do not use metrics from a dataset with fewer than one sample in each class.

Create a reproducible manifest before evaluating a dataset:

```powershell
$env:PYTHONPATH="backend"
python scripts\tools\dataset_manifest.py datasets\raw\labeled.jsonl `
  --output datasets\processed\labeled.manifest.json
```

The manifest records the SHA-256 hash, class counts, bot families and metadata
coverage. The evaluation report only marks the dataset ready when it has at least 20
sessions, at least 10 samples per class and no duplicate audit IDs. Model
release additionally requires ROC-AUC >= 0.85, TPR >= 0.85 and human FPR <= 2%.

## Browser collection

Open `scripts\web\human-training.html` in Chrome or Edge. Move naturally in the
pad, save each session after at least 80 points, then download the JSONL file.
Copy the downloaded file to `datasets\raw\human.jsonl` locally. Build the
feature baseline with:

```powershell
$env:PYTHONPATH="backend;scripts"
python scripts\tools\train_human_baseline.py datasets\raw\human.jsonl
```

### Pasif 15 dakikalık toplama

Tek tek oturum kaydetmek yerine `scripts\web\passive-human-collector.html`
dosyasını açabilirsin. **Toplamayı başlat** düğmesine bastıktan sonra sayfa
üzerinde normal şekilde hareket et. Toplayıcı:

- yalnızca bu sayfadaki pointer hareketlerini izler,
- 15 dakika sonra otomatik durur,
- hareketleri 30 saniyelik pencerelere böler,
- 80 noktadan az olan veya 100 pikselden az hareket içeren boş pencereleri atar,
- JSONL dosyasını tarayıcıdan indirir,
- hiçbir veriyi API'ye göndermez.

Dosyayı `datasets/raw/human-passive.jsonl` olarak kopyaladıktan sonra manifest
ve değerlendirme çalıştırılabilir:

```powershell
$env:PYTHONPATH="backend"
python scripts\tools\dataset_manifest.py datasets\raw\human-passive.jsonl `
  --output datasets\processed\human-passive.manifest.json
python scripts\tools\evaluate_dataset.py datasets\raw\human-passive.jsonl
```

Bu yöntem bir kişinin doğal hareketlerinden çok sayıda pencere üretir; kişisel
baseline için yararlıdır ancak 200 farklı insanı temsil etmez. Modeli üretime
almadan önce farklı kişilerden ve cihazlardan ek veri gerekir.

### Windows'ta arka planda global mouse toplama

Günlük iş yaparken ekranın tamamındaki pointer hareketlerini toplamak için
tarayıcı sayfası yerine Windows script'i kullanılabilir. Bu script yalnızca
`GetCursorPos` ile koordinat ve zamanı okur; tıklama, klavye, aktif pencere,
ekran görüntüsü veya ağ gönderimi yapmaz:

```powershell
python scripts\tools\collect_global_mouse.py `
  --duration-minutes 15 `
  --output datasets\raw\human-global.jsonl
```

Kısayol:

```powershell
.\scripts\launchers\start-global-mouse-collector.ps1
```

Durdurmak için `Ctrl+C` kullanılabilir; o ana kadar yeterli hareket içeren
30 saniyelik pencereler JSONL dosyasına yazılmış olur. Script tamamlandıktan
sonra `dataset_manifest.py` ve `evaluate_dataset.py` ile dosya kontrol edilir.
Bu global kayıt yöntemi yalnızca Windows içindir ve başka uygulamalardaki
mouse hareketlerini görebildiği için kullanıcı tarafından açıkça başlatılmalıdır.

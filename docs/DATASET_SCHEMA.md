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
python scripts\evaluate_dataset.py datasets\processed\audit-labeled.jsonl
```

Export'taki `risk_score` kullanılır; ham trajectory olmadığı için feature'lar
yeniden çıkarılmaz. Bir insan ve bir bot sınıfı yoksa sonuç
`insufficient_classes` olur. En az 20 örnek ve iki sınıf olmadan model yayını
`model_release_allowed: false` kalır.

Etiketleme API'si yalnızca `human`, `bot` veya `uncertain` kabul eder.
`uncertain` eğitim export'una dahil edilmez.

`label` is the ground-truth class (`human` or `bot`). `webdriver` and `pow_ok`
are optional signals used by the current scorer. A session needs at least
eight points; raw files remain local and are intentionally ignored by Git.
Letter challenge records may additionally include `letter` and `bot_family`.

Run an evaluation from the repository root:

```powershell
$env:PYTHONPATH="backend"
python scripts\evaluate_dataset.py datasets\raw\labeled.jsonl
```

The output reports class counts, mean risk, ROC-AUC, TPR, FPR and accuracy.
Do not use metrics from a dataset with fewer than one sample in each class.

## Browser collection

Open `scripts\human-training.html` in Chrome or Edge. Move naturally in the
pad, save each session after at least 80 points, then download the JSONL file.
Copy the downloaded file to `datasets\raw\human.jsonl` locally. Build the
feature baseline with:

```powershell
$env:PYTHONPATH="backend;scripts"
python scripts\train_human_baseline.py datasets\raw\human.jsonl
```

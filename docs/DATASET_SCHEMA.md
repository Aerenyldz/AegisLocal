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

`label` is the ground-truth class (`human` or `bot`). `webdriver` and `pow_ok`
are optional signals used by the current scorer. A session needs at least
eight points; raw files remain local and are intentionally ignored by Git.

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

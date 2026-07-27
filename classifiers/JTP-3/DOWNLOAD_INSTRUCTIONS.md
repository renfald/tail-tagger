# JTP-3 (Hydra) Classifier Model

This directory should contain the **JTP-3 Hydra** model and its calibration
metadata. JTP-3 is loaded through the vendored Hydra package, which needs the two
CSV metadata files below in addition to the weights.

> Prefer **Hydra 3.5** (`classifiers/JTP-3.5/`) for new work — it is the newer,
> more accurate model and is self-contained. JTP-3 is kept for compatibility.

## Required Files

Download **three files** from the [RedRocket/Hydra repository on Hugging Face](https://huggingface.co/RedRocket/Hydra):

1. **jtp-3-hydra.safetensors** (~1.0 GB) — the model weights (from `models/`)
2. **jtp-3-hydra-tags.csv** (~196 KB) — tag categories + implications (from `data/`)
3. **jtp-3-hydra-val.csv** (~42 MB) — per-tag validation data used for calibration (from `data/`)

All three must be placed in this directory, and the CSV base names must match the
`.safetensors` name (`jtp-3-hydra-*`) — the loader looks them up by that prefix.

**Note:** Without the two CSVs the model cannot be loaded/calibrated.

## Download Instructions

### Option A — Hugging Face CLI (recommended)
```bash
hf download RedRocket/Hydra models/jtp-3-hydra.safetensors data/jtp-3-hydra-tags.csv data/jtp-3-hydra-val.csv \
  --local-dir ./_hydra_dl
# then move the three files into classifiers/JTP-3/ (flatten the models/ and data/ subfolders)
```

### Option B — Manual
1. Visit: https://huggingface.co/RedRocket/Hydra/tree/main
2. From `models/` download `jtp-3-hydra.safetensors`
3. From `data/` download `jtp-3-hydra-tags.csv` and `jtp-3-hydra-val.csv`
4. Place all three directly in this directory (`classifiers/JTP-3/`)

## Expected Directory Structure

```
classifiers/JTP-3/
├── jtp-3-hydra.safetensors
├── jtp-3-hydra-tags.csv
├── jtp-3-hydra-val.csv
├── overrides.toml            (optional; blacklist/translation)
└── DOWNLOAD_INSTRUCTIONS.md   (this file)
```

## Requirements

JTP-3 (like Hydra 3.5) runs on the vendored Hydra package and needs:
- **pyvips[binary]** (image preprocessing via libvips — installed by setup)
- **einops**, **safetensors**, **torch** (installed by setup)

If you encounter import errors, refresh the environment:
```bash
pip install -r requirements.txt --upgrade
```
Or re-run `setup.bat` / `setup.sh`.

## About JTP-3

JTP-3 uses the Hydra architecture on a NaFlex SigLIP2 Vision Transformer with
variable-resolution image processing and per-tag calibrated thresholds. Once the
files are in place, restart the application and select "JTP-3 Hydra" from the
classifier dropdown.

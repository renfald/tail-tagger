# Hydra 3.5 Classifier Model

This directory should contain the **Hydra 3.5** classifier model — the newest and
most accurate model, and the recommended default.

## Required Files

Download **one file** from the [RedRocket/Hydra repository on Hugging Face](https://huggingface.co/RedRocket/Hydra):

1. **hydra-3.5.safetensors** (~1.06 GB) — the model weights (from `models/`)

Hydra 3.5 is fully self-contained: its ~8,900 tag labels **and** the per-tag
validation data used for calibration are embedded in the `.safetensors`. No
`tags.json` and no separate CSV metadata are required (unlike legacy JTP-3).

## Download Instructions

### Option A — Hugging Face CLI (recommended)
```bash
hf download RedRocket/Hydra models/hydra-3.5.safetensors --local-dir ./_hydra_dl
# then move models/hydra-3.5.safetensors into classifiers/JTP-3.5/
```

### Option B — Manual
1. Visit: https://huggingface.co/RedRocket/Hydra/tree/main/models
2. Download `hydra-3.5.safetensors`
3. Place it directly in this directory (`classifiers/JTP-3.5/`)

## Expected Directory Structure

```
classifiers/JTP-3.5/
├── hydra-3.5.safetensors
├── overrides.toml            (optional; blacklist/translation)
└── DOWNLOAD_INSTRUCTIONS.md   (this file)
```

## Requirements

Hydra 3.5 runs on the vendored Hydra package and needs:
- **pyvips[binary]** (image preprocessing via libvips — installed by setup)
- **einops**, **safetensors**, **torch** (installed by setup)

If you encounter import errors, refresh the environment:
```bash
pip install -r requirements.txt --upgrade
```
Or re-run `setup.bat` / `setup.sh`.

## About Hydra 3.5

Hydra 3.5 uses a NaFlex SigLIP2 Vision Transformer with per-tag "hydra" attention
pooling and calibrated-by-default per-tag thresholds. The confidence slider selects
the calibration trade-off (recall vs. precision) rather than a flat cutoff, and the
"Implied tags" control adds or removes e621 tag implications. Once the file is in
place, restart the application and select "Hydra 3.5" from the classifier dropdown.

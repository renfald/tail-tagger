# JTP-3 (Hydra) Classifier Model

This directory should contain the JTP-3 classifier model file.

## Required Files

You need to download **one file** from the [RedRocket/JointTaggerProject repository on Hugging Face](https://huggingface.co/RedRocket/JointTaggerProject):

1. **jtp-3-hydra.safetensors** - The model weights file (includes embedded tag metadata)

**Note:** JTP-3 does not require a separate `tags.json` file. Tag information is embedded in the model metadata.

## Download Instructions

1. Visit: https://huggingface.co/RedRocket/JointTaggerProject/tree/main/JTP-3
2. Download the `jtp-3-hydra.safetensors` file (~956 MB)
3. Place it directly in this directory (`classifiers/JTP-3/`)

## Expected Directory Structure

After downloading, this directory should contain:
```
classifiers/JTP-3/
├── jtp-3-hydra.safetensors
└── DOWNLOAD_INSTRUCTIONS.md (this file)
```

## Requirements

JTP-3 requires updated dependencies:
- **timm >= 1.0.19** (for NAFlex ViT support)
- **einops >= 0.6.0** (for tensor operations)

If you encounter import errors, run:
```bash
pip install -r requirements.txt --upgrade
```

Or re-run `setup.bat` to refresh the environment.

## About JTP-3

JTP-3 uses the Hydra architecture with NAFlex Vision Transformer, which supports variable-resolution image processing. It provides more accurate tagging compared to earlier JTP models, with confidence scores ranging from -1.0 (absent) to 1.0 (present).

Once the file is in place, restart the application and select "JTP-3 Hydra" from the classifier dropdown.

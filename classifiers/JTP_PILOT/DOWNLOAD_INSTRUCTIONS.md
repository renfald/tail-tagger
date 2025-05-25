# JTP_PILOT Classifier Model

This directory should contain the JTP_PILOT classifier model files.

## Required Files

You need to download **two files** from the [RedRocket/JointTaggerProject repository on Hugging Face](https://huggingface.co/RedRocket/JointTaggerProject/tree/main/JTP_PILOT):

1. **JTP_PILOT-e4-vit_so400m_patch14_siglip_384.safetensors** - The model weights file
2. **tags.json** - The tag mapping file

## Download Instructions

1. Visit: https://huggingface.co/RedRocket/JointTaggerProject/tree/main/JTP_PILOT
2. Download both files listed above
3. Place them directly in this directory (`classifiers/JTP_PILOT/`)

## Expected Directory Structure

After downloading, this directory should contain:
```
classifiers/JTP_PILOT/
├── JTP_PILOT-e4-vit_so400m_patch14_siglip_384.safetensors
├── tags.json
└── DOWNLOAD_INSTRUCTIONS.md (this file)
```

Once the files are in place, restart the application to use the JTP_PILOT classifier.
"""
Classifier tag override system.

Provides per-classifier configuration for:
- Blacklisting unwanted tags (e.g., rating tags)
- Translating tag names (e.g., vulva -> pussy for e621 compatibility)
"""

from tail_tagger.classifier.overrides.manager import TagOverrideManager

__all__ = ["TagOverrideManager"]

"""
Tag override manager for classifier results.

Handles loading and applying per-classifier tag overrides including:
- Blacklist: Remove unwanted tags from results
- Translation: Rename tags to user-preferred names
"""

from pathlib import Path
from typing import Optional

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:
    import tomli as tomllib  # Python 3.10


class TagOverrideManager:
    """Manages tag overrides for classifier inference results."""

    # Cache loaded configs to avoid re-reading files
    _config_cache: dict[str, Optional[dict]] = {}

    @classmethod
    def apply_overrides(
        cls,
        results: list[tuple[str, float]],
        model_id: str
    ) -> list[tuple[str, float]]:
        """
        Apply tag overrides to classifier results.

        Processing order:
        1. Blacklist (remove unwanted tags)
        2. Translation (rename tags)
        3. Deduplication (merge duplicates, keep highest confidence)
        4. Re-sort by confidence descending

        Args:
            results: List of (tag_name, score) tuples from classifier
            model_id: Classifier model identifier (e.g., "JTP-3")

        Returns:
            Filtered and translated list of (tag_name, score) tuples
        """
        # Load config (returns None if missing or invalid)
        config = cls._load_config(model_id)

        if config is None:
            # No overrides to apply, return original results
            return results

        # Extract configuration
        blacklist_section = config.get("blacklist", {})
        blacklist = set(blacklist_section.get("tags", []))
        translations = config.get("translations", {})

        # Step 1: Filter out blacklisted tags (on original tag names)
        filtered = [
            (tag, score) for tag, score in results
            if tag not in blacklist
        ]

        # Step 2: Apply translations
        translated = [
            (translations.get(tag, tag), score)
            for tag, score in filtered
        ]

        # Step 3: Deduplicate - keep highest confidence for each unique tag name
        deduplicated: dict[str, float] = {}
        for tag, score in translated:
            if tag not in deduplicated or score > deduplicated[tag]:
                deduplicated[tag] = score

        # Step 4: Convert back to list and sort by confidence descending
        result = [(tag, score) for tag, score in deduplicated.items()]
        result.sort(key=lambda x: x[1], reverse=True)

        return result

    @classmethod
    def _load_config(cls, model_id: str) -> Optional[dict]:
        """
        Load override config for a classifier model.

        Looks for: classifiers/{model_id}/overrides.toml

        Args:
            model_id: Classifier model identifier

        Returns:
            Config dict or None if file missing/invalid
        """
        # Check cache first
        if model_id in cls._config_cache:
            return cls._config_cache[model_id]

        # Determine config file path
        config_path = Path("classifiers") / model_id / "overrides.toml"

        # Missing config file is not an error (user may not need overrides)
        if not config_path.exists():
            cls._config_cache[model_id] = None
            return None

        # Try to load config
        try:
            with open(config_path, 'rb') as f:
                config = tomllib.load(f)

            # Validate config structure
            cls._validate_config(config, config_path)

            # Cache successful load
            cls._config_cache[model_id] = config
            return config

        except Exception as e:
            # Log warning but don't crash
            print(f"[WARNING] Failed to load classifier overrides for '{model_id}': {e}")
            print(f"[WARNING] Proceeding with inference without tag overrides")
            print(f"[WARNING] Check {config_path} for syntax errors")

            # Cache failure to avoid re-attempting
            cls._config_cache[model_id] = None
            return None

    @classmethod
    def _validate_config(cls, config: dict, config_path: Path) -> None:
        """
        Validate config structure.

        Raises ValueError if config is malformed.
        """
        # Check top-level keys
        valid_keys = {"translations", "blacklist"}
        invalid_keys = set(config.keys()) - valid_keys
        if invalid_keys:
            raise ValueError(
                f"Unknown config keys: {invalid_keys}. "
                f"Valid keys: {valid_keys}"
            )

        # Validate translations section
        if "translations" in config:
            translations = config["translations"]
            if not isinstance(translations, dict):
                raise ValueError(
                    "Config section 'translations' must be a table/dict"
                )

            # Check that values are strings
            for key, value in translations.items():
                if not isinstance(value, str):
                    raise ValueError(
                        f"Translation value for '{key}' must be a string, "
                        f"got {type(value).__name__}"
                    )

        # Validate blacklist section
        if "blacklist" in config:
            blacklist = config["blacklist"]
            if not isinstance(blacklist, dict):
                raise ValueError(
                    "Config section 'blacklist' must be a table/dict"
                )

            # Check for 'tags' key
            if "tags" in blacklist:
                tags = blacklist["tags"]
                if not isinstance(tags, list):
                    raise ValueError(
                        "Config 'blacklist.tags' must be an array/list"
                    )

                # Check that items are strings
                for i, item in enumerate(tags):
                    if not isinstance(item, str):
                        raise ValueError(
                            f"Blacklist tag at index {i} must be a string, "
                            f"got {type(item).__name__}"
                        )

    @classmethod
    def clear_cache(cls) -> None:
        """Clear cached configs (useful for testing or config reloading)."""
        cls._config_cache.clear()

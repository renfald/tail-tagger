import os
import json

class ConfigManager:
    """Manages application configuration loading and saving."""

    def __init__(self):
        self.config_path = os.path.join(os.getcwd(), "data", "config.json")
        self.default_config = {
            "last_opened_folder": "",
            "classifier_threshold": 0.30,
            "classifier_active_model_id": "JTP_PILOT2",
            "tag_source": "e621"
        }
        self.config = self._load_config()

    def _load_config(self):
        """Loads the configuration from config.json, creating it with defaults if it doesn't exist."""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # Ensure all expected keys are present, using defaults if needed
                for key, value in self.default_config.items():
                    if key not in config:
                        config[key] = value
                return config
        except FileNotFoundError:
            print("config.json not found, creating with defaults.")
            # Create the file with default values
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.default_config, f, indent=2)  # Use indent for readability.
            return self.default_config
        except json.JSONDecodeError:
            print("Error decoding config.json. Using default values.")
            return self.default_config

    def save_config(self):
        """Saves the configuration to config.json."""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"Error saving config: {e}")

    def get_config_value(self, key):
        """Returns a configuration value for the given key."""
        return self.config.get(key)

    def set_config_value(self, key, value):
        """Sets a configuration value and saves the config file."""
        self.config[key] = value
        self.save_config()
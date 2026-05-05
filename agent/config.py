import yaml
import os

_config = None

def load():
    global _config
    if _config is None:
        config_path = os.path.join(os.path.dirname(__file__), "..", "config.yaml")
        with open(config_path) as f:
            _config = yaml.safe_load(f)
    return _config

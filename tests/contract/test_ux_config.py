import json
import pytest
from pathlib import Path

def test_ux_config_schema_contract():
    config_path = Path("config/ux_translations.json")
    assert config_path.exists(), "Translation registry must exist"
    
    with open(config_path, "r") as f:
        d = json.load(f)
        
    assert isinstance(d, dict)

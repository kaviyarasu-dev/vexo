import json
import pytest
from pathlib import Path

def test_translation_dictionary_keys():
    config_path = Path("config/ux_translations.json")
    with open(config_path, "r") as f:
        d = json.load(f)
    
    assert "vwap" in d
    assert "rsi" in d
    assert "bollinger_bands" in d

def test_translation_content_complete():
    config_path = Path("config/ux_translations.json")
    with open(config_path, "r") as f:
        d = json.load(f)
        
    for key, val in d.items():
        assert "plain_label" in val
        assert "beginner_summary" in val
        assert "pro_label" in val
        assert "risk_tip" in val

import json
import pytest
from pathlib import Path

CONTRACT_PATH = Path("config/glossary.json")
DATA_PATH = Path("data/glossary.json")

CONTRACT_MANDATORY_KEYS = ["definition", "analogy", "risk_warning"]
USER_MANDATORY_KEYS = ["term", "simple_definition", "everyday_analogy", "risk_caution"]


def test_glossary_contract_schema():
    """Verify 100% of config/glossary.json entries adhere to the three-part educational schema."""
    assert CONTRACT_PATH.exists(), "config/glossary.json must exist"
    with open(CONTRACT_PATH, "r", encoding="utf-8") as f:
        glossary = json.load(f)

    assert isinstance(glossary, dict), "Glossary root must be a JSON object (dict)"
    assert len(glossary) >= 8, "Glossary must contain at least 8 core entries"

    for term_key, entry in glossary.items():
        assert isinstance(entry, dict), f"Entry '{term_key}' must be a dict"
        for key in CONTRACT_MANDATORY_KEYS:
            assert key in entry, f"Mandatory schema key '{key}' missing in '{term_key}'"
            assert isinstance(entry[key], str) and len(entry[key].strip()) > 0


def test_data_glossary_contract_schema():
    """Verify 100% of data/glossary.json entries adhere to the execution contract 'produces' specification."""
    assert DATA_PATH.exists(), "data/glossary.json must exist"
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        glossary = json.load(f)

    assert isinstance(glossary, dict), "Glossary root must be a JSON object (dict)"
    assert len(glossary) >= 8, "Glossary must contain at least 8 core entries"

    for term_key, entry in glossary.items():
        assert isinstance(entry, dict), f"Entry '{term_key}' must be a dict"
        for key in USER_MANDATORY_KEYS:
            assert key in entry, f"User-specified key '{key}' missing in '{term_key}'"
            assert isinstance(entry[key], str) and len(entry[key].strip()) > 0

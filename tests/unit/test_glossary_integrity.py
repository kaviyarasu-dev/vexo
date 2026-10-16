import json
import pytest
from pathlib import Path

CONFIG_GLOSSARY_PATH = Path("config/glossary.json")
DATA_GLOSSARY_PATH = Path("data/glossary.json")

REQUIRED_TERMS = [
    "vwap",
    "rsi",
    "macd",
    "bollinger_bands",
    "atr",
    "stt",
    "r_multiple",
    "max_pain"
]

EXTENDED_TERMS = [
    "52w_high",
    "volume_z_score",
    "slippage",
    "bhavcopy",
    "stop_loss",
    "survivorship_bias",
    "open_interest",
    "implied_volatility"
]

FORBIDDEN_PROMOTIONAL_PHRASES = [
    "guaranteed return",
    "guaranteed profit",
    "surefire",
    "risk-free",
    "get rich",
    "100% win",
    "foolproof"
]


@pytest.fixture
def glossary_data():
    assert CONFIG_GLOSSARY_PATH.exists(), "config/glossary.json must exist"
    with open(CONFIG_GLOSSARY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def data_glossary_data():
    assert DATA_GLOSSARY_PATH.exists(), "data/glossary.json must exist"
    with open(DATA_GLOSSARY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def test_config_and_data_glossary_files_exist():
    """Both config/glossary.json and data/glossary.json must exist."""
    assert CONFIG_GLOSSARY_PATH.exists()
    assert DATA_GLOSSARY_PATH.exists()


def test_core_terms_present(glossary_data):
    """Glossary must contain all mandatory core platform terms."""
    for term in REQUIRED_TERMS:
        assert term in glossary_data, f"Required term '{term}' missing from glossary"


def test_extended_terms_present(glossary_data):
    """Glossary should contain all extended quantitative and market terms."""
    for term in EXTENDED_TERMS:
        assert term in glossary_data, f"Extended term '{term}' missing from glossary"


def test_no_empty_strings(glossary_data):
    """All entries must have non-empty string values for all educational fields."""
    check_fields = ["definition", "analogy", "risk_warning", "simple_definition", "everyday_analogy", "risk_caution"]
    for term_key, entry in glossary_data.items():
        assert isinstance(entry, dict), f"Entry for '{term_key}' must be a dict"
        for field in check_fields:
            val = entry.get(field)
            assert isinstance(val, str) and len(val.strip()) > 0, (
                f"Field '{field}' in term '{term_key}' must be a non-empty string"
            )


def test_no_promotional_speculation(glossary_data):
    """Glossary entries must not contain promotional or misleading speculative promises."""
    for term_key, entry in glossary_data.items():
        content_blob = " ".join([
            entry.get("definition", ""),
            entry.get("analogy", ""),
            entry.get("risk_warning", "")
        ]).lower()
        for phrase in FORBIDDEN_PROMOTIONAL_PHRASES:
            assert phrase not in content_blob, (
                f"Forbidden promotional phrase '{phrase}' found in glossary entry '{term_key}'"
            )


def test_indian_market_grounding(glossary_data):
    """Indian market concepts (STT, Bhavcopy) must mention Indian market details."""
    stt_def = glossary_data["stt"]["definition"].lower()
    assert "india" in stt_def or "exchange" in stt_def or "tax" in stt_def

    bhavcopy_def = glossary_data["bhavcopy"]["definition"].lower()
    assert "national stock exchange" in bhavcopy_def or "nse" in bhavcopy_def or "exchange" in bhavcopy_def


def test_data_glossary_mirrors_config(glossary_data, data_glossary_data):
    """data/glossary.json must mirror terms in config/glossary.json."""
    assert set(REQUIRED_TERMS).issubset(set(data_glossary_data.keys()))
    for term in REQUIRED_TERMS:
        assert data_glossary_data[term]["simple_definition"] == glossary_data[term]["simple_definition"]

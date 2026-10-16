import pytest
from services.study_catalog_service import StudyCatalogService, BUILTIN_STUDIES, StudyItem


def test_study_catalog_initialization():
    service = StudyCatalogService()
    catalog = service.get_catalog()
    assert len(catalog) >= 25, "Expected comprehensive built-in catalog"
    assert all(isinstance(s, StudyItem) for s in catalog)


def test_study_catalog_filter_profiles():
    service = StudyCatalogService()
    profiles = service.get_catalog(category="technicals", sub_category="profiles")
    profile_ids = [p.id for p in profiles]
    
    # Must contain the exact profiles from TradingView's reference screenshot
    assert "tpo" in profile_ids
    assert "session_tpo" in profile_ids
    assert "auto_anchored_vp" in profile_ids
    assert "fixed_range_vp" in profile_ids
    assert "periodic_vp" in profile_ids
    assert "session_vp" in profile_ids
    assert "session_vp_hd" in profile_ids
    assert "visible_range_vp" in profile_ids


def test_study_catalog_filter_categories():
    service = StudyCatalogService()
    indicators = service.get_catalog(category="technicals", sub_category="indicators")
    strategies = service.get_catalog(category="technicals", sub_category="strategies")
    patterns = service.get_catalog(category="technicals", sub_category="patterns")
    options = service.get_catalog(category="technicals", sub_category="options")
    fundamentals = service.get_catalog(category="fundamentals")

    assert len(indicators) >= 6
    assert len(strategies) >= 4
    assert len(patterns) >= 4
    assert len(options) >= 3
    assert len(fundamentals) >= 2


def test_study_catalog_search():
    service = StudyCatalogService()
    
    # Search for volume profile
    results = service.search_studies("volume")
    ids = [r.id for r in results]
    assert "visible_range_vp" in ids
    assert "session_vp" in ids
    assert "vwap" in ids

    # Search for rsi
    rsi_results = service.search_studies("rsi")
    assert any("rsi" in r.id for r in rsi_results)

    # Search for max pain
    pain_results = service.search_studies("max pain")
    assert any("opt_max_pain" == r.id for r in pain_results)


def test_study_by_id():
    service = StudyCatalogService()
    item = service.get_study_by_id("visible_range_vp")
    assert item is not None
    assert item.name == "Visible range volume profile"
    assert item.overlay is True
    assert "vrvp" in item.tags


def test_study_catalog_add_and_delete_custom_study():
    service = StudyCatalogService()
    custom_item = StudyItem(
        id="custom_ind_999",
        name="Custom Super Scalp",
        section="personal",
        category="technicals",
        sub_category="indicators",
        description="Scalp indicator with period 9",
        author="Tester",
        overlay=True,
        default_inputs={"period": 9, "color": "#00E676"},
        tags=["custom", "scalp"],
        is_custom=True,
        base_type="ema"
    )
    added = service.add_custom_study(custom_item)
    assert added.is_custom is True
    assert added.base_type == "ema"
    
    # Verify retrieval
    found = service.get_study_by_id("custom_ind_999")
    assert found is not None
    assert found.name == "Custom Super Scalp"
    
    # Verify in catalog
    catalog = service.get_catalog(sub_category="indicators")
    assert any(s.id == "custom_ind_999" for s in catalog)
    
    # Delete study
    deleted = service.delete_custom_study("custom_ind_999")
    assert deleted is True
    assert service.get_study_by_id("custom_ind_999") is None


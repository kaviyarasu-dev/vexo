import pytest
import os
import re
import pandas as pd
import numpy as np
from services.indicators.trend import SMAIndicator, EMAIndicator, SupertrendIndicator
from services.indicators.oscillators import StochasticOscillator


def test_subpanes_container_in_html():
    with open("static/index.html", "r", encoding="utf-8") as f:
        html = f.read()

    assert 'id="chart-subpanes-container"' in html
    assert 'class="chart-subpanes-container"' in html
    assert '/static/js/chart_studies.js' in html


def test_chart_studies_js_components():
    with open("static/js/chart_studies.js", "r", encoding="utf-8") as f:
        js = f.read()

    # Calculation functions
    assert "computeSMA" in js
    assert "computeEMA" in js
    assert "computeBollingerBands" in js
    assert "computeSupertrend" in js
    assert "computeRSI" in js
    assert "computeMACD" in js
    assert "computeStochastic" in js
    assert "computeATR" in js

    # Class & singleton
    assert "class ActiveStudiesManager" in js
    assert "window.activeStudiesManager" in js
    assert "mountOverlayStudy" in js
    assert "mountSubPaneStudy" in js
    assert "recalculateAll" in js
    assert "toggleVisibility" in js
    assert "removeStudy" in js
    assert "openSettingsModal" in js


def test_study_dialog_css_subpane_rules():
    with open("static/css/study_dialog.css", "r", encoding="utf-8") as f:
        css = f.read()

    assert ".chart-subpane-wrapper" in css
    assert ".subpane-legend-hud" in css
    assert ".subpane-hud-btn" in css
    assert ".study-settings-modal-backdrop" in css
    assert ".study-settings-card" in css


def test_trend_indicators_pipeline():
    df = pd.DataFrame({
        "open": [10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21],
        "high": [11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22],
        "low": [9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20],
        "close": [10.5, 11.5, 12.5, 13.5, 14.5, 15.5, 16.5, 17.5, 18.5, 19.5, 20.5, 21.5],
        "volume": [100] * 12
    })

    sma = SMAIndicator(period=5)
    df = sma.compute(df)
    assert not np.isnan(df["SMA_5"].iloc[5])

    ema = EMAIndicator(period=5)
    df = ema.compute(df)
    assert not np.isnan(df["EMA_5"].iloc[5])

    st = SupertrendIndicator(period=5, multiplier=2.0)
    df = st.compute(df)
    assert "Supertrend_5" in df.columns
    assert "Supertrend_Direction_5" in df.columns


def test_stochastic_pipeline():
    df = pd.DataFrame({
        "high": [10, 12, 11, 13, 15, 14, 16, 18, 17, 19, 21, 20, 22, 24, 23, 25],
        "low": [8, 9, 8.5, 10, 12, 11.5, 13, 15, 14, 16, 18, 17, 19, 21, 20, 22],
        "close": [9, 11, 10, 12, 14, 13, 15, 17, 16, 18, 20, 19, 21, 23, 22, 24]
    })
    stoch = StochasticOscillator(k_period=5, d_period=3, smooth=3)
    df = stoch.compute(df)
    assert "Stoch_K" in df.columns
    assert "Stoch_D" in df.columns
    assert not np.isnan(df["Stoch_D"].iloc[-1])

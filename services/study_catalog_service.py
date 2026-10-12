from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class StudyItem(BaseModel):
    id: str
    name: str
    section: str = Field(..., description="personal | builtin | community")
    category: str = Field(..., description="technicals | fundamentals | scripts | community")
    sub_category: Optional[str] = Field(None, description="indicators | strategies | profiles | patterns | options")
    description: str
    author: str = "TradingView / NSE Quant"
    overlay: bool = True
    default_inputs: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    is_favorite: bool = False
    is_custom: bool = False
    base_type: Optional[str] = None


BUILTIN_STUDIES: List[Dict[str, Any]] = [
    # --- PROFILES (As featured in the reference TradingView image) ---
    {
        "id": "tpo",
        "name": "Time price opportunity",
        "section": "builtin",
        "category": "technicals",
        "sub_category": "profiles",
        "description": "Displays Time Price Opportunity (TPO / Market Profile) 30-minute letter brackets (A-M), Initial Balance, Value Area, and Point of Control.",
        "overlay": True,
        "default_inputs": {"bracket_minutes": 30, "value_area_pct": 70, "show_ib": True},
        "tags": ["tpo", "market profile", "auction market", "value area", "poc"]
    },
    {
        "id": "session_tpo",
        "name": "Session time price opportunity",
        "section": "builtin",
        "category": "technicals",
        "sub_category": "profiles",
        "description": "Calculates Market Profile / TPO distribution separately for each distinct NSE trading session (09:15 to 15:30 IST).",
        "overlay": True,
        "default_inputs": {"session_reset": "09:15", "value_area_pct": 70},
        "tags": ["tpo", "session", "market profile", "intraday"]
    },
    {
        "id": "auto_anchored_vp",
        "name": "Auto anchored volume profile",
        "section": "builtin",
        "category": "technicals",
        "sub_category": "profiles",
        "description": "Automatically anchors Volume Profile to significant swing highs, swing lows, highest volume bars, or session start.",
        "overlay": True,
        "default_inputs": {"anchor_mode": "swing_high_low", "rows": 70, "value_area_pct": 70},
        "tags": ["volume profile", "anchored", "vp", "poc"]
    },
    {
        "id": "fixed_range_vp",
        "name": "Fixed range volume profile",
        "section": "builtin",
        "category": "technicals",
        "sub_category": "profiles",
        "description": "Calculates volume distribution across price levels between a fixed start date and end date selected on the chart.",
        "overlay": True,
        "default_inputs": {"rows": 70, "value_area_pct": 70, "up_down_colors": True},
        "tags": ["frvp", "fixed range", "volume profile", "consolidation"]
    },
    {
        "id": "periodic_vp",
        "name": "Periodic volume profile",
        "section": "builtin",
        "category": "technicals",
        "sub_category": "profiles",
        "description": "Computes volume profiles for fixed recurring calendar periods such as weekly, monthly, or yearly periods.",
        "overlay": True,
        "default_inputs": {"period": "1W", "rows": 50, "value_area_pct": 70},
        "tags": ["periodic", "weekly", "monthly", "volume profile"]
    },
    {
        "id": "session_vp",
        "name": "Session volume profile",
        "section": "builtin",
        "category": "technicals",
        "sub_category": "profiles",
        "description": "Visualizes traded volume distribution per daily trading session, highlighting intraday POC, Value Area High (VAH), and Value Area Low (VAL).",
        "overlay": True,
        "default_inputs": {"rows": 70, "value_area_pct": 70},
        "tags": ["svp", "session volume profile", "intraday", "poc", "vah", "val"]
    },
    {
        "id": "session_vp_hd",
        "name": "Session volume profile HD",
        "section": "builtin",
        "category": "technicals",
        "sub_category": "profiles",
        "description": "High-Definition Session Volume Profile utilizing granular 1-minute aggregations for ultra-fine price level resolution.",
        "overlay": True,
        "default_inputs": {"rows": 150, "value_area_pct": 70, "data_resolution": "1m"},
        "tags": ["svp hd", "high definition", "volume profile", "tick granularity"]
    },
    {
        "id": "visible_range_vp",
        "name": "Visible range volume profile",
        "section": "builtin",
        "category": "technicals",
        "sub_category": "profiles",
        "description": "Dynamically computes volume distribution for only the candles currently visible in the chart viewport; recalculates on zoom/pan.",
        "overlay": True,
        "default_inputs": {"rows": 70, "value_area_pct": 70, "align_right": True},
        "tags": ["vrvp", "visible range", "volume profile", "auction", "hvn", "lvn"]
    },

    # --- INDICATORS ---
    {
        "id": "sma",
        "name": "Simple moving average",
        "section": "builtin",
        "category": "technicals",
        "sub_category": "indicators",
        "description": "Calculates the arithmetic average of closing prices over a specified lookback period (e.g. 20, 50, 200).",
        "overlay": True,
        "default_inputs": {"period": 20, "color": "#2962FF"},
        "tags": ["sma", "moving average", "trend", "overlay"]
    },
    {
        "id": "ema",
        "name": "Exponential moving average",
        "section": "builtin",
        "category": "technicals",
        "sub_category": "indicators",
        "description": "Calculates the exponentially weighted moving average, reacting faster to recent price fluctuations than an SMA.",
        "overlay": True,
        "default_inputs": {"period": 20, "color": "#FF6D00"},
        "tags": ["ema", "exponential", "trend", "moving average"]
    },
    {
        "id": "vwap",
        "name": "Volume weighted average price",
        "section": "builtin",
        "category": "technicals",
        "sub_category": "indicators",
        "description": "Volume Weighted Average Price resetting daily at 09:15 IST; fundamental benchmark used by institutions and day traders.",
        "overlay": True,
        "default_inputs": {"session_reset": "09:15", "color": "#F5AC00"},
        "tags": ["vwap", "institutional", "intraday benchmark", "volume"]
    },
    {
        "id": "bollinger_bands",
        "name": "Bollinger bands",
        "section": "builtin",
        "category": "technicals",
        "sub_category": "indicators",
        "description": "Volatility channel consisting of a 20-period SMA middle band with upper and lower bands positioned 2 standard deviations away.",
        "overlay": True,
        "default_inputs": {"period": 20, "std_dev": 2.0, "fill_background": True},
        "tags": ["bollinger", "bb", "volatility", "bands", "mean reversion"]
    },
    {
        "id": "rsi",
        "name": "Relative strength index",
        "section": "builtin",
        "category": "technicals",
        "sub_category": "indicators",
        "description": "Momentum oscillator that measures the speed and change of price movements between 0 and 100, highlighting overbought (70) and oversold (30) conditions.",
        "overlay": False,
        "default_inputs": {"period": 14, "overbought": 70, "oversold": 30},
        "tags": ["rsi", "momentum", "oscillator", "overbought", "oversold"]
    },
    {
        "id": "macd",
        "name": "Moving average convergence divergence",
        "section": "builtin",
        "category": "technicals",
        "sub_category": "indicators",
        "description": "Trend-following momentum indicator showing the relationship between two exponential moving averages (12 and 26) with a 9-day signal line and histogram.",
        "overlay": False,
        "default_inputs": {"fast_period": 12, "slow_period": 26, "signal_period": 9},
        "tags": ["macd", "momentum", "oscillator", "crossover"]
    },
    {
        "id": "supertrend",
        "name": "Supertrend",
        "section": "builtin",
        "category": "technicals",
        "sub_category": "indicators",
        "description": "ATR-based trend-following indicator providing clear trailing stop levels and directional green/red trend confirmation.",
        "overlay": True,
        "default_inputs": {"period": 10, "multiplier": 3.0},
        "tags": ["supertrend", "trailing stop", "trend following", "atr"]
    },
    {
        "id": "stochastic",
        "name": "Stochastic oscillator",
        "section": "builtin",
        "category": "technicals",
        "sub_category": "indicators",
        "description": "Compares a particular closing price to a range of prices over a given lookback period, generating %K and %D signal lines.",
        "overlay": False,
        "default_inputs": {"k_period": 14, "d_period": 3, "smooth": 3},
        "tags": ["stochastic", "stoch", "momentum", "oscillator"]
    },
    {
        "id": "atr",
        "name": "Average true range",
        "section": "builtin",
        "category": "technicals",
        "sub_category": "indicators",
        "description": "Measures market volatility by calculating the average range of price movements over 14 periods.",
        "overlay": False,
        "default_inputs": {"period": 14},
        "tags": ["atr", "volatility", "range", "risk management"]
    },
    {
        "id": "ichimoku",
        "name": "Ichimoku cloud",
        "section": "builtin",
        "category": "technicals",
        "sub_category": "indicators",
        "description": "Comprehensive trend definition system with Tenkan-sen, Kijun-sen, Senkou Span A/B (Kumo Cloud), and Chikou Span.",
        "overlay": True,
        "default_inputs": {"conversion": 9, "base": 26, "lagging_span": 52, "displacement": 26},
        "tags": ["ichimoku", "cloud", "kumo", "support resistance"]
    },

    # --- STRATEGIES ---
    {
        "id": "strat_sma_cross",
        "name": "Moving average cross strategy",
        "section": "builtin",
        "category": "technicals",
        "sub_category": "strategies",
        "description": "Enters Long when Fast SMA crosses above Slow SMA; exits or flips Short when Fast crosses below Slow. Renders buy/sell signals with live Backtest Dock.",
        "overlay": True,
        "default_inputs": {"fast_period": 9, "slow_period": 21, "capital": 100000},
        "tags": ["strategy", "sma cross", "backtest", "golden cross", "death cross"]
    },
    {
        "id": "strat_rsi_reversal",
        "name": "RSI mean reversion strategy",
        "section": "builtin",
        "category": "technicals",
        "sub_category": "strategies",
        "description": "Buys when RSI dips below 30 and crosses back above; exits when RSI reaches 70. Backtests win-rate and profit factor.",
        "overlay": True,
        "default_inputs": {"rsi_period": 14, "buy_level": 30, "exit_level": 70},
        "tags": ["strategy", "rsi", "mean reversion", "oversold bounce"]
    },
    {
        "id": "strat_bb_breakout",
        "name": "Bollinger bands breakout strategy",
        "section": "builtin",
        "category": "technicals",
        "sub_category": "strategies",
        "description": "Buys when candle closes above upper Bollinger Band during volatility expansion; exits on regression to middle band.",
        "overlay": True,
        "default_inputs": {"period": 20, "std_dev": 2.0},
        "tags": ["strategy", "bollinger", "volatility breakout"]
    },
    {
        "id": "strat_supertrend",
        "name": "Supertrend trend-following strategy",
        "section": "builtin",
        "category": "technicals",
        "sub_category": "strategies",
        "description": "Executes long orders on green Supertrend flips and short/exit on red Supertrend flips with tight risk-reward metrics.",
        "overlay": True,
        "default_inputs": {"atr_period": 10, "multiplier": 3.0},
        "tags": ["strategy", "supertrend", "trend following", "atr"]
    },
    {
        "id": "strat_macd_momentum",
        "name": "MACD momentum strategy",
        "section": "builtin",
        "category": "technicals",
        "sub_category": "strategies",
        "description": "Enters positions on MACD line and signal line crossovers accompanied by expanding histogram bars.",
        "overlay": True,
        "default_inputs": {"fast": 12, "slow": 26, "signal": 9},
        "tags": ["strategy", "macd", "momentum"]
    },

    # --- PATTERNS ---
    {
        "id": "pat_bullish_engulfing",
        "name": "Bullish engulfing",
        "section": "builtin",
        "category": "technicals",
        "sub_category": "patterns",
        "description": "2-candle bullish reversal pattern where a large green candle body completely engulfs the preceding red candle body. Labels candle with 'BE'.",
        "overlay": True,
        "default_inputs": {"min_body_ratio": 1.2},
        "tags": ["candlestick", "pattern", "bullish engulfing", "reversal"]
    },
    {
        "id": "pat_bearish_engulfing",
        "name": "Bearish engulfing",
        "section": "builtin",
        "category": "technicals",
        "sub_category": "patterns",
        "description": "2-candle bearish reversal pattern where a large red candle body completely engulfs the preceding green candle body. Labels candle with 'BE'.",
        "overlay": True,
        "default_inputs": {"min_body_ratio": 1.2},
        "tags": ["candlestick", "pattern", "bearish engulfing", "top reversal"]
    },
    {
        "id": "pat_hammer",
        "name": "Hammer & Inverted hammer",
        "section": "builtin",
        "category": "technicals",
        "sub_category": "patterns",
        "description": "Bullish rejection pattern with a small real body near the high and a long lower shadow at least double the body length. Labels with 'H'.",
        "overlay": True,
        "default_inputs": {"shadow_ratio": 2.0},
        "tags": ["candlestick", "hammer", "inverted hammer", "rejection"]
    },
    {
        "id": "pat_doji",
        "name": "Doji (Neutral, Dragonfly, Gravestone)",
        "section": "builtin",
        "category": "technicals",
        "sub_category": "patterns",
        "description": "Candle where opening and closing prices are virtually identical, indicating market indecision or equilibrium. Labels with 'D'.",
        "overlay": True,
        "default_inputs": {"max_body_pct": 0.1},
        "tags": ["candlestick", "doji", "indecision", "dragonfly", "gravestone"]
    },
    {
        "id": "pat_morning_star",
        "name": "Morning star",
        "section": "builtin",
        "category": "technicals",
        "sub_category": "patterns",
        "description": "3-candle bullish reversal pattern consisting of a tall red candle, a small indecision candle gapping down, and a strong green candle closing above the midpoint.",
        "overlay": True,
        "default_inputs": {},
        "tags": ["candlestick", "morning star", "3-candle reversal"]
    },
    {
        "id": "pat_double_top_bottom",
        "name": "Double top & Double bottom",
        "section": "builtin",
        "category": "technicals",
        "sub_category": "patterns",
        "description": "Classic chart pattern detecting 'M' top and 'W' bottom swing formations within ±0.5% price tolerance.",
        "overlay": True,
        "default_inputs": {"tolerance_pct": 0.5, "lookback_bars": 30},
        "tags": ["chart pattern", "double top", "double bottom", "m top", "w bottom"]
    },

    # --- OPTIONS ---
    {
        "id": "opt_max_pain",
        "name": "Max pain level",
        "section": "builtin",
        "category": "technicals",
        "sub_category": "options",
        "description": "Computes the option strike price where total option buyers suffer the greatest collective payout loss. Plotted as a horizontal price benchmark.",
        "overlay": True,
        "default_inputs": {"color": "#00E5FF", "line_style": "dashed"},
        "tags": ["options", "max pain", "expiry", "derivatives", "strike"]
    },
    {
        "id": "opt_pcr",
        "name": "Put-Call ratio (PCR)",
        "section": "builtin",
        "category": "technicals",
        "sub_category": "options",
        "description": "Plots total Put Open Interest divided by total Call Open Interest across time as an oscillator sub-pane.",
        "overlay": False,
        "default_inputs": {"baseline": 1.0},
        "tags": ["options", "pcr", "put call ratio", "sentiment", "oi"]
    },
    {
        "id": "opt_strike_oi_profile",
        "name": "Strike open interest profile",
        "section": "builtin",
        "category": "technicals",
        "sub_category": "options",
        "description": "Renders Call OI (red) and Put OI (green) bars horizontally alongside the chart at each active strike price.",
        "overlay": True,
        "default_inputs": {"num_strikes": 10},
        "tags": ["options", "open interest", "oi distribution", "strike profile"]
    },
    {
        "id": "opt_iv_rank",
        "name": "Implied volatility rank & percentile",
        "section": "builtin",
        "category": "technicals",
        "sub_category": "options",
        "description": "Displays the relative ranking of current option implied volatility against its 52-week historical high and low.",
        "overlay": False,
        "default_inputs": {"lookback_days": 252},
        "tags": ["options", "iv rank", "iv percentile", "volatility"]
    },

    # --- FUNDAMENTALS ---
    {
        "id": "fund_pe_ratio",
        "name": "P/E Ratio & Valuation metrics",
        "section": "builtin",
        "category": "fundamentals",
        "sub_category": None,
        "description": "Displays Price-to-Earnings, Price-to-Book, and Industry P/E valuation multiples as an on-chart information card.",
        "overlay": True,
        "default_inputs": {},
        "tags": ["fundamentals", "pe", "pb", "valuation", "eps"]
    },
    {
        "id": "fund_financial_health",
        "name": "Financial health & Debt metrics",
        "section": "builtin",
        "category": "fundamentals",
        "sub_category": None,
        "description": "Summarizes Debt-to-Equity, Return on Equity (ROE), ROCE, and Free Cash Flow for the active company.",
        "overlay": True,
        "default_inputs": {},
        "tags": ["fundamentals", "roe", "roce", "debt to equity", "balance sheet"]
    },

    # --- COMMUNITY / PRESETS ---
    {
        "id": "comm_intraday_momentum",
        "name": "NSE Intraday momentum pack",
        "section": "community",
        "category": "community",
        "sub_category": "editors_picks",
        "description": "Curated institutional day-trading setup bundling Session VWAP, 20 EMA, 70-Row Volume Profile, and RSI 14.",
        "overlay": True,
        "default_inputs": {},
        "tags": ["community", "intraday", "momentum", "vwap", "pack"]
    },
    {
        "id": "comm_swing_breakout",
        "name": "Swing trader breakout pack",
        "section": "community",
        "category": "community",
        "sub_category": "editors_picks",
        "description": "Swing trading template featuring 50 & 200 SMA, Bollinger Bands, and Bullish Engulfing pattern detector.",
        "overlay": True,
        "default_inputs": {},
        "tags": ["community", "swing", "breakout", "sma 200", "bb"]
    },
    {
        "id": "comm_options_seller",
        "name": "Option seller hedging suite",
        "section": "community",
        "category": "community",
        "sub_category": "editors_picks",
        "description": "Derivatives desk layout featuring Max Pain benchmark ray, Strike Open Interest distribution, and PCR oscillator.",
        "overlay": True,
        "default_inputs": {},
        "tags": ["community", "options", "hedging", "max pain", "oi"]
    },

    # --- PERSONAL (MY SCRIPTS) ---
    {
        "id": "pers_scalper_pro",
        "name": "Scalper Pro Setup",
        "section": "personal",
        "category": "scripts",
        "sub_category": "my_scripts",
        "description": "Custom scalping workspace combining 9 & 21 EMA, RSI 14, and Visible Range Volume Profile.",
        "overlay": True,
        "default_inputs": {"studies": ["ema", "rsi", "visible_range_vp"]},
        "tags": ["personal", "scalping", "ema", "rsi", "vrvp", "my scripts"]
    },
    {
        "id": "pers_trend_rider",
        "name": "Intraday Trend Rider",
        "section": "personal",
        "category": "scripts",
        "sub_category": "my_scripts",
        "description": "High-conviction trend following layout utilizing Supertrend (10, 3.0), Session VWAP, and Stochastic Oscillator.",
        "overlay": True,
        "default_inputs": {"studies": ["supertrend", "vwap", "stochastic"]},
        "tags": ["personal", "trend", "supertrend", "vwap", "stochastic", "my scripts"]
    }
]


class StudyCatalogService:
    """Service providing search, retrieval, and categorization of technical and quantitative studies."""

    def __init__(self, studies: Optional[List[Dict[str, Any]]] = None):
        raw_list = studies or BUILTIN_STUDIES
        self._studies = [StudyItem(**item) for item in raw_list]

    def get_catalog(
        self,
        section: Optional[str] = None,
        category: Optional[str] = None,
        sub_category: Optional[str] = None,
    ) -> List[StudyItem]:
        """Returns catalog filtered by section, category, and sub_category."""
        results = self._studies
        if section:
            sec_lower = section.lower()
            results = [s for s in results if s.section.lower() == sec_lower]
        if category:
            cat_lower = category.lower()
            results = [s for s in results if s.category.lower() == cat_lower]
        if sub_category:
            sub_lower = sub_category.lower()
            results = [s for s in results if s.sub_category and s.sub_category.lower() == sub_lower]
        return results

    def get_study_by_id(self, study_id: str) -> Optional[StudyItem]:
        """Returns a single study item by its ID."""
        for s in self._studies:
            if s.id.lower() == study_id.lower():
                return s
        return None

    def search_studies(
        self,
        query: str,
        section: Optional[str] = None,
        sub_category: Optional[str] = None
    ) -> List[StudyItem]:
        """Searches studies by name, description, and tags."""
        q = (query or "").strip().lower()
        base_list = self.get_catalog(section=section, sub_category=sub_category)
        if not q:
            return base_list

        matches = []
        for s in base_list:
            score = 0
            if q == s.id.lower() or q == s.name.lower():
                score += 100
            elif q in s.name.lower():
                score += 50
            elif any(q in t.lower() for t in s.tags):
                score += 30
            elif q in s.description.lower():
                score += 10

            if score > 0:
                matches.append((score, s))

        matches.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in matches]

    def add_custom_study(self, study: StudyItem) -> StudyItem:
        """Adds or updates a custom study in the catalog."""
        study.is_custom = True
        self._studies = [s for s in self._studies if s.id.lower() != study.id.lower()]
        self._studies.insert(0, study)
        return study

    def delete_custom_study(self, study_id: str) -> bool:
        """Deletes a study by its ID."""
        initial_len = len(self._studies)
        self._studies = [s for s in self._studies if s.id.lower() != study_id.lower()]
        return len(self._studies) < initial_len

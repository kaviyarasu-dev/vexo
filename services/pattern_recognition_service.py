import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict


@dataclass
class PatternSignal:
    time: int                   # unix timestamp in seconds
    pattern_id: str             # e.g. "bullish_engulfing"
    pattern_name: str           # e.g. "Bullish Engulfing"
    sentiment: str              # "bullish" | "bearish" | "neutral"
    position: str               # "belowBar" | "aboveBar"
    shape: str                  # "arrowUp" | "arrowDown" | "circle"
    color: str                  # hex color string
    badge_text: str             # Short badge code e.g. "BE"
    price: float                # price at signal bar
    description: str            # Educational definition
    confirmation_rule: str      # How traders confirm the signal
    historical_accuracy_pct: float # e.g. 64.5


class PatternRecognitionService:
    """
    Vectorized Candlestick and Chart Pattern Recognition Engine.
    Detects classic price action formations with educational metadata and confirmation criteria.
    """

    EDUCATIONAL_METADATA = {
        "bullish_engulfing": {
            "name": "Bullish Engulfing",
            "sentiment": "bullish",
            "position": "belowBar",
            "shape": "arrowUp",
            "color": "#089981",
            "badge": "BE",
            "desc": "A two-candle bullish reversal pattern where a large green candle completely engulfs the prior red candle's body.",
            "confirm": "Next candle must open above the engulfing close or break above its high with expanding volume.",
            "accuracy": 63.8
        },
        "bearish_engulfing": {
            "name": "Bearish Engulfing",
            "sentiment": "bearish",
            "position": "aboveBar",
            "shape": "arrowDown",
            "color": "#F23645",
            "badge": "BE",
            "desc": "A two-candle bearish reversal pattern where a large red candle completely engulfs the prior green candle's body.",
            "confirm": "Next candle should follow through by breaking below the engulfing candle's low.",
            "accuracy": 62.4
        },
        "hammer": {
            "name": "Hammer",
            "sentiment": "bullish",
            "position": "belowBar",
            "shape": "arrowUp",
            "color": "#089981",
            "badge": "HAM",
            "desc": "Bullish reversal candle with a small body near the top of the range and a lower shadow at least twice the body size.",
            "confirm": "Requires a subsequent higher close to confirm strong buying absorption from the lows.",
            "accuracy": 61.2
        },
        "inverted_hammer": {
            "name": "Inverted Hammer",
            "sentiment": "bullish",
            "position": "belowBar",
            "shape": "arrowUp",
            "color": "#089981",
            "badge": "IH",
            "desc": "Bullish reversal signal appearing at lows with a long upper wick testing overhead resistance before closing near open.",
            "confirm": "Confirmed when next bar gaps up or crosses the upper shadow high.",
            "accuracy": 58.7
        },
        "doji": {
            "name": "Doji",
            "sentiment": "neutral",
            "position": "aboveBar",
            "shape": "circle",
            "color": "#2962FF",
            "badge": "DOJI",
            "desc": "Indecision candle where open and close prices are virtually identical, indicating equilibrium between buyers and sellers.",
            "confirm": "Wait for directional breakout beyond the high or low of the Doji bar.",
            "accuracy": 54.0
        },
        "morning_star": {
            "name": "Morning Star",
            "sentiment": "bullish",
            "position": "belowBar",
            "shape": "arrowUp",
            "color": "#089981",
            "badge": "MS",
            "desc": "A three-candle bottom reversal consisting of a tall red candle, a small-bodied star, and a decisive tall green candle.",
            "confirm": "Third candle must close beyond the midpoint of the first red candle.",
            "accuracy": 67.5
        },
        "evening_star": {
            "name": "Evening Star",
            "sentiment": "bearish",
            "position": "aboveBar",
            "shape": "arrowDown",
            "color": "#F23645",
            "badge": "ES",
            "desc": "A three-candle top reversal consisting of a tall green candle, a small-bodied star, and a decisive tall red candle.",
            "confirm": "Third candle must close beyond the midpoint of the first green candle.",
            "accuracy": 66.1
        },
        "double_top": {
            "name": "Double Top (M-Pattern)",
            "sentiment": "bearish",
            "position": "aboveBar",
            "shape": "arrowDown",
            "color": "#F23645",
            "badge": "DT",
            "desc": "A classic chart pattern where price tests a resistance peak twice with a moderate trough between them, failing to break out.",
            "confirm": "Confirmed upon a decisive breakdown below the neckline (intervening trough).",
            "accuracy": 71.0
        },
        "double_bottom": {
            "name": "Double Bottom (W-Pattern)",
            "sentiment": "bullish",
            "position": "belowBar",
            "shape": "arrowUp",
            "color": "#089981",
            "badge": "DB",
            "desc": "A classic reversal pattern where price forms two distinct troughs at approximately the same level, rejecting further decline.",
            "confirm": "Confirmed upon a decisive breakout above the neckline (intervening peak).",
            "accuracy": 72.4
        }
    }

    def scan_all(self, df: pd.DataFrame, enabled_patterns: Optional[List[str]] = None) -> List[PatternSignal]:
        """
        Scans OHLCV DataFrame and returns a list of PatternSignal objects ordered chronologically.
        """
        if df.empty or len(df) < 3:
            return []

        # Prepare normalized arrays
        df_sorted = df.copy()
        if 'timestamp' in df_sorted.columns:
            if not pd.api.types.is_datetime64_any_dtype(df_sorted['timestamp']):
                df_sorted['timestamp'] = pd.to_datetime(df_sorted['timestamp'])
            # unix seconds
            if df_sorted['timestamp'].dt.tz is None:
                timestamps = (df_sorted['timestamp'].astype('int64') // 10**9).values
            else:
                timestamps = (df_sorted['timestamp'].astype('int64') // 10**9).values
        elif 'time' in df_sorted.columns:
            timestamps = df_sorted['time'].values
        else:
            timestamps = np.arange(len(df_sorted))

        opens = df_sorted['open'].values.astype(float)
        highs = df_sorted['high'].values.astype(float)
        lows = df_sorted['low'].values.astype(float)
        closes = df_sorted['close'].values.astype(float)
        n = len(df_sorted)

        signals: List[PatternSignal] = []
        if enabled_patterns:
            patterns_to_run = set()
            for p in enabled_patterns:
                clean = p.lower().strip()
                if clean.startswith("patt_"):
                    clean = clean[5:]
                elif clean.startswith("pat_"):
                    clean = clean[4:]
                if clean in ("double_top_bottom", "double_top_and_double_bottom"):
                    patterns_to_run.add("double_top")
                    patterns_to_run.add("double_bottom")
                elif clean == "hammer":
                    patterns_to_run.add("hammer")
                    patterns_to_run.add("inverted_hammer")
                else:
                    patterns_to_run.add(clean)
        else:
            patterns_to_run = set(self.EDUCATIONAL_METADATA.keys())

        # Vectorized metrics
        body = np.abs(closes - opens)
        candle_range = highs - lows
        candle_range = np.where(candle_range == 0, 0.001, candle_range) # prevent div by zero
        is_bullish = closes > opens
        is_bearish = closes < opens

        # 1. Doji
        if "doji" in patterns_to_run:
            meta = self.EDUCATIONAL_METADATA["doji"]
            doji_mask = (body / candle_range) <= 0.10
            for i in np.where(doji_mask)[0]:
                signals.append(PatternSignal(
                    time=int(timestamps[i]),
                    pattern_id="doji",
                    pattern_name=meta["name"],
                    sentiment=meta["sentiment"],
                    position=meta["position"],
                    shape=meta["shape"],
                    color=meta["color"],
                    badge_text=meta["badge"],
                    price=float(highs[i]),
                    description=meta["desc"],
                    confirmation_rule=meta["confirm"],
                    historical_accuracy_pct=meta["accuracy"]
                ))

        # 2. Bullish & Bearish Engulfing
        for i in range(1, n):
            # Bullish Engulfing
            if "bullish_engulfing" in patterns_to_run:
                if is_bearish[i - 1] and is_bullish[i]:
                    if opens[i] <= closes[i - 1] and closes[i] >= opens[i - 1] and body[i] > body[i - 1]:
                        meta = self.EDUCATIONAL_METADATA["bullish_engulfing"]
                        signals.append(PatternSignal(
                            time=int(timestamps[i]),
                            pattern_id="bullish_engulfing",
                            pattern_name=meta["name"],
                            sentiment=meta["sentiment"],
                            position=meta["position"],
                            shape=meta["shape"],
                            color=meta["color"],
                            badge_text=meta["badge"],
                            price=float(lows[i]),
                            description=meta["desc"],
                            confirmation_rule=meta["confirm"],
                            historical_accuracy_pct=meta["accuracy"]
                        ))

            # Bearish Engulfing
            if "bearish_engulfing" in patterns_to_run:
                if is_bullish[i - 1] and is_bearish[i]:
                    if opens[i] >= closes[i - 1] and closes[i] <= opens[i - 1] and body[i] > body[i - 1]:
                        meta = self.EDUCATIONAL_METADATA["bearish_engulfing"]
                        signals.append(PatternSignal(
                            time=int(timestamps[i]),
                            pattern_id="bearish_engulfing",
                            pattern_name=meta["name"],
                            sentiment=meta["sentiment"],
                            position=meta["position"],
                            shape=meta["shape"],
                            color=meta["color"],
                            badge_text=meta["badge"],
                            price=float(highs[i]),
                            description=meta["desc"],
                            confirmation_rule=meta["confirm"],
                            historical_accuracy_pct=meta["accuracy"]
                        ))

        # 3. Hammer & Inverted Hammer
        for i in range(1, n):
            b = body[i]
            r = candle_range[i]
            lower_shadow = min(opens[i], closes[i]) - lows[i]
            upper_shadow = highs[i] - max(opens[i], closes[i])

            if "hammer" in patterns_to_run:
                if b > 0 and lower_shadow >= 2.0 * b and upper_shadow <= 0.25 * r:
                    meta = self.EDUCATIONAL_METADATA["hammer"]
                    signals.append(PatternSignal(
                        time=int(timestamps[i]),
                        pattern_id="hammer",
                        pattern_name=meta["name"],
                        sentiment=meta["sentiment"],
                        position=meta["position"],
                        shape=meta["shape"],
                        color=meta["color"],
                        badge_text=meta["badge"],
                        price=float(lows[i]),
                        description=meta["desc"],
                        confirmation_rule=meta["confirm"],
                        historical_accuracy_pct=meta["accuracy"]
                    ))

            if "inverted_hammer" in patterns_to_run:
                if b > 0 and upper_shadow >= 2.0 * b and lower_shadow <= 0.25 * r:
                    meta = self.EDUCATIONAL_METADATA["inverted_hammer"]
                    signals.append(PatternSignal(
                        time=int(timestamps[i]),
                        pattern_id="inverted_hammer",
                        pattern_name=meta["name"],
                        sentiment=meta["sentiment"],
                        position=meta["position"],
                        shape=meta["shape"],
                        color=meta["color"],
                        badge_text=meta["badge"],
                        price=float(lows[i]),
                        description=meta["desc"],
                        confirmation_rule=meta["confirm"],
                        historical_accuracy_pct=meta["accuracy"]
                    ))

        # 4. Morning Star & Evening Star
        for i in range(2, n):
            b1 = body[i - 2]
            b2 = body[i - 1]
            b3 = body[i]

            if "morning_star" in patterns_to_run:
                if is_bearish[i - 2] and b1 > 0:
                    if b2 < 0.5 * b1 and is_bullish[i] and closes[i] > (opens[i - 2] + closes[i - 2]) / 2.0:
                        meta = self.EDUCATIONAL_METADATA["morning_star"]
                        signals.append(PatternSignal(
                            time=int(timestamps[i]),
                            pattern_id="morning_star",
                            pattern_name=meta["name"],
                            sentiment=meta["sentiment"],
                            position=meta["position"],
                            shape=meta["shape"],
                            color=meta["color"],
                            badge_text=meta["badge"],
                            price=float(lows[i]),
                            description=meta["desc"],
                            confirmation_rule=meta["confirm"],
                            historical_accuracy_pct=meta["accuracy"]
                        ))

            if "evening_star" in patterns_to_run:
                if is_bullish[i - 2] and b1 > 0:
                    if b2 < 0.5 * b1 and is_bearish[i] and closes[i] < (opens[i - 2] + closes[i - 2]) / 2.0:
                        meta = self.EDUCATIONAL_METADATA["evening_star"]
                        signals.append(PatternSignal(
                            time=int(timestamps[i]),
                            pattern_id="evening_star",
                            pattern_name=meta["name"],
                            sentiment=meta["sentiment"],
                            position=meta["position"],
                            shape=meta["shape"],
                            color=meta["color"],
                            badge_text=meta["badge"],
                            price=float(highs[i]),
                            description=meta["desc"],
                            confirmation_rule=meta["confirm"],
                            historical_accuracy_pct=meta["accuracy"]
                        ))

        # 5. Double Top & Double Bottom (Chart patterns with lookback swing detection)
        if "double_top" in patterns_to_run or "double_bottom" in patterns_to_run:
            lookback = 10
            for i in range(lookback * 2, n):
                # Search for previous swing peak / trough
                if "double_top" in patterns_to_run:
                    curr_high = highs[i]
                    prior_segment = highs[i - lookback * 2 : i - 3]
                    if len(prior_segment) > 0:
                        prev_peak_idx = int(np.argmax(prior_segment))
                        prev_peak = prior_segment[prev_peak_idx]
                        # Peak tolerance 0.75%
                        if abs(curr_high - prev_peak) / prev_peak <= 0.0075:
                            # Verify trough exists between peaks
                            trough_segment = lows[i - lookback * 2 + prev_peak_idx : i]
                            if len(trough_segment) > 0 and np.min(trough_segment) < prev_peak * 0.985:
                                if is_bearish[i]:
                                    meta = self.EDUCATIONAL_METADATA["double_top"]
                                    signals.append(PatternSignal(
                                        time=int(timestamps[i]),
                                        pattern_id="double_top",
                                        pattern_name=meta["name"],
                                        sentiment=meta["sentiment"],
                                        position=meta["position"],
                                        shape=meta["shape"],
                                        color=meta["color"],
                                        badge_text=meta["badge"],
                                        price=float(highs[i]),
                                        description=meta["desc"],
                                        confirmation_rule=meta["confirm"],
                                        historical_accuracy_pct=meta["accuracy"]
                                    ))

                if "double_bottom" in patterns_to_run:
                    curr_low = lows[i]
                    prior_segment_low = lows[i - lookback * 2 : i - 3]
                    if len(prior_segment_low) > 0:
                        prev_trough_idx = int(np.argmin(prior_segment_low))
                        prev_trough = prior_segment_low[prev_trough_idx]
                        if abs(curr_low - prev_trough) / prev_trough <= 0.0075:
                            peak_segment = highs[i - lookback * 2 + prev_trough_idx : i]
                            if len(peak_segment) > 0 and np.max(peak_segment) > prev_trough * 1.015:
                                if is_bullish[i]:
                                    meta = self.EDUCATIONAL_METADATA["double_bottom"]
                                    signals.append(PatternSignal(
                                        time=int(timestamps[i]),
                                        pattern_id="double_bottom",
                                        pattern_name=meta["name"],
                                        sentiment=meta["sentiment"],
                                        position=meta["position"],
                                        shape=meta["shape"],
                                        color=meta["color"],
                                        badge_text=meta["badge"],
                                        price=float(lows[i]),
                                        description=meta["desc"],
                                        confirmation_rule=meta["confirm"],
                                        historical_accuracy_pct=meta["accuracy"]
                                    ))

        # Sort chronologically by time
        signals.sort(key=lambda s: s.time)
        return signals

    def to_chart_markers(self, signals: List[PatternSignal]) -> List[Dict[str, Any]]:
        """Converts PatternSignals directly into Lightweight Charts marker objects."""
        markers = []
        for s in signals:
            markers.append({
                "time": s.time,
                "position": s.position,
                "color": s.color,
                "shape": s.shape,
                "text": s.badge_text,
                "id": f"{s.pattern_id}_{s.time}",
                "customData": {
                    "pattern_id": s.pattern_id,
                    "pattern_name": s.pattern_name,
                    "sentiment": s.sentiment,
                    "description": s.description,
                    "confirmation_rule": s.confirmation_rule,
                    "historical_accuracy_pct": s.historical_accuracy_pct,
                    "price": s.price
                }
            })
        return markers

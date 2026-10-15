import datetime
from typing import Dict, Any, List, Optional

from api.models.journal_models import DiagnosticBucket, DiagnosticsResponse
from db.connection import DuckDBConnectionManager


class JournalDiagnosticsService:
    def __init__(self, db: DuckDBConnectionManager):
        self.db = db

    def get_quantitative_diagnostics(self) -> DiagnosticsResponse:
        """
        Evaluates trades across 4 quantitative dimensions:
        1. Time-of-Day session windows (IST)
        2. Direction (Long vs. Short)
        3. Holding Duration (Intraday vs. Swing)
        4. Instrument (Equity vs. F&O)
        """
        cursor = self.db.get_read_cursor()
        trades: List[Dict[str, Any]] = []
        try:
            query = """
                SELECT 
                    trade_id, symbol, trade_type, direction,
                    entry_time, exit_time, pnl_net, r_multiple
                FROM journal_entries
                WHERE exit_time IS NOT NULL
            """
            rows = cursor.execute(query).fetchall()
            cols = [desc[0] for desc in cursor.description]
            for r in rows:
                trades.append(dict(zip(cols, r)))
        finally:
            cursor.close()

        # 1. Time-of-Day Buckets
        tod_groups = {
            "morning": {"label": "Morning Momentum (09:15 - 10:30 IST)", "trades": []},
            "midday": {"label": "Midday Range / Chop (10:30 - 13:00 IST)", "trades": []},
            "afternoon": {"label": "Afternoon Closing Flow (13:00 - 15:30 IST)", "trades": []},
            "off_hours": {"label": "Off-Hours / Premarket Entry", "trades": []},
        }

        # 2. Direction Buckets
        dir_groups = {
            "long": {"label": "Long (Buy Side)", "trades": []},
            "short": {"label": "Short (Sell Side)", "trades": []},
        }

        # 3. Holding Duration Buckets
        dur_groups = {
            "intraday": {"label": "Intraday (Same Day)", "trades": []},
            "swing": {"label": "Swing (Overnight > 1 Day)", "trades": []},
        }

        # 4. Instrument Buckets
        inst_groups = {
            "equity": {"label": "Equity Cash", "trades": []},
            "fno": {"label": "Derivatives (F&O)", "trades": []},
        }

        t_m_start = datetime.time(9, 15, 0)
        t_m_end = datetime.time(10, 30, 0)
        t_mid_end = datetime.time(13, 0, 0)
        t_aft_end = datetime.time(15, 30, 0)

        for t in trades:
            entry_dt = t["entry_time"]
            exit_dt = t["exit_time"]
            if isinstance(entry_dt, str):
                entry_dt = datetime.datetime.fromisoformat(entry_dt)
            if isinstance(exit_dt, str):
                exit_dt = datetime.datetime.fromisoformat(exit_dt)

            entry_time = entry_dt.time()

            # Time of Day classification
            if t_m_start <= entry_time < t_m_end:
                tod_groups["morning"]["trades"].append(t)
            elif t_m_end <= entry_time < t_mid_end:
                tod_groups["midday"]["trades"].append(t)
            elif t_mid_end <= entry_time <= t_aft_end:
                tod_groups["afternoon"]["trades"].append(t)
            else:
                tod_groups["off_hours"]["trades"].append(t)

            # Direction classification
            direction = str(t.get("direction", "")).upper()
            if direction == "SHORT":
                dir_groups["short"]["trades"].append(t)
            else:
                dir_groups["long"]["trades"].append(t)

            # Duration classification
            if entry_dt.date() == exit_dt.date():
                dur_groups["intraday"]["trades"].append(t)
            else:
                dur_groups["swing"]["trades"].append(t)

            # Instrument classification
            symbol = str(t.get("symbol", "")).upper()
            trade_type = str(t.get("trade_type", "")).upper()
            if trade_type in ("F&O", "OPTIONS", "FUTURES") or symbol.endswith("-INDEX") or ("CE" in symbol or "PE" in symbol):
                inst_groups["fno"]["trades"].append(t)
            else:
                inst_groups["equity"]["trades"].append(t)

        def _build_bucket(name: str, label: str, group_trades: List[Dict[str, Any]]) -> DiagnosticBucket:
            count = len(group_trades)
            if count == 0:
                return DiagnosticBucket(
                    name=name,
                    label=label,
                    trades_count=0,
                    win_rate=0.0,
                    net_pnl=0.0,
                    avg_r=0.0,
                    profit_factor=0.0,
                )

            wins = [tr for tr in group_trades if (tr.get("pnl_net") or 0) > 0]
            win_count = len(wins)
            win_rate = round((win_count / count) * 100.0, 2)
            net_pnl = round(sum(tr.get("pnl_net") or 0 for tr in group_trades), 2)

            r_vals = [tr["r_multiple"] for tr in group_trades if tr.get("r_multiple") is not None]
            avg_r = round(sum(r_vals) / len(r_vals), 2) if r_vals else 0.0

            gross_wins = sum(tr.get("pnl_net") or 0 for tr in wins)
            gross_losses = sum(abs(tr.get("pnl_net") or 0) for tr in group_trades if (tr.get("pnl_net") or 0) < 0)

            if gross_losses > 0:
                pf = round(gross_wins / gross_losses, 2)
            else:
                pf = 999.0 if gross_wins > 0 else 0.0

            return DiagnosticBucket(
                name=name,
                label=label,
                trades_count=count,
                win_rate=win_rate,
                net_pnl=net_pnl,
                avg_r=avg_r,
                profit_factor=pf,
            )

        tod_buckets = [_build_bucket(k, v["label"], v["trades"]) for k, v in tod_groups.items()]
        dir_buckets = [_build_bucket(k, v["label"], v["trades"]) for k, v in dir_groups.items()]
        dur_buckets = [_build_bucket(k, v["label"], v["trades"]) for k, v in dur_groups.items()]
        inst_buckets = [_build_bucket(k, v["label"], v["trades"]) for k, v in inst_groups.items()]

        return DiagnosticsResponse(
            success=True,
            time_of_day=tod_buckets,
            direction=dir_buckets,
            duration=dur_buckets,
            instruments=inst_buckets,
        )

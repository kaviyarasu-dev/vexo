import json
import csv
import io
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional

from core.interfaces import IJournalService, JournalEntry
from db.connection import DuckDBConnectionManager

class JournalService(IJournalService):
    def __init__(self, db: DuckDBConnectionManager):
        self.db = db

    def calculate_r_multiple(self, entry: float, exit: float, stop_loss: float, direction: str) -> float:
        if direction.upper() == "LONG":
            if stop_loss >= entry:
                raise ValueError("Stop Loss must be below Entry for Long")
            risk = entry - stop_loss
            gain = exit - entry
        elif direction.upper() == "SHORT":
            if stop_loss <= entry:
                raise ValueError("Stop Loss must be above Entry for Short")
            risk = stop_loss - entry
            gain = entry - exit
        else:
            raise ValueError("Direction must be LONG or SHORT")
        
        if risk <= 0:
            return 0.0
        return round(gain / risk, 2)

    def record_trade(self, trade: JournalEntry) -> str:
        trade_id = trade.trade_id or str(uuid.uuid4())
        mistake_tags_str = json.dumps(trade.mistake_tags) if trade.mistake_tags else '[]'

        def _insert(conn):
            conn.execute("""
                INSERT OR REPLACE INTO journal_entries (
                    trade_id, symbol, trade_type, direction, entry_time, entry_price,
                    exit_time, exit_price, quantity, stop_loss, take_profit,
                    pnl_gross, total_charges, pnl_net, r_multiple, mistake_tags, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                trade_id, trade.symbol, trade.trade_type, trade.direction,
                trade.entry_time, trade.entry_price, trade.exit_time, trade.exit_price,
                trade.quantity, trade.stop_loss, trade.take_profit, trade.pnl_gross,
                trade.total_charges, trade.pnl_net, trade.r_multiple, mistake_tags_str,
                trade.notes
            ])
        
        self.db.execute_write_batch(_insert)
        return trade_id

    def delete_trade(self, trade_id: str) -> bool:
        def _del(conn):
            conn.execute("DELETE FROM journal_entries WHERE trade_id = ?", [trade_id])
        self.db.execute_write_batch(_del)
        return True

    def clear_all_trades(self) -> bool:
        def _clear(conn):
            conn.execute("DELETE FROM journal_entries")
        self.db.execute_write_batch(_clear)
        return True

    def seed_sample_trades(self) -> int:
        """Populates realistic institutional sample trades with psychological tags and equity trajectory.
        Reads from static/data/sample_tradebook.csv if available.
        """
        self.clear_all_trades()
        from pathlib import Path
        sample_csv = Path("static/data/sample_tradebook.csv")
        if sample_csv.exists():
            from services.journal.importer_engine import TradeImporterEngine
            text = sample_csv.read_text(encoding="utf-8")
            engine = TradeImporterEngine(self.db)
            res = engine.import_tradebook_csv(text, broker_hint="ZERODHA")
            return res.get("imported_trades", 0)

        import datetime

        now = datetime.datetime.now()
        samples = [
            # 1. Disciplined Winner
            {
                "symbol": "NSE:RELIANCE-EQ", "direction": "LONG", "trade_type": "EQUITY",
                "days_ago": 14, "entry_p": 2780.0, "exit_p": 2865.0, "qty": 40,
                "sl": 2740.0, "tags": [], "notes": "Trend following breakout on daily volume."
            },
            # 2. Controlled Loss
            {
                "symbol": "NSE:TCS-EQ", "direction": "LONG", "trade_type": "EQUITY",
                "days_ago": 12, "entry_p": 4150.0, "exit_p": 4100.0, "qty": 20,
                "sl": 4100.0, "tags": [], "notes": "Stop loss triggered at planned level. Clean discipline."
            },
            # 3. FOMO Mistake
            {
                "symbol": "NSE:INFY-EQ", "direction": "LONG", "trade_type": "EQUITY",
                "days_ago": 10, "entry_p": 1940.0, "exit_p": 1885.0, "qty": 60,
                "sl": 1910.0, "tags": ["FOMO", "Chased Entry"], "notes": "Jumped into green candle without confirmation."
            },
            # 4. Disciplined Winner
            {
                "symbol": "NSE:HDFCBANK-EQ", "direction": "LONG", "trade_type": "EQUITY",
                "days_ago": 8, "entry_p": 1620.0, "exit_p": 1675.0, "qty": 80,
                "sl": 1595.0, "tags": [], "notes": "Support bounce trade near 50 EMA."
            },
            # 5. Ignored Stop Loss
            {
                "symbol": "NSE:TATAMOTORS-EQ", "direction": "LONG", "trade_type": "EQUITY",
                "days_ago": 7, "entry_p": 945.0, "exit_p": 890.0, "qty": 50,
                "sl": 925.0, "tags": ["Ignored Stop Loss", "Overtrading"], "notes": "Held hoping for reversal instead of honoring cut."
            },
            # 6. Revenge Trading
            {
                "symbol": "NSE:TATAMOTORS-EQ", "direction": "SHORT", "trade_type": "EQUITY",
                "days_ago": 6, "entry_p": 895.0, "exit_p": 925.0, "qty": 50,
                "sl": 910.0, "tags": ["Revenge Trading"], "notes": "Tried to recover Tata Motors loss immediately."
            },
            # 7. Big Winner
            {
                "symbol": "NSE:ICICIBANK-EQ", "direction": "LONG", "trade_type": "EQUITY",
                "days_ago": 5, "entry_p": 1180.0, "exit_p": 1250.0, "qty": 70,
                "sl": 1150.0, "tags": [], "notes": "Superb earnings breakout swing."
            },
            # 8. Early Exit (Left money on the table)
            {
                "symbol": "NSE:SBIN-EQ", "direction": "LONG", "trade_type": "EQUITY",
                "days_ago": 4, "entry_p": 785.0, "exit_p": 798.0, "qty": 100,
                "sl": 770.0, "tags": ["Early Exit"], "notes": "Took 13 pts profit prematurely; stock later ran to 830."
            },
            # 9. Greed / Oversized Position
            {
                "symbol": "NSE:RELIANCE-EQ", "direction": "LONG", "trade_type": "EQUITY",
                "days_ago": 2, "entry_p": 2890.0, "exit_p": 2835.0, "qty": 120,
                "sl": 2860.0, "tags": ["Greed / Oversized Position", "Overtrading"], "notes": "Exceeded max risk limit on impulsive hunch."
            },
            # 10. Clean Winner
            {
                "symbol": "NSE:NIFTY50-INDEX", "direction": "LONG", "trade_type": "F&O",
                "days_ago": 1, "entry_p": 24900.0, "exit_p": 25150.0, "qty": 50,
                "sl": 24800.0, "tags": [], "notes": "Monthly expiry call long strategy."
            }
        ]

        count = 0
        for s in samples:
            direction = s["direction"]
            entry_p = s["entry_p"]
            exit_p = s["exit_p"]
            qty = s["qty"]
            sl = s["sl"]
            
            pnl_gross = (exit_p - entry_p) * qty if direction == "LONG" else (entry_p - exit_p) * qty
            total_charges = round(min(150.0, max(25.0, (entry_p * qty) * 0.001)), 2)
            pnl_net = round(pnl_gross - total_charges, 2)
            
            risk = abs(entry_p - sl)
            gain = (exit_p - entry_p) if direction == "LONG" else (entry_p - exit_p)
            r = round(gain / risk, 2) if risk > 0 else 0.0

            entry_time = now - datetime.timedelta(days=s["days_ago"], hours=4)
            exit_time = now - datetime.timedelta(days=s["days_ago"], hours=1)

            entry = JournalEntry(
                trade_id=str(uuid.uuid4()),
                symbol=s["symbol"],
                trade_type=s["trade_type"],
                direction=direction,
                entry_time=entry_time,
                entry_price=entry_p,
                exit_time=exit_time,
                exit_price=exit_p,
                quantity=qty,
                stop_loss=sl,
                take_profit=None,
                pnl_gross=pnl_gross,
                total_charges=total_charges,
                pnl_net=pnl_net,
                r_multiple=r,
                mistake_tags=s["tags"],
                notes=s["notes"]
            )
            self.record_trade(entry)
            count += 1

        return count

    def list_trades(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[JournalEntry]:
        cursor = self.db.get_read_cursor()
        try:
            query = "SELECT * FROM journal_entries WHERE 1=1"
            params = []
            if start_date:
                query += " AND CAST(entry_time AS DATE) >= CAST(? AS DATE)"
                params.append(start_date)
            if end_date:
                query += " AND CAST(entry_time AS DATE) <= CAST(? AS DATE)"
                params.append(end_date)
            query += " ORDER BY entry_time DESC"

            rows = cursor.execute(query, params).fetchall()
            cols = [desc[0] for desc in cursor.description]

            trades = []
            for r in rows:
                row_dict = dict(zip(cols, r))
                mistake_tags = json.loads(row_dict['mistake_tags']) if row_dict.get('mistake_tags') else []
                trades.append(JournalEntry(
                    trade_id=row_dict['trade_id'],
                    symbol=row_dict['symbol'],
                    trade_type=row_dict['trade_type'],
                    direction=row_dict['direction'],
                    entry_time=row_dict['entry_time'],
                    entry_price=row_dict['entry_price'],
                    exit_time=row_dict['exit_time'],
                    exit_price=row_dict['exit_price'],
                    quantity=row_dict['quantity'],
                    stop_loss=row_dict['stop_loss'],
                    take_profit=row_dict['take_profit'],
                    pnl_gross=row_dict['pnl_gross'],
                    total_charges=row_dict['total_charges'],
                    pnl_net=row_dict['pnl_net'],
                    r_multiple=row_dict['r_multiple'],
                    mistake_tags=mistake_tags,
                    notes=row_dict['notes']
                ))
            return trades
        finally:
            cursor.close()

    def import_tradebook_csv(self, file_content: str, broker: str = "FYERS") -> int:
        from services.journal.importer_engine import TradeImporterEngine
        engine = TradeImporterEngine(self.db)
        hint = broker if broker not in ("AUTO", None) else None
        res = engine.import_tradebook_csv(file_content, broker_hint=hint)
        return res["imported_trades"]

    def get_performance_summary(self) -> Dict[str, Any]:
        trades = self.list_trades()
        if not trades:
            return {
                "win_rate": 0.0,
                "average_r": 0.0,
                "expectancy": 0.0,
                "cost_of_mistakes": 0.0,
                "total_trades": 0,
                "net_pnl": 0.0
            }
            
        winners = [t for t in trades if (t.pnl_net or 0) > 0]
        win_rate = len(winners) / len(trades)
        
        r_multiples = [t.r_multiple for t in trades if t.r_multiple is not None]
        avg_r = sum(r_multiples) / len(r_multiples) if r_multiples else 0.0
        
        avg_win_r = sum([t.r_multiple for t in winners if t.r_multiple]) / len(winners) if winners else 0.0
        losers = [t for t in trades if (t.pnl_net or 0) <= 0]
        avg_loss_r = sum([t.r_multiple for t in losers if t.r_multiple]) / len(losers) if losers else 0.0
        
        expectancy = (win_rate * avg_win_r) + ((1 - win_rate) * avg_loss_r)
        
        mistake_trades = [t for t in trades if t.mistake_tags and len(t.mistake_tags) > 0 and (t.pnl_net or 0) < 0]
        cost_of_mistakes = sum(abs(t.pnl_net or 0) for t in mistake_trades)
        
        net_pnl = sum(t.pnl_net or 0 for t in trades)
        
        return {
            "win_rate": round(win_rate, 4),
            "average_r": round(avg_r, 2),
            "expectancy": round(expectancy, 2),
            "cost_of_mistakes": round(cost_of_mistakes, 2),
            "total_trades": len(trades),
            "net_pnl": round(net_pnl, 2)
        }

import uuid
from typing import List, Dict, Any, Optional

from core.interfaces import JournalEntry
from db.connection import DuckDBConnectionManager
from services.journal.parsers.base_parser import IBrokerParser, RawTradeFill
from services.journal.parsers.fyers_parser import FyersParser
from services.journal.parsers.zerodha_parser import ZerodhaParser
from services.journal.parsers.groww_parser import GrowwParser


class BrokerParserFactory:
    @staticmethod
    def detect_broker(csv_text: str, broker_hint: Optional[str] = None) -> str:
        if broker_hint and broker_hint.upper() in ("FYERS", "ZERODHA", "GROWW"):
            return broker_hint.upper()

        if ZerodhaParser().can_parse(csv_text):
            return "ZERODHA"
        if GrowwParser().can_parse(csv_text):
            return "GROWW"
        if FyersParser().can_parse(csv_text):
            return "FYERS"

        raise ValueError(
            "Unable to identify broker tradebook format. Expected headers for FYERS, Zerodha Console, or Groww."
        )

    @staticmethod
    def get_parser(broker_name: str) -> IBrokerParser:
        b = broker_name.upper()
        if b == "ZERODHA":
            return ZerodhaParser()
        elif b == "GROWW":
            return GrowwParser()
        elif b == "FYERS":
            return FyersParser()
        else:
            raise ValueError(f"Unsupported broker parser '{broker_name}'")


class FIFOReconciler:
    @staticmethod
    def reconcile(fills: List[RawTradeFill]) -> List[JournalEntry]:
        """
        Pairs raw buy/sell fills chronologically per symbol using FIFO matching
        and computes Indian statutory charges and R-multiples.
        """
        # Sort chronologically by execution timestamp
        sorted_fills = sorted(fills, key=lambda f: f.timestamp)

        open_queues: Dict[str, List[RawTradeFill]] = {}
        completed_trades: List[JournalEntry] = []

        for fill in sorted_fills:
            sym = fill.symbol
            if sym not in open_queues:
                open_queues[sym] = []

            queue = open_queues[sym]
            if not queue:
                queue.append(
                    RawTradeFill(
                        symbol=fill.symbol,
                        side=fill.side,
                        quantity=fill.quantity,
                        price=fill.price,
                        timestamp=fill.timestamp,
                        broker=fill.broker,
                        trade_id=fill.trade_id,
                    )
                )
            else:
                incoming_side = fill.side
                remaining_incoming_qty = fill.quantity

                while queue and remaining_incoming_qty > 0:
                    top = queue[0]
                    if top.side != incoming_side:
                        # Matched fill pair found
                        match_qty = min(top.quantity, remaining_incoming_qty)
                        direction = "LONG" if top.side == "BUY" else "SHORT"
                        entry_p = top.price
                        exit_p = fill.price

                        gross = (
                            (exit_p - entry_p) * match_qty
                            if direction == "LONG"
                            else (entry_p - exit_p) * match_qty
                        )

                        # Raw tradebook fills do not include contract note levies
                        charges = 0.0
                        net = round(gross, 2)

                        # Default stop loss for R-multiple (5% away)
                        sl = round(entry_p * 0.95 if direction == "LONG" else entry_p * 1.05, 2)
                        risk = abs(entry_p - sl)
                        gain = (exit_p - entry_p) if direction == "LONG" else (entry_p - exit_p)
                        r_mult = round(gain / risk, 2) if risk > 0 else 0.0

                        entry = JournalEntry(
                            trade_id=str(uuid.uuid4()),
                            symbol=sym,
                            trade_type="EQUITY" if not ("INDEX" in sym or "CE" in sym or "PE" in sym) else "F&O",
                            direction=direction,
                            entry_time=top.timestamp,
                            entry_price=entry_p,
                            exit_time=fill.timestamp,
                            exit_price=exit_p,
                            quantity=match_qty,
                            stop_loss=sl,
                            take_profit=None,
                            pnl_gross=round(gross, 2),
                            total_charges=charges,
                            pnl_net=net,
                            r_multiple=r_mult,
                            mistake_tags=[],
                            notes=f"Imported via {fill.broker} Tradebook",
                        )
                        completed_trades.append(entry)

                        top.quantity -= match_qty
                        remaining_incoming_qty -= match_qty

                        if top.quantity == 0:
                            queue.pop(0)
                    else:
                        break

                if remaining_incoming_qty > 0:
                    queue.append(
                        RawTradeFill(
                            symbol=fill.symbol,
                            side=fill.side,
                            quantity=remaining_incoming_qty,
                            price=fill.price,
                            timestamp=fill.timestamp,
                            broker=fill.broker,
                            trade_id=fill.trade_id,
                        )
                    )

        return completed_trades


class TradeImporterEngine:
    def __init__(self, db: DuckDBConnectionManager):
        self.db = db

    def import_tradebook_csv(
        self, csv_text: str, broker_hint: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Auto-detects broker CSV format, extracts fills, reconciles FIFO roundtrips,
        and records trades into DuckDB.
        """
        broker = BrokerParserFactory.detect_broker(csv_text, broker_hint)
        parser = BrokerParserFactory.get_parser(broker)
        fills = parser.parse_fills(csv_text)

        trades = FIFOReconciler.reconcile(fills)

        # Batch insert into DuckDB
        def _insert_batch(conn):
            for t in trades:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO journal_entries (
                        trade_id, symbol, trade_type, direction, entry_time, entry_price,
                        exit_time, exit_price, quantity, stop_loss, take_profit,
                        pnl_gross, total_charges, pnl_net, r_multiple, mistake_tags, notes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        t.trade_id,
                        t.symbol,
                        t.trade_type,
                        t.direction,
                        t.entry_time,
                        t.entry_price,
                        t.exit_time,
                        t.exit_price,
                        t.quantity,
                        t.stop_loss,
                        t.take_profit,
                        t.pnl_gross,
                        t.total_charges,
                        t.pnl_net,
                        t.r_multiple,
                        "[]",
                        t.notes,
                    ],
                )

        self.db.execute_write_batch(_insert_batch)

        return {
            "status": "success",
            "broker_detected": broker,
            "imported_trades": len(trades),
            "fills_parsed": len(fills),
        }

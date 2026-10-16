import csv
import io
import uuid
from datetime import datetime
from typing import List

from services.journal.parsers.base_parser import IBrokerParser, RawTradeFill


class ZerodhaParser(IBrokerParser):
    def can_parse(self, csv_text: str) -> bool:
        reader = csv.reader(io.StringIO(csv_text.strip()))
        headers = next(reader, None)
        if not headers:
            return False
        clean = [h.strip().lower() for h in headers]
        # Zerodha Console reports signature: 'isin' + ('trade_type' or 'order_execution_time' or 'exchange')
        return "isin" in clean and ("trade_type" in clean or "order_execution_time" in clean or "exchange" in clean)

    def parse_fills(self, csv_text: str) -> List[RawTradeFill]:
        reader = csv.DictReader(io.StringIO(csv_text.strip()))
        if not reader.fieldnames:
            raise ValueError("Empty or invalid CSV")

        clean_fieldnames = {f.strip().lower(): f for f in reader.fieldnames}
        if "symbol" not in clean_fieldnames or "quantity" not in clean_fieldnames or "price" not in clean_fieldnames:
            raise ValueError("Zerodha CSV missing essential columns: symbol, quantity, price")

        fills: List[RawTradeFill] = []
        for row in reader:
            normalized = {k.strip().lower(): v.strip() for k, v in row.items() if k}
            raw_sym = normalized.get("symbol", "").upper()
            exchange = normalized.get("exchange", "NSE").upper()
            segment = normalized.get("segment", "EQ").upper()
            series = normalized.get("series", "EQ").upper()

            # Normalize symbol
            if raw_sym.startswith("NSE:") or raw_sym.startswith("BSE:"):
                sym = raw_sym
            elif segment == "EQ" or series == "EQ":
                sym = f"{exchange}:{raw_sym}-EQ"
            else:
                sym = f"{exchange}:{raw_sym}"

            # Trade Type (buy / sell)
            side_raw = normalized.get("trade_type", normalized.get("side", "")).upper()
            if side_raw in ("BUY", "B"):
                side = "BUY"
            elif side_raw in ("SELL", "S"):
                side = "SELL"
            else:
                raise ValueError(f"Unknown Zerodha trade_type side '{side_raw}'")

            qty = int(float(normalized.get("quantity", 0)))
            price = float(normalized.get("price", 0.0))

            # Datetime priority: order_execution_time > trade_date
            ts_str = normalized.get("order_execution_time") or normalized.get("trade_date", "")
            dt = self._parse_timestamp(ts_str)

            trade_id = normalized.get("trade_id", str(uuid.uuid4()))
            order_id = normalized.get("order_id", None)

            fills.append(
                RawTradeFill(
                    symbol=sym,
                    side=side,
                    quantity=qty,
                    price=price,
                    timestamp=dt,
                    broker="ZERODHA",
                    trade_id=trade_id,
                    order_id=order_id,
                )
            )

        return fills

    def _parse_timestamp(self, ts_str: str) -> datetime:
        ts_clean = ts_str.replace("Z", "").strip()
        for fmt in (
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%d",
            "%d-%m-%Y %H:%M:%S",
            "%d/%m/%Y %H:%M:%S",
            "%d-%b-%Y %H:%M:%S",
            "%d-%B-%Y %H:%M:%S",
        ):
            try:
                return datetime.strptime(ts_clean, fmt)
            except ValueError:
                continue
        raise ValueError(f"Unable to parse timestamp '{ts_str}' for Zerodha fill")

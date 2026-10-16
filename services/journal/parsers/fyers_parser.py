import csv
import io
import uuid
from datetime import datetime
from typing import List

from services.journal.parsers.base_parser import IBrokerParser, RawTradeFill


class FyersParser(IBrokerParser):
    def can_parse(self, csv_text: str) -> bool:
        reader = csv.reader(io.StringIO(csv_text.strip()))
        headers = next(reader, None)
        if not headers:
            return False
        clean = [h.strip().lower() for h in headers]
        required = {"symbol", "trade_date", "price", "quantity", "side"}
        return required.issubset(set(clean))

    def parse_fills(self, csv_text: str) -> List[RawTradeFill]:
        reader = csv.DictReader(io.StringIO(csv_text.strip()))
        if not reader.fieldnames:
            raise ValueError("Empty or invalid CSV")

        clean_fieldnames = [f.strip().lower() for f in reader.fieldnames]
        required = {"symbol", "trade_date", "price", "quantity", "side"}
        if not required.issubset(set(clean_fieldnames)):
            raise ValueError(f"CSV missing required columns for FYERS: {required}")

        fills: List[RawTradeFill] = []
        for row in reader:
            normalized = {k.strip().lower(): v.strip() for k, v in row.items() if k}
            sym = normalized.get("symbol", "")
            if not sym.startswith("NSE:"):
                sym = f"NSE:{sym}-EQ" if not sym.endswith(("-EQ", "-INDEX")) else f"NSE:{sym}"

            side = normalized.get("side", "").upper()
            if side not in ("BUY", "SELL"):
                raise ValueError(f"Invalid side value '{side}', expected BUY or SELL")

            qty = int(float(normalized.get("quantity", 0)))
            price = float(normalized.get("price", 0.0))
            raw_dt = normalized.get("trade_date", "")

            # Parse datetime
            dt = self._parse_timestamp(raw_dt)
            trade_id = normalized.get("trade_id", str(uuid.uuid4()))

            fills.append(
                RawTradeFill(
                    symbol=sym,
                    side=side,
                    quantity=qty,
                    price=price,
                    timestamp=dt,
                    broker="FYERS",
                    trade_id=trade_id,
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
        ):
            try:
                return datetime.strptime(ts_clean, fmt)
            except ValueError:
                continue
        raise ValueError(f"Unable to parse timestamp '{ts_str}' for FYERS fill")

import csv
import io
import uuid
from datetime import datetime
from typing import List

from services.journal.parsers.base_parser import IBrokerParser, RawTradeFill


class GrowwParser(IBrokerParser):
    def can_parse(self, csv_text: str) -> bool:
        reader = csv.reader(io.StringIO(csv_text.strip()))
        headers = next(reader, None)
        if not headers:
            return False
        clean = [h.strip().lower() for h in headers]
        # Groww reports signature: 'stock name' or ('symbol' and any of 'execution date & time', 'order status')
        if "stock name" in clean:
            return True
        if "execution date & time" in clean or "execution date" in clean:
            return True
        if "symbol" in clean and "type" in clean and "price" in clean and "isin" not in clean:
            return True
        return False

    def parse_fills(self, csv_text: str) -> List[RawTradeFill]:
        reader = csv.DictReader(io.StringIO(csv_text.strip()))
        if not reader.fieldnames:
            raise ValueError("Empty or invalid CSV")

        fills: List[RawTradeFill] = []
        for row in reader:
            normalized = {k.strip().lower(): v.strip() for k, v in row.items() if k}
            # Symbol extraction (Groww may have 'symbol' or 'stock name')
            raw_sym = normalized.get("symbol") or normalized.get("stock name", "")
            raw_sym = raw_sym.strip().upper()

            if not raw_sym:
                continue

            if raw_sym.startswith("NSE:") or raw_sym.startswith("BSE:"):
                sym = raw_sym
            else:
                clean_sym = raw_sym.split()[0].replace("-EQ", "")
                sym = f"NSE:{clean_sym}-EQ"

            # Side extraction ('type' or 'order type' or 'side')
            side_raw = normalized.get("type") or normalized.get("order type") or normalized.get("side", "")
            side_raw = side_raw.strip().upper()
            if side_raw in ("BUY", "B"):
                side = "BUY"
            elif side_raw in ("SELL", "S"):
                side = "SELL"
            else:
                raise ValueError(f"Unknown Groww order side '{side_raw}'")

            # Quantity extraction ('quantity' or 'qty')
            qty_val = normalized.get("quantity") or normalized.get("qty", "0")
            qty = int(float(qty_val))

            # Price extraction ('price' or 'average price' or 'avg. price' or 'execution price')
            price_val = (
                normalized.get("price")
                or normalized.get("average price")
                or normalized.get("avg. price")
                or normalized.get("execution price", "0.0")
            )
            price = float(price_val.replace("₹", "").replace(",", "").strip())

            # Timestamp extraction ('execution date & time' or 'date & time' or 'trade date' or 'date')
            ts_str = (
                normalized.get("execution date & time")
                or normalized.get("execution date")
                or normalized.get("date & time")
                or normalized.get("trade date")
                or normalized.get("date", "")
            )
            dt = self._parse_timestamp(ts_str)
            trade_id = normalized.get("order id") or normalized.get("trade id") or str(uuid.uuid4())

            fills.append(
                RawTradeFill(
                    symbol=sym,
                    side=side,
                    quantity=qty,
                    price=price,
                    timestamp=dt,
                    broker="GROWW",
                    trade_id=trade_id,
                )
            )

        if not fills:
            raise ValueError("No valid trade fills parsed from Groww CSV")

        return fills

    def _parse_timestamp(self, ts_str: str) -> datetime:
        ts_clean = ts_str.replace("Z", "").strip()
        for fmt in (
            "%d-%m-%Y %H:%M:%S",
            "%d/%m/%Y %H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%d-%m-%Y %I:%M %p",
            "%d/%m/%Y %I:%M %p",
            "%d-%m-%Y %I:%M:%S %p",
            "%d/%m/%Y %I:%M:%S %p",
            "%d-%b-%Y %H:%M:%S",
            "%d-%m-%Y",
            "%d/%m/%Y",
            "%Y-%m-%d",
        ):
            try:
                return datetime.strptime(ts_clean, fmt)
            except ValueError:
                continue
        raise ValueError(f"Unable to parse timestamp '{ts_str}' for Groww fill")

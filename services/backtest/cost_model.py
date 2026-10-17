from dataclasses import dataclass

@dataclass
class CostResult:
    brokerage: float
    stt: float
    exchange_charges: float
    sebi_fee: float
    gst: float
    stamp_duty: float
    slippage: float
    total_taxes_and_fees: float

class IndianEquityCostModel:
    def __init__(self, slippage_bps: float = 5.0):
        self.slippage_bps = slippage_bps

    def compute_fees(self, buy_val: float, sell_val: float, trade_type: str = "DELIVERY") -> CostResult:
        if trade_type.upper() == "DELIVERY":
            brokerage_buy = min(20.0, buy_val * 0.003)
            brokerage_sell = min(20.0, sell_val * 0.003)
            brokerage = brokerage_buy + brokerage_sell

            stt = (buy_val * 0.001) + (sell_val * 0.001)
            stamp_duty = buy_val * 0.00015
        else:
            # Intraday
            brokerage_buy = min(20.0, buy_val * 0.0003)
            brokerage_sell = min(20.0, sell_val * 0.0003)
            brokerage = brokerage_buy + brokerage_sell
            
            stt = sell_val * 0.00025
            stamp_duty = buy_val * 0.00003
        
        turnover = buy_val + sell_val
        exchange_charges = turnover * 0.0000297
        sebi_fee = turnover * 0.000001
        
        gst = (brokerage + exchange_charges + sebi_fee) * 0.18
        slippage = turnover * (self.slippage_bps / 10000.0)

        # Round components normally
        brokerage = round(brokerage, 2)
        stt = round(stt, 2)
        exchange_charges = round(exchange_charges, 2)
        sebi_fee = round(sebi_fee, 2)
        gst = round(gst, 2)
        stamp_duty = round(stamp_duty, 2)
        slippage = round(slippage, 2)

        total = brokerage + stt + exchange_charges + sebi_fee + gst + stamp_duty

        return CostResult(
            brokerage=brokerage,
            stt=stt,
            exchange_charges=exchange_charges,
            sebi_fee=sebi_fee,
            gst=gst,
            stamp_duty=stamp_duty,
            slippage=slippage,
            total_taxes_and_fees=round(total, 2)
        )

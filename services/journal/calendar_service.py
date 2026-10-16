import calendar
import datetime
from typing import Optional, Dict, Any, List

from api.models.journal_models import (
    CalendarDayItem,
    CalendarWeekSummary,
    CalendarMonthlyKPIs,
    CalendarResponse,
)
from db.connection import DuckDBConnectionManager


class JournalCalendarService:
    def __init__(self, db: DuckDBConnectionManager):
        self.db = db

    def get_monthly_calendar(
        self, year: Optional[int] = None, month: Optional[int] = None
    ) -> CalendarResponse:
        """
        Calculates daily realized P&L, weekly rollups, streaks, and monthly KPIs
        strictly by trade exit date in Indian Standard Time (IST).
        """
        now = datetime.datetime.now()
        y = year if year is not None and year > 0 else now.year
        m = month if month is not None and 1 <= month <= 12 else now.month

        _, num_days = calendar.monthrange(y, m)
        start_ts = f"{y:04d}-{m:02d}-01 00:00:00"
        end_ts = f"{y:04d}-{m:02d}-{num_days:02d} 23:59:59"

        # Query aggregated closed trades by exit date
        cursor = self.db.get_read_cursor()
        daily_map: Dict[str, Dict[str, Any]] = {}
        try:
            query = """
                SELECT 
                    STRFTIME(CAST(exit_time AS DATE), '%Y-%m-%d') as trade_date,
                    COUNT(*) as trades_count,
                    COALESCE(SUM(pnl_gross), 0.0) as gross_pnl,
                    COALESCE(SUM(total_charges), 0.0) as total_charges,
                    COALESCE(SUM(pnl_net), 0.0) as net_pnl,
                    COALESCE(SUM(CASE WHEN pnl_net > 0 THEN 1 ELSE 0 END), 0) as win_count,
                    COALESCE(SUM(CASE WHEN pnl_net < 0 THEN 1 ELSE 0 END), 0) as loss_count
                FROM journal_entries
                WHERE exit_time IS NOT NULL
                  AND exit_time >= CAST(? AS TIMESTAMP)
                  AND exit_time <= CAST(? AS TIMESTAMP)
                GROUP BY trade_date
                ORDER BY trade_date ASC
            """
            rows = cursor.execute(query, [start_ts, end_ts]).fetchall()
            for r in rows:
                daily_map[str(r[0])] = {
                    "trades_count": int(r[1]),
                    "gross_pnl": float(r[2]),
                    "total_charges": float(r[3]),
                    "net_pnl": float(r[4]),
                    "win_count": int(r[5]),
                    "loss_count": int(r[6]),
                }
        finally:
            cursor.close()

        # Build full calendar days list for the month
        days: List[CalendarDayItem] = []
        for day_idx in range(1, num_days + 1):
            date_str = f"{y:04d}-{m:02d}-{day_idx:02d}"
            dt = datetime.date(y, m, day_idx)
            dow = dt.weekday()  # 0=Mon, 6=Sun

            if date_str in daily_map:
                info = daily_map[date_str]
                net = round(info["net_pnl"], 2)
                t_count = info["trades_count"]
                if net > 0:
                    status = "WIN"
                elif net < 0:
                    status = "LOSS"
                elif t_count > 0:
                    status = "EVEN"
                else:
                    status = "NO_TRADES"

                days.append(
                    CalendarDayItem(
                        date=date_str,
                        day_of_month=day_idx,
                        day_of_week=dow,
                        net_pnl=net,
                        gross_pnl=round(info["gross_pnl"], 2),
                        total_charges=round(info["total_charges"], 2),
                        trades_count=t_count,
                        win_count=info["win_count"],
                        loss_count=info["loss_count"],
                        status=status,
                    )
                )
            else:
                days.append(
                    CalendarDayItem(
                        date=date_str,
                        day_of_month=day_idx,
                        day_of_week=dow,
                        net_pnl=0.0,
                        gross_pnl=0.0,
                        total_charges=0.0,
                        trades_count=0,
                        win_count=0,
                        loss_count=0,
                        status="NO_TRADES",
                    )
                )

        # Build weekly rollups based on calendar row
        weeks: List[CalendarWeekSummary] = []
        current_week_num = 1
        week_days: List[CalendarDayItem] = []

        for d in days:
            week_days.append(d)
            if d.day_of_week == 6 or d.day_of_month == num_days:
                # End of week row (Sunday) or end of month
                w_net = round(sum(item.net_pnl for item in week_days), 2)
                w_trades = sum(item.trades_count for item in week_days)
                w_win = sum(item.win_count for item in week_days)
                w_loss = sum(item.loss_count for item in week_days)

                weeks.append(
                    CalendarWeekSummary(
                        week_number=current_week_num,
                        net_pnl=w_net,
                        trades_count=w_trades,
                        win_count=w_win,
                        loss_count=w_loss,
                    )
                )
                current_week_num += 1
                week_days = []

        # Monthly KPIs and streak statistics
        monthly_net = round(sum(d.net_pnl for d in days), 2)
        active_days = [d for d in days if d.trades_count > 0]
        trading_days = len(active_days)
        win_days = sum(1 for d in active_days if d.net_pnl > 0)
        loss_days = sum(1 for d in active_days if d.net_pnl < 0)
        win_day_pct = (
            round((win_days / trading_days) * 100.0, 2) if trading_days > 0 else 0.0
        )

        # Compute consecutive winning and losing day streaks
        max_win_streak = 0
        curr_win_streak = 0
        max_loss_streak = 0
        curr_loss_streak = 0

        for d in active_days:
            if d.net_pnl > 0:
                curr_win_streak += 1
                curr_loss_streak = 0
            elif d.net_pnl < 0:
                curr_loss_streak += 1
                curr_win_streak = 0
            else:
                curr_win_streak = 0
                curr_loss_streak = 0

            if curr_win_streak > max_win_streak:
                max_win_streak = curr_win_streak
            if curr_loss_streak > max_loss_streak:
                max_loss_streak = curr_loss_streak

        win_day_pnls = [d.net_pnl for d in active_days if d.net_pnl > 0]
        loss_day_pnls = [abs(d.net_pnl) for d in active_days if d.net_pnl < 0]

        avg_win_day_pnl = (
            round(sum(win_day_pnls) / win_days, 2) if win_days > 0 else 0.0
        )
        avg_loss_day_pnl = (
            round(sum(loss_day_pnls) / loss_days, 2) if loss_days > 0 else 0.0
        )

        gross_day_wins = sum(win_day_pnls)
        gross_day_losses = sum(loss_day_pnls)
        if gross_day_losses > 0:
            profit_factor = round(gross_day_wins / gross_day_losses, 2)
        else:
            profit_factor = 999.0 if gross_day_wins > 0 else 0.0

        kpis = CalendarMonthlyKPIs(
            monthly_net_pnl=monthly_net,
            trading_days=trading_days,
            win_days=win_days,
            loss_days=loss_days,
            win_day_pct=win_day_pct,
            max_win_streak=max_win_streak,
            max_loss_streak=max_loss_streak,
            avg_win_day_pnl=avg_win_day_pnl,
            avg_loss_day_pnl=avg_loss_day_pnl,
            profit_factor=profit_factor,
        )

        return CalendarResponse(
            success=True,
            year=y,
            month=m,
            kpis=kpis,
            days=days,
            weeks=weeks,
        )

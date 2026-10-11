import abc
from datetime import datetime
from typing import Optional, Union, List, Dict, Any
import pandas as pd
import pyarrow as pa

from dataclasses import dataclass

@dataclass(frozen=True)
class AuthToken:
    """Immutable representation of Fyers OAuth credentials."""
    access_token: str
    refresh_token: Optional[str]
    access_token_expires_at: datetime
    refresh_token_expires_at: Optional[datetime]


@dataclass
class Candle:
    """Canonical OHLCV candle entity."""
    symbol: str
    timestamp: Any  # datetime for 1m, date or datetime for 1D
    open: float
    high: float
    low: float
    close: float
    volume: int


@dataclass
class SymbolEntity:
    """Master instrument entity."""
    symbol: str
    name: str
    isin: Optional[str] = None
    exchange: str = "NSE"
    segment: str = "EQUITY"
    series: str = "EQ"
    lot_size: int = 1
    tick_size: float = 0.05
    category: Optional[str] = None
    tier: int = 4
    priority_rank: int = 9999
    listing_date: Optional[Any] = None
    is_active: bool = True
    updated_at: Optional[datetime] = None


@dataclass
class Checkpoint:
    """Resumable download checkpoint state."""
    symbol: str
    timeframe: str
    earliest_ts: Optional[datetime] = None
    latest_ts: Optional[datetime] = None
    total_candles: int = 0
    status: str = "PENDING"
    consecutive_empty_count: int = 0
    last_attempt_at: Optional[datetime] = None
    error_message: Optional[str] = None

@dataclass
class CorporateAction:
    id: str
    symbol: str
    action_type: str                  # "SPLIT", "BONUS", "DIVIDEND", "RIGHTS"
    ex_date: datetime | str
    record_date: Optional[datetime | str] = None
    ratio_from: Optional[float] = None
    ratio_to: Optional[float] = None
    dividend_amount: Optional[float] = None
    description: Optional[str] = None

@dataclass
class AdjustmentFactor:
    symbol: str
    ex_date: datetime | str
    factor_price: float
    factor_volume: float

class CandleQueryRequest: pass
class CandleQueryResponse: pass
class StreamMetadata: pass
@dataclass
class ScreenerFilter:
    universe: str
    as_of_date: Optional[str] = None
    technical_rules: Optional[list[dict[str, Any]]] = None
    min_turnover_cr: float = 0.0

@dataclass
class ScreenerResult:
    symbol: str
    name: str
    category: str
    close: float
    turnover_cr: float
    matched_rules: list[str]
    as_of_date: str
@dataclass
class AlertRule:
    alert_id: str
    symbol: str
    rule_type: str                   # 'PRICE_CROSS', 'VWAP_CROSS', 'RSI_THRESHOLD'
    condition_params: Dict[str, Any]
    channel: str                     # 'IN_APP', 'EMAIL', 'TELEGRAM'
    is_active: bool = True
    last_triggered_at: Optional[datetime] = None

from dataclasses import dataclass, field

@dataclass
class AlertTrigger:
    alert_id: str
    symbol: str
    rule_type: str
    trigger_price: float
    trigger_time: datetime
    message: str

@dataclass
class BacktestConfig:
    strategy_name: str
    symbol: str
    timeframe: str = "1D"
    start_date: str = "2020-01-01"
    end_date: str = "2023-12-31"
    initial_capital: float = 1000000.0
    trade_type: str = "DELIVERY"
    parameters: Dict[str, Any] = None
    slippage_bps: float = 5.0
    stop_loss_pct: Optional[float] = None
    take_profit_pct: Optional[float] = None
    position_size_type: str = "PERCENT_CAPITAL"
    position_size_val: float = 100.0

@dataclass
class BacktestResult:
    cagr: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown_pct: float
    win_rate: float
    profit_factor: float
    total_trades: int
    gross_pnl: float
    net_pnl: float
    total_taxes_and_fees: float
    equity_curve: List[Dict[str, Any]]
    data_version_hash: str
    survivorship_bias_warning: str
    trades: List[Dict[str, Any]] = field(default_factory=list)
    monthly_returns: Dict[str, Dict[str, float]] = field(default_factory=dict)
    benchmark_curve: List[Dict[str, Any]] = field(default_factory=list)
    drawdown_curve: List[Dict[str, Any]] = field(default_factory=list)
    extra_metrics: Dict[str, Any] = field(default_factory=dict)
    sebi_disclaimer: str = (
        "DISCLAIMER: This application is a self-directed quantitative data analysis and backtesting "
        "tool for educational and research purposes only. It does NOT constitute investment advice, "
        "financial advisory, or a recommendation to buy or sell any securities under SEBI regulations. "
        "Historical performance is NOT indicative of future returns."
    )
class WalkForwardConfig: pass
class WalkForwardResult: pass
@dataclass
class JournalEntry:
    trade_id: str
    symbol: str
    trade_type: str                   # 'PAPER' or 'MANUAL'
    direction: str                    # 'LONG' or 'SHORT'
    entry_time: datetime
    entry_price: float
    exit_time: Optional[datetime]
    exit_price: Optional[float]
    quantity: int
    stop_loss: float
    take_profit: Optional[float]
    pnl_gross: Optional[float]
    total_charges: Optional[float]
    pnl_net: Optional[float]
    r_multiple: Optional[float]
    mistake_tags: List[str]
    notes: Optional[str]

@dataclass
class PaperFill:
    symbol: str
    quantity: int
    side: str
    fill_price: float
    total_charges: float

class IAuthService(abc.ABC):
    @abc.abstractmethod
    def get_auth_url(self) -> str: pass
    
    @abc.abstractmethod
    def exchange_code_for_token(self, code: str) -> AuthToken: pass
    
    @abc.abstractmethod
    def get_valid_token(self) -> str: pass
    
    @abc.abstractmethod
    def validate_session(self) -> bool: pass
    
    @abc.abstractmethod
    def refresh_token_if_needed(self) -> bool: pass

class IMarketDataProvider(abc.ABC):
    @abc.abstractmethod
    def fetch_candles(self, symbol: str, resolution: str, range_from: str, range_to: str, cont_flag: str = "0") -> list[dict]: pass
    
    @abc.abstractmethod
    def fetch_quotes(self, symbols: list[str]) -> dict: pass
    
    @abc.abstractmethod
    def fetch_option_chain(self, symbol: str, strikes: int = 20) -> dict: pass

class ISymbolRepository(abc.ABC):
    @abc.abstractmethod
    def upsert_symbols(self, symbols: list[SymbolEntity]) -> int: pass
    
    @abc.abstractmethod
    def search_symbols(self, query: str, category: str | None, limit: int = 20) -> list[SymbolEntity]: pass
    
    @abc.abstractmethod
    def get_by_symbol(self, symbol: str) -> SymbolEntity | None: pass
    
    @abc.abstractmethod
    def list_active_symbols(self, tier: int | None = None) -> list[SymbolEntity]: pass

class ICandleReader(abc.ABC):
    @abc.abstractmethod
    def get_raw_candles(self, symbol: str, timeframe: str, start: datetime, end: datetime, limit: int = 1000, cursor: str | None = None) -> list[Candle]: pass
    
    @abc.abstractmethod
    def get_adjusted_candles(self, symbol: str, timeframe: str, start: datetime, end: datetime, limit: int = 1000) -> list[Candle]: pass
    
    @abc.abstractmethod
    def get_latest_candle(self, symbol: str, timeframe: str) -> Candle | None: pass

class ICandleWriter(abc.ABC):
    @abc.abstractmethod
    def batch_insert_1m(self, candles: Union[list[dict], pa.Table]) -> int: pass
    
    @abc.abstractmethod
    def batch_insert_1d(self, candles: Union[list[dict], pa.Table]) -> int: pass
    
    @abc.abstractmethod
    def stage_and_merge_1m(self, staging_table: str) -> int: pass

class ICheckpointRepository(abc.ABC):
    @abc.abstractmethod
    def get_checkpoint(self, symbol: str, timeframe: str) -> Checkpoint | None: pass
    
    @abc.abstractmethod
    def update_checkpoint(self, checkpoint: Checkpoint) -> None: pass
    
    @abc.abstractmethod
    def list_pending_symbols(self, timeframe: str, tier: int | None = None) -> list[str]: pass

class ICorporateActionRepository(abc.ABC):
    @abc.abstractmethod
    def upsert_actions(self, actions: list[CorporateAction]) -> int: pass
    
    @abc.abstractmethod
    def get_factors(self, symbol: str) -> list[AdjustmentFactor]: pass
    
    @abc.abstractmethod
    def recompute_adjustment_factors(self, symbol: str) -> None: pass

class IResamplingService(abc.ABC):
    @abc.abstractmethod
    def resample(self, symbol: str, target_timeframe: str, start: datetime, end: datetime, adjusted: bool = True) -> pd.DataFrame: pass

class IIndicator(abc.ABC):
    @abc.abstractmethod
    def name(self) -> str: pass
    
    @abc.abstractmethod
    def required_columns(self) -> list[str]: pass
    
    @abc.abstractmethod
    def compute(self, df: pd.DataFrame) -> pd.DataFrame: pass

class IDataExporter(abc.ABC):
    @abc.abstractmethod
    def export(self, symbol: str, timeframe: str, start: datetime, end: datetime, format: str, adjusted: bool = True) -> str: pass

class ICandleService(abc.ABC):
    @abc.abstractmethod
    def get_candles(self, request: CandleQueryRequest) -> CandleQueryResponse: pass
    
    @abc.abstractmethod
    def get_stream_info(self, symbol: str) -> StreamMetadata: pass

class IScreenerService(abc.ABC):
    @abc.abstractmethod
    def run_screener(self, filter_params: ScreenerFilter) -> list[ScreenerResult]: pass
    
    @abc.abstractmethod
    def save_preset(self, name: str, filter_params: ScreenerFilter) -> str: pass

    @abc.abstractmethod
    def create_custom_template(self, name: str, description: str, universe: str, conditions: list[dict[str, Any]]) -> dict: pass

    @abc.abstractmethod
    def delete_custom_template(self, template_id: str) -> bool: pass

class IAlertService(abc.ABC):
    @abc.abstractmethod
    def create_alert(self, symbol: str, rule_type: str, params: Dict[str, Any], channel: str = "IN_APP") -> str: pass

    @abc.abstractmethod
    def list_alerts(self, symbol: Optional[str] = None) -> list[AlertRule]: pass

    @abc.abstractmethod
    def delete_alert(self, alert_id: str) -> bool: pass

    @abc.abstractmethod
    def evaluate_rules(self, latest_candles: dict[str, Candle]) -> list[AlertTrigger]: pass
    
    @abc.abstractmethod
    def dispatch_alert(self, alert: AlertTrigger) -> bool: pass

class IBacktestEngine(abc.ABC):
    @abc.abstractmethod
    def run_backtest(self, config: BacktestConfig) -> BacktestResult: pass
    
    @abc.abstractmethod
    def run_walk_forward(self, config: WalkForwardConfig) -> WalkForwardResult: pass

class IJournalService(abc.ABC):
    @abc.abstractmethod
    def record_trade(self, trade: JournalEntry) -> str:
        """Saves or updates trade record in journal_entries table."""
        pass
    
    @abc.abstractmethod
    def list_trades(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[JournalEntry]:
        """Retrieves trade records for review."""
        pass
    
    @abc.abstractmethod
    def import_tradebook_csv(self, file_content: str, broker: str = "FYERS") -> int:
        """Parses external tradebook CSV and reconciles into journal entries."""
        pass

    @abc.abstractmethod
    def get_performance_summary(self) -> Dict[str, Any]:
        """Calculates win rate, average R, expectancy, and cost of mistakes."""
        pass


class IComplianceRule(abc.ABC):
    """Interface for institutional and regulatory compliance rules."""
    @abc.abstractmethod
    def rule_id(self) -> str:
        """Unique identifier for the compliance rule."""
        pass

    @abc.abstractmethod
    def validate(self, context: Dict[str, Any]) -> bool:
        """Validates that context satisfies the compliance constraint."""
        pass

    @abc.abstractmethod
    def get_notice(self) -> str:
        """Returns statutory notice or disclaimer text associated with this rule."""
        pass


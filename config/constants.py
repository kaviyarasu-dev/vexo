# Canonical Timeframes
CANONICAL_TIMEFRAMES = [
    "1m", "3m", "5m", "10m", "15m", "30m", "1h", "2h", "4h", "1D", "1W"
]

# Indian Session Alignment
MARKET_OPEN_IST = "09:15:00"
MARKET_CLOSE_IST = "15:30:00"
MARKET_OPEN_UTC = "03:45:00"
MARKET_CLOSE_UTC = "10:00:00"
DUCKDB_TIME_BUCKET_ORIGIN = "2000-01-01 03:45:00"

# Rate Limits
RATE_GOVERNOR_BURST_PER_SEC = 10
RATE_GOVERNOR_TARGET_PER_MIN = 180
RATE_GOVERNOR_DAILY_CAP = 90000

# Other Defaults
DEFAULT_1M_HISTORY_YEARS = 5
DEFAULT_1D_HISTORY_YEARS = 15
UVICORN_WORKERS = 1

# Fyers Auth URLs
FYERS_AUTH_CODE_URL = "https://api-t1.fyers.in/api/v3/generate-authcode"
FYERS_VALIDATE_AUTH_URL = "https://api-t1.fyers.in/api/v3/validate-authcode"
FYERS_REFRESH_TOKEN_URL = "https://api-t1.fyers.in/api/v3/validate-refresh-token"
FYERS_PROFILE_URL = "https://api-t1.fyers.in/api/v3/profile"

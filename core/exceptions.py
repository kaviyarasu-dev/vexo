class QuantPlatformError(Exception):
    """Base exception for all NSE Quant Platform errors."""
    pass

class MarketDataError(QuantPlatformError):
    """Raised when upstream market data provider fails."""
    pass

class RateLimitExceededError(MarketDataError):
    """Raised when API rate limits are breached."""
    pass

class AuthenticationError(QuantPlatformError):
    """Raised when broker authentication fails or expires."""
    pass

class AuthenticationExpiredError(AuthenticationError):
    """Raised when broker token expires."""
    pass

class DatabaseError(QuantPlatformError):
    """Raised when DuckDB operations fail."""
    pass

class ResamplingError(QuantPlatformError):
    """Raised when session alignment or resampling math fails."""
    pass

class ConfigurationError(QuantPlatformError):
    """Raised when environment variables or settings are invalid."""
    pass

class FyersAPIError(MarketDataError):
    def __init__(self, message: str, status_code: int = None, error_code: str = None):
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code

class KeyringUnavailableError(QuantPlatformError):
    """Raised when OS keyring is not available."""
    pass

class VaultError(QuantPlatformError):
    """Raised when vault operations fail."""
    pass

class LookaheadBiasError(QuantPlatformError):
    """Raised when a strategy attempts to access future data or execute at current bar close."""
    pass

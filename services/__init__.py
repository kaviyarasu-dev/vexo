"""Services package for NSE Quant Platform."""
from services.vault import ICredentialVault, OSKeyringVault, EncryptedFileVault, CompositeVault, get_credential_vault
from services.auth_service import AuthService
from services.symbol_service import SymbolService
from services.chunk_generator import CalendarChunker, DateChunk, generate_chunks
from services.fyers_client import FyersMarketDataProvider
from services.downloader_service import HistoricalDownloader

__all__ = [
    "ICredentialVault",
    "OSKeyringVault",
    "EncryptedFileVault",
    "CompositeVault",
    "get_credential_vault",
    "AuthService",
    "SymbolService",
    "CalendarChunker",
    "DateChunk",
    "generate_chunks",
    "FyersMarketDataProvider",
    "HistoricalDownloader",
]

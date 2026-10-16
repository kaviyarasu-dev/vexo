"""One-shot Fyers token generation utility via PyFyers SDK / OAuth flow.
Securely exchanges authorization code for daily access token & 15-day refresh token,
saving credentials to the configured secure vault (OS Keyring or Encrypted Vault).
Plaintext storage in .env is strictly forbidden.
"""

import getpass
from pathlib import Path
import sys
import webbrowser
from urllib.parse import parse_qs, urlparse

# Ensure project root is in sys.path when script is run directly
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import get_settings
from services.auth_service import AuthService
from services.vault import get_credential_vault


def extract_auth_code_from_input(user_input: str) -> str:
    """Extract auth_code whether user pasted the full redirect URL or raw code."""
    user_input = user_input.strip()
    if "auth_code=" in user_input or "?" in user_input:
        parsed = urlparse(user_input)
        params = parse_qs(parsed.query)
        if "auth_code" in params:
            return params["auth_code"][0]
    return user_input


def run_token_generation() -> int:
    """Executes the one-shot OAuth token generation workflow."""
    print("=" * 65)
    print("  NSE Quant Platform - One-Shot Fyers Token Generator")
    print("=" * 65)

    settings = get_settings()
    vault = get_credential_vault(settings.AUTH_CREDENTIAL_STORAGE)
    auth_service = AuthService(settings=settings, vault=vault)

    print(f"\n[1] Using Fyers App ID: {settings.FYERS_APP_ID}")
    print(f"[2] Credential Storage Backend: {settings.AUTH_CREDENTIAL_STORAGE}")
    print("[3] Generating OAuth login URL...")

    auth_url = auth_service.get_auth_url()
    print(f"\nOpening browser for OAuth authorization:\n  {auth_url}\n")

    try:
        webbrowser.open(auth_url)
    except Exception:
        print("Note: Could not open browser automatically. Please open the link above manually.")

    print("-" * 65)
    print("After logging in, your browser will redirect to your registered redirect URI.")
    print("Copy the entire redirected URL or just the 'auth_code' parameter value.")
    print("-" * 65)

    try:
        raw_input_code = input("\nEnter redirected URL or auth code: ").strip()
    except (KeyboardInterrupt, EOFError):
        print("\nOperation cancelled by user.")
        return 1

    if not raw_input_code:
        print("[ERROR] No authorization code provided. Exiting.")
        return 1

    auth_code = extract_auth_code_from_input(raw_input_code)

    try:
        pin = getpass.getpass("Enter your 4-digit Fyers PIN (for 15-day automated renewals): ").strip()
    except (KeyboardInterrupt, EOFError):
        print("\nOperation cancelled by user.")
        return 1

    if not pin:
        print("[WARNING] No PIN entered. Automated 15-day daily refresh will require re-login.")
        pin = None

    print("\nExchanging authorization code for tokens...")
    try:
        token = auth_service.exchange_code_for_token(auth_code=auth_code, pin=pin)
        print("\n[SUCCESS] Token generation and vault persistence completed!")
        print(f"  Access Token Expiry:  {token.access_token_expires_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        if token.refresh_token_expires_at:
            print(f"  Refresh Token Expiry: {token.refresh_token_expires_at.strftime('%Y-%m-%d %H:%M:%S UTC')} (15 days)")
        print(f"  Storage Backend:      {settings.AUTH_CREDENTIAL_STORAGE}")

        # Probe session viability
        print("\nValidating session against Fyers profile endpoint...")
        if auth_service.validate_session():
            print("[SUCCESS] Session validated successfully. System is ready for market data ingestion!")
        else:
            print("[NOTICE] Credentials saved, but profile probe did not return 'ok'. Check account status.")
        return 0
    except Exception as exc:
        print(f"\n[ERROR] Token generation failed: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(run_token_generation())

"""Command-line interface for Fyers API v3 authentication and session diagnostics.
Supports --login, --status, --refresh, and --preflight commands.
Ensures zero secret leakage to stdout or system logs.
"""

import argparse
import getpass
from pathlib import Path
import sys
import webbrowser

# Ensure project root is in sys.path when script is run directly
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import get_settings
from services.auth_service import AuthService
from services.vault import get_credential_vault
from scripts.generate_token import extract_auth_code_from_input


def handle_login(auth_service: AuthService) -> int:
    """Perform browser OAuth login and store tokens in secure vault."""
    auth_url = auth_service.get_auth_url()
    print("\nOpening browser for OAuth login:")
    print(f"  {auth_url}\n")

    try:
        webbrowser.open(auth_url)
    except Exception:
        pass

    try:
        raw_code = input("Enter redirected URL or auth code: ").strip()
    except (KeyboardInterrupt, EOFError):
        print("\nLogin cancelled.")
        return 1

    if not raw_code:
        print("Error: No authorization code entered.")
        return 1

    code = extract_auth_code_from_input(raw_code)

    try:
        pin = getpass.getpass("Enter your 4-digit Fyers PIN (for automated renewal): ").strip()
    except (KeyboardInterrupt, EOFError):
        print("\nLogin cancelled.")
        return 1

    try:
        token = auth_service.exchange_code_for_token(code, pin=pin or None)
        print("\nAuthentication successful!")
        print(f"Access token valid until:  {token.access_token_expires_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        if token.refresh_token_expires_at:
            print(f"Refresh token valid until: {token.refresh_token_expires_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        return 0
    except Exception as exc:
        print(f"\nAuthentication failed: {exc}")
        return 1


def handle_status(auth_service: AuthService) -> int:
    """Output authentication status and countdown timers without exposing secrets."""
    status = auth_service.get_token_status()
    is_valid = status["is_valid"]
    access_countdown = status["access_token_countdown"]
    refresh_days = status["refresh_days_remaining"]
    refresh_countdown = status["refresh_token_countdown"]
    is_near_expiry = status.get("is_near_expiry", False)
    countdown_timer = status.get("countdown_timer")

    status_label = "Active" if is_valid else "Expired / Inactive"

    # Canonical status line expected by acceptance criteria
    print(f"Status: {status_label} | Access Token Expires In: {access_countdown} | Refresh Token Valid: {refresh_countdown}")

    if is_near_expiry and countdown_timer:
        print(f"\n[CRITICAL WARNING] Refresh token is within 48 hours of expiration!")
        print(f"  Countdown to mandatory re-login: {countdown_timer}")
        print(f"  Action required: Run 'python scripts/auth_cli.py --login' to renew your 15-day session.")

    if not status["is_refresh_valid"] and status["has_refresh_token"]:
        print("\n[ALERT] 15-day refresh window has expired. Please run: python scripts/auth_cli.py --login")
    elif not status["has_refresh_token"]:
        print("\n[NOTE] No credentials found in vault. Please run: python scripts/auth_cli.py --login")

    return 0 if is_valid else 1


def handle_refresh(auth_service: AuthService) -> int:
    """Manually invoke refresh_token_if_needed."""
    print("Attempting to renew Fyers access token via stored refresh token...")
    try:
        refreshed = auth_service.refresh_token_if_needed()
        if refreshed:
            print("Access token renewed successfully.")
            handle_status(auth_service)
            return 0
        else:
            print("Current access token is still valid. Renewal not required.")
            handle_status(auth_service)
            return 0
    except Exception as exc:
        print(f"Token refresh failed: {exc}")
        return 1


def handle_preflight(auth_service: AuthService) -> int:
    """Execute pre-flight check at 15:40 IST before post-market sync."""
    print("Executing pre-flight session check (15:40 IST protocol)...")
    valid = auth_service.preflight_session_check()
    if valid:
        print("[PASSED] Pre-flight check succeeded. System is ready for market data ingestion.")
        return 0
    else:
        print("[FAILED] Pre-flight check failed. Downloader scheduled ingestion must be halted.")
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="NSE Quant Platform - Fyers Authentication CLI")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--login", action="store_true", help="Initiate browser OAuth login")
    group.add_argument("--status", action="store_true", help="Display token viability and expiration countdowns")
    group.add_argument("--refresh", action="store_true", help="Manually force access token renewal")
    group.add_argument("--preflight", action="store_true", help="Probe session viability (15:40 IST pre-flight check)")
    group.add_argument("--logout", action="store_true", help="Purge all credentials from secure vault")

    args = parser.parse_args()

    settings = get_settings()
    vault = get_credential_vault(settings.AUTH_CREDENTIAL_STORAGE)
    auth_service = AuthService(settings=settings, vault=vault)

    if args.login:
        return handle_login(auth_service)
    elif args.status:
        return handle_status(auth_service)
    elif args.refresh:
        return handle_refresh(auth_service)
    elif args.preflight:
        return handle_preflight(auth_service)
    elif args.logout:
        auth_service.logout()
        print("Logged out. Vault cleared.")
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())

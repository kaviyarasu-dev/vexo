---
name: fyers-api-integration
description: Best practices and exact logic for integrating with Fyers API v3 in Python.
---

# Fyers API v3 Integration Guide

## Overview
This skill provides the standard operating procedure for interacting with the Fyers API v3 within this project.

## Authentication & Secrets
- NEVER hardcode `client_id` or `secret_key`.
- Use the OS keyring to retrieve the `access_token` and `app_id`.
- The access token must be injected into the Fyers Model dynamically.

## Data Fetching
- **History API**: When fetching OHLCV data via `fyers.history()`, ensure the timezone is strictly converted to IST.
- Validate the response structure using Pydantic models before returning it to the Service layer.

## Error Handling
- Wrap API calls in `try-except` blocks.
- Check the `s` (status) field in the JSON response. If `s == "error"`, raise a custom `FyersAPIError`.
- Handle rate limits gracefully with backoff retries.

## Reference Code
```python
from fyers_apiv3 import fyersModel

def get_fyers_client(token: str, client_id: str) -> fyersModel.FyersModel:
    return fyersModel.FyersModel(
        client_id=client_id,
        is_async=False,
        token=token,
        log_path=""
    )
```

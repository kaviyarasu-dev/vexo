# Secrets Management Rule

1. **No .env Files for Secrets:** The standard practice of storing secrets in `.env` files is NOT secure enough for production trading apps. 
2. **OS Keyring:** Use the Python `keyring` library (`import keyring`) to securely store and retrieve the `client_id`, `secret_key`, and `access_token` securely from the operating system's credential manager.
3. **Commit Hooks:** The `.agents/hooks.json` automatically runs a script that blocks any tool call attempting to write files containing patterns like `client_id = "..."`. DO NOT try to bypass this.

import os
import sys
import json
import re

def main():
    # Antigravity sets AGY_HOOK_PAYLOAD env var with the tool call details
    payload_str = os.environ.get('AGY_HOOK_PAYLOAD')
    if not payload_str:
        return 0

    try:
        payload = json.loads(payload_str)
        tool_name = payload.get('tool_name', '')
        arguments = payload.get('arguments', {})
        
        # Check if the tool is write_to_file or multi_replace_file_content
        if tool_name in ['write_to_file', 'multi_replace_file_content', 'replace_file_content']:
            content = str(arguments)
            # Simple regex to catch hardcoded Fyers keys or common secret patterns
            secret_patterns = [
                r'client_id[\s=:]+[\'"][a-zA-Z0-9-]{10,}[:a-zA-Z0-9]*[\'"]',
                r'secret_key[\s=:]+[\'"][a-zA-Z0-9-]{10,}[\'"]',
                r'app_id[\s=:]+[\'"][a-zA-Z0-9-]{10,}[\'"]'
            ]
            
            for pattern in secret_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    print("SECURITY VIOLATION: Hardcoded API keys detected in code. Please use OS Keyring or .env.")
                    sys.exit(1) # Block the tool call

    except Exception as e:
        # Failsafe: allow execution if payload parsing fails, but log it
        print(f"Hook warning: {str(e)}", file=sys.stderr)
        
    return 0

if __name__ == '__main__':
    sys.exit(main())

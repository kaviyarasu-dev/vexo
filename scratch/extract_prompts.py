import re

runbook_path = r"d:\trading-app\AGENT_RUNBOOK.md"
output_path = r"d:\trading-app\PENDING_PROMPTS.md"

with open(runbook_path, "r", encoding="utf-8") as f:
    content = f.read()

# We want to extract the ``` blocks that contain the prompt. 
# The blocks are under headers like: ### Conversation 7 — Phase 06: ...

pending_phases = [
    "00", "06", "07", "08", "09", "10", "11", 
    "15", "12", "13", "14", "16", "17", "18", "19"
]

# We will iterate over the conversations
conversations = re.split(r'(### Conversation \d+ — Phase [^\n]+)', content)

output_lines = ["# Pending Phase Prompts\n\nHere are the exact prompts for the phases that are not yet complete. Copy each block and run it in a **fresh conversation**.\n\n"]

for i in range(1, len(conversations), 2):
    header = conversations[i]
    body = conversations[i+1]
    
    # Check if this header matches any of our pending phases
    # Phase 00 is in "Phase 00A & 00"
    is_pending = False
    for phase in pending_phases:
        # regex to match Phase XX or Phase XX & YY
        if re.search(r'\b' + phase + r'\b', header):
            is_pending = True
            break
            
    if is_pending:
        # Extract the prompt which is inside the first ``` block
        prompt_match = re.search(r'```(.*?)```', body, re.DOTALL)
        if prompt_match:
            prompt_text = prompt_match.group(1).strip()
            
            output_lines.append(f"## {header.replace('### ', '')}\n")
            output_lines.append(f"**Copy the prompt below:**\n\n```text\n{prompt_text}\n```\n\n---\n\n")

with open(output_path, "w", encoding="utf-8") as f:
    f.writelines(output_lines)
    
print("Successfully wrote PENDING_PROMPTS.md")

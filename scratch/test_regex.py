import asyncio
import re
import os

async def extract_prompts_from_runbook(filepath: str) -> dict:
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    phases = {}
    pattern = re.compile(r'### Conversation \d+ [^\w]+(Phase [^:]+).*?```\s*(?:/goal)?\n(.*?)```', re.DOTALL)
    matches = pattern.findall(content)
    
    for phase_name, prompt_text in matches:
        phases[phase_name.strip()] = f"/goal\n{prompt_text.strip()}"
        
    return phases

async def main():
    phases = await extract_prompts_from_runbook("d:/trading-app/AGENT_RUNBOOK.md")
    for name, text in phases.items():
        print(f"--- {name} ---")
        print(text[:100])
        print("...")

asyncio.run(main())

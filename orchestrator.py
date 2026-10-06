import asyncio
import re
import os
import sys
from dotenv import load_dotenv
from google.antigravity import Agent, LocalAgentConfig

# Load environment variables from .env file (including GEMINI_API_KEY)
load_dotenv()

EXPECTED_PHASES = [
    "Phase 00A & 00", "Phase 01", "Phase 02", "Phase 03", "Phase 04", 
    "Phase 05", "Phase 06", "Phase 07", "Phase 08", "Phase 09", 
    "Phase 10", "Phase 11", "Phase 15", "Phase 12", "Phase 13", 
    "Phase 14", "Phase 16", "Phase 17", "Phase 18", "Phase 19"
]

async def extract_prompts_from_runbook(filepath: str) -> dict:
    """Reads AGENT_RUNBOOK.md and extracts prompts block by block."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Simple regex to extract blocks that look like prompts (e.g. Conversation 1, Conversation 2)
    phases = {}
    
    # Finding sections like: ### Conversation 1 — Phase 00...
    # followed by a code block starting with /goal
    pattern = re.compile(r'### Conversation \d+ [^\w]+(Phase [^:]+).*?```\s*(?:/goal)?\n(.*?)```', re.DOTALL)
    matches = pattern.findall(content)
    
    for phase_name, prompt_text in matches:
        phases[phase_name.strip()] = f"/goal\n{prompt_text.strip()}"
        
    return phases

async def main():
    print("Reading AGENT_RUNBOOK.md...")
    runbook_path = "AGENT_RUNBOOK.md"
    phases = await extract_prompts_from_runbook(runbook_path)
    
    if not phases:
        sys.exit("CRITICAL ERROR: No phases found in Runbook. Check formatting.")

    print(f"Extracted {len(phases)} phases from the markdown.")

    # 1. STRICT VALIDATION: Ensure ALL expected phases were found
    for expected_phase in EXPECTED_PHASES:
        found = any(expected_phase in k for k in phases.keys())
        if not found:
            sys.exit(f"CRITICAL ERROR: Missing {expected_phase} in Runbook. Halting to prevent broken state.")

    print("SUCCESS: All 20 phases validated and present.")

    # 2. START INDEX: Set to 1 to skip 'Phase 00A & 00' which is already completed.
    # To run everything from the beginning, set this to 0.
    START_INDEX = 1
    
    phases_to_run = EXPECTED_PHASES[START_INDEX:]
    print(f"Starting execution from: {phases_to_run[0]}")

    for phase_name in phases_to_run:
        # Find the exact prompt key
        matching_key = next(k for k in phases.keys() if phase_name in k)
        prompt = phases[matching_key]
        
        print(f"\n{'='*50}\nStarting {matching_key}...\n{'='*50}")
        
        if "--dry-run" in sys.argv:
            print(f"[DRY-RUN] Would have executed this prompt:\n{prompt[:200]}...\n")
            print(f"Finished {matching_key}. Moving to next phase...")
            continue
            
        async with Agent(LocalAgentConfig()) as agent:
            # We append a strict instruction to enforce GOAL_COMPLETE
            full_prompt = f"{prompt}\n\n[SYSTEM ORCHESTRATOR]: Execute this phase. You MUST reply with <!-- GOAL_COMPLETE --> when you have successfully finished the entire task."
            
            response = await agent.chat(full_prompt)
            output_text = await response.text()
            
            print(f"Agent Output for {matching_key}:")
            print(output_text)
            
            # 3. STRICT HALT: Check if the phase actually succeeded
            if "<!-- GOAL_COMPLETE -->" not in output_text:
                sys.exit(f"CRITICAL ERROR: {matching_key} did not complete successfully (Missing GOAL_COMPLETE). Halting execution to prevent cascading failures.")
            
        print(f"Finished {matching_key} successfully. Moving to next phase...")
        
    print("\nAll selected phases completed perfectly!")

if __name__ == "__main__":
    asyncio.run(main())

import asyncio
import re
import os
import sys
import json
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

    phases = {}
    pattern = re.compile(r'### Conversation \d+ [^\w]+(Phase [^:]+).*?```\s*(?:/goal)?\n(.*?)```', re.DOTALL)
    matches = pattern.findall(content)
    
    for phase_name, prompt_text in matches:
        phases[phase_name.strip()] = f"/goal\n{prompt_text.strip()}"
        
    return phases

def get_handoff_content() -> str:
    path = "plan/HANDOFF.md"
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return ""

def check_phase09_gate() -> tuple[bool, str]:
    path = "artifacts/m1_benchmark_results.json"
    if not os.path.exists(path):
        return False, f"File {path} not found."
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if data.get("overall_status") == "PASSED":
            return True, ""
        return False, f"overall_status is '{data.get('overall_status')}', expected 'PASSED'."
    except Exception as e:
        return False, f"Error parsing JSON: {str(e)}"

async def chat_with_retry(agent, prompt: str, max_retries: int = 3) -> str:
    for attempt in range(max_retries):
        try:
            response = await agent.chat(prompt)
            return await response.text()
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            print(f"Network/API Error during agent.chat: {e}. Retrying {attempt + 1}/{max_retries} in 10s...")
            await asyncio.sleep(10)

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
        matching_key = next(k for k in phases.keys() if phase_name in k)
        prompt = phases[matching_key]
        
        print(f"\n{'='*50}\nStarting {matching_key}...\n{'='*50}")
        
        if "--dry-run" in sys.argv:
            print(f"[DRY-RUN] Would have executed this prompt:\n{prompt[:200]}...\n")
            print(f"Finished {matching_key}. Moving to next phase...")
            continue
            
        # Pre-flight check for Stage 4 Hard Gate
        if "Phase 10" in phase_name:
            passed, err_msg = check_phase09_gate()
            if not passed:
                sys.exit(f"CRITICAL ERROR: Phase 09 HARD GATE must pass before starting Stage 4 (Phase 10)! {err_msg}. Halting.")
            print("SUCCESS: Phase 09 Hard Gate verified before starting Phase 10!")

        old_handoff = get_handoff_content()
            
        async with Agent(LocalAgentConfig()) as agent:
            # We append a strict instruction to enforce GOAL_COMPLETE
            full_prompt = f"{prompt}\n\n[SYSTEM ORCHESTRATOR]: Execute this phase. You MUST reply with <!-- GOAL_COMPLETE --> when you have successfully finished the entire task."
            
            output_text = await chat_with_retry(agent, full_prompt)
            
            print(f"Agent Output for {matching_key} (Turn 1):")
            print(output_text)
            
            # The autonomous self-healing loop
            turn = 2
            while True:
                # 1. Check for failure
                if "<!-- GOAL_FAILED -->" in output_text or "permanently blocked" in output_text.lower():
                    sys.exit(f"CRITICAL ERROR: {matching_key} reported it is blocked. Halting execution to prevent cascading failures.")
                    
                if turn > 20:
                    sys.exit(f"CRITICAL ERROR: {matching_key} exceeded maximum allowed turns (20). Agent might be stuck. Halting.")
                    
                # 2. Check for GOAL_COMPLETE
                if "<!-- GOAL_COMPLETE -->" not in output_text:
                    print(f"[{matching_key}] Goal not complete yet. Forcing agent to continue (Turn {turn})...")
                    continuation_prompt = "You did not include <!-- GOAL_COMPLETE --> in your response. Please continue executing until the goal is met, or state why you are permanently blocked."
                    output_text = await chat_with_retry(agent, continuation_prompt)
                    turn += 1
                    continue
                
                # 3. GOAL_COMPLETE is present! Validate Handoff
                new_handoff = get_handoff_content()
                old_count = old_handoff.upper().count("STATUS: DONE")
                new_count = new_handoff.upper().count("STATUS: DONE")
                
                if new_count <= old_count:
                    print(f"[{matching_key}] Agent forgot to update HANDOFF.md. Reminding agent (Turn {turn})...")
                    handoff_prompt = "You output <!-- GOAL_COMPLETE -->, but you forgot to append a new 'STATUS: DONE' entry for this phase in `plan/HANDOFF.md` as required. Please append it now and reply with <!-- GOAL_COMPLETE --> again."
                    output_text = await chat_with_retry(agent, handoff_prompt)
                    turn += 1
                    continue
                
                # If we reach here, GOAL_COMPLETE is present AND Handoff is successfully updated!
                break

        print(f"Finished {matching_key} successfully. Moving to next phase...")
        
    print("\nAll selected phases completed perfectly!")

if __name__ == "__main__":
    asyncio.run(main())

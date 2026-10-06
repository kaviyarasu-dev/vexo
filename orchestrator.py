import asyncio
import re
from google.antigravity import Agent, LocalAgentConfig

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
        print("No phases found in Runbook. Check formatting.")
        return

    print(f"Found {len(phases)} phases to execute.")

    # Execute Phase 00, 01, 02 (Stage 1) sequentially as an example
    target_phases = [
        "Phase 00A & 00", 
        "Phase 01", 
        "Phase 02 & 03"
    ]

    for phase_name in target_phases:
        # Find the matching prompt
        matching_key = next((k for k in phases.keys() if phase_name in k), None)
        if not matching_key:
            print(f"Skipping {phase_name} - Not found in extracted prompts.")
            continue
            
        prompt = phases[matching_key]
        print(f"\n{'='*50}\nStarting {matching_key}...\n{'='*50}")
        
        # Instantiate a FRESH agent for this phase (enforcing "One Fresh Conversation" rule)
        async with Agent(LocalAgentConfig()) as agent:
            # We append a system reminder to ensure it stops when the goal is complete
            full_prompt = f"{prompt}\n\n[SYSTEM ORCHESTRATOR]: Execute this phase. Reply with <!-- GOAL_COMPLETE --> when done."
            
            response = await agent.chat(full_prompt)
            print(f"Agent Output for {matching_key}:")
            print(await response.text())
            
        print(f"Finished {matching_key}. Moving to next phase...")
        
    print("\nAll selected phases completed!")

if __name__ == "__main__":
    asyncio.run(main())

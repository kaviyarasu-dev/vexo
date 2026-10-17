# Instructions for Plan Runner Sessions

1. **Scope:** Execute only the plan assigned to your session. Do not work ahead or modify other plans.
2. **Autonomous Execution:** Never prompt or ask the user questions. If blocked, write the root cause and attempted remediations to `BLOCKED.md` in this plan folder and terminate gracefully.
3. **Git State:** Never commit, push, create branches, or alter git tracking state.
4. **Resumption & Idempotence:** Check current code state before making edits.
5. **Project Standards:** Adhere strictly to the project rules in `.agents/GEMINI.md`:
   - Single-writer DuckDB process (`uvicorn workers=1`).
   - Use independent cursors (`conn.cursor()`) for read queries.
   - All timestamps and schedules align strictly with Indian Standard Time (IST).
   - Zero secrets in code; never hardcode API keys or credentials.
6. **Checkpoints:** After completing each numbered step (`### Step N: ...`), run the checkpoint verify command from your step prompt. Proceed to the next step only when it exits 0.
7. **Acceptance:** Execute all verify commands in the plan's Acceptance section before reporting completion.
8. **Protected Paths:** Never edit `manifest.json`, `HANDOFF.md`, `INSTRUCTIONS.md`, or anything under `.agents/` or `.gemini/`.

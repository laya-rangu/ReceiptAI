# ReceiptAI working agreement

## User-approved workflow

- Work one numbered implementation task at a time and make each result easy to review.
- Explain what changed, the technologies involved, the checks run, known gaps, and how the user can verify it.
- Commit and push each completed, checked task to `https://github.com/laya-rangu/ReceiptAI`.
- Stop at the review checkpoint before starting the next task unless the user explicitly requests continued work.
- The initial scaffold predates this workflow. Treat it as draft code; its presence is not proof that its associated roadmap tasks are complete.
- Do not spawn additional agents unless the user explicitly requests delegation.

## Repository boundaries

- Repository root: this ReceiptAI folder. A separate, unrelated repository exists above it in the user's home directory.
- Before staging or pushing, verify `git rev-parse --show-toplevel` and `git remote -v` refer to this project.
- Stage only intended project files. Never commit `.env` files, API keys, local receipt files, databases, `.venv`, `node_modules`, or generated build output.
- Never force push or overwrite remote history.

## Checks

- Backend: from `backend`, run `../.venv/Scripts/python.exe -m pytest -q` and `../.venv/Scripts/python.exe -m ruff check app tests` on Windows.
- Frontend: from `frontend`, run `npm run typecheck` and `npm run build` when relevant.
- Browser and end-to-end coverage must be reported separately from compilation and API tests.
- Do not claim live extraction, PostgreSQL, Redis, Supabase, semantic search, MCP, A2A, or cloud deployment are verified without actually exercising them.
- Follow the numbered tasks in `docs/TASKS.md`; record results in `docs/CHECKPOINTS.md`.

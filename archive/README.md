# archive/ — unmaintained

This directory holds earlier prototypes that are **no longer built, tested, or released**.
They are kept for historical reference only.

| Path | What it was |
|---|---|
| `backend/` | A FastAPI SaaS API (`codeguard-backend`, proprietary license, Postgres + Redis) wrapping its *own* multi-language analyzer, an sklearn AI-code detector, and an OpenAI LLM layer. Shares no code with the CLI. The persistence layer (`app/models/`) was never committed, so it does not run as-is. |
| `frontend/` | A Create-React-App dashboard (React 18, MUI 5) targeting the backend's `/api/v1`. |
| `frontendv2/` | A Vite + React 19 "workbench" (editor + results + AI chat) targeting `/api/v2`. |
| `demo_test.py` | A Rich-console integration script that drives a running backend at `localhost:8000`. |

**The current, supported tool is the `codeguard` CLI in [`../src/codeguard/`](../src/codeguard/).**
It is a pure-Python, offline, multi-language static analyzer with no server, database, or
network dependency. See the repository [README](../README.md).

If a REST API or dashboard is revived in the future it will be a thin layer over the CLI's
public library API, not a continuation of this code.

# AutoSRE — A Self-Healing Cloud Operations Agent

AutoSRE is an **agentic AI Site Reliability Engineer** that autonomously detects, diagnoses, and remediates cloud service incidents by reasoning over logs and performing UI actions using **Amazon Nova** models.

Instead of only alerting engineers, AutoSRE:

- Interprets system alerts  
- Identifies root cause  
- Executes corrective actions through UI automation  
- Verifies recovery  
- Publishes a post-mortem to Slack  

**Goal:** Reduce MTTR from ~45 minutes → &lt; 2 minutes.

---

## Project layout

```
AutoSRE/
├── dashboard/             # Operations dashboard (Phase 2): login, services, rollback
│   ├── app.py             # FastAPI app + API (health, rollback, services)
│   └── static/            # login.html, services.html, service.html
├── src/autosre/
│   ├── __init__.py
│   ├── config.py           # Settings from env
│   ├── models.py           # IncidentEvent, Diagnosis, PlannedAction, etc.
│   ├── workflow.py         # Closed-loop orchestration
│   ├── cli.py              # Entry point (autosre --demo)
│   ├── incident_detection/ # Alert ingestion (simulated CloudWatch)
│   ├── log_storage/        # Logs + deployment history for RCA
│   ├── reasoning_agent/    # Root cause analysis (Nova Pro/Lite)
│   ├── planner/            # Diagnosis → UI action sequence
│   ├── ui_automation/      # Nova Act — dashboard actions
│   ├── recovery_verification/
│   └── slack_reporter/     # Post-mortem to Slack
├── tests/
├── pyproject.toml
├── .env.example
└── README.md
```

---

## Setup

1. **Clone and create venv**

   ```bash
   python -m venv .venv
   .venv\Scripts\activate   # Windows
   # source .venv/bin/activate  # macOS/Linux
   pip install -e .
   ```

2. **Environment**

   Copy `.env.example` to `.env` and set:

   - `AWS_REGION` (and optional AWS credentials for Nova)
   - `SLACK_BOT_TOKEN` and `SLACK_CHANNEL_ID` for post-mortems
   - `OPERATIONS_DASHBOARD_URL` for UI automation target (default: http://localhost:3000)

---

## Operations dashboard (demo target)

Start the dashboard so the agent (Nova Act) has a UI to drive:

```bash
cd dashboard
python -m uvicorn app:app --host 0.0.0.0 --port 3000
# or: python app.py
```

Then open http://localhost:3000. Use **Demo login**, open **Services** → **Checkout** → **Deployments** tab → **Rollback** on v1.4.1. The **GET /api/health** endpoint returns `degraded` until a rollback is executed, then `healthy` (for recovery verification).

---

## CI/CD

GitHub Actions runs on push and pull requests to `main` (and the dashboard branch):

- **Test:** Python 3.11 and 3.12; `pip install -e ".[dev]"` and `pytest tests/ -v`
- **Lint:** `ruff check` and `ruff format --check` on `src`, `dashboard`, and `tests`

Run locally:

```bash
pip install -e ".[dev]"
pytest tests/ -v
ruff check src dashboard tests
ruff format --check src dashboard tests
```

---

## Run

- **Single incident run (default: latency_spike)**

  ```bash
  autosre
  # or
  python -m autosre
  ```

- **Demo scenario (deterministic)**

  ```bash
  autosre --demo
  ```

  Runs one full cycle (alert → analyze → plan → act → verify → report) and prints the result. Optional narrative text can be supplied via a local file (see repo; not committed).
---

## Architecture (from PRD)

| Component              | Role                          |
|------------------------|-------------------------------|
| Incident Simulator     | CloudWatch mock; emits `IncidentEvent` |
| Log Storage            | Logs + deployment history for Nova     |
| Reasoning Agent (Nova) | Root cause → `Diagnosis` + recommended action |
| Planner                | `Diagnosis` → list of `PlannedAction`  |
| UI Action Agent (Nova Act) | Executes actions on operations dashboard |
| Recovery Monitor       | Verifies health after remediation       |
| Slack Reporter         | Posts post-mortem report                |

---

## Status

- **Scaffolding:** Package layout, config, models, and stub implementations for all components.
- **Phase 2:** Operations dashboard (FastAPI + static HTML) with login, services, Deployments panel, Rollback, and /api/health for recovery verification.
- **Phase 5:** Slack reporter: real publish via `slack_sdk.WebClient` and Block Kit; fallback text; no token/channel → skip.
- **Phase 6:** Incident/log storage: `LogStore` records incidents, append_log/append_deployment, get_logs_for_incident and get_deployment_history with stub fallbacks; optional file persistence via `LOG_STORAGE_DATA_DIR`.
- **Phase 7:** Workflow hardening: logging, try/except around record_incident/reasoning/verify/Slack; reasoning retries (`REASONING_MAX_RETRIES`); post-mortem on escalation, UI failure, or verify exception; config `recovery_verify_timeout_seconds`.
- **Phase 8:** Demo script: `autosre --demo` runs deterministic scenario (incident id `inc-demo0001`). Narrative text is loaded from `demo_narrative.txt` when present (file is gitignored); otherwise minimal fallback text is used. CLI exits 0 on success and 1 on failure.

---

## License

MIT.

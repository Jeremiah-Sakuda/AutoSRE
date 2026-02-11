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
   - `OPERATIONS_DASHBOARD_URL` for UI automation target

---

## Run

- **Single incident run (default: latency_spike)**

  ```bash
  autosre
  # or
  python -m autosre
  ```

- **Demo scenario (deterministic for judges)**

  ```bash
  autosre --demo
  ```

  Flow: dashboard shows degraded service → alert fires → agent analyzes logs → states “Bad deployment detected” → navigates dashboard → clicks rollback → metrics recover → Slack report.

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
- **Next:** Wire real Amazon Nova (reasoning + Act) APIs, optional operations dashboard, and real Slack publish.

---

## License

MIT.

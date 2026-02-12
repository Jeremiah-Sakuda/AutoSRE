# AutoSRE

**Self-healing cloud operations agent** — detect, diagnose, remediate, and report incidents using AI reasoning and automation.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## Overview

AutoSRE is an **agentic AI** system that closes the loop from alert to recovery: it consumes incidents (simulated or from CloudWatch), reasons over logs and deployment history with **Amazon Nova**, plans corrective actions, executes them via UI automation (**Nova Act**) or direct AWS APIs, verifies recovery, and publishes a post-mortem to **Slack**.

**Goal:** Reduce mean time to recovery (MTTR) from tens of minutes to under two minutes for common failure modes.

| Step | What AutoSRE does |
|------|-------------------|
| **Detect** | Ingest one incident (simulated or CloudWatch alarm). |
| **Analyze** | Root-cause analysis with Nova over logs and deployment history → diagnosis and recommended action. |
| **Plan** | Map diagnosis to concrete actions (e.g. rollback, restart, scale up). |
| **Execute** | Run actions on an operations dashboard (Nova Act) or via AWS (e.g. Lambda alias rollback). |
| **Verify** | Poll health endpoint or CloudWatch until healthy or timeout. |
| **Report** | Publish a post-mortem to Slack (when configured). |

---

## Features

- **Dual run modes** — Simulated incidents + demo dashboard, or real AWS (CloudWatch alarms + Lambda rollback).
- **Pluggable reasoning** — Amazon Nova (Bedrock) for root-cause analysis, or stub for CI/local runs without AWS.
- **UI and API remediation** — Nova Act for browser-based dashboards, or direct boto3 for Lambda alias rollback.
- **Recovery verification** — Configurable health polling with timeout and recovery-time tracking.
- **Slack post-mortems** — Block Kit reports with timeline, root cause, and action taken.
- **Optional persistence** — File-backed incident/log storage for RCA context.

---

## Requirements

- **Python 3.11+** (3.12 recommended)
- **Optional:** AWS account and Bedrock access for Nova reasoning
- **Optional:** Slack app (Bot Token + channel) for post-mortems
- **Optional:** Nova Act API key for real UI automation (otherwise stub)

---

## Quick Start

```bash
# Clone and enter project
git clone <repository-url>
cd AutoSRE

# Virtual environment
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate   # macOS / Linux

# Install (editable + dev tools)
pip install -e ".[dev]"

# Configure (copy and edit)
cp .env.example .env
# Set OPERATIONS_DASHBOARD_URL and optionally AWS/Slack

# Start demo dashboard (separate terminal)
cd dashboard && python -m uvicorn app:app --host 0.0.0.0 --port 3000

# Run one cycle (simulated incident → stub reasoning → stub UI → verify → report)
autosre
```

**Deterministic demo** (fixed incident ID, optional narrative):

```bash
autosre --demo
```

Exit code: `0` on successful recovery, `1` on failure or escalation.

---

## Installation

| Method | Command |
|--------|---------|
| Editable (recommended) | `pip install -e .` |
| With dev dependencies | `pip install -e ".[dev]"` |
| From repo root | Ensures `autosre` CLI and `python -m autosre` work |

The CLI is registered as `autosre`; use `autosre --version` to confirm.

---

## Configuration

All configuration is via **environment variables** (and optionally a `.env` file in the project root). Copy `.env.example` to `.env` and adjust.

### Essential

| Variable | Description | Default |
|----------|-------------|--------|
| `OPERATIONS_DASHBOARD_URL` | Base URL of the operations dashboard | `http://localhost:3000` |
| `REASONING_USE_BEDROCK` | Use Amazon Nova for RCA (`true`/`false`) | `false` |
| `UI_STUB` | Stub UI automation only (`true`/`false`) | `true` |

### AWS (Bedrock / real integration)

| Variable | Description | Default |
|----------|-------------|--------|
| `AWS_REGION` | AWS region | `us-east-1` |
| `NOVA_MODEL_ID` | Bedrock model for reasoning | `us.amazon.nova-2-lite-v1:0` |
| `USE_AWS_INTEGRATION` | Use CloudWatch + Lambda instead of dashboard | `false` |
| `CLOUDWATCH_ALARM_NAMES` | Comma-separated alarm names | — |
| `LAMBDA_FUNCTION_NAME` | Lambda name for rollback | — |
| `LAMBDA_ALIAS_NAME` | Alias to roll back (e.g. `live`) | `live` |
| `LAMBDA_LOG_GROUP_NAME` | Log group for RCA (optional) | — |

### Slack

| Variable | Description |
|----------|-------------|
| `SLACK_BOT_TOKEN` | Bot token (e.g. `xoxb-...`) |
| `SLACK_CHANNEL_ID` | Channel ID (e.g. `C...`) |

### Other

| Variable | Description | Default |
|----------|-------------|--------|
| `METRICS_URL` | Health URL for verification (empty = dashboard + `/api/health`) | — |
| `LOG_STORAGE_DATA_DIR` | Directory for incident/log persistence | — |
| `REASONING_MAX_RETRIES` | Retries for reasoning agent | `2` |
| `RECOVERY_VERIFY_TIMEOUT_SECONDS` | Max wait for healthy | `120.0` |
| `NOVA_ACT_API_KEY` | API key for Nova Act (when not using stub) | — |

See `.env.example` for the full list and comments.

---

## Usage

### CLI

| Command | Description |
|---------|-------------|
| `autosre` | One cycle: default incident type `latency_spike`, generated ID. |
| `autosre --demo` | Deterministic run with incident `inc-demo0001`; optional `demo_narrative.txt` in cwd. |
| `autosre --incident-type <type>` | One cycle with given type: `latency_spike`, `crash_loop`, `memory_leak`, `deployment_failure`. |
| `autosre --version` | Print version. |

### Demo narrative (optional)

For `autosre --demo`, create `demo_narrative.txt` in the current directory (gitignored) with `[section]` blocks:

- `[intro]` — Title or intro line  
- `[scenario]` — Scenario description  
- `[dashboard_note]` — Shown if dashboard health check fails  
- `[running]` — Text while workflow runs  
- `[success]` / `[failure]` — Result messages  

If the file is missing, minimal default text is used.

### Operations dashboard (demo target)

The included dashboard is a **demo UI** for the agent (or manual testing): login, list services, open a service, and trigger a rollback. It is **not** suitable for production.

**Security:** The dashboard has **no real authentication** (any credentials accepted) and **no authorization** on API routes. Use only locally; do not expose to the internet.

**Start:**

```bash
cd dashboard
python -m uvicorn app:app --host 0.0.0.0 --port 3000
```

Then open **http://localhost:3000**. Flow: Login → Services → Service detail → Deployments tab → Rollback.  
`GET /api/health` returns `{"status": "degraded"}` until a rollback is executed, then `{"status": "healthy"}`.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/`, `/services`, `/services/{id}` | Static pages (login, services, service detail). |
| POST | `/api/login` | Demo login (redirects to `/services`). |
| GET | `/api/services`, `/api/services/{id}`, `/api/services/{id}/deployments` | JSON data. |
| POST | `/api/services/{id}/rollback` | Body: `{"to_version": "v1.4.1"}`. |
| GET | `/api/health` | `{"status": "degraded" \| "healthy"}`. |

---

## Real AWS integration

Set `USE_AWS_INTEGRATION=true` and configure:

- **Incidents** — CloudWatch alarms (optionally filtered by `CLOUDWATCH_ALARM_NAMES`) in `ALARM` state.
- **Logs** — CloudWatch Logs from `LAMBDA_LOG_GROUP_NAME` (or default `/aws/lambda/<LAMBDA_FUNCTION_NAME>`) for the incident window.
- **Remediation** — Lambda alias rollback: alias (e.g. `live`) is pointed to the previous published version.
- **Verification** — Poll CloudWatch until alarm(s) return to `OK` or timeout.

**Minimal IAM:** `cloudwatch:DescribeAlarms`, `logs:FilterLogEvents`, `lambda:GetAlias`, `lambda:ListVersionsByFunction`, `lambda:UpdateAlias`.

**Setup:** Deploy a Lambda with at least two versions and an alias; create a CloudWatch alarm (e.g. on Errors); set the env vars above; run `autosre`.

---

## Workflow (single run)

1. **Detect** — One incident from stream (simulated or CloudWatch).
2. **Store** — Record incident in `LogStore`; load logs and deployment history for the service.
3. **Analyze** — Reasoning agent (Nova or stub) → `Diagnosis` (summary, confidence, recommended action). Retries on failure; fallback to escalate.
4. **Plan** — Planner → list of `PlannedAction` (e.g. navigate, click_rollback). Escalate → empty list.
5. **Execute** — UI agent (stub or Nova Act) or AWS executor runs actions.
6. **Verify** — Recovery monitor polls health until `healthy` or `RECOVERY_VERIFY_TIMEOUT_SECONDS`.
7. **Report** — Post-mortem to Slack (if token and channel set). Success only when status is `recovered`.

---

## Project structure

```
AutoSRE/
├── dashboard/                 # Demo operations UI (FastAPI + static HTML)
│   ├── app.py
│   └── static/                # login, services, service detail
├── src/autosre/
│   ├── cli.py                 # Entry point: autosre, --demo, --incident-type
│   ├── config.py              # Pydantic settings from env
│   ├── models.py              # IncidentEvent, Diagnosis, PlannedAction, PostMortemReport, etc.
│   ├── workflow.py            # Closed loop: detect → analyze → plan → act → verify → report
│   ├── incident_detection/    # Simulated or CloudWatch incident stream
│   ├── log_storage/           # Incidents, logs, deployment history (optional file persistence)
│   ├── reasoning_agent/       # Root-cause analysis (Nova or stub)
│   ├── planner/               # Diagnosis → PlannedAction list
│   ├── ui_automation/         # Nova Act or stub
│   ├── remediation/           # AWS executor (Lambda rollback)
│   ├── recovery_verification/  # Health polling / CloudWatch
│   └── slack_reporter/        # Post-mortem to Slack
├── tests/
├── scripts/                   # e.g. CloudFormation demo
├── pyproject.toml
├── requirements.txt
└── .env.example
```

---

## Development

**Tests:**

```bash
pytest tests/ -v
```

**Lint / format:**

```bash
ruff check src dashboard tests
ruff format --check src dashboard tests
```

**CI (GitHub Actions):** On push/PR to `main` (and push to `phase-2-operations-dashboard`): matrix Python 3.11 and 3.12, `pip install -e ".[dev]"`, `pytest`, then `ruff check` and `ruff format --check`.

---

## License

MIT.

# AutoSRE — A Self-Healing Cloud Operations Agent

AutoSRE is an **agentic AI Site Reliability Engineer** that autonomously detects, diagnoses, and remediates cloud service incidents by reasoning over logs and performing UI actions using **Amazon Nova** models.

Instead of only alerting engineers, AutoSRE:

- **Interprets** system alerts (e.g. latency spikes, crash loops)
- **Identifies** root cause using logs and deployment history (Nova reasoning)
- **Plans** concrete UI actions (e.g. rollback, restart, scale up)
- **Executes** those actions on an operations dashboard (Nova Act or stub)
- **Verifies** recovery by polling a health endpoint
- **Publishes** a post-mortem to Slack (when configured)

**Goal:** Reduce MTTR from ~45 minutes to under 2 minutes.

---

## Table of contents

- [Prerequisites](#prerequisites)
- [Project layout](#project-layout)
- [Setup](#setup)
- [Environment variables](#environment-variables)
- [Operations dashboard (demo target)](#operations-dashboard-demo-target)
- [Running AutoSRE](#running-autosre)
- [Real AWS demo (CloudWatch + Lambda)](#real-aws-demo-cloudwatch--lambda)
- [Workflow (what happens in a run)](#workflow-what-happens-in-a-run)
- [CI/CD](#cicd)
- [Architecture](#architecture)
- [Status](#status)
- [License](#license)

---

## Prerequisites

- **Python 3.11 or 3.12** (recommended; 3.13 may work)
- **pip** and optionally a virtual environment
- For **real Nova reasoning**: AWS account, Bedrock access, and credentials (or env vars)
- For **real Slack post-mortems**: Slack app with Bot Token and a channel ID
- For **real UI automation**: Nova Act SDK and API key (otherwise stub mode is used)

---

## Project layout

```
AutoSRE/
├── dashboard/                  # Operations dashboard (Phase 2)
│   ├── app.py                  # FastAPI app: login, services, rollback, health API
│   └── static/
│       ├── login.html          # Demo login page
│       ├── services.html       # Services list (Checkout, Payments)
│       └── service.html        # Service detail: Deployments tab, Rollback
├── src/autosre/
│   ├── __init__.py
│   ├── config.py               # Settings from environment (.env)
│   ├── models.py               # IncidentEvent, Diagnosis, PlannedAction, PostMortemReport, etc.
│   ├── workflow.py             # Closed-loop: detect → analyze → plan → act → verify → report
│   ├── cli.py                  # Entry point: autosre, autosre --demo, autosre --incident-type
│   ├── incident_detection/     # Simulated CloudWatch-style alert stream
│   │   └── simulator.py        # get_incident_stream(), DEMO_INCIDENT_ID
│   ├── log_storage/            # Incidents, logs, deployment history for RCA
│   │   └── store.py            # LogStore: record_incident, get_logs_for_incident, get_deployment_history
│   ├── reasoning_agent/        # Root cause analysis (Bedrock Nova or stub)
│   │   ├── agent.py            # ReasoningAgent.analyze() → Diagnosis
│   │   └── prompts.py           # SYSTEM_PROMPT, build_user_prompt
│   ├── planner/                # Diagnosis → list of UI actions
│   │   └── agent.py            # PlannerAgent.plan() → list[PlannedAction]
│   ├── ui_automation/          # Executes planned actions (Nova Act or stub)
│   │   ├── agent.py            # UIActionAgent.execute()
│   │   └── prompts.py          # actions_to_prompts (natural-language for Nova Act)
│   ├── recovery_verification/ # Polls health endpoint until healthy or timeout
│   │   └── monitor.py          # RecoveryMonitor.verify(), get_recovery_time_seconds()
│   └── slack_reporter/        # Post-mortem to Slack (Block Kit + text fallback)
│       └── reporter.py         # SlackReporter.publish()
├── tests/                      # Pytest tests for workflow, dashboard, storage, agents, etc.
├── pyproject.toml              # Package metadata, dependencies, scripts (autosre), ruff, pytest
├── requirements.txt            # Pip-installable deps (canonical install: pip install -e .)
├── .env.example                # Template for .env (copy and fill in)
└── README.md
```

---

## Setup

1. **Clone the repository** (if not already):

   ```bash
   git clone <repo-url>
   cd AutoSRE
   ```

2. **Create and activate a virtual environment**:

   ```bash
   python -m venv .venv
   .venv\Scripts\activate   # Windows
   # source .venv/bin/activate   # macOS/Linux
   ```

3. **Install the package in editable mode** (recommended so the `autosre` CLI is available):

   ```bash
   pip install -e .
   ```

   For development (tests, linting):

   ```bash
   pip install -e ".[dev]"
   ```

4. **Configure environment**:

   Copy `.env.example` to `.env` in the project root and set at least:

   - `OPERATIONS_DASHBOARD_URL` — URL of the dashboard the agent will drive (default `http://localhost:3000`).

   Optionally set AWS and Slack variables if you want real Bedrock reasoning and Slack post-mortems; see [Environment variables](#environment-variables).

---

## Environment variables

All settings are loaded from the environment (and from a `.env` file in the project root if present). Names are uppercase with underscores.

| Variable | Description | Default |
|----------|-------------|--------|
| **AWS / Bedrock** | | |
| `AWS_REGION` | AWS region for Bedrock | `us-east-1` |
| `AWS_ACCESS_KEY_ID` | Optional; omit to use default credential chain | — |
| `AWS_SECRET_ACCESS_KEY` | Optional; omit to use default credential chain | — |
| `NOVA_MODEL_ID` | Bedrock model for root-cause analysis | `us.amazon.nova-2-lite-v1:0` |
| `BEDROCK_READ_TIMEOUT_SECONDS` | Timeout for Bedrock Converse API | `300` |
| `REASONING_USE_BEDROCK` | Set to `true` to call Nova; `false` uses stub (no AWS) | `false` |
| **Slack** | | |
| `SLACK_BOT_TOKEN` | Bot token (e.g. `xoxb-...`) for post-mortem channel | `""` |
| `SLACK_CHANNEL_ID` | Channel ID (e.g. `C...`) for post-mortems | `""` |
| **Dashboard / demo** | | |
| `OPERATIONS_DASHBOARD_URL` | Base URL of the operations dashboard | `http://localhost:3000` |
| `METRICS_URL` | Health URL for recovery verification; if empty, derived from `OPERATIONS_DASHBOARD_URL` + `/api/health` | `""` |
| `INCIDENT_SOURCE` | Alert source (e.g. `simulated`) | `simulated` |
| **Real AWS integration** | | |
| `USE_AWS_INTEGRATION` | Set to `true` to use CloudWatch + Lambda instead of the dashboard (real API path) | `false` |
| `CLOUDWATCH_ALARM_NAMES` | Comma-separated alarm names to treat as incident source | `""` |
| `LAMBDA_FUNCTION_NAME` | Lambda function name for rollback demo (used when `USE_AWS_INTEGRATION=true`) | `""` |
| `LAMBDA_ALIAS_NAME` | Lambda alias to roll back (e.g. `live`, `prod`) | `live` |
| `LAMBDA_LOG_GROUP_NAME` | CloudWatch Logs group for RCA (default: `/aws/lambda/<LAMBDA_FUNCTION_NAME>`) | `""` |
| **Log storage** | | |
| `LOG_STORAGE_DATA_DIR` | Directory for persisting incidents/logs/deployments; empty = in-memory only | `""` |
| **Workflow** | | |
| `REASONING_MAX_RETRIES` | Number of retries for reasoning agent on failure | `2` |
| `RECOVERY_VERIFY_TIMEOUT_SECONDS` | Max seconds to wait for healthy before declaring NOT_RECOVERED | `120.0` |
| **UI automation (Nova Act)** | | |
| `UI_STUB` | `true` = log actions only (no browser); `false` = use Nova Act when configured | `true` |
| `NOVA_ACT_API_KEY` | API key for Nova Act (when not using stub) | `""` |

---

## Operations dashboard (demo target)

The dashboard is a **demo UI** that the agent (or a human) can use to view services, deployments, and trigger rollbacks. It is **not** a production-ready app.

**Security warning:** The dashboard has **no real authentication**: any username/password is accepted at login, and all API routes are unauthenticated. It is intended for **local demo only**. Do not expose it to the internet or use in production without adding authentication and authorization (and consider CSRF protection if you add session-based auth).

### Starting the dashboard

From the project root:

```bash
cd dashboard
python -m uvicorn app:app --host 0.0.0.0 --port 3000
```

Or:

```bash
python app.py
```

Then open **http://localhost:3000** in a browser.

### Dashboard flow

1. **Login** — Use "Demo login" (e.g. username `demo`, password `demo`). You are redirected to `/services`.
2. **Services** — List of services (e.g. Checkout, Payments). Click a service to open its detail page.
3. **Service detail** — Tabs: Overview, Deployments, Instances, Scaling. Open **Deployments** and click **Rollback** on a version (e.g. v1.4.1) to simulate a rollback.
4. **Health API** — `GET /api/health` returns `{"status": "degraded"}` until a rollback has been executed, then `{"status": "healthy"}`. The AutoSRE recovery monitor uses this to verify recovery.

### Dashboard API (for reference)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Login page (HTML) |
| GET | `/services` | Services list page (HTML) |
| GET | `/services/{service_id}` | Service detail page (HTML) |
| POST | `/api/login` | Demo login; accepts any body, redirects to `/services` |
| GET | `/api/services` | List services (JSON) |
| GET | `/api/services/{service_id}` | Service detail + deployments (JSON) |
| GET | `/api/services/{service_id}/deployments` | Deployments for service (JSON) |
| POST | `/api/services/{service_id}/rollback` | Body: `{"to_version": "v1.4.1"}`; marks health as healthy for demo |
| GET | `/api/health` | `{"status": "degraded" \| "healthy"}` |

---

## Running AutoSRE

The main entry point is the `autosre` CLI (or `python -m autosre`).

### Single incident run (default: latency_spike)

```bash
autosre
# or
python -m autosre
```

- Uses the **default incident type** `latency_spike` and a generated incident ID.
- Runs one full cycle: detect one incident → analyze → plan → act (stub or Nova Act) → verify → report to Slack (if configured).

To choose the incident type (for the simulated alert):

```bash
autosre --incident-type crash_loop
autosre --incident-type memory_leak
autosre --incident-type deployment_failure
```

### Demo scenario (deterministic)

```bash
autosre --demo
```

- Uses a **fixed incident ID** `inc-demo0001` and `latency_spike`.
- Prints intro text, optional scenario text, and "Running workflow..." then the result.
- Optional: create a file `demo_narrative.txt` in the **current directory** (this file is gitignored). Use `[section]` blocks such as `[intro]`, `[scenario]`, `[dashboard_note]`, `[running]`, `[success]`, `[failure]` to customize the printed narrative; if the file is missing, minimal fallback text is used.
- **Exit code:** `0` on success (recovery verified), `1` on failure or escalation.

### Version

```bash
autosre --version
```

### Real AWS demo (CloudWatch + Lambda)

When **`USE_AWS_INTEGRATION=true`**, the agent uses **real AWS APIs** instead of the simulated dashboard:

- **Incidents** — CloudWatch Alarms in `ALARM` state (optionally filtered by `CLOUDWATCH_ALARM_NAMES`) are mapped to `IncidentEvent`.
- **Logs** — CloudWatch Logs for the configured log group (e.g. `/aws/lambda/<LAMBDA_FUNCTION_NAME>`) are fetched for the incident time window and passed to the reasoning agent.
- **Remediation** — For a rollback recommendation, the agent performs a **Lambda alias rollback** via boto3: the configured alias (e.g. `live`) is pointed to the previous published version.
- **Verification** — Recovery is verified by polling CloudWatch until the configured alarm(s) return to `OK` state (or timeout).

**Setup for a real AWS demo:**

1. Deploy a small Lambda (e.g. Python) with at least two published versions and an alias (e.g. `live`) pointing to the current version.
2. Create a CloudWatch alarm on that Lambda (e.g. Errors metric). Optionally trigger the alarm by invoking a failing version.
3. Set in `.env`:
   - `USE_AWS_INTEGRATION=true`
   - `CLOUDWATCH_ALARM_NAMES=YourAlarmName`
   - `LAMBDA_FUNCTION_NAME=your-function-name`
   - `LAMBDA_ALIAS_NAME=live` (or your alias)
   - `LAMBDA_LOG_GROUP_NAME=/aws/lambda/your-function-name` (optional; default derived from function name)
4. Ensure AWS credentials have at least: `cloudwatch:DescribeAlarms`, `logs:FilterLogEvents`, `lambda:GetAlias`, `lambda:ListVersionsByFunction`, `lambda:UpdateAlias`.
5. Run: `autosre`

The agent will read the alarm, fetch Lambda logs, reason over them, and if it recommends rollback, update the alias via boto3; verification then waits for the alarm to return to OK.

**IAM (minimal):** `cloudwatch:DescribeAlarms`, `logs:FilterLogEvents`, `lambda:GetAlias`, `lambda:ListVersionsByFunction`, `lambda:UpdateAlias`, `lambda:GetFunction` (optional for version listing).

---

## Workflow (what happens in a run)

A single run performs one closed loop:

1. **Detect** — Get one incident from the incident stream (simulated CloudWatch: latency_spike, crash_loop, memory_leak, deployment_failure). The event includes `incident_id`, `service_name`, `incident_type`, `detected_at`, `raw_payload`.
2. **Store** — Record the incident in `LogStore` (in-memory or under `LOG_STORAGE_DATA_DIR` if set). Fetch logs and deployment history for that service for the reasoning step.
3. **Analyze** — Reasoning agent (Bedrock Nova if `REASONING_USE_BEDROCK=true`, else stub) produces a `Diagnosis`: summary, confidence, `recommended_action` (rollback, restart, scale_up, restart_db_pool, escalate), and reasoning. Retries on failure up to `REASONING_MAX_RETRIES`; on final failure uses a safe fallback (escalate).
4. **Plan** — Planner maps `Diagnosis` to a list of `PlannedAction` (e.g. navigate to deployment panel, click_rollback to v1.4.1). If the action is escalate, the list is empty.
5. **Act** — UI agent executes the planned actions. In stub mode it only logs them and returns success; with Nova Act it drives the browser against `OPERATIONS_DASHBOARD_URL`. On failure, a post-mortem is still published and the run returns failure.
6. **Verify** — Recovery monitor polls `METRICS_URL` (or dashboard `/api/health`) until the response is `healthy` or `RECOVERY_VERIFY_TIMEOUT_SECONDS` elapses. Tracks recovery time from the start of the action phase.
7. **Report** — Build a `PostMortemReport` (incident_id, root_cause, action_taken, recovery_time_seconds, prevention_suggestion, timeline) and send it to Slack via `SlackReporter`. If Slack is not configured (no token/channel), the report is skipped; if the Slack API fails, the error is logged and the workflow still completes.

The run is considered **successful** only when the recovery status is `recovered`.

---

## CI/CD

GitHub Actions runs on push and pull requests to `main` (and to the `phase-2-operations-dashboard` branch):

- **Test:** Python 3.11 and 3.12; `pip install -e ".[dev]"` and `pytest tests/ -v`.
- **Lint:** `ruff check` and `ruff format --check` on `src`, `dashboard`, and `tests`.

To run the same locally:

```bash
pip install -e ".[dev]"
pytest tests/ -v
ruff check src dashboard tests
ruff format --check src dashboard tests
```

---

## Architecture

| Component | Role |
|-----------|------|
| Incident Simulator | CloudWatch-style mock; emits `IncidentEvent` (single event per run in current implementation). |
| Log Storage | Records incidents; provides logs and deployment history for the reasoning agent. In-memory or file-backed via `LOG_STORAGE_DATA_DIR`. |
| Reasoning Agent (Nova) | Root cause analysis: incident + logs + deployment history → `Diagnosis` (summary, confidence, recommended_action, reasoning). Uses Bedrock Converse or stub. |
| Planner | Maps `Diagnosis` to a list of `PlannedAction` (e.g. navigate, click_rollback) for the UI agent. |
| UI Action Agent (Nova Act) | Executes planned actions on the operations dashboard. Stub mode logs only; real mode uses Nova Act SDK. |
| Recovery Monitor | Polls health endpoint until `healthy` or timeout; reports `RecoveryStatus` and recovery time. |
| Slack Reporter | Sends post-mortem to Slack via `slack_sdk.WebClient` and Block Kit (with plain-text fallback). Skips if token/channel not set; returns False on API failure. |

---

## Status

- **Scaffolding:** Package layout, config, models, and stub implementations for all components.
- **Phase 2:** Operations dashboard (FastAPI + static HTML): login, services list, service detail with Deployments panel and Rollback, `/api/health` for recovery verification.
- **Phase 5:** Slack reporter: real publish via `slack_sdk.WebClient` and Block Kit; fallback text; no token/channel → skip.
- **Phase 6:** Incident/log storage: `LogStore` with record_incident, get_logs_for_incident, get_deployment_history; optional file persistence via `LOG_STORAGE_DATA_DIR`.
- **Phase 7:** Workflow hardening: logging, try/except around record_incident, reasoning, verify, and Slack; reasoning retries (`REASONING_MAX_RETRIES`); post-mortem on escalation, UI failure, or verify exception; `recovery_verify_timeout_seconds` in config.
- **Phase 8:** Demo script: `autosre --demo` with deterministic incident id `inc-demo0001`; optional `demo_narrative.txt`; CLI exit 0/1.

---

## License

MIT.

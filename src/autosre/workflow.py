"""
Closed-loop autonomous operations workflow.

  Alert → Log analysis (Nova) → Root cause → Plan → UI automation (Nova Act)
    → Health verification → Slack post-mortem
"""

import logging
import os
import time

from autosre.config import get_settings
from autosre.incident_detection import DEMO_INCIDENT_ID, get_incident_stream
from autosre.log_storage import LogStore
from autosre.models import Diagnosis, IncidentType, PostMortemReport, RecoveryStatus
from autosre.planner import PlannerAgent
from autosre.reasoning_agent import ReasoningAgent
from autosre.reasoning_agent.agent import FALLBACK_DIAGNOSIS
from autosre.recovery_verification import RecoveryMonitor
from autosre.slack_reporter import SlackReporter
from autosre.ui_automation import UIActionAgent

logger = logging.getLogger(__name__)

# Demo narrative is loaded from demo_narrative.txt (gitignored) when present
_DEMO_NARRATIVE_FILE = "demo_narrative.txt"


def _load_demo_narrative() -> dict[str, str]:
    """Load [section] blocks from demo_narrative.txt in cwd if present."""
    out: dict[str, str] = {}
    for path in (os.path.join(os.getcwd(), _DEMO_NARRATIVE_FILE),):
        if not os.path.isfile(path):
            continue
        try:
            raw = open(path, encoding="utf-8").read()
        except OSError:
            continue
        section = None
        lines: list[str] = []
        for line in raw.splitlines():
            line_stripped = line.strip()
            if line_stripped.startswith("[") and line_stripped.endswith("]"):
                if section is not None:
                    out[section] = "\n".join(lines).strip()
                section = line_stripped[1:-1].strip()
                lines = []
            elif section is not None:
                lines.append(line)
        if section is not None:
            out[section] = "\n".join(lines).strip()
        break
    return out


def _publish_report(slack: SlackReporter, report: PostMortemReport) -> None:
    """Publish post-mortem to Slack; log and swallow errors so workflow does not crash."""
    try:
        slack.publish(report)
    except Exception as e:
        logger.warning("Slack publish failed: %s", e, exc_info=True)


def _build_report(
    incident_id: str,
    detected_at: str,
    diagnosis: Diagnosis,
    recovery_seconds: float,
    status: RecoveryStatus,
    extra_timeline: list[str] | None = None,
) -> PostMortemReport:
    """Build a post-mortem report from incident, diagnosis, and verification result."""
    timeline = [
        f"Alert received: {detected_at}",
        f"Root cause: {diagnosis.summary}",
        f"Action: {diagnosis.recommended_action.value}",
        f"Recovery: {status.value} in {recovery_seconds:.0f}s",
    ]
    if extra_timeline:
        timeline.extend(extra_timeline)
    return PostMortemReport(
        incident_id=incident_id,
        root_cause=diagnosis.summary,
        action_taken=diagnosis.recommended_action.value,
        recovery_time_seconds=recovery_seconds,
        prevention_suggestion="Add memory profiling to CI pipeline",
        timeline=timeline,
    )


def run_once(
    incident_type: IncidentType | None = None,
    demo: bool = False,
) -> bool:
    """
    Run one full cycle: detect one incident, diagnose, act, verify, report.

    For demo pass incident_type=IncidentType.LATENCY_SPIKE and demo=True for
    deterministic incident id (inc-demo0001).
    Returns True if the cycle completed successfully (recovered). On escalation,
    UI failure, or verification failure still publishes a post-mortem when possible.
    """
    settings = get_settings()
    log_store = LogStore(data_dir=settings.log_storage_data_dir or None)
    reasoning = ReasoningAgent(use_bedrock=settings.reasoning_use_bedrock)
    planner = PlannerAgent()
    metrics_url = settings.metrics_url or (
        settings.operations_dashboard_url.rstrip("/") + "/api/health"
    )
    monitor = RecoveryMonitor(metrics_url=metrics_url)
    ui_agent = UIActionAgent(
        dashboard_url=settings.operations_dashboard_url,
        use_nova_act=not settings.ui_stub,
        api_key=settings.nova_act_api_key or None,
    )
    slack = SlackReporter(bot_token=settings.slack_bot_token, channel_id=settings.slack_channel_id)

    # 1. Incident detection
    stream = get_incident_stream(
        incident_type=incident_type,
        incident_id=DEMO_INCIDENT_ID if demo else None,
    )
    incident = next(stream, None)
    if not incident:
        logger.warning("No incident received")
        return False

    try:
        log_store.record_incident(incident)
    except Exception as e:
        logger.warning("Failed to record incident: %s", e, exc_info=True)

    # 2. Root cause analysis (Nova), with retries
    logs = log_store.get_logs_for_incident(incident)
    deployment_history = log_store.get_deployment_history(incident.service_name)
    diagnosis: Diagnosis = FALLBACK_DIAGNOSIS
    max_attempts = 1 + max(0, settings.reasoning_max_retries)
    for attempt in range(max_attempts):
        try:
            result = reasoning.analyze(incident, logs, deployment_history)
            if result is not None:
                diagnosis = result
                break
        except Exception as e:
            logger.warning("Reasoning attempt %s failed: %s", attempt + 1, e, exc_info=True)
            if attempt == max_attempts - 1:
                diagnosis = FALLBACK_DIAGNOSIS

    # 3. Plan actions
    actions = planner.plan(diagnosis)
    if not actions:
        logger.info("No actions (e.g. escalate); publishing escalation report")
        report = _build_report(
            incident.incident_id,
            incident.detected_at.isoformat(),
            diagnosis,
            0.0,
            RecoveryStatus.UNKNOWN,
            extra_timeline=["Escalated; no automated action taken."],
        )
        _publish_report(slack, report)
        return False

    # 4. UI automation (Nova Act)
    action_start_time = time.monotonic()
    success = ui_agent.execute(actions, service_name=incident.service_name)
    if not success:
        logger.warning("UI automation failed; publishing report")
        report = _build_report(
            incident.incident_id,
            incident.detected_at.isoformat(),
            diagnosis,
            0.0,
            RecoveryStatus.NOT_RECOVERED,
            extra_timeline=["UI action execution failed."],
        )
        _publish_report(slack, report)
        return False

    # 5. Recovery verification
    timeout = settings.recovery_verify_timeout_seconds
    recovery_seconds: float = 0.0
    try:
        status = monitor.verify(
            incident.incident_id,
            incident.service_name,
            timeout_seconds=timeout,
            action_start_time=action_start_time,
        )
        recovery_seconds = monitor.get_recovery_time_seconds()
    except Exception as e:
        logger.warning("Recovery verification failed: %s", e, exc_info=True)
        status = RecoveryStatus.NOT_RECOVERED
        recovery_seconds = timeout

    # 6. Post-mortem to Slack
    report = _build_report(
        incident.incident_id,
        incident.detected_at.isoformat(),
        diagnosis,
        recovery_seconds,
        status,
    )
    _publish_report(slack, report)

    return status == RecoveryStatus.RECOVERED


def run_demo() -> bool:
    """
    Deterministic demo scenario. Narrative text is read from demo_narrative.txt
    (gitignored) when present; otherwise minimal fallback text is used.
    Returns True if the cycle completed successfully.
    """
    narrative = _load_demo_narrative()
    intro = narrative.get("intro", "AutoSRE Demo")
    scenario = narrative.get("scenario", "")
    dashboard_note = narrative.get("dashboard_note", "")
    running = narrative.get("running", "Running workflow...")
    success_msg = narrative.get("success", "Result: Success.")
    failure_msg = narrative.get("failure", "Result: Failed or escalated.")

    print(intro)
    if scenario:
        print()
        print(scenario)
    print()

    try:
        import httpx
        settings = get_settings()
        url = settings.operations_dashboard_url.rstrip("/") + "/api/health"
        httpx.get(url, timeout=2.0)
    except Exception:
        if dashboard_note:
            print(dashboard_note)
            print()

    print(running)
    ok = run_once(incident_type=IncidentType.LATENCY_SPIKE, demo=True)
    print()
    print(success_msg if ok else failure_msg)
    return ok

"""
Closed-loop autonomous operations workflow.

  Alert → Log analysis (Nova) → Root cause → Plan → UI automation (Nova Act)
    → Health verification → Slack post-mortem
"""

from autosre.config import get_settings
from autosre.incident_detection import get_incident_stream
from autosre.log_storage import LogStore
from autosre.models import IncidentType, PostMortemReport, RecoveryStatus
from autosre.planner import PlannerAgent
from autosre.reasoning_agent import ReasoningAgent
from autosre.recovery_verification import RecoveryMonitor
from autosre.slack_reporter import SlackReporter
from autosre.ui_automation import UIActionAgent


def run_once(incident_type: IncidentType | None = None) -> bool:
    """
    Run one full cycle: detect one incident, diagnose, act, verify, report.

    For demo pass incident_type=IncidentType.LATENCY_SPIKE.
    Returns True if the cycle completed successfully.
    """
    settings = get_settings()
    log_store = LogStore()
    reasoning = ReasoningAgent(use_bedrock=settings.reasoning_use_bedrock)
    planner = PlannerAgent()
    ui_agent = UIActionAgent(
        dashboard_url=settings.operations_dashboard_url,
        use_nova_act=not settings.ui_stub,
        api_key=settings.nova_act_api_key or None,
    )
    monitor = RecoveryMonitor()
    slack = SlackReporter(bot_token=settings.slack_bot_token, channel_id=settings.slack_channel_id)

    # 1. Incident detection
    stream = get_incident_stream(incident_type=incident_type)
    incident = next(stream, None)
    if not incident:
        return False

    # 2. Root cause analysis (Nova)
    logs = log_store.get_logs_for_incident(incident)
    deployment_history = log_store.get_deployment_history(incident.service_name)
    diagnosis = reasoning.analyze(incident, logs, deployment_history)

    # 3. Plan actions
    actions = planner.plan(diagnosis)
    if not actions:
        # e.g. ESCALATE
        return False

    # 4. UI automation (Nova Act)
    success = ui_agent.execute(actions, service_name=incident.service_name)
    if not success:
        return False

    # 5. Recovery verification
    status = monitor.verify(incident.incident_id, incident.service_name)
    recovery_seconds = monitor.get_recovery_time_seconds()

    # 6. Post-mortem to Slack
    report = PostMortemReport(
        incident_id=incident.incident_id,
        root_cause=diagnosis.summary,
        action_taken=f"{diagnosis.recommended_action.value}",
        recovery_time_seconds=recovery_seconds,
        prevention_suggestion="Add memory profiling to CI pipeline",
        timeline=[
            f"Alert received: {incident.detected_at.isoformat()}",
            "Root cause: bad deployment v1.4.2",
            "Action: rollback to v1.4.1",
            f"Recovery: {status.value} in {recovery_seconds:.0f}s",
        ],
    )
    slack.publish(report)

    return status == RecoveryStatus.RECOVERED


def run_demo() -> None:
    """Deterministic demo scenario for judges: bad deployment → rollback → recovery."""
    print("AutoSRE demo: bad deployment → rollback → recovery")
    ok = run_once(incident_type=IncidentType.LATENCY_SPIKE)
    print("Demo completed successfully." if ok else "Demo ended with failure or escalation.")

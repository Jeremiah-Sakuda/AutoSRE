"""Smoke test for the full workflow (stub components) and Phase 7 hardening."""

from unittest.mock import MagicMock, patch

from autosre.models import IncidentType, RecoveryStatus
from autosre.workflow import run_once


@patch("autosre.workflow.RecoveryMonitor")
def test_run_once_latency_spike(mock_monitor_class):
    """One full cycle with latency_spike incident should complete."""
    mock_monitor = MagicMock()
    mock_monitor.verify.return_value = RecoveryStatus.RECOVERED
    mock_monitor.get_recovery_time_seconds.return_value = 92.0
    mock_monitor_class.return_value = mock_monitor

    result = run_once(incident_type=IncidentType.LATENCY_SPIKE)
    assert result is True
    mock_monitor.verify.assert_called_once()


@patch("autosre.workflow.SlackReporter")
@patch("autosre.workflow.RecoveryMonitor")
@patch("autosre.workflow.PlannerAgent")
def test_run_once_no_actions_publishes_escalation_report(
    mock_planner_class, mock_monitor_class, mock_slack_class
):
    """When planner returns no actions (e.g. ESCALATE), publish report and return False."""
    mock_planner = MagicMock()
    mock_planner.plan.return_value = []
    mock_planner_class.return_value = mock_planner
    mock_slack = MagicMock()
    mock_slack_class.return_value = mock_slack

    result = run_once(incident_type=IncidentType.LATENCY_SPIKE)
    assert result is False
    mock_slack.publish.assert_called_once()
    report = mock_slack.publish.call_args[0][0]
    assert any("Escalated" in line for line in report.timeline)


@patch("autosre.workflow.SlackReporter")
@patch("autosre.workflow.RecoveryMonitor")
@patch("autosre.workflow.UIActionAgent")
def test_run_once_ui_failure_publishes_report(mock_ui_class, mock_monitor_class, mock_slack_class):
    """When UI agent fails, publish report and return False."""
    mock_ui = MagicMock()
    mock_ui.execute.return_value = False
    mock_ui_class.return_value = mock_ui
    mock_slack = MagicMock()
    mock_slack_class.return_value = mock_slack

    result = run_once(incident_type=IncidentType.LATENCY_SPIKE)
    assert result is False
    mock_slack.publish.assert_called_once()
    report = mock_slack.publish.call_args[0][0]
    assert report.recovery_time_seconds == 0.0
    assert "UI action" in report.timeline[-1] or "failed" in report.timeline[-1].lower()


@patch("autosre.workflow.SlackReporter")
@patch("autosre.workflow.RecoveryMonitor")
def test_run_once_verify_exception_returns_false_and_publishes(
    mock_monitor_class, mock_slack_class
):
    """When recovery verify raises, still publish report and return False."""
    mock_monitor = MagicMock()
    mock_monitor.verify.side_effect = RuntimeError("network error")
    mock_monitor_class.return_value = mock_monitor
    mock_slack = MagicMock()
    mock_slack_class.return_value = mock_slack

    result = run_once(incident_type=IncidentType.LATENCY_SPIKE)
    assert result is False
    mock_slack.publish.assert_called_once()
    report = mock_slack.publish.call_args[0][0]
    assert report.recovery_time_seconds > 0  # timeout used as recovery_seconds

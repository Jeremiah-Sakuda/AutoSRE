"""Smoke test for the full workflow (stub components)."""

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

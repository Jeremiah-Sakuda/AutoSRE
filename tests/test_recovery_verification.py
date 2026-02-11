"""Tests for recovery verification (Phase 4)."""

import time
from unittest.mock import MagicMock, patch

from autosre.models import RecoveryStatus
from autosre.recovery_verification.monitor import STUB_RECOVERY_SECONDS, RecoveryMonitor


def test_monitor_stub_when_no_metrics_url():
    """When metrics_url is empty, returns RECOVERED after short sleep (stub)."""
    monitor = RecoveryMonitor(metrics_url="")
    status = monitor.verify("inc-1", "checkout", timeout_seconds=120)
    assert status == RecoveryStatus.RECOVERED
    assert monitor.get_recovery_time_seconds() == STUB_RECOVERY_SECONDS


def test_monitor_stub_with_none_metrics_url():
    """When metrics_url is None, uses stub behavior."""
    monitor = RecoveryMonitor(metrics_url=None)
    status = monitor.verify("inc-1", "checkout")
    assert status == RecoveryStatus.RECOVERED
    assert monitor.get_recovery_time_seconds() == STUB_RECOVERY_SECONDS


@patch("autosre.recovery_verification.monitor.time.sleep")
@patch("autosre.recovery_verification.monitor.httpx.Client")
def test_monitor_recovered_when_healthy(mock_client_class, mock_sleep):
    """When GET returns status healthy, returns RECOVERED and sets recovery time."""
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {"status": "healthy"}
    mock_client = MagicMock()
    mock_client.get.return_value = mock_response
    mock_client_class.return_value.__enter__.return_value = mock_client

    monitor = RecoveryMonitor(metrics_url="http://localhost:3000/api/health")
    action_start = time.monotonic()
    status = monitor.verify(
        "inc-1",
        "checkout",
        timeout_seconds=30,
        action_start_time=action_start,
    )
    assert status == RecoveryStatus.RECOVERED
    recovery_sec = monitor.get_recovery_time_seconds()
    assert recovery_sec >= 0
    assert recovery_sec < 10


@patch("autosre.recovery_verification.monitor.httpx.Client")
@patch("autosre.recovery_verification.monitor.time.sleep")
def test_monitor_polls_until_healthy(mock_sleep, mock_client_class):
    """Polls until response is healthy; recovery time reflects delay."""

    def mk_resp(status: str):
        r = MagicMock()
        r.raise_for_status = MagicMock()
        r.json.return_value = {"status": status}
        return r

    mock_client = mock_client_class.return_value.__enter__.return_value
    mock_client.get.side_effect = [
        mk_resp("degraded"),
        mk_resp("degraded"),
        mk_resp("healthy"),
    ]

    monitor = RecoveryMonitor(metrics_url="http://localhost:3000/api/health")
    action_start = time.monotonic()
    status = monitor.verify(
        "inc-1",
        "checkout",
        timeout_seconds=30,
        action_start_time=action_start,
    )
    assert status == RecoveryStatus.RECOVERED
    assert mock_client.get.call_count == 3
    assert mock_sleep.call_count >= 2


@patch("autosre.recovery_verification.monitor.httpx.Client")
@patch("autosre.recovery_verification.monitor.time.monotonic")
@patch("autosre.recovery_verification.monitor.time.sleep")
def test_monitor_timeout_returns_not_recovered(mock_sleep, mock_monotonic, mock_client_class):
    """When timeout is reached without healthy, returns NOT_RECOVERED."""
    start = 1000.0
    deadline = start + 0.1
    mock_monotonic.side_effect = [start, start + 0.05, deadline + 0.01]

    def mk_resp(status: str):
        r = MagicMock()
        r.raise_for_status = MagicMock()
        r.json.return_value = {"status": status}
        return r

    mock_client = mock_client_class.return_value.__enter__.return_value
    mock_client.get.return_value = mk_resp("degraded")

    monitor = RecoveryMonitor(metrics_url="http://localhost:3000/api/health")
    status = monitor.verify(
        "inc-1",
        "checkout",
        timeout_seconds=0.1,
        action_start_time=start,
    )
    assert status == RecoveryStatus.NOT_RECOVERED
    assert monitor.get_recovery_time_seconds() == 0.1

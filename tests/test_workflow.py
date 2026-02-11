"""Smoke test for the full workflow (stub components)."""

from autosre.models import IncidentType
from autosre.workflow import run_once


def test_run_once_latency_spike():
    """One full cycle with latency_spike incident should complete."""
    result = run_once(incident_type=IncidentType.LATENCY_SPIKE)
    assert result is True

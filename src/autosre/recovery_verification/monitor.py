"""Verifies service health after remediation actions."""

import time

from autosre.models import RecoveryStatus


class RecoveryMonitor:
    """
    Checks metrics (latency, error rate) to confirm recovery.

    Stub: waits briefly then returns RECOVERED for deterministic demo.
    """

    def verify(self, incident_id: str, service_name: str, timeout_seconds: float = 120) -> RecoveryStatus:
        """Poll until recovery signals or timeout. Returns recovery status."""
        # Stub: short wait then recovered
        time.sleep(1)
        return RecoveryStatus.RECOVERED

    def get_recovery_time_seconds(self) -> float:
        """Return elapsed time from action to recovery (stub)."""
        return 92.0

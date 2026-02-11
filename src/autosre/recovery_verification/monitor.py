"""Verifies service health after remediation actions."""

import logging
import time

import httpx

from autosre.models import RecoveryStatus

logger = logging.getLogger(__name__)

DEFAULT_POLL_INTERVAL = 3.0
STUB_RECOVERY_SECONDS = 92.0


class RecoveryMonitor:
    """
    Checks metrics (health endpoint) to confirm recovery.

    When metrics_url is set: polls GET metrics_url until response has
    status == "healthy" or timeout. Tracks recovery time from action_start_time.
    When metrics_url is empty: stub behavior (short sleep, RECOVERED) for demo/CI.
    """

    def __init__(self, metrics_url: str | None = None) -> None:
        self._metrics_url = (metrics_url or "").strip()
        self._last_recovery_seconds: float = 0.0

    def verify(
        self,
        incident_id: str,
        service_name: str,
        timeout_seconds: float = 120,
        action_start_time: float | None = None,
    ) -> RecoveryStatus:
        """Poll until recovery (status == healthy) or timeout. Returns recovery status."""
        if not self._metrics_url:
            time.sleep(1)
            self._last_recovery_seconds = STUB_RECOVERY_SECONDS
            return RecoveryStatus.RECOVERED

        start = action_start_time if action_start_time is not None else time.monotonic()
        deadline = start + timeout_seconds
        poll_interval = DEFAULT_POLL_INTERVAL

        while time.monotonic() < deadline:
            try:
                with httpx.Client(timeout=5.0) as client:
                    r = client.get(self._metrics_url)
                    r.raise_for_status()
                    data = r.json()
                    if data.get("status") == "healthy":
                        self._last_recovery_seconds = time.monotonic() - start
                        logger.info(
                            "Recovery verified",
                            extra={
                                "incident_id": incident_id,
                                "service_name": service_name,
                                "recovery_seconds": self._last_recovery_seconds,
                            },
                        )
                        return RecoveryStatus.RECOVERED
            except Exception as e:
                logger.debug("Health poll failed: %s", e)
            time.sleep(poll_interval)

        self._last_recovery_seconds = timeout_seconds
        logger.warning(
            "Recovery timeout",
            extra={"incident_id": incident_id, "service_name": service_name},
        )
        return RecoveryStatus.NOT_RECOVERED

    def get_recovery_time_seconds(self) -> float:
        """Return elapsed time from action to recovery (from last verify run)."""
        return self._last_recovery_seconds

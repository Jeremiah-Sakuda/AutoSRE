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
    Checks metrics (health endpoint or CloudWatch) to confirm recovery.

    When metrics_url is set: polls GET metrics_url until response has
    status == "healthy" or timeout.
    When metrics_url is empty and use_aws_integration with alarm names: polls
    CloudWatch describe_alarms until alarm state is OK (or timeout).
    When metrics_url is empty and not AWS: stub behavior (short sleep, RECOVERED).
    """

    def __init__(
        self,
        metrics_url: str | None = None,
        use_aws_integration: bool = False,
        cloudwatch_alarm_names: str = "",
        aws_region: str = "us-east-1",
    ) -> None:
        self._metrics_url = (metrics_url or "").strip()
        self._use_aws_integration = use_aws_integration
        self._cloudwatch_alarm_names = (cloudwatch_alarm_names or "").strip()
        self._aws_region = aws_region
        self._last_recovery_seconds: float = 0.0

    def verify(
        self,
        incident_id: str,
        service_name: str,
        timeout_seconds: float = 120,
        action_start_time: float | None = None,
    ) -> RecoveryStatus:
        """Poll until recovery (status == healthy or alarm OK) or timeout. Returns recovery status."""
        start = action_start_time if action_start_time is not None else time.monotonic()
        deadline = start + timeout_seconds
        poll_interval = DEFAULT_POLL_INTERVAL

        # CloudWatch verification path: metrics_url empty but AWS integration with alarms
        if not self._metrics_url and self._use_aws_integration and self._cloudwatch_alarm_names:
            alarm_names = [n.strip() for n in self._cloudwatch_alarm_names.split(",") if n.strip()]
            if alarm_names:
                while time.monotonic() < deadline:
                    if self._check_cloudwatch_alarms_ok(alarm_names):
                        self._last_recovery_seconds = time.monotonic() - start
                        logger.info(
                            "Recovery verified (CloudWatch alarms OK)",
                            extra={
                                "incident_id": incident_id,
                                "service_name": service_name,
                                "recovery_seconds": self._last_recovery_seconds,
                            },
                        )
                        return RecoveryStatus.RECOVERED
                    time.sleep(poll_interval)
                self._last_recovery_seconds = timeout_seconds
                logger.warning(
                    "Recovery timeout (CloudWatch alarms not OK)",
                    extra={"incident_id": incident_id, "service_name": service_name},
                )
                return RecoveryStatus.NOT_RECOVERED

        # Stub path: no metrics_url and no AWS verification
        if not self._metrics_url:
            time.sleep(1)
            self._last_recovery_seconds = STUB_RECOVERY_SECONDS
            return RecoveryStatus.RECOVERED

        # HTTP health-check path
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

    def _check_cloudwatch_alarms_ok(self, alarm_names: list[str]) -> bool:
        """Return True if all given CloudWatch alarms are in OK state."""
        try:
            import boto3

            client = boto3.client("cloudwatch", region_name=self._aws_region)
            response = client.describe_alarms(AlarmNames=alarm_names)
            for alarm in response.get("MetricAlarms") or []:
                if alarm.get("StateValue") != "OK":
                    return False
            return True
        except Exception as e:
            logger.debug("CloudWatch describe_alarms failed: %s", e)
            return False

    def get_recovery_time_seconds(self) -> float:
        """Return elapsed time from action to recovery (from last verify run)."""
        return self._last_recovery_seconds

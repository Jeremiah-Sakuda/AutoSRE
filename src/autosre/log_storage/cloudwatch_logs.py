"""CloudWatch Logs provider for RCA: fetch real Lambda (or other) logs by time window."""

from __future__ import annotations

import logging
from datetime import timezone

from autosre.config import get_settings
from autosre.models import IncidentEvent

logger = logging.getLogger(__name__)


def _default_log_group(lambda_function_name: str) -> str:
    """Default log group for a Lambda function name."""
    name = (lambda_function_name or "").strip()
    if not name:
        return ""
    return f"/aws/lambda/{name}"


def get_logs_for_incident_cloudwatch(
    incident: IncidentEvent,
    log_group_name: str | None = None,
    window_seconds: int = 3600,
) -> str:
    """
    Fetch CloudWatch Logs for the incident's time window and service context.

    Uses boto3 logs.filter_log_events for the given log group and time range
    (detected_at - window_seconds to detected_at). Returns a single string
    (one line per event) for the reasoning agent.

    If log_group_name is empty, derives from config lambda_log_group_name or
    /aws/lambda/<lambda_function_name>.
    """
    settings = get_settings()
    group = (log_group_name or "").strip()
    if not group:
        group = (settings.lambda_log_group_name or "").strip()
    if not group:
        group = _default_log_group(settings.lambda_function_name)
    if not group:
        logger.warning("No CloudWatch log group configured; returning empty logs")
        return ""

    detected_at = incident.detected_at
    if hasattr(detected_at, "replace") and detected_at.tzinfo is None:
        detected_at = detected_at.replace(tzinfo=timezone.utc)
    end_ts_ms = int(detected_at.timestamp() * 1000)
    start_ts_ms = end_ts_ms - (window_seconds * 1000)

    try:
        import boto3

        client = boto3.client("logs", region_name=settings.aws_region)
        lines: list[str] = []
        next_token = None
        while True:
            kwargs = {
                "logGroupName": group,
                "startTime": start_ts_ms,
                "endTime": end_ts_ms,
            }
            if next_token:
                kwargs["nextToken"] = next_token
            response = client.filter_log_events(**kwargs)
            for event in response.get("events") or []:
                ts = event.get("timestamp")
                msg = event.get("message", "")
                if ts is not None:
                    lines.append(f"[{ts}] {msg}")
                else:
                    lines.append(msg)
            next_token = response.get("nextToken")
            if not next_token:
                break
        return "\n".join(lines) if lines else ""
    except Exception as e:
        logger.warning("CloudWatch filter_log_events failed: %s", e, exc_info=True)
        return ""

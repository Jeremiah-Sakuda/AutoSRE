"""Real CloudWatch Alarms as incident source for AWS integration."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import uuid4

from autosre.config import get_settings
from autosre.models import IncidentEvent, IncidentType

logger = logging.getLogger(__name__)


def _metric_to_incident_type(metric_name: str, namespace: str) -> IncidentType:
    """Map CloudWatch metric to IncidentType."""
    name_lower = (metric_name or "").lower()
    if "error" in name_lower or "failure" in name_lower:
        return IncidentType.CRASH_LOOP
    if "duration" in name_lower or "latency" in name_lower:
        return IncidentType.LATENCY_SPIKE
    if "memory" in name_lower or "throttle" in name_lower:
        return IncidentType.MEMORY_LEAK
    return IncidentType.CRASH_LOOP


def _alarm_to_incident(alarm: dict) -> IncidentEvent | None:
    """Convert a CloudWatch alarm (in ALARM state) to IncidentEvent."""
    try:
        name = alarm.get("AlarmName") or ""
        state_updated = alarm.get("StateUpdatedTimestamp")
        if state_updated:
            detected_at = state_updated
            if hasattr(detected_at, "replace"):
                detected_at = detected_at.replace(tzinfo=timezone.utc)
        else:
            detected_at = datetime.now(timezone.utc)
        dimensions = alarm.get("Dimensions") or []
        service_name = name
        for dim in dimensions:
            if dim.get("Name") == "FunctionName":
                service_name = dim.get("Value", name)
                break
        metric_name = alarm.get("MetricName") or "Unknown"
        namespace = alarm.get("Namespace") or ""
        incident_type = _metric_to_incident_type(metric_name, namespace)
        raw_payload = {
            "source": "cloudwatch",
            "AlarmName": name,
            "AlarmArn": alarm.get("AlarmArn"),
            "MetricName": metric_name,
            "Namespace": namespace,
            "StateValue": alarm.get("StateValue"),
            "Threshold": alarm.get("Threshold"),
        }
        return IncidentEvent(
            incident_id=f"inc-cw-{uuid4().hex[:8]}",
            incident_type=incident_type,
            service_name=service_name,
            detected_at=detected_at,
            raw_payload=raw_payload,
        )
    except Exception as e:
        logger.warning("Skip alarm (invalid): %s", e, exc_info=True)
        return None


def get_incident_stream(
    incident_type: IncidentType | None = None,
    incident_id: str | None = None,
    alarm_names: list[str] | None = None,
):
    """
    Yield incident events from CloudWatch Alarms in ALARM state.

    incident_type and incident_id are ignored (for API compatibility with simulator).
    Optionally filter by alarm name(s); if not provided, uses config cloudwatch_alarm_names.
    """
    # unused; kept for same signature as simulator
    _ = incident_type
    _ = incident_id

    settings = get_settings()
    names = alarm_names
    if names is None and settings.cloudwatch_alarm_names:
        names = [n.strip() for n in settings.cloudwatch_alarm_names.split(",") if n.strip()]

    try:
        import boto3

        client = boto3.client("cloudwatch", region_name=settings.aws_region)
        kwargs = {"StateValue": "ALARM"}
        if names:
            kwargs["AlarmNames"] = names
        response = client.describe_alarms(**kwargs)
        metric_alarms = response.get("MetricAlarms") or []
    except Exception as e:
        logger.warning("CloudWatch describe_alarms failed: %s", e, exc_info=True)
        return

    for alarm in metric_alarms:
        event = _alarm_to_incident(alarm)
        if event:
            yield event

"""
Incident detection layer.

Receives alerts from monitoring source (simulated CloudWatch or real CloudWatch Alarms).
Outputs structured IncidentEvent.
"""

from autosre.incident_detection.simulator import DEMO_INCIDENT_ID
from autosre.models import IncidentType


def get_incident_stream(
    incident_type: IncidentType | None = None,
    incident_id: str | None = None,
    alarm_names: list[str] | None = None,
):
    """
    Yield incident events. When use_aws_integration is True, uses CloudWatch Alarms;
    otherwise uses the simulator.
    """
    from autosre.config import get_settings

    settings = get_settings()
    if settings.use_aws_integration:
        from autosre.incident_detection.cloudwatch import get_incident_stream as cw_stream

        yield from cw_stream(
            incident_type=incident_type,
            incident_id=incident_id,
            alarm_names=alarm_names,
        )
        return
    from autosre.incident_detection.simulator import get_incident_stream as sim_stream

    yield from sim_stream(incident_type=incident_type, incident_id=incident_id)


__all__ = ["DEMO_INCIDENT_ID", "get_incident_stream"]

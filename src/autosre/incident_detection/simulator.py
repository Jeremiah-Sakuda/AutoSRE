"""Simulated CloudWatch-style incident source for demo and development."""

from datetime import datetime
from uuid import uuid4

from autosre.models import IncidentEvent, IncidentType


def get_incident_stream(incident_type: IncidentType | None = None):
    """
    Yield simulated incident events (generator).

    For demo: use incident_type=IncidentType.LATENCY_SPIKE for deterministic flow.
    """
    event = IncidentEvent(
        incident_id=f"inc-{uuid4().hex[:8]}",
        incident_type=incident_type or IncidentType.LATENCY_SPIKE,
        service_name="checkout",
        detected_at=datetime.utcnow(),
        raw_payload={
            "source": "simulated",
            "metric": "latency_p99",
            "value": 2500,
            "threshold": 500,
        },
    )
    yield event

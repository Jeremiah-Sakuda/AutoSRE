"""Simulated CloudWatch-style incident source for demo and development."""

from datetime import datetime
from uuid import uuid4

from autosre.models import IncidentEvent, IncidentType


DEMO_INCIDENT_ID = "inc-demo0001"


def get_incident_stream(
    incident_type: IncidentType | None = None,
    incident_id: str | None = None,
):
    """
    Yield simulated incident events (generator).

    For demo: use incident_type=IncidentType.LATENCY_SPIKE and
    incident_id=DEMO_INCIDENT_ID (or "inc-demo0001") for deterministic flow.
    """
    event = IncidentEvent(
        incident_id=incident_id or f"inc-{uuid4().hex[:8]}",
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

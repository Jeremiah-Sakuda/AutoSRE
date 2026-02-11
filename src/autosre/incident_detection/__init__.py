"""
Incident detection layer.

Receives alerts from monitoring source (simulated CloudWatch).
Outputs structured IncidentEvent.
"""

from autosre.incident_detection.simulator import DEMO_INCIDENT_ID, get_incident_stream

__all__ = ["DEMO_INCIDENT_ID", "get_incident_stream"]

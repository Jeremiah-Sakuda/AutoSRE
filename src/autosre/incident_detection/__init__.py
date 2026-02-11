"""
Incident detection layer.

Receives alerts from monitoring source (simulated CloudWatch).
Outputs structured IncidentEvent.
"""

from autosre.incident_detection.simulator import get_incident_stream

__all__ = ["get_incident_stream"]

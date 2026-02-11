"""In-memory / stub log store for reasoning agent input."""

from autosre.models import IncidentEvent


class LogStore:
    """Provides logs and deployment context for a given incident."""

    def get_logs_for_incident(self, incident: IncidentEvent) -> str:
        """Return log snippet relevant to the incident (stub)."""
        return (
            f"[{incident.detected_at.isoformat()}] service={incident.service_name} "
            "level=ERROR message=memory allocation failure "
            "deployment=v1.4.2"
        )

    def get_deployment_history(self, service_name: str, limit: int = 5) -> list[dict]:
        """Return recent deployments for the service (stub)."""
        return [
            {"version": "v1.4.2", "timestamp": "2025-02-11T10:00:00Z", "status": "deployed"},
            {"version": "v1.4.1", "timestamp": "2025-02-11T09:30:00Z", "status": "deployed"},
        ]

"""Incident and log storage for RCA: in-memory with optional file persistence."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from autosre.models import IncidentEvent, IncidentType

# Stub fallbacks when store has no data (backward compatible)
STUB_LOG_SNIPPET = (
    "[{ts}] service={service} level=ERROR message=memory allocation failure deployment=v1.4.2"
)
STUB_DEPLOYMENTS = [
    {"version": "v1.4.2", "timestamp": "2025-02-11T10:00:00Z", "status": "deployed"},
    {"version": "v1.4.1", "timestamp": "2025-02-11T09:30:00Z", "status": "deployed"},
]

_INCIDENTS_FILE = "incidents.json"
_LOG_ENTRIES_FILE = "log_entries.json"
_DEPLOYMENTS_FILE = "deployments.json"


def _iso(dt: datetime) -> str:
    return dt.isoformat() if hasattr(dt, "isoformat") else str(dt)


class LogStore:
    """
    Provides incident recording, logs, and deployment history for RCA.

    In-memory by default. If config log_storage_data_dir is set, data is
    loaded on init and saved after each mutation (record_incident, append_log,
    append_deployment).
    """

    def __init__(self, data_dir: str | None = None) -> None:
        self._data_dir = Path(data_dir) if data_dir else None
        self._incidents: list[dict] = []
        self._log_entries: list[dict] = []  # service_name, timestamp, message
        self._deployments: list[dict] = []  # service_name, version, timestamp, status
        if self._data_dir and self._data_dir.is_dir():
            self._load()

    def _load(self) -> None:
        for name, attr in [
            (_INCIDENTS_FILE, "_incidents"),
            (_LOG_ENTRIES_FILE, "_log_entries"),
            (_DEPLOYMENTS_FILE, "_deployments"),
        ]:
            path = self._data_dir / name
            if path.is_file():
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                    if isinstance(data, list):
                        setattr(self, attr, data)
                except (json.JSONDecodeError, OSError):
                    pass

    def _save(self, filename: str, data: list) -> None:
        if not self._data_dir:
            return
        self._data_dir.mkdir(parents=True, exist_ok=True)
        path = self._data_dir / filename
        try:
            path.write_text(json.dumps(data, indent=0), encoding="utf-8")
        except OSError:
            pass

    def record_incident(self, incident: IncidentEvent) -> None:
        """Persist an incident for audit and retrieval."""
        payload = {
            "incident_id": incident.incident_id,
            "incident_type": incident.incident_type.value,
            "service_name": incident.service_name,
            "detected_at": _iso(incident.detected_at),
            "raw_payload": incident.raw_payload,
        }
        self._incidents.append(payload)
        self._save(_INCIDENTS_FILE, self._incidents)

    def get_incident(self, incident_id: str) -> IncidentEvent | None:
        """Return a stored incident by id, or None (also None if payload is invalid)."""
        for p in self._incidents:
            if p.get("incident_id") != incident_id:
                continue
            try:
                detected_at_str = p.get("detected_at") or ""
                detected_at = datetime.fromisoformat(
                    str(detected_at_str).replace("Z", "+00:00")
                )
                incident_type = IncidentType(p["incident_type"])
            except (ValueError, KeyError, TypeError):
                return None
            return IncidentEvent(
                incident_id=p["incident_id"],
                incident_type=incident_type,
                service_name=p["service_name"],
                detected_at=detected_at,
                raw_payload=p.get("raw_payload") or {},
            )
        return None

    def append_log(
        self, service_name: str, message: str, timestamp: datetime | None = None
    ) -> None:
        """Append a log line for the given service (for RCA)."""
        ts = timestamp or datetime.utcnow()
        self._log_entries.append(
            {
                "service_name": service_name,
                "timestamp": _iso(ts),
                "message": message,
            }
        )
        self._save(_LOG_ENTRIES_FILE, self._log_entries)

    def get_logs_for_incident(self, incident: IncidentEvent, window_seconds: int = 3600) -> str:
        """Return log snippet relevant to the incident (service + time window). Fallback to stub if empty."""
        cutoff = incident.detected_at.timestamp() - window_seconds
        lines = []
        for e in self._log_entries:
            if e.get("service_name") != incident.service_name:
                continue
            try:
                ts_str = e.get("timestamp", "")
                dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                if dt.timestamp() >= cutoff:
                    lines.append(f"[{ts_str}] {e.get('message', '')}")
            except (ValueError, TypeError):
                continue
        if lines:
            return "\n".join(lines)
        return STUB_LOG_SNIPPET.format(
            ts=incident.detected_at.isoformat(),
            service=incident.service_name,
        )

    def append_deployment(
        self,
        service_name: str,
        version: str,
        timestamp: str | datetime,
        status: str = "deployed",
    ) -> None:
        """Record a deployment event for a service."""
        ts = _iso(timestamp) if isinstance(timestamp, datetime) else str(timestamp)
        self._deployments.append(
            {
                "service_name": service_name,
                "version": version,
                "timestamp": ts,
                "status": status,
            }
        )
        self._save(_DEPLOYMENTS_FILE, self._deployments)

    def get_deployment_history(self, service_name: str, limit: int = 5) -> list[dict]:
        """Return recent deployments for the service. Fallback to stub list if empty."""
        filtered = [d for d in self._deployments if d.get("service_name") == service_name]
        filtered.sort(key=lambda d: d.get("timestamp", ""), reverse=True)
        result = [
            {
                "version": d.get("version"),
                "timestamp": d.get("timestamp"),
                "status": d.get("status"),
            }
            for d in filtered[:limit]
        ]
        if result:
            return result
        return STUB_DEPLOYMENTS.copy()

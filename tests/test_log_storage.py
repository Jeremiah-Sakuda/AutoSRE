"""Tests for Phase 6 incident and log storage."""

import tempfile
from datetime import datetime
from pathlib import Path

from autosre.models import IncidentEvent, IncidentType
from autosre.log_storage.store import (
    LogStore,
    STUB_DEPLOYMENTS,
    STUB_LOG_SNIPPET,
)


def test_record_incident_and_get_incident():
    store = LogStore()
    incident = IncidentEvent(
        incident_id="inc-abc123",
        incident_type=IncidentType.LATENCY_SPIKE,
        service_name="checkout",
        detected_at=datetime(2025, 2, 11, 12, 0, 0),
        raw_payload={"metric": "latency_p99"},
    )
    store.record_incident(incident)
    retrieved = store.get_incident("inc-abc123")
    assert retrieved is not None
    assert retrieved.incident_id == "inc-abc123"
    assert retrieved.service_name == "checkout"
    assert retrieved.incident_type == IncidentType.LATENCY_SPIKE
    assert store.get_incident("nonexistent") is None


def test_get_logs_for_incident_empty_returns_stub():
    store = LogStore()
    incident = IncidentEvent(
        incident_id="inc-1",
        incident_type=IncidentType.LATENCY_SPIKE,
        service_name="checkout",
        detected_at=datetime(2025, 2, 11, 12, 0, 0),
    )
    logs = store.get_logs_for_incident(incident)
    assert STUB_LOG_SNIPPET.format(ts=incident.detected_at.isoformat(), service="checkout") == logs


def test_append_log_and_get_logs_for_incident():
    store = LogStore()
    incident = IncidentEvent(
        incident_id="inc-1",
        incident_type=IncidentType.MEMORY_LEAK,
        service_name="checkout",
        detected_at=datetime(2025, 2, 11, 12, 0, 0),
    )
    store.append_log("checkout", "level=ERROR message=OOM", datetime(2025, 2, 11, 11, 30, 0))
    store.append_log("checkout", "deployment=v1.4.2", datetime(2025, 2, 11, 11, 45, 0))
    logs = store.get_logs_for_incident(incident, window_seconds=3600)
    assert "OOM" in logs
    assert "v1.4.2" in logs
    assert "checkout" not in logs or "message=" in logs


def test_get_logs_for_incident_filters_other_service():
    store = LogStore()
    incident = IncidentEvent(
        incident_id="inc-1",
        incident_type=IncidentType.LATENCY_SPIKE,
        service_name="checkout",
        detected_at=datetime(2025, 2, 11, 12, 0, 0),
    )
    store.append_log("payments", "error in payments", datetime(2025, 2, 11, 11, 0, 0))
    logs = store.get_logs_for_incident(incident)
    assert "payments" not in logs
    assert "checkout" in logs or "memory" in logs.lower()


def test_get_deployment_history_empty_returns_stub():
    store = LogStore()
    history = store.get_deployment_history("checkout", limit=5)
    assert history == STUB_DEPLOYMENTS


def test_append_deployment_and_get_deployment_history():
    store = LogStore()
    store.append_deployment("checkout", "v1.4.2", "2025-02-11T10:00:00Z", "deployed")
    store.append_deployment("checkout", "v1.4.1", "2025-02-11T09:30:00Z", "deployed")
    history = store.get_deployment_history("checkout", limit=5)
    assert len(history) == 2
    assert history[0]["version"] == "v1.4.2"
    assert history[0]["timestamp"] == "2025-02-11T10:00:00Z"
    assert history[1]["version"] == "v1.4.1"
    history_limited = store.get_deployment_history("checkout", limit=1)
    assert len(history_limited) == 1
    assert history_limited[0]["version"] == "v1.4.2"


def test_get_deployment_history_filters_by_service():
    store = LogStore()
    store.append_deployment("checkout", "v1.4.2", "2025-02-11T10:00:00Z")
    store.append_deployment("payments", "v2.0.0", "2025-02-11T10:05:00Z")
    history = store.get_deployment_history("checkout")
    assert len(history) == 1
    assert history[0]["version"] == "v1.4.2"
    assert store.get_deployment_history("other") == STUB_DEPLOYMENTS


def test_persistence_roundtrip():
    with tempfile.TemporaryDirectory() as tmp:
        data_dir = Path(tmp)
        store1 = LogStore(data_dir=str(data_dir))
        store1.record_incident(
            IncidentEvent(
                incident_id="inc-persist",
                incident_type=IncidentType.CRASH_LOOP,
                service_name="checkout",
                detected_at=datetime(2025, 2, 11, 12, 0, 0),
            )
        )
        store1.append_log("checkout", "crash loop log", datetime(2025, 2, 11, 11, 0, 0))
        store1.append_deployment("checkout", "v1.4.2", "2025-02-11T10:00:00Z")

        store2 = LogStore(data_dir=str(data_dir))
        incident = store2.get_incident("inc-persist")
        assert incident is not None
        assert incident.incident_type == IncidentType.CRASH_LOOP
        logs = store2.get_logs_for_incident(incident, window_seconds=7200)
        assert "crash loop log" in logs
        history = store2.get_deployment_history("checkout")
        assert len(history) == 1
        assert history[0]["version"] == "v1.4.2"

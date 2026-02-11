"""Shared data models for the AutoSRE workflow."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class IncidentType(str, Enum):
    """Simulated incident types (CloudWatch mock)."""

    LATENCY_SPIKE = "latency_spike"
    CRASH_LOOP = "crash_loop"
    MEMORY_LEAK = "memory_leak"
    DEPLOYMENT_FAILURE = "deployment_failure"


class IncidentEvent(BaseModel):
    """Structured incident event from detection layer."""

    incident_id: str
    incident_type: IncidentType
    service_name: str
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    raw_payload: dict[str, Any] = Field(default_factory=dict)


class RecommendedAction(str, Enum):
    """Planner output: corrective action to take."""

    ROLLBACK = "rollback"
    RESTART = "restart"
    SCALE_UP = "scale_up"
    RESTART_DB_POOL = "restart_db_pool"
    ESCALATE = "escalate"


class Diagnosis(BaseModel):
    """Output of root cause analysis (Nova reasoning)."""

    summary: str
    confidence: float = Field(ge=0.0, le=1.0)
    recommended_action: RecommendedAction
    reasoning: str = ""


class PlannedAction(BaseModel):
    """Planner output: concrete step for UI automation."""

    action_type: str  # e.g. "click_rollback", "restart_instance"
    target: str  # e.g. "deployment_panel", "service_checkout"
    parameters: dict[str, Any] = Field(default_factory=dict)


class RecoveryStatus(str, Enum):
    """Result of recovery verification."""

    RECOVERED = "recovered"
    NOT_RECOVERED = "not_recovered"
    UNKNOWN = "unknown"


class PostMortemReport(BaseModel):
    """Content for Slack post-mortem."""

    incident_id: str
    root_cause: str
    action_taken: str
    recovery_time_seconds: float
    prevention_suggestion: str = ""
    timeline: list[str] = Field(default_factory=list)

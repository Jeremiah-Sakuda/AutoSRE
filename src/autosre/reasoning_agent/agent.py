"""Reasoning agent (Nova Pro/Lite) for root cause analysis."""

from autosre.models import Diagnosis, IncidentEvent, RecommendedAction


class ReasoningAgent:
    """
    Analyzes incident context and produces a structured diagnosis.

    In production this will call Amazon Nova with constrained prompts
    and structured outputs. Stub returns deterministic demo result.
    """

    def analyze(self, incident: IncidentEvent, logs: str, deployment_history: list) -> Diagnosis:
        """Produce diagnosis and recommended action from incident context."""
        # Stub: deterministic demo output for "bad deployment → latency spike"
        return Diagnosis(
            summary=(
                "Checkout service latency increased after deployment v1.4.2. "
                "Logs show memory allocation failure. Likely a memory leak in latest release."
            ),
            confidence=0.92,
            recommended_action=RecommendedAction.ROLLBACK,
            reasoning="Logs and deployment timeline point to v1.4.2; rollback is lowest risk.",
        )

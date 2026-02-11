"""Reasoning agent (Nova Pro/Lite) for root cause analysis via Bedrock Converse API."""

import json
import re
import logging
from typing import Any

from autosre.config import get_settings
from autosre.models import Diagnosis, IncidentEvent, RecommendedAction
from autosre.reasoning_agent.prompts import SYSTEM_PROMPT, build_user_prompt

logger = logging.getLogger(__name__)

# Fallback diagnosis when Bedrock fails or response is invalid
FALLBACK_DIAGNOSIS = Diagnosis(
    summary="Root cause could not be determined; escalation recommended.",
    confidence=0.0,
    recommended_action=RecommendedAction.ESCALATE,
    reasoning="Analysis failed or returned invalid output.",
)


def _parse_diagnosis_from_text(text: str) -> Diagnosis | None:
    """Extract JSON from model output and parse into Diagnosis. Returns None on failure."""
    if not text or not text.strip():
        return None
    # Strip optional markdown code block
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```\s*$", "", cleaned)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    summary = data.get("summary")
    confidence = data.get("confidence", 0.0)
    action_str = (data.get("recommended_action") or "").strip().lower()
    reasoning = data.get("reasoning") or ""
    if not summary or not isinstance(summary, str):
        return None
    try:
        confidence = float(confidence)
        confidence = max(0.0, min(1.0, confidence))
    except (TypeError, ValueError):
        confidence = 0.0
    action_map = {
        "rollback": RecommendedAction.ROLLBACK,
        "restart": RecommendedAction.RESTART,
        "scale_up": RecommendedAction.SCALE_UP,
        "restart_db_pool": RecommendedAction.RESTART_DB_POOL,
        "escalate": RecommendedAction.ESCALATE,
    }
    recommended_action = action_map.get(action_str, RecommendedAction.ESCALATE)
    return Diagnosis(
        summary=summary,
        confidence=confidence,
        recommended_action=recommended_action,
        reasoning=reasoning,
    )


def _get_bedrock_client():
    """Create Bedrock Runtime client with configured timeout and region."""
    import boto3
    from botocore.config import Config

    settings = get_settings()
    config = Config(read_timeout=settings.bedrock_read_timeout_seconds)
    kwargs = {"region_name": settings.aws_region, "config": config}
    if settings.aws_access_key_id and settings.aws_secret_access_key:
        kwargs["aws_access_key_id"] = settings.aws_access_key_id
        kwargs["aws_secret_access_key"] = settings.aws_secret_access_key
    return boto3.client("bedrock-runtime", **kwargs)


class ReasoningAgent:
    """
    Analyzes incident context using Amazon Nova via Bedrock Converse API.

    Produces a structured Diagnosis. On API or parse failure, returns
    a safe fallback (ESCALATE) so the pipeline does not break.
    """

    def __init__(
        self,
        model_id: str | None = None,
        use_bedrock: bool = True,
    ) -> None:
        """
        Args:
            model_id: Bedrock model ID (default from config).
            use_bedrock: If False, use stub behavior for tests/demo without AWS.
        """
        self._model_id = model_id or get_settings().nova_model_id
        self._use_bedrock = use_bedrock

    def analyze(
        self,
        incident: IncidentEvent,
        logs: str,
        deployment_history: list,
    ) -> Diagnosis:
        """Produce diagnosis and recommended action from incident context."""
        if not self._use_bedrock:
            return self._stub_analyze(incident)
        try:
            client = _get_bedrock_client()
            user_content = build_user_prompt(
                incident_type=incident.incident_type.value,
                service_name=incident.service_name,
                logs=logs,
                deployment_history=deployment_history,
            )
            response = client.converse(
                modelId=self._model_id,
                messages=[
                    {
                        "role": "user",
                        "content": [{"text": user_content}],
                    }
                ],
                system=[{"text": SYSTEM_PROMPT}],
                inferenceConfig={
                    "maxTokens": 1024,
                    "temperature": 0.2,
                },
            )
            text = _extract_text_from_converse_response(response)
            diagnosis = _parse_diagnosis_from_text(text)
            if diagnosis is not None:
                logger.info(
                    "Reasoning agent produced diagnosis",
                    extra={
                        "incident_id": incident.incident_id,
                        "recommended_action": diagnosis.recommended_action.value,
                        "confidence": diagnosis.confidence,
                    },
                )
                return diagnosis
        except Exception as e:  # noqa: BLE001
            logger.warning(
                "Bedrock reasoning failed; using fallback",
                extra={"incident_id": incident.incident_id, "error": str(e)},
                exc_info=True,
            )
        return FALLBACK_DIAGNOSIS

    def _stub_analyze(self, incident: IncidentEvent) -> Diagnosis:
        """Deterministic stub for demo or when use_bedrock=False."""
        return Diagnosis(
            summary=(
                "Checkout service latency increased after deployment v1.4.2. "
                "Logs show memory allocation failure. Likely a memory leak in latest release."
            ),
            confidence=0.92,
            recommended_action=RecommendedAction.ROLLBACK,
            reasoning="Logs and deployment timeline point to v1.4.2; rollback is lowest risk.",
        )


def _extract_text_from_converse_response(response: dict[str, Any]) -> str:
    """Extract concatenated text from Bedrock Converse response (output.message.content)."""
    parts = []
    try:
        output = response.get("output") or {}
        message = output.get("message") or {}
        content = message.get("content") or []
        for block in content:
            if block.get("text"):
                parts.append(block["text"])
    except (AttributeError, TypeError):
        pass
    return "".join(parts)

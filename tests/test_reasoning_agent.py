"""Unit tests for the reasoning agent (Phase 1: Bedrock Nova)."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from autosre.models import Diagnosis, IncidentEvent, IncidentType, RecommendedAction
from autosre.reasoning_agent.agent import (
    ReasoningAgent,
    _extract_text_from_converse_response,
    _parse_diagnosis_from_text,
    FALLBACK_DIAGNOSIS,
)


def test_parse_diagnosis_from_text_valid_json():
    text = '''{"summary": "Memory leak in v1.4.2", "confidence": 0.9, "recommended_action": "rollback", "reasoning": "Logs point to deployment."}'''
    d = _parse_diagnosis_from_text(text)
    assert d is not None
    assert d.summary == "Memory leak in v1.4.2"
    assert d.confidence == 0.9
    assert d.recommended_action == RecommendedAction.ROLLBACK
    assert d.reasoning == "Logs point to deployment."


def test_parse_diagnosis_from_text_with_markdown_fence():
    text = '```json\n{"summary": "Bad deploy", "confidence": 0.8, "recommended_action": "restart", "reasoning": ""}\n```'
    d = _parse_diagnosis_from_text(text)
    assert d is not None
    assert d.summary == "Bad deploy"
    assert d.recommended_action == RecommendedAction.RESTART


def test_parse_diagnosis_from_text_invalid_json_returns_none():
    assert _parse_diagnosis_from_text("not json at all") is None
    assert _parse_diagnosis_from_text("") is None
    assert _parse_diagnosis_from_text("{}") is None  # missing summary


def test_parse_diagnosis_from_text_unknown_action_maps_to_escalate():
    text = '{"summary": "Something broke", "confidence": 0.5, "recommended_action": "unknown_action", "reasoning": "?"}'
    d = _parse_diagnosis_from_text(text)
    assert d is not None
    assert d.recommended_action == RecommendedAction.ESCALATE


def test_extract_text_from_converse_response():
    response = {
        "output": {
            "message": {
                "content": [
                    {"text": "Hello "},
                    {"text": "world"},
                ]
            }
        }
    }
    assert _extract_text_from_converse_response(response) == "Hello world"
    assert _extract_text_from_converse_response({}) == ""
    assert _extract_text_from_converse_response({"output": {}}) == ""


@pytest.fixture
def sample_incident():
    return IncidentEvent(
        incident_id="inc-abc123",
        incident_type=IncidentType.LATENCY_SPIKE,
        service_name="checkout",
        detected_at=datetime.utcnow(),
        raw_payload={"metric": "latency_p99", "value": 2500},
    )


def test_reasoning_agent_stub_mode(sample_incident):
    agent = ReasoningAgent(use_bedrock=False)
    diagnosis = agent.analyze(sample_incident, "some logs", [])
    assert diagnosis.recommended_action == RecommendedAction.ROLLBACK
    assert diagnosis.confidence == 0.92
    assert "v1.4.2" in diagnosis.summary


@patch("autosre.reasoning_agent.agent._get_bedrock_client")
def test_reasoning_agent_bedrock_success(mock_get_client, sample_incident):
    mock_client = MagicMock()
    mock_client.converse.return_value = {
        "output": {
            "message": {
                "content": [
                    {
                        "text": '{"summary": "Deployment v1.4.2 caused latency.", "confidence": 0.88, "recommended_action": "rollback", "reasoning": "Logs and timeline."}'
                    }
                ]
            }
        }
    }
    mock_get_client.return_value = mock_client

    agent = ReasoningAgent(use_bedrock=True)
    diagnosis = agent.analyze(sample_incident, "logs here", [{"version": "v1.4.2"}])

    assert diagnosis.summary == "Deployment v1.4.2 caused latency."
    assert diagnosis.confidence == 0.88
    assert diagnosis.recommended_action == RecommendedAction.ROLLBACK
    mock_client.converse.assert_called_once()
    call_kw = mock_client.converse.call_args.kwargs
    assert "messages" in call_kw
    assert call_kw["modelId"] == "us.amazon.nova-2-lite-v1:0"


@patch("autosre.reasoning_agent.agent._get_bedrock_client")
def test_reasoning_agent_bedrock_invalid_response_returns_fallback(mock_get_client, sample_incident):
    mock_client = MagicMock()
    mock_client.converse.return_value = {
        "output": {
            "message": {
                "content": [{"text": "I'm not JSON, just prose."}]
            }
        }
    }
    mock_get_client.return_value = mock_client

    agent = ReasoningAgent(use_bedrock=True)
    diagnosis = agent.analyze(sample_incident, "logs", [])

    assert diagnosis == FALLBACK_DIAGNOSIS
    assert diagnosis.recommended_action == RecommendedAction.ESCALATE


@patch("autosre.reasoning_agent.agent._get_bedrock_client")
def test_reasoning_agent_bedrock_exception_returns_fallback(mock_get_client, sample_incident):
    mock_get_client.side_effect = Exception("AWS credentials missing")

    agent = ReasoningAgent(use_bedrock=True)
    diagnosis = agent.analyze(sample_incident, "logs", [])

    assert diagnosis == FALLBACK_DIAGNOSIS
    assert diagnosis.recommended_action == RecommendedAction.ESCALATE

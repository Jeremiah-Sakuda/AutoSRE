"""Tests for Slack reporter (Phase 5: post-mortem publish)."""

from unittest.mock import MagicMock, patch

from autosre.models import PostMortemReport
from autosre.slack_reporter.reporter import (
    SlackReporter,
    _build_post_mortem_blocks,
    _build_post_mortem_text,
)


def test_build_post_mortem_text():
    report = PostMortemReport(
        incident_id="inc-1",
        root_cause="Memory leak in v1.4.2",
        action_taken="rollback",
        recovery_time_seconds=92.0,
        prevention_suggestion="Add memory profiling",
        timeline=["Alert received", "Rollback executed"],
    )
    text = _build_post_mortem_text(report)
    assert "inc-1" in text
    assert "Memory leak" in text
    assert "rollback" in text
    assert "92" in text
    assert "Add memory profiling" in text
    assert "Alert received" in text


def test_build_post_mortem_blocks():
    report = PostMortemReport(
        incident_id="inc-demo",
        root_cause="Bad deployment",
        action_taken="rollback",
        recovery_time_seconds=45.0,
    )
    blocks = _build_post_mortem_blocks(report)
    assert len(blocks) >= 4
    assert blocks[0]["type"] == "header"
    assert any(b.get("type") == "section" for b in blocks)


def test_publish_no_token_returns_false():
    reporter = SlackReporter(bot_token="", channel_id="C123")
    report = PostMortemReport(
        incident_id="inc-1",
        root_cause="test",
        action_taken="rollback",
        recovery_time_seconds=0.0,
    )
    assert reporter.publish(report) is False


def test_publish_no_channel_returns_false():
    reporter = SlackReporter(bot_token="xoxb-xxx", channel_id="")
    report = PostMortemReport(
        incident_id="inc-1",
        root_cause="test",
        action_taken="rollback",
        recovery_time_seconds=0.0,
    )
    assert reporter.publish(report) is False


@patch("slack_sdk.WebClient")
def test_publish_with_token_calls_chat_post_message(mock_web_client_class):
    mock_client = MagicMock()
    mock_web_client_class.return_value = mock_client

    reporter = SlackReporter(bot_token="xoxb-xxx", channel_id="C123")
    report = PostMortemReport(
        incident_id="inc-1",
        root_cause="Memory leak",
        action_taken="rollback",
        recovery_time_seconds=92.0,
        timeline=["Step 1", "Step 2"],
    )
    result = reporter.publish(report)

    assert result is True
    mock_web_client_class.assert_called_once_with(token="xoxb-xxx")
    mock_client.chat_postMessage.assert_called_once()
    call_kw = mock_client.chat_postMessage.call_args[1]
    assert call_kw["channel"] == "C123"
    assert "text" in call_kw
    assert "blocks" in call_kw
    assert "inc-1" in call_kw["text"]
    assert "Memory leak" in call_kw["text"]


@patch("slack_sdk.WebClient")
def test_publish_api_failure_returns_false(mock_web_client_class):
    mock_client = MagicMock()
    mock_client.chat_postMessage.side_effect = Exception("Slack API error")
    mock_web_client_class.return_value = mock_client

    reporter = SlackReporter(bot_token="xoxb-xxx", channel_id="C123")
    report = PostMortemReport(
        incident_id="inc-1",
        root_cause="test",
        action_taken="rollback",
        recovery_time_seconds=0.0,
    )
    result = reporter.publish(report)

    assert result is False

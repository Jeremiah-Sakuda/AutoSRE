"""Slack reporter for automated post-mortem."""

import logging

from autosre.models import PostMortemReport

logger = logging.getLogger(__name__)


def _build_post_mortem_text(report: PostMortemReport) -> str:
    """Plain-text fallback for notifications and accessibility."""
    lines = [
        f"*AutoSRE Post-Mortem* — Incident `{report.incident_id}`",
        f"*Root cause:* {report.root_cause}",
        f"*Action taken:* {report.action_taken}",
        f"*Recovery time:* {report.recovery_time_seconds:.0f}s",
    ]
    if report.prevention_suggestion:
        lines.append(f"*Prevention:* {report.prevention_suggestion}")
    if report.timeline:
        lines.append("*Timeline:*")
        for entry in report.timeline:
            lines.append(f"  • {entry}")
    return "\n".join(lines)


def _build_post_mortem_blocks(report: PostMortemReport) -> list[dict]:
    """Block Kit layout for post-mortem in Slack."""
    blocks: list[dict] = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "AutoSRE Post-Mortem", "emoji": True},
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Incident:*\n`{report.incident_id}`"},
                {"type": "mrkdwn", "text": f"*Recovery:*\n{report.recovery_time_seconds:.0f}s"},
            ],
        },
        {"type": "section", "text": {"type": "mrkdwn", "text": f"*Root cause:*\n{report.root_cause}"}},
        {"type": "section", "text": {"type": "mrkdwn", "text": f"*Action taken:*\n{report.action_taken}"}},
    ]
    if report.prevention_suggestion:
        blocks.append(
            {"type": "section", "text": {"type": "mrkdwn", "text": f"*Prevention:*\n{report.prevention_suggestion}"}}
        )
    if report.timeline:
        timeline_text = "\n".join(f"• {e}" for e in report.timeline)
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": f"*Timeline:*\n{timeline_text}"}})
    return blocks


class SlackReporter:
    """Publishes post-mortem to Slack via slack_sdk WebClient and Block Kit; fallback text when token not configured."""

    def __init__(self, bot_token: str = "", channel_id: str = "") -> None:
        self.bot_token = bot_token
        self.channel_id = channel_id

    def publish(self, report: PostMortemReport) -> bool:
        """Send post-mortem to configured Slack channel. Returns False if token/channel missing or API fails."""
        if not self.bot_token or not self.channel_id:
            logger.info(
                "Slack publish skipped: no token or channel",
                extra={"root_cause": report.root_cause[:80], "action_taken": report.action_taken},
            )
            return False
        try:
            from slack_sdk import WebClient

            client = WebClient(token=self.bot_token)
            text = _build_post_mortem_text(report)
            blocks = _build_post_mortem_blocks(report)
            client.chat_postMessage(
                channel=self.channel_id,
                text=text,
                blocks=blocks,
            )
            logger.info("Slack post-mortem published", extra={"incident_id": report.incident_id})
            return True
        except Exception as e:
            logger.warning("Slack publish failed: %s", e, exc_info=True)
            return False

"""Slack reporter for automated post-mortem."""

from autosre.models import PostMortemReport


class SlackReporter:
    """Publishes post-mortem to Slack. Stub: logs when token not configured."""

    def __init__(self, bot_token: str = "", channel_id: str = "") -> None:
        self.bot_token = bot_token
        self.channel_id = channel_id

    def publish(self, report: PostMortemReport) -> bool:
        """Send post-mortem to configured Slack channel."""
        if not self.bot_token or not self.channel_id:
            print("[SlackReporter] No token/channel; skipping publish.")
            print(f"  Root cause: {report.root_cause}")
            print(f"  Action: {report.action_taken}")
            print(f"  Recovery: {report.recovery_time_seconds}s")
            return False
        # TODO: slack_sdk WebClient chat_postMessage
        return True

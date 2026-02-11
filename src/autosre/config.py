"""Application configuration loaded from environment."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """AutoSRE settings from env vars."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # AWS (Amazon Nova)
    aws_region: str = "us-east-1"
    # Optional: explicit credentials; otherwise use default chain
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None

    # Slack
    slack_bot_token: str = ""
    slack_channel_id: str = ""

    # Demo / operations dashboard
    operations_dashboard_url: str = "http://localhost:3000"
    incident_source: str = "simulated"


def get_settings() -> Settings:
    """Return loaded settings (singleton-style)."""
    return Settings()

"""Application configuration loaded from environment."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """AutoSRE settings from env vars."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # AWS (Amazon Nova / Bedrock)
    aws_region: str = "us-east-1"
    # Optional: explicit credentials; otherwise use default chain
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    # Bedrock model for reasoning (Nova 2 Lite or Pro)
    nova_model_id: str = "us.amazon.nova-2-lite-v1:0"
    # Timeout for Bedrock Converse (Nova can take long for reasoning)
    bedrock_read_timeout_seconds: int = 300
    # Set true to call Bedrock Nova for reasoning; false uses stub (demo/CI without AWS)
    reasoning_use_bedrock: bool = False

    # Slack
    slack_bot_token: str = ""
    slack_channel_id: str = ""

    # Demo / operations dashboard
    operations_dashboard_url: str = "http://localhost:3000"
    incident_source: str = "simulated"

    # UI automation (Nova Act): set False to use real browser; True for stub (CI/demo without browser)
    ui_stub: bool = True
    # Nova Act API key (optional; from nova.amazon.com/act); else uses AWS IAM
    nova_act_api_key: str = ""


def get_settings() -> Settings:
    """Return loaded settings (singleton-style)."""
    return Settings()

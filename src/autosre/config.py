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
    # Health URL for recovery verification (default: dashboard + /api/health)
    metrics_url: str = ""

    # Real AWS integration (CloudWatch + Lambda); when True, agent uses real APIs instead of dashboard
    use_aws_integration: bool = False
    # CloudWatch alarm name(s) to treat as incident source (comma-separated for multiple)
    cloudwatch_alarm_names: str = ""
    # Lambda function name for rollback demo (used when use_aws_integration is True)
    lambda_function_name: str = ""
    # Lambda alias to roll back (e.g. live, prod); default "live"
    lambda_alias_name: str = "live"
    # CloudWatch Logs group for RCA (e.g. /aws/lambda/<name>); default derived from lambda_function_name if empty
    lambda_log_group_name: str = ""

    # UI automation (Nova Act): True = stub only; False = use real browser
    ui_stub: bool = True
    nova_act_api_key: str = ""

    # Phase 6: incident / log storage (optional file persistence)
    log_storage_data_dir: str = ""

    # Phase 7: workflow hardening
    reasoning_max_retries: int = 2
    recovery_verify_timeout_seconds: float = 120.0


def get_settings() -> Settings:
    """Return loaded settings from environment (and .env if present)."""
    return Settings()

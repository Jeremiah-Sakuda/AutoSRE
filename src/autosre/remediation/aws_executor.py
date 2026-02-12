"""AWS action executor: Lambda rollback (and optionally other actions) via boto3."""

from __future__ import annotations

import logging

from autosre.config import get_settings
from autosre.models import PlannedAction

logger = logging.getLogger(__name__)


class AWSExecutor:
    """
    Executes planned actions via boto3 (Lambda version/alias).

    Implements the same contract as UIActionAgent.execute(actions, service_name) -> bool.
    For ROLLBACK (click_rollback): Lambda publish_version + update_alias to previous version.
    Other action types are no-op in this minimal slice (can be extended later).
    """

    def __init__(self) -> None:
        self._settings = get_settings()

    def execute(
        self,
        actions: list[PlannedAction],
        service_name: str | None = None,
    ) -> bool:
        """Execute the list of planned actions via AWS APIs. Returns True if all succeeded."""
        if not actions:
            return True

        has_rollback = any(
            a.action_type == "click_rollback" for a in actions
        )
        if not has_rollback:
            logger.info("No rollback action in plan; other AWS actions not yet implemented")
            return True

        function_name = (
            self._settings.lambda_function_name or (service_name or "").strip()
        ).strip()
        if not function_name:
            logger.warning("Lambda function name not configured; skipping rollback")
            return False

        alias_name = (self._settings.lambda_alias_name or "live").strip()
        return self._lambda_rollback(function_name, alias_name)

    def _lambda_rollback(self, function_name: str, alias_name: str) -> bool:
        """
        Point the Lambda alias to the previous version (rollback).

        Gets current alias version, lists versions, updates alias to the previous version.
        """
        try:
            import boto3

            client = boto3.client("lambda", region_name=self._settings.aws_region)

            # Resolve alias to current version
            try:
                alias = client.get_alias(FunctionName=function_name, Name=alias_name)
            except client.exceptions.ResourceNotFoundException:
                logger.warning("Alias %s not found for %s", alias_name, function_name)
                return False
            current_version = alias.get("FunctionVersion")
            if not current_version:
                logger.warning("Alias has no FunctionVersion")
                return False
            if current_version == "$LATEST":
                # Alias points to $LATEST; we could publish current and then point to previous published
                # For simplicity: list versions and point to latest published (other than $LATEST)
                versions = client.list_versions_by_function(FunctionName=function_name)
                published = [
                    v for v in (versions.get("Versions") or [])
                    if v.get("Version") != "$LATEST"
                ]
                published.sort(key=lambda v: int(v.get("Version", "0")), reverse=True)
                if len(published) < 2:
                    logger.warning("No previous published version to roll back to")
                    return False
                previous_version = published[1].get("Version")
            else:
                try:
                    current_num = int(current_version)
                except (ValueError, TypeError):
                    logger.warning("Cannot parse version %s", current_version)
                    return False
                versions = client.list_versions_by_function(FunctionName=function_name)
                all_versions = [
                    v for v in (versions.get("Versions") or [])
                    if v.get("Version") != "$LATEST"
                ]
                all_versions.sort(key=lambda v: int(v.get("Version", "0")), reverse=True)
                previous_version = None
                for v in all_versions:
                    if int(v.get("Version", 0)) < current_num:
                        previous_version = v.get("Version")
                        break
                if not previous_version:
                    logger.warning("No previous version to roll back to")
                    return False

            client.update_alias(
                FunctionName=function_name,
                Name=alias_name,
                FunctionVersion=previous_version,
            )
            logger.info(
                "Lambda rollback: %s alias %s -> version %s",
                function_name,
                alias_name,
                previous_version,
            )
            return True
        except Exception as e:
            logger.warning("Lambda rollback failed: %s", e, exc_info=True)
            return False

"""UI action agent (Nova Act) — executes planned steps on the operations dashboard."""

import logging
import os

from autosre.models import PlannedAction
from autosre.ui_automation.prompts import actions_to_prompts

logger = logging.getLogger(__name__)


def _run_nova_act(dashboard_url: str, prompts: list[str], api_key: str | None) -> bool:
    """Run Nova Act with the given prompts. Returns True if all steps succeeded."""
    try:
        from nova_act import NovaAct
    except ImportError as e:
        logger.warning("Nova Act SDK not available; cannot run UI automation: %s", e)
        return False
    if api_key:
        os.environ["NOVA_ACT_API_KEY"] = api_key
    try:
        with NovaAct(starting_page=dashboard_url) as nova:
            for prompt in prompts:
                nova.act(prompt)
        return True
    except Exception as e:
        logger.warning("Nova Act execution failed: %s", e, exc_info=True)
        return False


class UIActionAgent:
    """
    Performs UI automation against the operations dashboard.

    In stub mode (default): logs actions and returns True (no browser).
    With use_nova_act=True: uses Nova Act SDK to run natural-language prompts.
    """

    def __init__(
        self,
        dashboard_url: str = "http://localhost:3000",
        use_nova_act: bool = False,
        api_key: str | None = None,
    ) -> None:
        self.dashboard_url = dashboard_url.rstrip("/")
        self._use_nova_act = use_nova_act
        self._api_key = api_key or ""

    def execute(
        self,
        actions: list[PlannedAction],
        service_name: str | None = None,
    ) -> bool:
        """Execute the list of planned actions. Returns True if all succeeded."""
        if not actions:
            return True
        prompts = actions_to_prompts(
            actions,
            service_name=service_name,
            include_login=True,
        )
        if self._use_nova_act:
            return _run_nova_act(
                self.dashboard_url,
                prompts,
                self._api_key or None,
            )
        for action in actions:
            logger.info(
                "UIAction (stub) %s on %s params=%s",
                action.action_type,
                action.target,
                action.parameters,
            )
        return True

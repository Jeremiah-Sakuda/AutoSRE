"""UI action agent (Nova Act) — executes planned steps on the operations dashboard."""

from autosre.models import PlannedAction


class UIActionAgent:
    """
    Performs UI automation against the operations dashboard.

    Production: Nova Act for real browser/UI interaction.
    Stub: logs actions for demo.
    """

    def __init__(self, dashboard_url: str = "http://localhost:3000") -> None:
        self.dashboard_url = dashboard_url

    def execute(self, actions: list[PlannedAction]) -> bool:
        """Execute the list of planned actions. Returns True if all succeeded."""
        for action in actions:
            self._execute_one(action)
        return True

    def _execute_one(self, action: PlannedAction) -> None:
        """Execute a single action (stub: log only)."""
        # TODO: Nova Act integration
        print(f"[UIAction] {action.action_type} on {action.target} params={action.parameters}")

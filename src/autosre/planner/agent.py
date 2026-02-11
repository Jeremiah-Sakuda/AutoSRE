"""Planner: diagnosis → concrete UI actions."""

from autosre.models import Diagnosis, PlannedAction, RecommendedAction


class PlannerAgent:
    """Maps diagnosis to a sequence of UI automation steps."""

    def plan(self, diagnosis: Diagnosis) -> list[PlannedAction]:
        """Convert diagnosis into ordered list of UI actions."""
        action_map = {
            RecommendedAction.ROLLBACK: [
                PlannedAction(action_type="navigate", target="deployment_panel", parameters={}),
                PlannedAction(
                    action_type="click_rollback",
                    target="deployment_panel",
                    parameters={"to_version": "v1.4.1"},
                ),
            ],
            RecommendedAction.RESTART: [
                PlannedAction(action_type="navigate", target="service_instances", parameters={}),
                PlannedAction(
                    action_type="restart_instance", target="service_instances", parameters={}
                ),
            ],
            RecommendedAction.SCALE_UP: [
                PlannedAction(action_type="navigate", target="service_scaling", parameters={}),
                PlannedAction(
                    action_type="scale_replicas",
                    target="service_scaling",
                    parameters={"replicas": 4},
                ),
            ],
            RecommendedAction.RESTART_DB_POOL: [
                PlannedAction(action_type="navigate", target="db_pool", parameters={}),
                PlannedAction(action_type="restart_pool", target="db_pool", parameters={}),
            ],
            RecommendedAction.ESCALATE: [],
        }
        return action_map.get(diagnosis.recommended_action, [])

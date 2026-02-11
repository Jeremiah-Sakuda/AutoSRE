"""Convert PlannedAction list into natural-language prompts for Nova Act."""

from autosre.models import PlannedAction


def actions_to_prompts(
    actions: list[PlannedAction],
    service_name: str | None = None,
    include_login: bool = True,
) -> list[str]:
    """
    Build a list of short, direct prompts for Nova Act act() calls.

    Uses deterministic labels matching the operations dashboard:
    Demo login, Services, Checkout/Payments, Deployments tab, Rollback button.
    """
    prompts: list[str] = []
    if include_login:
        prompts.append("Click the Demo login button.")
    if service_name:
        display = service_name.capitalize()
        prompts.append(f"Click the {display} service link.")
    for action in actions:
        if action.action_type == "navigate" and action.target == "deployment_panel":
            prompts.append("Click the Deployments tab.")
        elif action.action_type == "click_rollback":
            to_version = action.parameters.get("to_version", "previous")
            prompts.append(f"Click the Rollback button for version {to_version}.")
        elif action.action_type == "navigate" and action.target == "service_instances":
            prompts.append("Open the service instances section.")
        elif action.action_type == "restart_instance":
            prompts.append("Click the Restart button for the first instance.")
        elif action.action_type == "navigate" and action.target == "service_scaling":
            prompts.append("Open the scaling section.")
        elif action.action_type == "scale_replicas":
            replicas = action.parameters.get("replicas", 4)
            prompts.append(f"Set replicas to {replicas} and apply.")
        elif action.action_type == "navigate" and action.target == "db_pool":
            prompts.append("Open the database pool section.")
        elif action.action_type == "restart_pool":
            prompts.append("Click the Restart pool button.")
        else:
            prompts.append(f"Perform {action.action_type} on {action.target}.")
    return prompts

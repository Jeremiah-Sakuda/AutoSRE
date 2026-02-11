"""Tests for UI automation (Phase 3: Nova Act integration and stub)."""

from unittest.mock import patch

from autosre.models import PlannedAction
from autosre.ui_automation.agent import UIActionAgent
from autosre.ui_automation.prompts import actions_to_prompts


def test_actions_to_prompts_rollback_with_service():
    actions = [
        PlannedAction(action_type="navigate", target="deployment_panel", parameters={}),
        PlannedAction(
            action_type="click_rollback",
            target="deployment_panel",
            parameters={"to_version": "v1.4.1"},
        ),
    ]
    prompts = actions_to_prompts(actions, service_name="checkout", include_login=True)
    assert "Click the Demo login button." in prompts
    assert "Click the Checkout service link." in prompts
    assert "Click the Deployments tab." in prompts
    assert "Click the Rollback button for version v1.4.1." in prompts
    assert len(prompts) == 4


def test_actions_to_prompts_rollback_no_service():
    actions = [
        PlannedAction(action_type="navigate", target="deployment_panel", parameters={}),
        PlannedAction(
            action_type="click_rollback",
            target="deployment_panel",
            parameters={"to_version": "v1.4.1"},
        ),
    ]
    prompts = actions_to_prompts(actions, service_name=None, include_login=True)
    assert prompts[0] == "Click the Demo login button."
    assert "Deployments tab" in prompts[1]
    assert "Rollback button for version v1.4.1" in prompts[2]


def test_ui_agent_stub_mode_returns_true():
    agent = UIActionAgent(dashboard_url="http://localhost:3000", use_nova_act=False)
    actions = [
        PlannedAction(action_type="navigate", target="deployment_panel", parameters={}),
        PlannedAction(
            action_type="click_rollback",
            target="deployment_panel",
            parameters={"to_version": "v1.4.1"},
        ),
    ]
    result = agent.execute(actions, service_name="checkout")
    assert result is True


def test_ui_agent_stub_mode_empty_actions_returns_true():
    agent = UIActionAgent(dashboard_url="http://localhost:3000", use_nova_act=False)
    assert agent.execute([], service_name=None) is True


@patch("autosre.ui_automation.agent._run_nova_act")
def test_ui_agent_nova_act_mode_calls_run(mock_run):
    mock_run.return_value = True
    agent = UIActionAgent(
        dashboard_url="http://localhost:3000",
        use_nova_act=True,
        api_key="test-key",
    )
    actions = [
        PlannedAction(action_type="navigate", target="deployment_panel", parameters={}),
        PlannedAction(
            action_type="click_rollback",
            target="deployment_panel",
            parameters={"to_version": "v1.4.1"},
        ),
    ]
    result = agent.execute(actions, service_name="checkout")
    assert result is True
    mock_run.assert_called_once()
    call_args = mock_run.call_args[0]
    assert call_args[0] == "http://localhost:3000"
    assert "Click the Demo login button." in call_args[1]
    assert "Click the Rollback button for version v1.4.1." in call_args[1]
    assert mock_run.call_args[0][2] == "test-key"


@patch("autosre.ui_automation.agent._run_nova_act")
def test_ui_agent_nova_act_mode_failure_returns_false(mock_run):
    mock_run.return_value = False
    agent = UIActionAgent(
        dashboard_url="http://localhost:3000",
        use_nova_act=True,
    )
    actions = [
        PlannedAction(action_type="navigate", target="deployment_panel", parameters={}),
    ]
    result = agent.execute(actions, service_name="checkout")
    assert result is False

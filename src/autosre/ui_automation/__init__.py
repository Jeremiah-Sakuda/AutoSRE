"""
UI automation (Amazon Nova Act).

Executes planned actions against the operations dashboard:
login, navigate, click rollback, restart instance, scale replicas.
"""

from autosre.ui_automation.agent import UIActionAgent

__all__ = ["UIActionAgent"]

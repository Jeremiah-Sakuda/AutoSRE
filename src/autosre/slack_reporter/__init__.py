"""
Slack post-mortem reporter.

Publishes incident timeline, root cause, remediation, and prevention suggestion.
"""

from autosre.slack_reporter.reporter import SlackReporter

__all__ = ["SlackReporter"]

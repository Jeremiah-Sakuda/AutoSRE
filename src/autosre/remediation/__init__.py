"""
Remediation layer: execute planned actions via real AWS APIs.

When use_aws_integration is True, workflow uses AWSExecutor instead of UIActionAgent.
"""

from autosre.remediation.aws_executor import AWSExecutor

__all__ = ["AWSExecutor"]

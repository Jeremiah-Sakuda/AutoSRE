# Scripts and snippets for AutoSRE

## Real AWS demo (CloudWatch + Lambda)

Use the [Real AWS demo section](../README.md#real-aws-demo-cloudwatch--lambda) in the main README for full setup.

- **cloudformation-aws-demo.yaml** — Minimal CloudFormation template to create a Lambda function with two versions, an alias (`live`), and a CloudWatch alarm on Errors. Deploy this stack, then set `USE_AWS_INTEGRATION=true`, `CLOUDWATCH_ALARM_NAMES=<AlarmLogicalId>`, `LAMBDA_FUNCTION_NAME=<stack output>`, and run `autosre`.

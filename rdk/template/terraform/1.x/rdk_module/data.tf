# Define the data sources used to determine the current context of this execution.
data "aws_caller_identity" "current" {}
data "aws_partition" "current" {}

data "archive_file" "lambda" {
  count = local.create_lambda_function ? 1 : 0
  type        = "zip"
  source_file = "${path.module}/../../${var.rule_name}/${var.rule_name}.py"
  output_path = "${path.module}/../../${var.rule_name}/${var.rule_name}.zip"
}

# Trust policy to allow Config service to assume Lambda role
data "aws_iam_policy_document" "aws_config_policy_doc" {
  count = local.create_new_lambda_role ? 1 : 0

  statement {
    sid = "AllowLambdaAssumeRole"

    actions = [
      "sts:AssumeRole",
    ]

    principals {
      type = "Service"
      identifiers = [
        "lambda.amazonaws.com",
      ]
    }
  }
}

data "aws_iam_policy" "read_only_access" {
  arn = "arn:${data.aws_partition.current.partition}:iam::aws:policy/ReadOnlyAccess"
}

data "aws_iam_policy_document" "config_iam_policy" {
  count = local.create_new_lambda_role ? 1 : 0
  # Allow reading from the rule bucket
  statement {
    sid       = "AllowGetS3Objects"
    actions   = ["s3:GetObject"]
    resources = ["arn:${data.aws_partition.current.partition}:s3:::${var.source_bucket}/${local.rule_name_source}"]
  }

  # Allow Lambda to log events
  statement {
    sid = "AllowCloudWatchLogging"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
      "logs:DescribeLogStreams",
    ]
    resources = ["arn:aws:logs:*:*:log-group:/aws/lambda/RDK-Rule-Function-*"]
  }

  # Allow Lambda to put evaluations
  statement {
    sid       = "AllowConfigPutEvaluations"
    actions   = ["config:PutEvaluations"]
    resources = ["*"]
  }

  # Allow Lambda to read IAM resource details
  statement {
    sid = "AllowIAMDetailRead"
    actions = [
      "iam:List*",
      "iam:Describe*",
      "iam:Get*",
    ]
    resources = ["arn:aws:iam::*:*"]
  }

  # Allow role assumption -- this has been limited to avoid overly permissive roles
  statement {
    sid       = "AllowAssumeRole"
    actions   = ["sts:AssumeRole"]
    resources = var.arns_lambda_can_assume
  }
}

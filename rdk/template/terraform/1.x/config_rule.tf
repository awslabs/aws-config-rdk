locals {
  event_triggered        = (length(var.source_events) > 0 ? true : false)
  periodic_triggered     = var.source_periodic != "NONE" ? true : false
  create_new_lambda_role = (var.lambda_role_arn == "NONE" ? true : false)
  rule_name_source       = format("%s.zip", var.rule_name)

  rdk_role_name         = format("%s-awsconfig-role", lower(var.rule_name))
  prebuilt_rdk_role_arn = format("arn:aws:iam::%s:role/%s", data.aws_caller_identity.current.account_id, local.rdk_role_name)
  rdk_lambda_rule_role  = local.create_new_lambda_role ? local.prebuilt_rdk_role_arn : var.lambda_role_arn
}

# Define the data sources used to determine the current context of this execution.
data "aws_caller_identity" "current" {}
data "aws_partition" "current" {}

data "aws_iam_policy" "read_only_access" {
  arn = format("arn:%s:iam::aws:policy/ReadOnlyAccess", data.aws_partition.current.partition)
}

data "aws_iam_policy_document" "config_iam_policy" {
  statement {
    sid = "AllowGetS3Objects"

    actions = [
      "s3:GetObject",
    ]

    resources = [
      format("arn:%s:s3:::%s/%s", data.aws_partition.current.partition, var.source_bucket, local.rule_name_source),
    ]
  }

  statement {
    sid = "AllowCloudWatchLogging"

    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
      "logs:DescribeLogStreams",
    ]

    resources = ["*"]
  }

  statement {
    sid = "AllowConfigPutEvaluations"

    actions = [
      "config:PutEvaluations",
    ]

    resources = ["*"]
  }

  statement {
    sid = "AllowIAMDetailRead"

    actions = [
      "iam:List*",
      "iam:Describe*",
      "iam:Get*",
    ]

    resources = ["*"]
  }

  statement {
    sid = "AllowAssumeRole"

    actions = [
      "sts:AssumeRole",
    ]

    resources = ["*"]
  }
}

resource "aws_s3_bucket_object" "rule_code" {
  bucket = var.source_bucket
  key    = local.rule_name_source
  source = local.rule_name_source
}

resource "aws_lambda_function" "rdk_rule" {
  function_name = var.rule_lambda_name
  description   = "Create a new AWS lambda function for rule code"
  runtime       = var.source_runtime
  handler       = var.source_handler
  role          = local.rdk_lambda_rule_role
  timeout       = var.lambda_timeout
  s3_bucket     = var.source_bucket
  s3_key        = local.rule_name_source
  memory_size   = "256"
  layers        = var.lambda_layers

  vpc_config {
    subnet_ids         = var.subnet_ids
    security_group_ids = var.security_group_ids
  }

  depends_on = [
    aws_s3_bucket_object.rule_code,
  ]
}

resource "aws_lambda_permission" "lambda_invoke" {
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.rdk_rule.arn
  principal     = "config.amazonaws.com"
  statement_id  = "AllowExecutionFromConfig"
}

resource "aws_config_config_rule" "event_triggered" {
  count       = local.event_triggered ? 1 : 0
  name        = var.rule_name
  description = var.rule_name

  scope {
    compliance_resource_types = var.source_events
  }

  input_parameters = var.source_input_parameters

  source {
    owner             = "CUSTOM_LAMBDA"
    source_identifier = aws_lambda_function.rdk_rule.arn

    source_detail {
      event_source = "aws.config"
      message_type = "ConfigurationItemChangeNotification"
    }
  }
}

resource "aws_config_config_rule" "periodic_triggered_rule" {
  count       = local.periodic_triggered ? 1 : 0
  name        = var.rule_name
  description = var.rule_name

  input_parameters = var.source_input_parameters

  source {
    owner             = "CUSTOM_LAMBDA"
    source_identifier = aws_lambda_function.rdk_rule.arn

    source_detail {
      event_source                = "aws.config"
      message_type                = "ScheduledNotification"
      maximum_execution_frequency = var.source_periodic
    }
  }


  depends_on = [aws_lambda_permission.lambda_invoke]
}

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

resource "aws_iam_role" "awsconfig" {
  count = local.create_new_lambda_role ? 1 : 0
  name  = local.rdk_role_name

  assume_role_policy = data.aws_iam_policy_document.aws_config_policy_doc[count.index].json
}

resource "aws_iam_policy" "awsconfig_policy" {
  count = local.create_new_lambda_role ? 1 : 0
  name  = format("%s-awsconfig-policy", lower(var.rule_name))

  policy = data.aws_iam_policy_document.config_iam_policy.json
}

resource "aws_iam_role_policy_attachment" "awsconfig_policy_attach" {
  count      = local.create_new_lambda_role ? 1 : 0
  role       = aws_iam_role.awsconfig[count.index].name
  policy_arn = aws_iam_policy.awsconfig_policy[count.index].arn
}

resource "aws_iam_role_policy_attachment" "readonly_role_policy_attach" {
  count      = local.create_new_lambda_role ? 1 : 0
  role       = aws_iam_role.awsconfig[count.index].name
  policy_arn = data.aws_iam_policy.read_only_access.arn
}

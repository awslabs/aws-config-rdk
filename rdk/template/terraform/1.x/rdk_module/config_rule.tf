locals {
  event_triggered        = length(var.source_events) > 0 ? true : false
  periodic_triggered     = var.source_periodic != "" ? true : false
  create_new_lambda_role = var.lambda_role_arn == "" ? true : false
  rule_name_source       = "${var.rule_name}.zip"

  rdk_role_name         = "${lower(var.rule_name)}-awsconfig-role"
  prebuilt_rdk_role_arn = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${local.rdk_role_name}"
  rdk_lambda_rule_role  = local.create_new_lambda_role ? local.prebuilt_rdk_role_arn : var.lambda_role_arn
}

resource "aws_s3_object" "rule_code" {
  bucket = var.source_bucket
  key    = local.rule_name_source
  source = data.archive_file.lambda.output_path
  etag   = filemd5(data.archive_file.lambda.output_path)
}

resource "aws_lambda_function" "rdk_rule" {
  depends_on       = [aws_s3_object.rule_code]
  function_name    = var.rule_lambda_name
  description      = "Create a new AWS Lambda function for rule code"
  runtime          = var.source_runtime
  handler          = var.source_handler
  role             = local.rdk_lambda_rule_role
  timeout          = var.lambda_timeout
  s3_bucket        = aws_s3_object.rule_code.bucket
  s3_key           = aws_s3_object.rule_code.key
  source_code_hash = aws_s3_object.rule_code.etag
  memory_size      = "256"
  layers           = var.lambda_layers

  vpc_config {
    subnet_ids         = var.subnet_ids
    security_group_ids = var.security_group_ids
  }
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
  depends_on  = [aws_lambda_permission.lambda_invoke]
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
}

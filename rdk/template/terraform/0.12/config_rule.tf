

data "aws_caller_identity" "current" {}

data "aws_partition" "current" {}

data "aws_iam_policy" "read_only_access" {
  arn = format("arn:%s:iam::aws:policy/ReadOnlyAccess",data.aws_partition.current.partition)
}

data "aws_iam_policy_document" "config_iam_policy" {

    statement{
      actions=[
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents",
                "logs:DescribeLogStreams"
            ]
      resources = ["*"]
      effect = "Allow"
      sid= "2"
    }
    statement{
      actions=["config:PutEvaluations"]
      resources = ["*"]
      effect = "Allow"
      sid= "3"
    }
    statement{
      actions=[
                "iam:List*",
                "iam:Get*"
            ]
      resources = ["*"]
      effect = "Allow"
      sid= "4"
    }
    statement{
      actions=["sts:AssumeRole"]
      resources = ["*"]
      effect = "Allow"
      sid= "5"
    }

}


provider "aws" {
  profile    = "default"
  
}

resource "aws_s3_bucket_object" "rule_code" {
  bucket = var.source_bucket
  key    = local.rule_name_source
  source = local.rule_name_source

}

resource "aws_lambda_function" "rdk_rule" {

  function_name               = var.rule_lambda_name
  description                 = "Create a new AWS lambda function for rule code"
  runtime                     = var.source_runtime
  handler                     = var.source_handler
  role                        = local.create_new_lambda_role ? format ("arn:aws:iam::%s:role/%s", data.aws_caller_identity.current.account_id,format("%s-awsconfig-role", lower(var.rule_name))) : var.lambda_role_arn
  timeout                     = var.lambda_timeout
  s3_bucket                   = var.source_bucket
  s3_key                      = local.rule_name_source
  memory_size                 = "256"
  layers                      = var.lambda_layers
  vpc_config {
    subnet_ids            = var.subnet_ids
    security_group_ids    = var.security_group_ids
  }

  depends_on = [aws_s3_bucket_object.rule_code]
}

resource "aws_lambda_permission" "lambda_invoke" {
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.rdk_rule.arn
  principal     = "config.amazonaws.com"
  statement_id  = "AllowExecutionFromConfig"
}

resource "aws_config_config_rule" "event_triggered" {
  count = local.event_triggered ? 1 : 0
  name = var.rule_name
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
  count = local.periodic_triggered ? 1 : 0
  name = var.rule_name
  description = var.rule_name

  input_parameters = var.source_input_parameters
  source {
    owner             = "CUSTOM_LAMBDA"
    source_identifier = aws_lambda_function.rdk_rule.arn
    source_detail {
      event_source = "aws.config"
      message_type = "ScheduledNotification"
      maximum_execution_frequency = var.source_periodic
    }
  }


  depends_on = [aws_lambda_permission.lambda_invoke]
}

resource "aws_iam_role" "awsconfig" {
  count = local.create_new_lambda_role ? 1 : 0
  name = format("%s-awsconfig-role", lower(var.rule_name))

  assume_role_policy = <<POLICY
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": "sts:AssumeRole",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Effect": "Allow",
      "Sid": "AllowLambdaAssumeRole"
    }
  ]
}
POLICY
}



resource "aws_iam_policy" "awsconfig_policy" {
  count = local.create_new_lambda_role ? 1 : 0
  name = format("%s-awsconfig-policy", lower(var.rule_name))

  policy = data.aws_iam_policy_document.config_iam_policy.json
}


resource "aws_iam_role_policy_attachment" "awsconfig_policy_attach" {
  count = local.create_new_lambda_role ? 1 : 0
  role       = aws_iam_role.awsconfig[count.index].name
  policy_arn = aws_iam_policy.awsconfig_policy[count.index].arn
}
resource "aws_iam_role_policy_attachment" "readonly-role-policy-attach" {
  count = local.create_new_lambda_role ? 1 : 0
  role       = aws_iam_role.awsconfig[count.index].name
  policy_arn = data.aws_iam_policy.read_only_access.arn
}
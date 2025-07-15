# Required Arguments

variable "rule_name" {
  type        = string
  description = "Rule name to export."
}

variable "rule_lambda_name" {
  type        = string
  description = "Lambda function name for the Config Rule to export."
}

variable "source_runtime" {
  type        = string
  description = "Runtime for lambda function."
}

variable "source_handler" {
  type        = string
  description = "Lambda handler name."
}

variable "source_bucket" {
  type        = string
  description = "Amazon S3 bucket used to export the rule code."
}

variable "source_input_parameters" {
  description = "JSON for required and optional Config parameters."
  type        = string
}

# Optional Arguments

variable "subnet_ids" {
  description = "Comma-separated list of Subnets to deploy your Lambda function(s)."
  type        = list(string)
  default     = []
}

variable "security_group_ids" {
  description = "Comma-separated list of Security Groups to deploy with your Lambda function(s)."
  type        = list(string)
  default     = []
}

variable "source_events" {
  description = "Resource types that will trigger event-based Rule evaluation."
  type        = list(string)
  default     = []
}

variable "lambda_layers" {
  type        = list(string)
  description = "Comma-separated list of Lambda Layer ARNs to deploy with your Lambda function(s)."
  default     = []
}

variable "source_periodic" {
  description = "Maximum execution frequency for scheduled Rules."
  type        = string
  default     = ""
}

variable "lambda_role_arn" {
  description = "Assign existing iam role to lambda functions. If omitted, new lambda role will be created."
  type        = string
  default     = ""
}

variable "lambda_timeout" {
  description = "Lambda function timeout"
  type        = number
  default     = 900
}

variable "arns_lambda_can_assume" {
  description = "List of ARNs/ARN patterns the Lambda function is allowed to assume."
  type        = list(string)
  # These 2 role names represent the bulk of role ARNs used to configure Config
  # However, we support passing an additional ARN just in case.
  default = [
    "arn:aws:iam::*:role/rdk/config-role",
    "arn:aws:iam::*:role/aws-service-role/config.amazonaws.com/AWSServiceRoleForConfig"
  ]
}
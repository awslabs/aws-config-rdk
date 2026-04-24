variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "response_model_arn" {
  type    = string
  default = "anthropic.claude-3-haiku-20240307-v1:0"
}

variable "max_retrieved_chunks" {
  type    = number
  default = 5
}

variable "max_conversation_turns" {
  type    = number
  default = 10
}

variable "rate_limit_per_minute" {
  type    = number
  default = 100
}

variable "burst_limit" {
  type    = number
  default = 200
}

variable "latency_threshold_ms" {
  type    = number
  default = 10000
}

variable "session_ttl_seconds" {
  type    = number
  default = 3600
}

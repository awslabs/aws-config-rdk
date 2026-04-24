resource "aws_s3vectors_vector_bucket" "example" {
  vector_bucket_name = "example-bucket"
}

resource "aws_s3vectors_vector_bucket_policy" "example" {
  vector_bucket_arn = aws_s3vectors_vector_bucket.example.vector_bucket_arn
  policy           = data.aws_iam_policy_document.vector_bucket_permissions.json
}

resource "aws_s3vectors_index" "example" {
  index_name         = "example-index"
  vector_bucket_name = aws_s3vectors_vector_bucket.example.vector_bucket_name

  data_type       = "float32"
  dimension       = 256
  distance_metric = "euclidean"
  metadata_configuration {
    non_filterable_metadata_keys = [
      "AMAZON_BEDROCK_TEXT",
      "AMAZON_BEDROCK_METADATA",
    ]
  }
}

resource "aws_s3_bucket" "knowledge_base_bucket" {
  bucket = "rag-chatbot-kb-bucket-${data.aws_caller_identity.current.account_id}-${data.aws_region.current.region}"
}

resource "aws_s3_bucket_policy" "knowledge_base_bucket_policy" {
  bucket = aws_s3_bucket.knowledge_base_bucket.id
  policy = data.aws_iam_policy_document.kb_permissions_bucket_policy.json
}

resource "aws_s3_bucket" "multimodal_storage" {
  bucket = "rag-chatbot-multimodal-storage-${data.aws_caller_identity.current.account_id}-${data.aws_region.current.region}"
}

resource "aws_s3_bucket_policy" "multimodal_storage_bucket_policy" {
  bucket = aws_s3_bucket.multimodal_storage.id
  policy = data.aws_iam_policy_document.multimodal_storage_permissions_bucket_policy.json
}

resource "aws_iam_role" "example" {
  name = "example-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "bedrock.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy" "kb_policy" {
  name   = "example-kb-policy"
  role   = aws_iam_role.example.id
  policy = data.aws_iam_policy_document.kb_permissions.json
}

resource "aws_bedrockagent_knowledge_base" "example" {
  depends_on = [aws_s3_bucket_policy.knowledge_base_bucket_policy]
  name       = "example"
  role_arn   = aws_iam_role.example.arn
  knowledge_base_configuration {
    vector_knowledge_base_configuration {
      embedding_model_arn = "arn:aws:bedrock:${data.aws_region.current.region}::foundation-model/amazon.titan-embed-text-v2:0"
      supplemental_data_storage_configuration {
        storage_location {
          type = "S3"
          s3_location {
            uri = "s3://${aws_s3_bucket.multimodal_storage.id}"
          }
        }
      }
      embedding_model_configuration {
        bedrock_embedding_model_configuration {
          dimensions          = 256
          embedding_data_type = "FLOAT32"
        }
      }
    }
    type = "VECTOR"
  }

  storage_configuration {
    type = "S3_VECTORS"
    s3_vectors_configuration {
      index_arn = aws_s3vectors_index.example.index_arn
    }
  }
}

resource "awscc_bedrock_data_source" "example" {
  name              = "example-data-source"
  knowledge_base_id = aws_bedrockagent_knowledge_base.example.id
  data_source_configuration = {
    s3_configuration = {
      bucket_arn = aws_s3_bucket.knowledge_base_bucket.arn
    }
    type = "S3"
  }
}

resource "aws_dynamodb_table" "session_table" {
  name         = "rag-chatbot-session-table"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "sessionId"

  attribute {
    name = "sessionId"
    type = "S"
  }
}

resource "aws_iam_role" "lambda_role" {
  name               = "rag-chatbot-query-handler-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
}

resource "aws_iam_role_policy" "lambda_policy" {
  name   = "rag-chatbot-query-handler-policy"
  role   = aws_iam_role.lambda_role.id
  policy = data.aws_iam_policy_document.lambda_policy.json
}

resource "aws_lambda_function" "query_handler" {
  function_name    = "rag-chatbot-query-handler"
  runtime          = "python3.14"
  handler          = "handler.handler"
  role             = aws_iam_role.lambda_role.arn
  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256

  environment {
    variables = {
      KNOWLEDGE_BASE_ID      = aws_bedrockagent_knowledge_base.example.id
      RESPONSE_MODEL_ARN     = var.response_model_arn
      MAX_RETRIEVED_CHUNKS   = tostring(var.max_retrieved_chunks)
      MAX_CONVERSATION_TURNS = tostring(var.max_conversation_turns)
      SESSION_TABLE_NAME     = aws_dynamodb_table.session_table.name
      SESSION_TTL_SECONDS    = tostring(var.session_ttl_seconds)
      LATENCY_THRESHOLD_MS   = tostring(var.latency_threshold_ms)
      METRICS_NAMESPACE      = "RagChatbotApi"
    }
  }
}

resource "aws_api_gateway_rest_api" "api" {
  name        = "rag-chatbot-api"
  description = "RAG Chatbot API"
}

resource "aws_api_gateway_resource" "query" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  parent_id   = aws_api_gateway_rest_api.api.root_resource_id
  path_part   = "query"
}

resource "aws_api_gateway_method" "query_post" {
  rest_api_id      = aws_api_gateway_rest_api.api.id
  resource_id      = aws_api_gateway_resource.query.id
  http_method      = "POST"
  authorization    = "NONE"
  api_key_required = true
}

resource "aws_api_gateway_integration" "query_post" {
  rest_api_id             = aws_api_gateway_rest_api.api.id
  resource_id             = aws_api_gateway_resource.query.id
  http_method             = aws_api_gateway_method.query_post.http_method
  type                    = "AWS_PROXY"
  integration_http_method = "POST"
  uri                     = aws_lambda_function.query_handler.invoke_arn
}

resource "aws_api_gateway_deployment" "api" {
  rest_api_id = aws_api_gateway_rest_api.api.id

  depends_on = [aws_api_gateway_integration.query_post]
}

resource "aws_api_gateway_stage" "prod" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  deployment_id = aws_api_gateway_deployment.api.id
  stage_name    = "prod"
}

resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.query_handler.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.api.execution_arn}/*/*"
}

resource "aws_api_gateway_api_key" "chatbot" {
  name    = "ChatbotApiKey"
  enabled = true
}

resource "aws_api_gateway_usage_plan" "chatbot" {
  name = "ChatbotUsagePlan"

  api_stages {
    api_id = aws_api_gateway_rest_api.api.id
    stage  = aws_api_gateway_stage.prod.stage_name
  }

  throttle_settings {
    rate_limit  = var.rate_limit_per_minute
    burst_limit = var.burst_limit
  }
}

resource "aws_api_gateway_usage_plan_key" "chatbot_key" {
  key_id        = aws_api_gateway_api_key.chatbot.id
  key_type      = "API_KEY"
  usage_plan_id = aws_api_gateway_usage_plan.chatbot.id
}

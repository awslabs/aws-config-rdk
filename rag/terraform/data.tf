data "aws_region" "current" {}
data "aws_caller_identity" "current" {}

data "aws_iam_policy_document" "lambda_assume_role" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

data "aws_iam_policy_document" "lambda_policy" {
  statement {
    effect = "Allow"

    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]

    resources = ["*"]
  }

  statement {
    effect = "Allow"

    actions = [
      "bedrock:InvokeModel",
      "bedrock:Retrieve",
      "bedrock:RetrieveAndGenerate"
    ]

    resources = ["*"]
  }

  statement {
    effect = "Allow"

    actions = [
      "dynamodb:GetItem",
      "dynamodb:PutItem",
      "dynamodb:UpdateItem",
      "dynamodb:DeleteItem",
      "dynamodb:Query",
      "dynamodb:Scan",
      "dynamodb:BatchGetItem",
      "dynamodb:BatchWriteItem"
    ]

    resources = [
      aws_dynamodb_table.session_table.arn,
      "${aws_dynamodb_table.session_table.arn}/*"
    ]
  }
}

data "aws_iam_policy_document" "multimodal_storage_permissions_bucket_policy" {
  statement {
    effect = "Allow"

    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:ListBucket"
    ]

    resources = [
      aws_s3_bucket.multimodal_storage.arn,
      "${aws_s3_bucket.multimodal_storage.arn}/*"
    ]
    principals {
      identifiers = ["bedrock.amazonaws.com"]
      type        = "Service"
    }
    principals {
      identifiers = [aws_iam_role.example.arn]
      type        = "AWS"
    }
  }
}

data "aws_iam_policy_document" "kb_permissions_bucket_policy" {
  statement {
    effect = "Allow"

    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:ListBucket"
    ]

    resources = [
      aws_s3_bucket.knowledge_base_bucket.arn,
      "${aws_s3_bucket.knowledge_base_bucket.arn}/*",
    ]
    principals {
      identifiers = ["bedrock.amazonaws.com"]
      type        = "Service"
    }
    principals {
      identifiers = [aws_iam_role.example.arn]
      type        = "AWS"
    }
  }
}

data "aws_iam_policy_document" "kb_permissions" {
  statement {
    effect = "Allow"

    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:ListBucket",
      "s3:*",
    ]
    resources = [
      aws_s3vectors_vector_bucket.example.vector_bucket_arn,
      "${aws_s3vectors_vector_bucket.example.vector_bucket_arn}/*",
      aws_s3_bucket.knowledge_base_bucket.arn,
      "${aws_s3_bucket.knowledge_base_bucket.arn}/*",
      aws_s3_bucket.multimodal_storage.arn,
      "${aws_s3_bucket.multimodal_storage.arn}/*"
    ]
  }
  statement {
    effect = "Allow"

    actions = [
      "s3vectors:PutIndex",
      "s3vectors:GetIndex",
      "s3vectors:DeleteIndex",
      "s3vectors:PutVectors"
    ]
    resources = [
      aws_s3vectors_index.example.index_arn
    ]
  }
  statement {
    effect = "Allow"

    actions = [
      "s3vectors:QueryVectors",
      "s3vectors:Describe*",
      "s3vectors:Get*",
      "s3vectors:List*",
    ]
    resources = [
      "*"
    ]
  }
  statement {
    effect = "Allow"

    actions = [
      "bedrock:InvokeModel",
    ]
    resources = ["*"]
  }
}

data "aws_iam_policy_document" "vector_bucket_permissions" {
  statement {
    effect = "Allow"

    actions = [
      "s3vectors:*", # could be PutVectors if scoping down
    ]
    resources = [
      aws_s3vectors_vector_bucket.example.vector_bucket_arn,
      "${aws_s3vectors_vector_bucket.example.vector_bucket_arn}/*"
    ]
    principals {
      identifiers = ["arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"]
      type        = "AWS"
    }
  }
}


data "archive_file" "lambda_zip" {
  type        = "zip"
  source_file = "${path.module}/../lambda-python/handler.py"
  output_path = "${path.module}/build/query-handler.zip"

}


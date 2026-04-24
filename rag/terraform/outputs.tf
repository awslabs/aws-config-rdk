output "api_endpoint" {
  value       = aws_api_gateway_stage.prod.invoke_url
  description = "The public API Gateway endpoint for the RAG chatbot."
}

# output "api_key" {
#   value       = aws_api_gateway_api_key.chatbot.value
#   description = "API key created for the chatbot API."
# }

output "lambda_function_name" {
  value       = aws_lambda_function.query_handler.function_name
  description = "Name of the deployed Lambda function."
}

output "session_table_name" {
  value       = aws_dynamodb_table.session_table.name
  description = "Name of the DynamoDB session table."
}

# Terraform deployment for RAG Chatbot

This Terraform configuration deploys the same RAG chatbot infrastructure.

## Key behavior

- The Lambda function source remains in `../lambda-python/handler.py`.
- Docs need to be manually uploaded to the S3 bucket created by TF, then synced. After that, the solution can be queried to ask it any questions about RDK documentation (assuming that's what you uploaded).
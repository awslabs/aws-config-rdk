import json
import os
import uuid
import datetime
import logging
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
if not logger.handlers:
    logger.setLevel(logging.INFO)


def _get_env(name, default=None):
    value = os.getenv(name)
    if value is None or value == '':
        return default
    return value


def _get_int_env(name, default):
    value = _get_env(name)
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def get_dynamo_table():
    table_name = _get_env('SESSION_TABLE_NAME', '')
    return boto3.resource('dynamodb').Table(table_name)


def get_bedrock_client():
    session = boto3.Session()
    for service_name in ('bedrock-agent-runtime', 'bedrock-runtime'):
        if service_name in session.get_available_services():
            return session.client(service_name)
    return boto3.client('bedrock-agent-runtime')


def extract_citations(bedrock_response):
    citations = []
    for citation in (bedrock_response.get('citations') or []):
        if not isinstance(citation, dict):
            continue
        for ref in (citation.get('retrievedReferences') or []):
            if not isinstance(ref, dict):
                continue
            passage = ''
            content = ref.get('content')
            if isinstance(content, dict):
                passage = content.get('text', '') or ''
            uri = ''
            location = ref.get('location')
            if isinstance(location, dict):
                uri = location.get('s3Location', {}).get('uri', '') or ''
            document_name = uri.split('/')[-1] if uri else ''
            citations.append({'documentName': document_name, 'passage': passage})
    return citations


def truncate_history(history, max_turns):
    if max_turns <= 0:
        return []
    if len(history) <= max_turns:
        return history
    return history[-max_turns:]


def log_request(request_id, status_code, latency_ms):
    logger.info(json.dumps({
        'level': 'info',
        'message': 'request_completed',
        'requestId': request_id,
        'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'statusCode': status_code,
        'latencyMs': latency_ms,
    }))


def publish_metrics(metrics, namespace):
    metric_definitions = [{'Name': m['name'], 'Unit': m['unit']} for m in metrics]
    emf_log = {
        '_aws': {
            'Timestamp': int(datetime.datetime.now(datetime.timezone.utc).timestamp() * 1000),
            'CloudWatchMetrics': [
                {
                    'Namespace': namespace,
                    'Dimensions': [],
                    'Metrics': metric_definitions,
                }
            ],
        }
    }
    for m in metrics:
        emf_log[m['name']] = m['value']
    logger.info(json.dumps(emf_log))


def check_latency_warning(request_id, latency_ms, threshold_ms):
    if latency_ms > threshold_ms:
        logger.warning(json.dumps({
            'level': 'warning',
            'message': 'high_latency',
            'requestId': request_id,
            'latencyMs': latency_ms,
        }))


def load_session(session_id):
    if not session_id:
        return []
    try:
        result = get_dynamo_table().get_item(Key={'sessionId': session_id})
        history = result.get('Item', {}).get('history')
        return history if isinstance(history, list) else []
    except Exception as err:
        logger.error(json.dumps({
            'level': 'error',
            'message': 'session_load_failed',
            'sessionId': session_id,
            'error': str(err),
        }))
        return []


def save_session(session_id, history):
    if not session_id:
        return
    try:
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        expires_at = int(datetime.datetime.now(datetime.timezone.utc).timestamp()) + _get_int_env('SESSION_TTL_SECONDS', 3600)
        get_dynamo_table().put_item(Item={
            'sessionId': session_id,
            'history': history,
            'createdAt': now,
            'updatedAt': now,
            'expiresAt': expires_at,
        })
    except Exception as err:
        logger.error(json.dumps({
            'level': 'error',
            'message': 'session_save_failed',
            'sessionId': session_id,
            'error': str(err),
        }))


def json_response(status_code, body):
    return {
        'statusCode': status_code,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps(body),
    }


def is_bedrock_error(err):
    if isinstance(err, ClientError):
        return True
    if hasattr(err, 'response') and isinstance(err.response, dict):
        return True
    message = str(err) if err is not None else ''
    return 'Bedrock' in message or 'ThrottlingException' in message or 'AccessDeniedException' in message


def handler(event, context):
    start_time = datetime.datetime.now(datetime.timezone.utc)
    request_id = str(uuid.uuid4())
    status_code = 200

    try:
        body = json.loads(event.get('body') or '{}')
    except Exception:
        status_code = 400
        return json_response(status_code, {
            'error': 'Invalid JSON in request body',
            'requestId': request_id,
        })

    query = body.get('query')
    if not isinstance(query, str) or not query.strip():
        status_code = 400
        return json_response(status_code, {
            'error': 'Query field is required and must be non-empty',
            'requestId': request_id,
        })

    session_id = body.get('sessionId') or str(uuid.uuid4())
    history = load_session(session_id) if body.get('sessionId') else []
    history = truncate_history(history, _get_int_env('MAX_CONVERSATION_TURNS', 10))

    bedrock_input = {
        'input': {'text': query},
        'retrieveAndGenerateConfiguration': {
            'type': 'KNOWLEDGE_BASE',
            'knowledgeBaseConfiguration': {
                'knowledgeBaseId': _get_env('KNOWLEDGE_BASE_ID', ''),
                'modelArn': _get_env('RESPONSE_MODEL_ARN', 'anthropic.claude-3-haiku-20240307-v1:0'),
                'retrievalConfiguration': {
                    'vectorSearchConfiguration': {
                        'numberOfResults': _get_int_env('MAX_RETRIEVED_CHUNKS', 5),
                    }
                },
            },
        },
    }

    try:
        bedrock_response = get_bedrock_client()._make_api_call('RetrieveAndGenerate', bedrock_input)
        answer = ''
        if isinstance(bedrock_response, dict):
            output = bedrock_response.get('output')
            if isinstance(output, dict):
                answer = output.get('text', '') or ''

        citations = extract_citations(bedrock_response)
        updated_history = [*history, {
            'query': query,
            'answer': answer,
            'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }]
        save_session(session_id, updated_history)

        return json_response(200, {
            'answer': answer,
            'citations': citations,
            'sessionId': session_id,
            'requestId': request_id,
        })

    except Exception as err:
        if is_bedrock_error(err):
            status_code = 502
            logger.error(json.dumps({
                'level': 'error',
                'message': 'bedrock_error',
                'requestId': request_id,
                'error': str(err),
            }))
            return json_response(status_code, {
                'error': 'Knowledge base service unavailable',
                'requestId': request_id,
            })

        status_code = 500
        logger.error(json.dumps({
            'level': 'error',
            'message': 'unexpected_error',
            'requestId': request_id,
            'error': str(err),
        }))
        return json_response(status_code, {
            'error': 'Internal server error',
            'requestId': request_id,
        })

    finally:
        latency_ms = int((datetime.datetime.now(datetime.timezone.utc) - start_time).total_seconds() * 1000)
        log_request(request_id, status_code, latency_ms)
        metrics = [
            {'name': 'RequestCount', 'value': 1, 'unit': 'Count'},
            {'name': 'Latency', 'value': latency_ms, 'unit': 'Milliseconds'},
        ]
        if status_code >= 400:
            metrics.append({'name': 'ErrorCount', 'value': 1, 'unit': 'Count'})
        publish_metrics(metrics, _get_env('METRICS_NAMESPACE', 'RagChatbotApi'))
        check_latency_warning(request_id, latency_ms, _get_int_env('LATENCY_THRESHOLD_MS', 10000))

RULE = __import__('<%RuleName%>')

def lambda_handler(event, context):
    return RULE.internal_lambda_handler(event, context)

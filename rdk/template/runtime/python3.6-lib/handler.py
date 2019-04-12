RULE = __import__('<%RuleName%>')

def lambda_handler(event, context):
    my_rule = RULE.<%RuleName%>()
    return my_rule.internal_lambda_handler(event, context)

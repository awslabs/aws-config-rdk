# Introduction

RDK creates an `evaluate_compliance()` function for you, but you don’t need to keep the default structure; you can even create multiple functions to evaluate compliance. We’re going to start with the default structure and keep building on top of it in the following examples.

## Compliance evaluation function for evaluations triggered by periodic frequency

> :warning: This section uses helper functions (eg. `build_evaluation()`) that are only present in non-`rdklib` runtimes. If you are using an `rdklib` runtime (eg. `python3.12-lib`), most of this guidance will not be relevant to you.

One of the `evaluate_compliance()` function's inputs is `event`. See [Example Events for AWS Config Rules](https://docs.aws.amazon.com/config/latest/developerguide/evaluate-config_develop-rules_example-events.html) for more information. Events have different type of information required to evaluate compliance of AWS resources based on Config rule type.

For periodic trigger type rules, the _messageType_ element in _invokingEvent_ element of Event has the value of _ScheduledNotification_. Scheduled compliance validation usually checks numerous resources of same type for compliance and the published event has no _Configuration_item_ so you should use AWS SDK (i.e. [boto3](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/quickstart.html) for python) to gather required information for compliance evaluation.

Imagine you want to scan your account for IAM roles with no policies attached to them and report them as non-compliant resources. Once you have created your rule and set `-m` , `--maximum-frequency` option of `rdk create` command to the desired value, AWS Config triggers your rule at the set frequency and your Lambda function calls the `evaluate_compliance()` function to report the results.
Let’s build the logic:

1. Initiate an empty evaluations list: `evaluations = []`
2. Create a boto3 client representing AWS Identity and Access Management (IAM): `iam_client = get_client('iam', event)`
we use get_client function which is defined in our skeleton file to create the client.
1. Getting a list of roles: `roles_list = iam_client.list_roles()`
2. We can create a loop and for every role gather a list of attached inline policies and managed policies.
   1. Inline policies: `role_policies_inline = iam_client.list_role_policies(RoleName=role_name)['PolicyNames']`
   2. Managed policies: `role_policies_managed = iam_client.list_attached_role_policies(RoleName=role_name)['AttachedPolicies']`
3. Finally, we’re going to check the length of inline and managed policy arrays and if it is equal to zero, it means the role does not have any attached policies and is noncompliant.
4. We use build_evaluation function, already defined in our skeleton file to create an evaluation dictionary and append it to the evaluation list initiated on step1.

Here's the fully-developed `evaluate_compliance()` function for this example:

```python
def evaluate_compliance(event, configuration_item, valid_rule_parameters):
    evaluations = []
    iam_client = get_client('iam', event)

    roles_list = iam_client.list_roles()

    while True:

        for role in roles_list['Roles']:
            role_name = role['RoleName']
            role_policies_inline = iam_client.list_role_policies(RoleName=role_name)['PolicyNames']
            role_policies_managed = iam_client.list_attached_role_policies(RoleName=role_name)['AttachedPolicies']
            if len(role_policies_inline)+len(role_policies_managed) == 0 :
                evaluations.append(build_evaluation(role['RoleId'], 'NON_COMPLIANT', event, resource_type='AWS::IAM::Role'))
                continue

            evaluations.append(build_evaluation(role['RoleId'], 'COMPLIANT', event, resource_type='AWS::IAM::Role'))

        # Marker is used for pagination, in cases where the API call returns too many results to display at once
        if "Marker" in roles_list:
                roles_list = iam_client.list_roles(Marker=roles_list["Marker"])
        else:
            break

    if not evaluations:
        evaluations.append(build_evaluation(event['accountId'],'NOT_APPLICABLE', event, resource_type='AWS::::Account'))
    return evaluations

```

Make sure to read the `boto3` documentation for each class you are using to understand its limitations and capabilities. In our case, the `list_roles` method might not return a complete list of roles in one call, so we use a `while` loop to check for `Marker` in the results to make subsequent calls in case of receiving a truncated role list. Read more about Marker on `list_roles` method [documentation](https://boto3.amazonaws.com/v1/documentation/api/1.9.42/reference/services/iam.html#IAM.Client.list_roles).

Notes:

- For compliant resources, we are also creating an evaluation dictionary and appending it to the evaluation list.
- You can remove any unused arguments of the `evaluate_compliance` function definition, as long as you also remove them from when the `lambda_handler` function calls `evaluate_compliance`.
- The `build_evaluation` function returns an evaluation dictionary (refer to previous section for more information).

## Compliance evaluation function for evaluations triggered by configuration changes

For configuration change type rules, the _messageType_ element in _invokingEvent_ element of Event has the value of _ConfigurationItemChangeNotification_. If the returned _messageType_ value is _OversizedConfigurationItemChangeNotification_, helper functions will automatically pull resource’s Configuration_item, so you don’t need to do anything. _invokingEvent_ also contains Configuration_item which provides information on the changed resource. We are going to recreate the previous function, this time using information included in Configuration_item. To view an example of information included in a Configuration_item you can:
Run `rdk sample-ci <resource type>`, or check the AWS Config Resource Schema repository on GitHub. Every time an AWS resource type indicated during rule creation is changed, this rule will be triggered and an event will be published (e.g. in our case if an IAM role is change, an event would be published).

We can recreate the example in the previous section using Configuration_item. IAM Role Configuration_item includes `rolePolicyList` (inline policies) and `attachedManagedPolicies` (managed policies) keys in its `configuration` element. With this information our assessment logic can be done in one step:

- Check the length of `rolePolicyList` and `attachedManagedPolicies` arrays and return `NON_COMPLIANT` if both are equal to 0.

Here's the fully-developed `evaluate_compliance` function for this example:

```python
def evaluate_compliance(event, configuration_item, valid_rule_parameters):

    if len(configuration_item['configuration']['attachedManagedPolicies'])+len(configuration_item['configuration']['rolePolicyList']) == 0:
        return 'NON_COMPLIANT'
    
    return 'COMPLIANT'

```

Notes:

- Once you deploy the rule, AWS Config evaluates all the resources in scope using the already available configuration items (it does not create a new configuration item unless the resource is changed)
- After the initial evaluation, Config runs compliance evaluation for configuration change triggered rules once resource at a time and when the resource changes.
- If the configuration_item does not provide all the necessary information for compliance evaluation, you can use boto3 to gather any extra information you require to complete the evaluation.
- In this example, the `evaluate_compliance` function returns the compliance status as a string. If `lambda_handler` receives a string from `evaluate_compliance` functions, it uses the `build_evaluation_from_config_item` function to build compliance results.
  - The `build_evaluation_from_config_item` function returns an evaluation dictionary (refer to previous section for more information)
- If you need to add annotations to your compliance results, instead of returning a string, you can call `build_evaluation_from_config_item` function and pass the annotation string.

Here's the modified `evaluate_compliance` function to include annotations in compliance evaluation:

```python
def evaluate_compliance(event, configuration_item, valid_rule_parameters):

    if len(configuration_item['configuration']['attachedManagedPolicies'])+len(configuration_item['configuration']['rolePolicyList']) == 0:
        return build_evaluation_from_config_item(configuration_item, 'NON_COMPLIANT', annotation='Your custom annotation')
    
    return 'COMPLIANT'
```

## Compliance evaluation function for evaluations for hybrid trigger type

Writing evaluation logic for these types of rules is rather complicated and need to be very well-thought of before execution. It’s best not to create hybrid triggered rules unless you can’t accomplish compliance evaluation using periodic or change-triggered rules.

Imagine a scenario where you need assess your resources periodically and upon any resource changes, for example you want a Config rule that checks for unused IAM Roles, but it ignores newly created roles for a few days (role cooldown period). In this scenario if you rely only on configuration change triggers, your new roles will be marked non-compliant upon creation (technically they have never been used before), so you need another mechanism to check them regularly to assess their compliance. In this case you can modify your evaluation logic to accommodate both trigger types. One way to do this is modifying the `evaluate_compliance` function to take an extra argument:

```python
def evaluate_compliance(event, configuration_item, valid_rule_parameters, message_type):
    if message_type in ["ConfigurationItemChangeNotification","OversizedConfigurationItemChangeNotification"]:
        # Add evaluation logic for configuration change trigger type
    else:
        # Add evaluation logic for scheduled trigger type

```

When calling the `evaluate_compliance` function from lambda_handler function, pass `invoking_event['messageType']` as message type:

```python
compliance_result = evaluate_compliance(event, configuration_item, valid_rule_parameters, invoking_event['messageType'])
```

Another way would be creating two separate functions, one for periodic evaluations and one for configuration change triggered evaluations, and modifying lambda_handler function to call the proper function based on the `invoking_event['messageType']` (trigger type):

```python
...
if invoking_event['messageType'] in ["ConfigurationItemChangeNotification","OversizedConfigurationItemChangeNotification"]:
            compliance_result = evaluate_changetrigger_compliance(event, configuration_item, rule_parameters)
        elif invoking_event['messageType'] == 'ScheduledNotification':
            compliance_result = evaluate_scheduled_compliance(event, configuration_item, rule_parameters)
        else:
            return {'internalErrorMessage': 'Unexpected message type ' + str(invoking_event)}
...
```

Once you pick the best approach for your evaluation logic, the rest would be similar to what we covered on previous sections for periodic and configuration change triggered rules.

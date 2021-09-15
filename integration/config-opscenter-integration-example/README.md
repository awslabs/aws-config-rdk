### AWS Config and OpsCenter integration ###

This is an example showing how we can create a CloudWatch event to monitoring
a change of compliance status and create an OpsItem in OpsCenter.

# Scenario

User wants to leverage OpsCenter to have a central location where operations engineers and IT professionals
can view, investigate, and resolve operational work items (OpsItems) related to AWS resources. User also wants
to create OpsItem automatically on non-compliant resouces found by AWS Config. In addition, OpsCenter provides
action action to trigger a runbook. Engineers/professionals can easily trigger the remediation process with this
feature.


# Example Walkthrough

pre-requisite:
    aws account,
    awscli,
    IAM role permission to create config rules, cloudwatch event and opsitem with cloudformation

1. execute "sh build.sh"
    - create an IAM role and a managed config rule that checks if server side encryption enabled for a S3 bucket

2. [Optional] Create a non-encrypted S3 bucket if you do not have one

3. Go to AWS Config > Rules > my-config-rule-S3BucketServerSideEncryptionEnabled in Console
    - click action button and select re-evaluate

4. Once the evaluation is done, go to AWS Systems Manager > OpsCenter in the console and user will see OpsItems created
    - User can get the details for the non-compliant resources, suggested runbook for remediation
    - User can execute the runbook to resolve the issue.
    - Please check the doc for more information on OpsCenter
        https://docs.aws.amazon.com/systems-manager/latest/userguide/OpsCenter.html

5. execute "sh cleanup.sh"

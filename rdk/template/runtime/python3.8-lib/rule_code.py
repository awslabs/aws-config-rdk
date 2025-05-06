from rdklib import Evaluator, Evaluation, ConfigRule, ComplianceType
<%ApplicableResources1%>
class <%RuleName%>(ConfigRule):
    # NOTE - you should typically only implement one of evaluate_change() or evaluate_periodic()!
    # If implementing a periodic rule, you will need to delete evaluate_change() and uncomment evaluate_periodic()

    def evaluate_change(self, event, client_factory, configuration_item, valid_rule_parameters):
        ################################################
        # Add your custom change-triggered logic here. #
        ################################################

        return [Evaluation(ComplianceType.NOT_APPLICABLE)]


    # def evaluate_periodic(self, event, client_factory, valid_rule_parameters):
    # ########################################
    # # Add your custom periodic logic here. #
    # ########################################
    # # If you are evaluating resources that are not supported by the Config Service...
    # # ...it is often helpful to specify the account as the resource type/ID 
    #     account_id = event['accountId']
    #     return [
    #         Evaluation(
    #             complianceType=ComplianceType.COMPLIANT,
    #             resourceId=account_id,
    #             resourceType="AWS::::Account",
    #             annotation="Use this field to explain why this evaluation occurred.",
    #         )
    #     ]
            

    def evaluate_parameters(self, rule_parameters):
        valid_rule_parameters = rule_parameters
        return valid_rule_parameters


################################
# DO NOT MODIFY ANYTHING BELOW #
################################
def lambda_handler(event, context):
    my_rule = <%RuleName%>()
    evaluator = Evaluator(my_rule<%ApplicableResources2%>)
    return evaluator.handle(event, context)

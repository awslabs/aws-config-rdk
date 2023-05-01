from rdklib import Evaluator, Evaluation, ConfigRule, ComplianceType
<%ApplicableResources1%>
class <%RuleName%>(ConfigRule):
    def evaluate_change(self, event, client_factory, configuration_item, valid_rule_parameters):
        ###############################
        # Add your custom logic here. #
        ###############################

        return [Evaluation(ComplianceType.NOT_APPLICABLE)]

    #def evaluate_periodic(self, event, client_factory, valid_rule_parameters):
    #    pass

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

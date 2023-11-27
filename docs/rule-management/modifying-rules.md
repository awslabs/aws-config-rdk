# Modifying rules

Once you have created the rule, you can modify your rules by either editing _parameters.json_ or by running `rdk modify` command which takes the same arguments and options as `rdk create` command.

To edit your rule evaluation logic, edit the python file in your rule
directory to add whatever logic your Rule requires in the
`evaluate_compliance` function (view [Writing and evaluate_compliance function for more information](./rdk-lambda-function/writing-an-evaluate_compliance-function.md)).
It is worth noting that until you actually call the `deploy` command
your rule only exists in your working directory, none of the Rule
commands discussed thus far actually makes changes to your account.

resource "aws_iam_role" "awsconfig" {
  count = local.create_new_lambda_role ? 1 : 0
  name  = local.rdk_role_name

  assume_role_policy = data.aws_iam_policy_document.aws_config_policy_doc[count.index].json
}

resource "aws_iam_policy" "awsconfig_policy" {
  count = local.create_new_lambda_role ? 1 : 0
  name  = "${lower(var.rule_name)}-awsconfig-policy"

  policy = data.aws_iam_policy_document.config_iam_policy.json
}

resource "aws_iam_role_policy_attachment" "awsconfig_policy_attach" {
  count      = local.create_new_lambda_role ? 1 : 0
  role       = aws_iam_role.awsconfig[count.index].name
  policy_arn = aws_iam_policy.awsconfig_policy[count.index].arn
}

resource "aws_iam_role_policy_attachment" "readonly_role_policy_attach" {
  count      = local.create_new_lambda_role ? 1 : 0
  role       = aws_iam_role.awsconfig[count.index].name
  policy_arn = data.aws_iam_policy.read_only_access.arn
}

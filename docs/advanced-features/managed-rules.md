# Managed Rules

The RDK is able to deploy AWS Managed Rules.

To do so, create a rule using `rdk create` and provide a valid
SourceIdentifier via the `--source-identifier` CLI option. The list of
Managed Rules can be found
[here](https://docs.aws.amazon.com/config/latest/developerguide/managed-rules-by-aws-config.html)
, and note that the Identifier can be obtained by replacing the dashes
with underscores and using all capitals (for example, the
"guardduty-enabled-centralized" rule has the SourceIdentifier
"GUARDDUTY_ENABLED_CENTRALIZED"). Just like custom Rules you will need
to specify source events and/or a maximum evaluation frequency, and also
pass in any Rule parameters. The resulting Rule directory will contain
only the parameters.json file, but using `rdk deploy` or
`rdk create-rule-template` can be used to deploy the Managed Rule like
any other Custom Rule.

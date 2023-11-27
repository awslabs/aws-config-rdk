# RuleSets

New as of version 0.3.11, it is possible to add RuleSet tags to rules
that can be used to deploy and test groups of rules together. Rules can
belong to multiple RuleSets, and RuleSet membership is stored only in
the parameters.json metadata. The [deploy](../commands/deploy.md),
[create-rule-template](../commands/create-rule-template.md), and [test-local](../commands/test-local.md)
commands are RuleSet-aware such that a RuleSet can be passed in as the
target instead of `--all` or a specific named Rule.

A comma-delimited list of RuleSets can be added to a Rule when you
create it (using the `--rulesets` flag), as part of a `modify` command,
or using new `ruleset` subcommands to add or remove individual rules
from a RuleSet.

Running `rdk rulesets list` will display a list of the RuleSets
currently defined across all of the Rules in the working directory

```bash
rdk rulesets list
RuleSets:  AnotherRuleSet MyNewSet
```

Naming a specific RuleSet will list all of the Rules that are part of
that RuleSet.

```bash
rdk rulesets list AnotherRuleSet
Rules in AnotherRuleSet :  RSTest
```

Rules can be added to or removed from RuleSets using the `add` and
`remove` subcommands:

```bash
rdk rulesets add MyNewSet RSTest
RSTest added to RuleSet MyNewSet

rdk rulesets remove AnotherRuleSet RSTest
RSTest removed from RuleSet AnotherRuleSet
```

RuleSets are a convenient way to maintain a single repository of Config
Rules that may need to have subsets of them deployed to different
environments. For example your development environment may contain some
of the Rules that you run in Production but not all of them; RuleSets
gives you a way to identify and selectively deploy the appropriate Rules
to each environment.

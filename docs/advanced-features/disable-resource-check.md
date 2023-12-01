# Disable the supported resource types check

It is now possible to define a resource type that is not yet supported
by rdk. To disable the supported resource check use the optional flag
'--skip-supported-resource-check' during the create command.

```bash
rdk create MyRule --runtime python3.11 --resource-types AWS::New::ResourceType --skip-supported-resource-check
'AWS::New::ResourceType' not found in list of accepted resource types.
Skip-Supported-Resource-Check Flag set (--skip-supported-resource-check), ignoring missing resource type error.
Running create!
Local Rule files created.
```

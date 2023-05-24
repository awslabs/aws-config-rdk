# Developer Notes

These notes are intended to help RDK developers update the repository consistently.

## New Runtime Support Process

These instructions document the parts of the repository that need to be updated when support for a new Lambda runtime is added.

### Update pyproject.toml

- Add to `classifiers` list:

```yaml
"Programming Language :: Python :: <VER>,"
```

- Add to `include` list:

```yaml
"rdk/template/runtime/python<VER>/*",
"rdk/template/runtime/python<VER>-lib/*",
```

### Update README.md

- Update documentation and examples

### Update rdk.py

- Update references to include new version

### Update Linux and Windows Buildspec files (`testing` folder)

- Add new test cases for the new version

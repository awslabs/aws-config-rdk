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

## New Version Release Process (for Maintainers)

To release a new version of RDK...

1. Update `pyproject.toml` with the new version number
2. Update `rdk/__init__.py`  with the new version number
3. Locally `git pull origin master` to ensure you have the latest code
4. Locally `git push --tags <new version number>` to create a tagged version, which will kick off the remaining workflows.
# New Runtime Support Process
These instructions document the parts of the repository that need to be updated when support for a new Lambda runtime is added.

## Update pyproject.toml

- Add to `classifiers` list:
```
"Programming Language :: Python :: <VER>,"
```

- Add to `include` list:     
```
"rdk/template/runtime/python<VER>/*",
"rdk/template/runtime/python<VER>-lib/*",
```

## Update README.rst

- Update documentation and examples

## Update getting_started.rst

- Update examples

## Update rdk.py

- Update references to include new version

## Update Linux and Windows Buildspec files (`testing` folder)

- Add new test cases for the new version
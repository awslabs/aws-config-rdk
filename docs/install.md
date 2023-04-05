## Prerequisites

RDK requires `cdk` version 2 (or higher) to be installed and available in the `PATH`. 

RDK is developed in Python and requires Python v3.8 (or higher).

## Installing RDK

RDK is distributed as a Python Package (`rdk`)

### Using `pip`

_CLI_:

```bash
pip install 'rdk>=1,<2'
```

_requirements.txt_:

```text
rdk>=1,<2
```

### Using `pipenv`

_CLI_:

```bash
pipenv install 'rdk>=1,<2'
```

_Pipfile_:

```toml
[[source]]
name = "pypi"
verify_ssl = true

[packages]
rdk = ">=1,<2"
```

### Using `poetry`

_CLI_:

```bash
poetry add 'rdk>=1,<2'
```

_pyproject.toml_:

```toml
[tool.poetry]
[[tool.poetry.source]]
name = "pypi"
default = true

[tool.poetry.dependencies]
rdk = ">=1,<2"
```

### Using `pipx`

```bash
pipx install 'rdk>=1,<2'
```

### Using `conda`

```bash
conda install 'rdk>=1,<2'
```

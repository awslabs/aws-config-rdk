#!/usr/bin/env bash

################################################################################
# GENERATE CLI REFERENCE
################################################################################

# Bash Options
set -e
set -o pipefail

declare content_md="docs/reference/cli.md"

# Init
echo > "${content_md}"

# rdk
cat << '_EO_SECTION_START' >> "${content_md}"
## `rdk`

```text
_EO_SECTION_START
rdk --help >> "${content_md}" 2>&1
cat << '_EO_SECTION_END' >> "${content_md}"
```

_EO_SECTION_END

# rdk-init
cat << '_EO_SECTION_START' >> "${content_md}"
## `rdk init`

```text
_EO_SECTION_START
rdk init --help >> "${content_md}" 2>&1
cat << '_EO_SECTION_END' >> "${content_md}"
```

_EO_SECTION_END

# rdk-deploy
cat << '_EO_SECTION_START' >> "${content_md}"
## `rdk deploy`

```text
_EO_SECTION_START
rdk test --help >> "${content_md}" 2>&1
cat << '_EO_SECTION_END' >> "${content_md}"
```
_EO_SECTION_END

# Done
exit 0

################################################################################

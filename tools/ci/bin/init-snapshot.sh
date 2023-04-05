#!/usr/bin/env bash

################################################################################
# MAKE HELPER TO CHECK WHETHER `make init` NEEDS TO RUN
################################################################################

# Bash Option
set -e
set -o pipefail
export IFS=$'\n'

# err
function _kaput() {
  echo "$@" >&2
  exit 1
}

# Skip if we are running on jenkins
# jenkins/bogie has a really old version of pipenv that
# is not init-snapshot compatible.
# Also, on jenkins, we're always starting with a fresh init anyways
if test -n "${BUILD_URL}" || [[ "${CI}" == "Jenkins" ]]; then
  exit 0
fi

# Read operation
declare operation="check"
if [[ $# -gt 0 ]]; then
  if [[ "${1}" == "save" ]]; then
    operation="save"
  fi
fi

# get reporoot
declare reporoot
reporoot=$(git rev-parse --show-toplevel) \
  || _kaput "Failed to get repository root"

# Things to include in snapshot
declare -a snapshot_things
for _file in \
  "${reporoot}/Makefile" \
  "${reporoot}/requirements.txt" \
  "${reporoot}/Pipfile.lock" \
  "${reporoot}/.python-version"; do
  if test -f "${_file}"; then
    snapshot_things+=("${_file}")
  fi
done
while IFS= read -r -d '' _file; do
  snapshot_things+=("${_file}")
done < <(find "${reporoot}/tools/githooks" -type f -print0)

# Calculate snapshot
declare snapshot
snapshot=$(
  cat "${snapshot_things[@]}" \
    | openssl dgst -sha256
) || _kaput "ERROR: Failed to calculate snapshot"

# snapshot location
declare snapshot_root="${reporoot}/.venv"
declare snapshot_file="${snapshot_root}/init-snapshot"

# create/save
if [[ "${operation}" == "save" ]]; then
  # create
  mkdir -p "${snapshot_root}" \
    && echo "${snapshot}" > "${snapshot_file}"
else
  # check
  test -f "${snapshot_file}" || exit 2
  if [[ $(head -1 "${snapshot_file}") == "${snapshot}" ]]; then
    exit 0
  else
    exit 2
  fi
fi

# Done
exit 0

################################################################################

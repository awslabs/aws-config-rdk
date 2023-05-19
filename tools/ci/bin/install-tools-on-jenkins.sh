#!/usr/bin/env bash

################################################################################
# INSTALL TOOLS NEEDED FOR JENKINS JOBS
################################################################################

# Bash Options
set -e
set -o pipefail
export IFS=$'\n'

# err
function _kaput() {
  echo "$@" >&2
  exit 1
}

# Ensure we're running on Jenkins
if test -z "${BUILD_URL}"; then
  _kaput "ERROR: This script should only run within a Jenkins job"
fi

# Setup ~/.local
declare home_local="/home/git/.local"
if test -e "${home_local}"; then
  chmod -R 0755 "${home_local}"
  rm -rf "${home_local}"
fi
mkdir -p "${home_local}/bin" "${home_local}/lib"

# Install pipenv
declare PYENV_VERSION
PYENV_VERSION=$(pyenv versions --bare | grep 3.8 | sort -n | tail -1)
export PYENV_VERSION
pip3 install \
  --index-url https://artifactory.cloud.example.com/artifactory/api/pypi/pypi-internalfacing/simple \
  --upgrade \
  --ignore-installed \
  --user \
  -- pipenv

# Verify pipenv
hash -r
"${home_local}/bin/pipenv" --version

# Done
exit 0

################################################################################

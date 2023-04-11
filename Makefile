###############################################################################
# Makefile
###############################################################################

#
# https://www.gnu.org/software/make/manual/html_node/index.html
# https://www.gnu.org/software/make/manual/html_node/Quick-Reference.html#Quick-Reference
#

# -----------------------------------------------------------------------------
# MAKE CONFIGURATIONS
# -----------------------------------------------------------------------------

# Default Shell is bash, with errors
SHELL := /usr/bin/env bash
.SHELLFLAGS := -eu -o pipefail -c

# Do not run in parallel
.NOTPARALLEL:

# -----------------------------------------------------------------------------
# CHECK PRE-REQS
# -----------------------------------------------------------------------------

# This is intended to run as early as possible to ensure that various things
# that is Makefile depends on is available.

override prereq_binaries := git python3 pipenv cfn-guard
$(foreach bin,$(prereq_binaries),\
	$(if $(shell command -v $(bin) 2>/dev/null),,\
		$(error '$(bin)' is not installed or available in PATH)\
	)\
)

# Make sure we have at least git v2
ifneq ($(shell git --version | cut -d ' ' -f3 | cut -d. -f1),2)
$(error git is not compatible. Need at least git-2.0)
endif

# -----------------------------------------------------------------------------
# VARIABLES - PROJECT CONFIGURATIONS
# -----------------------------------------------------------------------------

# Root of the repository
override REPOROOT := $(shell git rev-parse --show-toplevel)

# Directories
override SRC_DIR := $(REPOROOT)/rdk
override TESTS_DIR := $(REPOROOT)/tests
override TOOLS_DIR := $(REPOROOT)/tools
override REPORTS_DIR := $(REPOROOT)/.reports
override GITHOOKS_DIR := $(TOOLS_DIR)/githooks
override DOCS_DIR := $(REPOROOT)/docs
override TESTS_UNIT_DIR := $(TESTS_DIR)/unit

# Setup.py configs
override PKG_SETUP := $(REPOROOT)/setup.py
override SETUP_PY_ARGS := --quiet --no-user-cfg

# python versions
override PYENV_VERSION := $(shell head -1 $(REPOROOT)/.python-version)
export PYENV_VERSION

# terraform version
override TFENV_TERRAFORM_VERSION := $(shell head -1 $(REPOROOT)/.terraform-version)
export TFENV_TERRAFORM_VERSION

# pipenv configs
# https://pipenv.pypa.io/en/latest/advanced/#configuration-with-environment-variables
override PIPENV_VENV_IN_PROJECT := 1
override PIPENV_DEFAULT_PYTHON_VERSION := $(PYENV_VERSION)
export PIPENV_VENV_IN_PROJECT
export PIPENV_DEFAULT_PYTHON_VERSION

# Collections of file types in the repo
override py_files_in_repo := $(PKG_SETUP) $(SRC_DIR) $(TESTS_DIR)
override md_files_in_repo := $(REPOROOT)/README.md $(DOCS_DIR)

# Path to init-snapshot helper
override INIT_SNAPSHOT := $(TOOLS_DIR)/ci/bin/init-snapshot.sh
ifneq ($(shell test -x $(INIT_SNAPSHOT); echo $$?),0)
$(shell chmod +x $(INIT_SNAPSHOT))
endif

# ------------------------------------------------------------------------------
# TARGETS - PRIMARY
# ------------------------------------------------------------------------------

### * init | Initialize this repository for development
.PHONY: init
init: \
	_githooks-install \
	_python-pipenv-install \
	_helper-init-snapshot-save

### * fmt | Format source code
.PHONY: fmt
fmt: \
	_helper-init-snapshot-check \
	_fmt-python-docstrings \
	_fmt-python-isort \
	_fmt-python-black \
	_fmt-markdown-mdformat

### * lint | Lint source code
.PHONY: lint
lint: \
	_helper-init-snapshot-check \
	_test-reports-mkdir \
	_lint-python-docstrings \
	_lint-python-isort \
	_lint-python-black \
	_lint-python-pylint \
	_lint-python-bandit \
	_lint-python-mypy \
	_lint-python-setup \
	_lint-markdown-mdformat

### * test | Run unit tests
.PHONY: test
test: \
	_helper-init-snapshot-check \
	_test-reports-mkdir \
	_test-python-pytest

### * sonar | Run sonar analysis
.PHONY: sonar
sonar: \
	_helper-init-snapshot-check \
	_test-sonar-scan

### * build | Build python package
.PHONY: build
build: \
	_helper-init-snapshot-check \
	_lint-python-setup \
	_build-wheel \
	_deploy-check-dist

### * deploy | Publish python package
.PHONY: deploy
deploy: \
	_helper-init-snapshot-check \
	_deploy-check-dist \
	_deploy-upload-dist

### * freeze | Update and lock dependencies
.PHONY: freeze
freeze: \
	_python-pipenv-lock \
	_python-pipenv-gen-requirements

### * docs-build | Build documentation from sources
.PHONY: docs-build
docs-build: \
	_helper-init-snapshot-check \
	_docs-generate-ref-cli \
	_docs-generate-ref-api \
	_docs-build

### * docs-server | Start a local server to host documentation
.PHONY: docs-server
docs-server: \
	docs-build \
	_docs-serve

### * docs-deploy | Publish documentation to Github Pages
.PHONY: docs-deploy
docs-deploy: \
	docs-build \
	_docs-publish-gh-pages

### * tf-init | Initialize terraform
.PHONY: tf-init
tf-init: \
	_helper-init-snapshot-check \
	_tf-create-plugin-cache \
	_tf-init

### * tf-plan | Run terraform-plan
.PHONY: tf-plan
tf-plan: \
	_helper-init-snapshot-check \
	_tf-clean-planfile \
	_tf-plan

### * tf-apply | Run terraform-apply
.PHONY: tf-apply
tf-apply: \
	_helper-init-snapshot-check \
	_tf-apply

### * tf-destroy | Run terraform-destroy
.PHONY: tf-destroy
tf-destroy: \
	_helper-init-snapshot-check \
	_tf-clean-planfile \
	_tf-destroy \
	_tf-workspace-delete \
	_tf-clean-data-dir

### * clean | Clean repository
.PHONY: clean
clean: \
	_githooks-clean \
	_clean-dist \
	_test-reports-rm \
	_python-pipenv-rm \
	_clean-all-tf-data-dir \
	_clean-empty-dirs \
	_clean-git

# -----------------------------------------------------------------------------
# TARGETS - PYTHON DEPENDENCY MANAGEMENT
# -----------------------------------------------------------------------------

.PHONY: _python-pipenv-install
_python-pipenv-install:
	@pipenv sync --dev
	@pipenv clean
	@pipenv check || true

.PHONY: _python-pipenv-lock
_python-pipenv-lock:
	@rm -f Pipfile.lock
	@pipenv lock --clear --dev

.PHONY: _python-pipenv-gen-requirements
_python-pipenv-gen-requirements:
	@rm -f > $(REPOROOT)/requirements.txt
	@pipenv requirements > $(REPOROOT)/requirements.txt

.PHONY: _python-pipenv-rm
_python-pipenv-rm:
	@pipenv --rm || true
	@pipenv --clear

# ------------------------------------------------------------------------------
# TARGETS - FORMATTING
# ------------------------------------------------------------------------------

.PHONY: _fmt-python-isort
_fmt-python-isort:
	@pipenv run -- isort -- $(py_files_in_repo)

.PHONY: _fmt-python-black
_fmt-python-black:
	@pipenv run -- black -- $(py_files_in_repo)

.PHONY: _fmt-python-docstrings
_fmt-python-docstrings:
	@pipenv run -- docformatter \
		--in-place \
		--recursive \
		--blank \
		--pre-summary-newline \
		--make-summary-multi-line \
		-- $(py_files_in_repo)

.PHONY: _fmt-markdown-mdformat
_fmt-markdown-mdformat:
	@pipenv run -- mdformat \
		--number \
		--wrap no \
		-- $(md_files_in_repo)

# -----------------------------------------------------------------------------
# TARGETS - LINTING
# -----------------------------------------------------------------------------

.PHONY: _lint-python-isort
_lint-python-isort:
	@pipenv run -- isort --check -- $(py_files_in_repo)

.PHONY: _lint-python-black
_lint-python-black:
	@pipenv run -- black --check -- $(py_files_in_repo)

# pylint runs multiple times
# We need to do this to support multiple output formats
# run1: For the terminal (developer feedback)
# run2: For sonar compatible messages
# run3: For JSON formatted output, that then produces an HTML
.PHONY: _lint-python-pylint
_lint-python-pylint:
	@pipenv run -- pylint \
	--reports=n \
	--output-format=colorized \
	-- $(SRC_DIR)
	@pipenv run -- pylint \
	--exit-zero \
	--reports=n \
	--output-format=text \
	--msg-template='{path}:{line}: [{msg_id}({symbol}), {obj}] {msg}' \
	-- $(SRC_DIR) \
	> $(REPORTS_DIR)/pylint-sonar.txt
	@pipenv run -- pylint \
	--exit-zero \
	--reports=y \
	--output-format=jsonextended \
	-- $(SRC_DIR) \
	> $(REPORTS_DIR)/pylint.json
	@pipenv run -- pylint-json2html \
	--input-format jsonextended \
	--output $(REPORTS_DIR)/pylint.html \
	$(REPORTS_DIR)/pylint.json

# bandit runs multiple times
# We need to do this to support multiple output formats
# run1: For the terminal (developer feedback)
# run2: For sonar compatible messages
# run3: For HTML report
.PHONY: _lint-python-bandit
_lint-python-bandit:
	@pipenv run -- bandit \
		--recursive \
		--quiet \
		--configfile $(REPOROOT)/.bandit.yaml \
		--format screen \
		-- $(SRC_DIR)
	@pipenv run -- bandit \
		--recursive \
		--quiet \
		--exit-zero \
		--configfile $(REPOROOT)/.bandit.yaml \
		--format json \
		--output $(REPORTS_DIR)/bandit.json \
		-- $(SRC_DIR)
	@pipenv run -- bandit \
		--recursive \
		--quiet \
		--exit-zero \
		--configfile $(REPOROOT)/.bandit.yaml \
		--format html \
		--output $(REPORTS_DIR)/bandit.html \
		-- $(SRC_DIR)

.PHONY: _lint-python-mypy
_lint-python-mypy:
	@pipenv run -- mypy \
		-- $(SRC_DIR)

.PHONY: _lint-python-docstrings
_lint-python-docstrings:
	@pipenv run -- docformatter \
		--check \
		--recursive \
		--blank \
		--pre-summary-newline \
		--make-summary-multi-line \
		-- $(py_files_in_repo)

.PHONY: _lint-python-setup
_lint-python-setup:
	@pipenv run -- \
		python -W ignore -- \
		$(PKG_SETUP) $(SETUP_PY_ARGS) check --strict

.PHONY: _lint-markdown-mdformat
_lint-markdown-mdformat:
	@pipenv run -- mdformat \
		--check \
		--number \
		--wrap no \
		-- $(md_files_in_repo)

# -----------------------------------------------------------------------------
# TARGETS - TESTING
# -----------------------------------------------------------------------------

.PHONY: _test-reports-mkdir
_test-reports-mkdir:
	@mkdir -p $(REPORTS_DIR)

.PHONY: _test-reports-rm
_test-reports-rm:
	@rm -rf $(REPORTS_DIR)

.PHONY: _test-python-pytest
_test-python-pytest:
	@rm -rf $(REPOROOT)/.rdk
	@pipenv run -- pytest $(TESTS_UNIT_DIR)
	@rm -rf $(REPOROOT)/.rdk

.PHONY: _test-sonar-scan
_test-sonar-scan:
	@if ! command -v sonar-scanner >/dev/null 2>&1; then \
		echo "sonar-scanner is not installed" >&2; \
		exit 1; \
	fi
	@if ! test -n "$${SONAR_TOKEN}"; then \
		echo "SONAR_TOKEN is not set" >&2; \
		exit 1; \
	fi
	@rdk_version=$$(grep 'VERSION.*=.*' \
		rdk/__init__.py \
		| head -1 | cut -d '=' -f2 \
		| tr -d ' ' | tr -d '"' \
	) \
	&& git_branch=$$(git rev-parse --abbrev-ref HEAD) \
	&& export SONAR_SCANNER_OPTS="-Xmx512m" \
	&& sonar-scanner \
		-Dsonar.login="$${SONAR_TOKEN}" \
		-Dsonar.projectVersion="$${rdk_version}" \
		-Dsonar.branch.name="$${git_branch}"

# -----------------------------------------------------------------------------
# TARGETS - BUILD
# -----------------------------------------------------------------------------

.PHONY: _build-wheel
_build-wheel:
	@pipenv run -- \
		python -W ignore -- \
		$(PKG_SETUP) $(SETUP_PY_ARGS) bdist_wheel \
			--universal \
			--python-tag "py3" \
			--owner "nobody" \
			--group "nobody"

# -----------------------------------------------------------------------------
# TARGETS - DEPLOY
# -----------------------------------------------------------------------------

.PHONY: _deploy-check-dist
_deploy-check-dist:
	@find ./dist -mindepth 1 -maxdepth 1 -type f -print0 \
	| xargs -0 -- pipenv run -- twine check --strict

.PHONY: _deploy-upload-dist
_deploy-upload-dist:
	@find ./dist -mindepth 1 -maxdepth 1 -type f -print0 \
	| xargs -0 -- pipenv run -- twine upload \
		--config-file $(REPOROOT)/twine.pypirc \
		--non-interactive \
		--repository artifactory \
		--verbose \
		--

# ------------------------------------------------------------------------------
# TARGETS - GITHOOKS
# ------------------------------------------------------------------------------

.PHONY: _githooks-install
_githooks-install:
	@chmod +x $(GITHOOKS_DIR)/bin/*
	@git config --local core.hooksPath $(GITHOOKS_DIR)/bin
	@git config --local commit.template $(GITHOOKS_DIR)/etc/commit-template
	@git config --local fetch.prune true
	@git config --local fetch.pruneTags true
	@git config --local push.default simple
	@git config --local pull.ff true
	@git config --local pull.rebase false
	@git config --local user.useConfigOnly true

.PHONY: _githooks-clean
_githooks-clean:
	@for c in \
		core.hooksPath \
		commit.template \
	; do \
		if git config --local --get $$c >/dev/null 2>&1; then \
			git config --local --unset $$c; \
		fi; \
	done

# -----------------------------------------------------------------------------
# TARGETS - DOCS
# -----------------------------------------------------------------------------

.PHONY: _docs-generate-ref-cli
_docs-generate-ref-cli:
	@chmod +x $(TOOLS_DIR)/docs/bin/generate-ref-cli.sh
	@pipenv run -- $(TOOLS_DIR)/docs/bin/generate-ref-cli.sh

.PHONY: _docs-generate-ref-api
_docs-generate-ref-api:
	@rm -rf $(DOCS_DIR)/reference/api
	@pipenv run -- pdoc -o $(DOCS_DIR)/reference/api rdk.pytest

.PHONY: _docs-build
_docs-build:
	@pipenv run -- mkdocs build

.PHONY: _docs-serve
_docs-serve:
	@pipenv run -- mkdocs serve

.PHONY: _docs-publish-gh-pages
_docs-publish-gh-pages:
	@pipenv run -- mkdocs gh-deploy --message "docs: publish from {sha}"

# -----------------------------------------------------------------------------
# TARGETS - CLEAN
# -----------------------------------------------------------------------------

.PHONY: _clean-dist
_clean-dist:
	@rm -rf ./build ./dist ./*.egg-info

.PHONY: _clean-git
_clean-git:
	@git clean -fdXq

.PHONY: _clean-empty-dirs
_clean-empty-dirs:
	@find $(REPOROOT) -type d -empty -print0 \
	| xargs -0 -- rm -rf

.PHONY: _clean-all-tf-data-dir
_clean-all-tf-data-dir:
	@find $(REPOROOT) -type d -name '.terraform' -print0 \
	| xargs -0 -- rm -rf
	@find $(REPOROOT) -type d -name '*.terraform' -print0 \
	| xargs -0 -- rm -rf
	@find $(REPOROOT) -type f -name 'tfplan' -print0 \
	| xargs -0 -- rm -f
	@find $(REPOROOT) -type f -name '*tfplan*' -print0 \
	| xargs -0 -- rm -f

# -----------------------------------------------------------------------------
# TARGETS - HELPERS
# -----------------------------------------------------------------------------

.PHONY: _helper-init-snapshot-save
_helper-init-snapshot-save:
	@$(INIT_SNAPSHOT) save

.PHONY: _helper-init-snapshot-check
_helper-init-snapshot-check:
	@$(INIT_SNAPSHOT) check ; rc=$$?; \
	if [[ "$$rc" -eq 0 ]]; then exit 0; fi; \
	if [[ "$$rc" -eq 1 ]]; then \
		echo "ERROR: Failed to check if repository initialization is required." >&2; \
		exit 1; \
	fi; \
	if [[ "$$rc" -eq 2 ]]; then \
		echo "WARNING: Repository initialization is required. Running now ..." >&2; \
		cd $(REPOROOT) || exit 1; \
		make init || exit 1; \
	fi

# -----------------------------------------------------------------------------
# TARGETS - HELP (DEFAULT)
# -----------------------------------------------------------------------------

### * help | Prints this message
.PHONY: help
.DEFAULT_GOAL := help
help:
	@echo "USAGE: make [target ...]"
	@echo
	@echo "TARGETS:"
	@echo
	@grep -E '^###[[:blank:]]*\*[[:blank:]]*' $(lastword $(MAKEFILE_LIST)) \
		| sed -e 's|^###[[:blank:]]*\*[[:blank:]]*|  |g' \
		| column -s'|' -t
	@echo

###############################################################################

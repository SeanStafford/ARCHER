#################################################################################
# GLOBALS                                                                       #
#################################################################################

PROJECT_NAME = archer
PYTHON_VERSION = 3.9
PYTHON_INTERPRETER = python3
PACKAGE_MANAGER = pip

#################################################################################
# INSTALLATION COMMANDS                                                         #
#################################################################################

## Create virtual environment (if it doesn't exist)
.PHONY: venv
venv:
	@if [ ! -d ".venv" ]; then \
		echo "Creating virtual environment..."; \
		$(PYTHON_INTERPRETER) -m venv .venv; \
		echo ">>> Virtual environment created at .venv"; \
		echo ">>> Activate with: source .venv/bin/activate"; \
	else \
		echo ">>> Virtual environment already exists at .venv"; \
	fi

## Install Python Dependencies
.PHONY: install
install: venv
	pip install -e .
	@echo ">>> Base dependencies installed."

## Install development dependencies
.PHONY: install-dev
install-dev: venv
	pip install -e ".[dev]"
	@echo ">>> Development dependencies installed"

## Install embeddings/clustering dependencies
.PHONY: install-embeddings
install-embeddings: venv
	pip install -e ".[embeddings]"
	@echo ">>> Embeddings dependencies installed (sentence-transformers, UMAP, HDBSCAN)"

## Verify system dependencies
.PHONY: check-deps
check-deps:
	@bash scripts/check_dependencies.sh archer/

#################################################################################
# CODE HYGIENE COMMANDS                                                         #
#################################################################################

## Delete all compiled Python files, caches, and LaTeX artifacts
.PHONY: clean
clean:
	find . -type f -name "*.py[co]" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	find .archive -type f -name "*.aux" -delete 2>/dev/null || true
	find .archive -type f -name "*.log" -delete 2>/dev/null || true
	find .archive -type f -name "*.out" -delete 2>/dev/null || true
	find .archive -type f -name "*.toc" -delete 2>/dev/null || true
	find .archive -type f -name "*.synctex.gz" -delete 2>/dev/null || true
	@echo ">>> Cleaned Python cache files and LaTeX artifacts"

## Lint code using ruff (use `make format` to auto-fix)
## Usage: make lint [DIR=path/to/dir]
.PHONY: lint
lint:
	@DIR=$${DIR:-archer}; \
	ruff check $$DIR; \
	ruff format --check $$DIR; \
	echo ">>> Linting complete ($$DIR)"

## Format source code with ruff
## Usage: make format [DIR=path/to/dir]
.PHONY: format
format:
	@DIR=$${DIR:-archer}; \
	ruff check --select I --fix $$DIR; \
	ruff format $$DIR; \
	echo ">>> Code formatted ($$DIR)"

#################################################################################
# TESTING COMMANDS                                                              #
#################################################################################

## Run all tests (excluding slow tests by default)
.PHONY: test
test:
	pytest
	@echo ">>> Tests complete (slow tests excluded)"

## Run all tests including slow tests
.PHONY: test-all
test-all:
	pytest -m ''
	@echo ">>> All tests complete (including slow)"

## Run only unit tests
.PHONY: test-unit
test-unit:
	pytest -m unit
	@echo ">>> Unit tests complete"

## Run only integration tests
.PHONY: test-integration
test-integration:
	pytest -m integration
	@echo ">>> Integration tests complete"

## Run tests with coverage report
.PHONY: test-cov
test-cov:
	pytest --cov=archer --cov-report=term-missing --cov-report=html
	@echo ">>> Coverage report generated in htmlcov/"

## Run tests and open coverage report
.PHONY: test-cov-html
test-cov-html: test-cov
	@echo ">>> Opening coverage report..."
	xdg-open htmlcov/index.html 2>/dev/null || open htmlcov/index.html 2>/dev/null || echo "Please open htmlcov/index.html manually"

## Test roundtrip conversion on a single resume
.PHONY: test-roundtrip
test-roundtrip:
	@if [ -z "$(FILE)" ]; then \
		echo "ERROR: FILE parameter required"; \
		echo "Usage: make test-roundtrip FILE=path/to/resume.tex"; \
		exit 1; \
	fi
	$(PYTHON_INTERPRETER) scripts/test_roundtrip.py test $(FILE)

## Test roundtrip conversion on all resumes (batch mode)
.PHONY: test-roundtrip-all
test-roundtrip-all:
	$(PYTHON_INTERPRETER) scripts/test_roundtrip.py batch
	@echo ">>> Roundtrip tests complete"

#################################################################################
# RESUME PROCESSING COMMANDS                                                    #
#################################################################################

## Clean and normalize all historical resumes (raw/ → processed/)
.PHONY: normalize-archive
normalize-archive:
	$(PYTHON_INTERPRETER) scripts/normalize_latex.py batch
	@echo ">>> Resume archive normalized"

## Convert all LaTeX resumes to structured YAML (archive/ → structured/)
.PHONY: generate-yaml-archive
generate-yaml-archive:
	$(PYTHON_INTERPRETER) scripts/convert_template.py batch
	@echo ">>> YAML archive generated in resume_archive/structured/"

#################################################################################
# RESUME REGISTRY COMMANDS                                                      #
#################################################################################

## Show registry statistics (counts by status and type)
.PHONY: registry-stats
registry-stats:
	$(PYTHON_INTERPRETER) scripts/manage_registry.py stats

## List all resumes in registry
.PHONY: registry-list
registry-list:
	$(PYTHON_INTERPRETER) scripts/manage_registry.py list

## Initialize registry with historical resumes
.PHONY: registry-init
registry-init:
	$(PYTHON_INTERPRETER) scripts/manage_registry.py init

## View recent pipeline events (JSON output)
## Usage: make logs [RESUME=resume_name]
.PHONY: logs
logs:
ifdef RESUME
	@$(PYTHON_INTERPRETER) scripts/tail_log.py -c -r $(RESUME) | jq
else
	@$(PYTHON_INTERPRETER) scripts/tail_log.py -c -n 5 | jq
endif

## Track status history for a resume (requires RESUME variable)
## Usage: make track RESUME=resume_name
.PHONY: track
track:
ifndef RESUME
	@echo "Error: RESUME variable required. Usage: make track RESUME=resume_name"
	@exit 1
endif
	@$(PYTHON_INTERPRETER) scripts/tail_log.py track $(RESUME) -r

#################################################################################
# UTILITY COMMANDS                                                              #
#################################################################################

## Show recently modified files (like tree + ls -ltr)
## Usage: make recent [DIR=path/to/dir]
.PHONY: recent
recent:
	@DIR=$${DIR:-.}; \
	find $$DIR -type f -not -path '*/\.*' -not -path '*/__pycache__/*' -not -path '*/venv/*' -not -path '*/.venv/*' -printf '%T@ %p\n' | sort -n | tail -20 | perl -MTime::Piece -MTime::Seconds -nE 'chomp; ($$t, $$f) = split / /, $$_, 2; $$now = time; $$diff = $$now - int($$t); if ($$diff < 60) { $$ago = sprintf "%ds ago", $$diff } elsif ($$diff < 3600) { $$ago = sprintf "%dm ago", $$diff/60 } elsif ($$diff < 86400) { $$ago = sprintf "%dh ago", $$diff/3600 } else { $$ago = sprintf "%dd ago", $$diff/86400 } printf "%-12s %s\n", $$ago, $$f'

## Clean up ARCHER temporary files in /tmp/archer/
.PHONY: clean-tmp
clean-tmp:
	@echo "Removing ARCHER temp files from /tmp/archer/..."
	@rm -rf /tmp/archer/*
	@echo ">>> Cleaned /tmp/archer/"

## Clean old log directories, keeping last N of each type (default N=2)
## Usage: make clean-logs [N=3] [TYPE=render]
.PHONY: clean-logs
clean-logs:
	@N=$${N:-2}; \
	TYPE=$${TYPE:-all}; \
	LOGS_DIR="outs/logs"; \
	if [ "$$TYPE" = "all" ]; then \
		LOG_TYPES="convert render roundtrip test"; \
	else \
		LOG_TYPES="$$TYPE"; \
	fi; \
	echo "Cleaning log directories (keeping last $$N of each type)..."; \
	echo ""; \
	for log_type in $$LOG_TYPES; do \
		dirs=$$(find $$LOGS_DIR -maxdepth 1 -type d -name "$${log_type}_*" | sort); \
		total=$$(echo "$$dirs" | grep -c "^" 2>/dev/null || echo 0); \
		if [ $$total -eq 0 ]; then \
			echo "  $$log_type: No directories found"; \
			continue; \
		fi; \
		to_keep=$$N; \
		to_delete=$$((total - to_keep)); \
		if [ $$to_delete -le 0 ]; then \
			echo "  $$log_type: $$total directories (keeping all)"; \
		else \
			echo "  $$log_type: $$total directories → deleting $$to_delete, keeping $$to_keep"; \
			echo "$$dirs" | head -n $$to_delete | while read dir; do \
				echo "    - Removing: $$(basename $$dir)"; \
				rm -rf "$$dir"; \
			done; \
		fi; \
	done; \
	echo ""; \
	echo ">>> Log cleanup complete"

## Show frequency of conventional commit types
.PHONY: commit-stats
commit-stats:
	@echo "Commit type frequency:"
	@git log --oneline | grep -oP '(?<=^[0-9a-f]{7} )[^:]+' | sort | uniq -c | sort -rn

## Stop tracking changes to notebooks (for local experimentation)
.PHONY: ignore-notebooks
ignore-notebooks:
	@git ls-files 'notebooks/*.ipynb' | xargs -r git update-index --assume-unchanged
	@echo ">>> Notebooks marked as unchanged (local changes will be ignored)"
	@echo ">>> Ignored files:"
	@git ls-files -v | grep '^h'

## Resume tracking changes to notebooks
.PHONY: track-notebooks
track-notebooks:
	@git ls-files 'notebooks/*.ipynb' | xargs -r git update-index --no-assume-unchanged
	@echo ">>> Notebooks tracking resumed"
	@echo ">>> Currently ignored files:"
	@git ls-files -v | grep '^h' || echo "(none)"

## Undo last N commits (default 1), keeping changes staged
# Usage: make git-undo
# Usage: make git-undo N=3
.PHONY: git-undo
git-undo:
	@n=$${N:-1}; \
	echo "Undoing last $$n commit(s). Messages (newest first):"; \
	echo "============================================================"; \
	for i in $$(seq 0 $$((n-1))); do \
		echo ""; \
		hash=$$(git log --format="%h" -n 1 HEAD~$$i); \
		msg=$$(git log --format="%B" -n 1 HEAD~$$i); \
		printf "%s \033[33m%s\033[0m\n\n" "$$hash" "$$msg"; \
		echo "------------------------------------------------------------"; \
	done; \
	echo "============================================================"; \
	git reset --soft HEAD~$$n && \
	echo ">>> Undid last $$n commit(s), changes remain staged" && \
	echo ">>> To recover: git reflog (commits are at HEAD@{1}, HEAD@{2}, etc.)"

#################################################################################
# Self Documenting Boilerplate                                                  #
#################################################################################

.DEFAULT_GOAL := help

define PRINT_HELP_PYSCRIPT
import re, sys; \
lines = '\n'.join([line for line in sys.stdin]); \
matches = re.findall(r'\n## (.*)\n[\s\S]+?\n([a-zA-Z_-]+):', lines); \
print('ARCHER - Algorithmic Resume Composition to Hasten Employer Recognition\n'); \
print('Available commands:\n'); \
print('\n'.join(['{:20}{}'.format(*reversed(match)) for match in matches]))
endef
export PRINT_HELP_PYSCRIPT

help:
	@$(PYTHON_INTERPRETER) -c "$${PRINT_HELP_PYSCRIPT}" < $(MAKEFILE_LIST)

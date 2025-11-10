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

## Verify system dependencies (LaTeX)
.PHONY: check-deps
check-deps:
	@echo "Checking system dependencies..."
	@command -v pdflatex >/dev/null 2>&1 || \
		(echo "ERROR: pdflatex not found. Please install a LaTeX distribution." && \
		 echo "See README.md for installation instructions." && exit 1)
	@pdflatex --version | head -n 1
	@echo ">>> All system dependencies satisfied"

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
.PHONY: lint
lint:
	ruff check archer
	ruff format --check archer
	@echo ">>> Linting complete"

## Format source code with ruff
.PHONY: format
format:
	ruff check --select I --fix archer  # Fix import sorting
	ruff format archer
	@echo ">>> Code formatted"

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
	$(PYTHON_INTERPRETER) scripts/process_all_resumes.py
	@echo ">>> Resume archive normalized"

## Convert all LaTeX resumes to structured YAML (archive/ → structured/)
.PHONY: generate-yaml-archive
generate-yaml-archive:
	$(PYTHON_INTERPRETER) scripts/latex_to_yaml.py batch
	@echo ">>> YAML archive generated in resume_archive/structured/"

#################################################################################
# UTILITY COMMANDS                                                              #
#################################################################################

## Show recently modified files (like tree + ls -ltr)
.PHONY: recent
recent:
	@find . -type f -not -path '*/\.*' -not -path '*/__pycache__/*' -not -path '*/venv/*' -not -path '*/.venv/*' -printf '%T@ %p\n' | sort -n | tail -20 | perl -MTime::Piece -MTime::Seconds -nE 'chomp; ($$t, $$f) = split / /, $$_, 2; $$now = time; $$diff = $$now - int($$t); if ($$diff < 60) { $$ago = sprintf "%ds ago", $$diff } elsif ($$diff < 3600) { $$ago = sprintf "%dm ago", $$diff/60 } elsif ($$diff < 86400) { $$ago = sprintf "%dh ago", $$diff/3600 } else { $$ago = sprintf "%dd ago", $$diff/86400 } printf "%-12s %s\n", $$ago, $$f'

## Clean up ARCHER temporary files in /tmp/archer/
.PHONY: clean-tmp
clean-tmp:
	@echo "Removing ARCHER temp files from /tmp/archer/..."
	@rm -rf /tmp/archer/*
	@echo ">>> Cleaned /tmp/archer/"

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
	@echo ">>> Ignored notebooks:"
	@git ls-files -v | grep '^h'

## Resume tracking changes to notebooks
.PHONY: track-notebooks
track-notebooks:
	@git ls-files 'notebooks/*.ipynb' | xargs -r git update-index --no-assume-unchanged
	@echo ">>> Notebooks tracking resumed"
	@echo ">>> Currently ignored notebooks:"
	@git ls-files -v | grep '^h' || echo "(none)"

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

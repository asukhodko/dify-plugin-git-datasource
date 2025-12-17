.PHONY: venv install install-dev test test-property test-unit lint format clean package package-fast help

VENV := .venv
PYTHON := $(VENV)/bin/python3
PIP := $(VENV)/bin/pip
PYTEST := $(PYTHON) -m pytest
PLUGIN_NAME := git_datasource
DIST_DIR := dist

# Default target
help:
	@echo "Git Datasource Plugin - Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make venv          - Create virtual environment"
	@echo "  make install       - Install production dependencies"
	@echo "  make install-dev   - Install development dependencies (testing, linting)"
	@echo ""
	@echo "Testing:"
	@echo "  make test          - Run all tests"
	@echo "  make test-property - Run property-based tests only"
	@echo "  make test-unit     - Run unit tests only"
	@echo "  make test-cov      - Run tests with coverage report"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint          - Run linter (ruff)"
	@echo "  make format        - Format code (ruff)"
	@echo ""
	@echo "Build:"
	@echo "  make package       - Build plugin package (.difypkg) with tests"
	@echo "  make package-fast  - Build plugin package (skip tests)"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean         - Remove build artifacts and cache"

# Create virtual environment
venv:
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip

# Install production dependencies
install: venv
	$(PIP) install -r requirements.txt

# Install development dependencies
install-dev: venv
	$(PIP) install -r requirements.txt
	$(PIP) install -r requirements-dev.txt

# Run all tests
test:
	$(PYTEST) tests/ -v

# Run property-based tests
test-property:
	$(PYTEST) tests/property/ -v

# Run unit tests
test-unit:
	$(PYTEST) tests/unit/ -v

# Run tests with coverage
test-cov:
	$(PYTEST) tests/ -v --cov=. --cov-report=term-missing --cov-report=html

# Lint code
lint:
	$(PYTHON) -m ruff check .

# Format code
format:
	$(PYTHON) -m ruff format .
	$(PYTHON) -m ruff check --fix .

# Build plugin package
package: lint test
	@echo "Building plugin package..."
	@mkdir -p $(DIST_DIR)
	dify-plugin plugin package . -o $(DIST_DIR)/$(PLUGIN_NAME).difypkg
	@echo "Package created:"
	@ls -la $(DIST_DIR)/*.difypkg

# Build package without tests (faster, for development)
package-fast:
	@echo "Building plugin package (skipping tests)..."
	@mkdir -p $(DIST_DIR)
	dify-plugin plugin package . -o $(DIST_DIR)/$(PLUGIN_NAME).difypkg
	@echo "Package created:"
	@ls -la $(DIST_DIR)/*.difypkg

# Clean build artifacts
clean:
	rm -rf __pycache__ */__pycache__ */*/__pycache__
	rm -rf .pytest_cache */.pytest_cache
	rm -rf .coverage htmlcov
	rm -rf *.egg-info build
	rm -rf .ruff_cache
	rm -rf $(DIST_DIR)
	find . -name "*.pyc" -delete
	find . -name ".DS_Store" -delete

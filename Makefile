# QGIS MCP Secure - Makefile
# Automation for common development tasks

.PHONY: help install install-dev test test-coverage lint format security clean build docs

# Default target
.DEFAULT_GOAL := help

# Colors
BLUE := \033[0;34m
GREEN := \033[0;32m
RED := \033[0;31m
YELLOW := \033[0;33m
NC := \033[0m # No Color

help: ## Show this help message
	@echo "$(BLUE)QGIS MCP Secure - Development Commands$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "$(GREEN)%-20s$(NC) %s\n", $$1, $$2}'

install: ## Install production dependencies
	@echo "$(BLUE)Installing production dependencies...$(NC)"
	pip install -r requirements.txt

install-dev: ## Install development dependencies
	@echo "$(BLUE)Installing development dependencies...$(NC)"
	pip install -r requirements-dev.txt
	pre-commit install

install-all: ## Install all dependencies including security tools
	@echo "$(BLUE)Installing all dependencies...$(NC)"
	pip install -e .[all]
	pre-commit install

test: ## Run tests
	@echo "$(BLUE)Running tests...$(NC)"
	pytest tests/ -v

test-coverage: ## Run tests with coverage report
	@echo "$(BLUE)Running tests with coverage...$(NC)"
	pytest tests/ \
		--cov=src/qgis_mcp \
		--cov-report=html \
		--cov-report=term-missing \
		--cov-report=xml \
		--cov-fail-under=80 \
		-v

test-watch: ## Run tests in watch mode
	@echo "$(BLUE)Running tests in watch mode...$(NC)"
	pytest-watch tests/ -v

lint: ## Run all linters
	@echo "$(BLUE)Running linters...$(NC)"
	@echo "$(YELLOW)Flake8...$(NC)"
	flake8 src/ tests/
	@echo "$(YELLOW)Black (check)...$(NC)"
	black --check src/ tests/
	@echo "$(YELLOW)isort (check)...$(NC)"
	isort --check-only src/ tests/
	@echo "$(YELLOW)Mypy...$(NC)"
	mypy src/

format: ## Format code with black and isort
	@echo "$(BLUE)Formatting code...$(NC)"
	black src/ tests/
	isort src/ tests/

format-check: ## Check code formatting without making changes
	@echo "$(BLUE)Checking code format...$(NC)"
	black --check --diff src/ tests/
	isort --check-only --diff src/ tests/

security: ## Run security checks
	@echo "$(BLUE)Running security checks...$(NC)"
	@echo "$(YELLOW)Bandit...$(NC)"
	bandit -r src/ -f json -o bandit-report.json
	bandit -r src/
	@echo "$(YELLOW)Safety...$(NC)"
	safety check --full-report
	@echo "$(YELLOW)pip-audit...$(NC)"
	pip-audit --desc

security-full: ## Run comprehensive security audit
	@echo "$(BLUE)Running comprehensive security audit...$(NC)"
	@$(MAKE) security
	@echo "$(YELLOW)Checking for secrets...$(NC)"
	detect-secrets scan --baseline .secrets.baseline

complexity: ## Analyze code complexity
	@echo "$(BLUE)Analyzing code complexity...$(NC)"
	radon cc src/ -a -s
	radon mi src/ -s

quality: ## Run all quality checks
	@echo "$(BLUE)Running quality checks...$(NC)"
	@$(MAKE) lint
	@$(MAKE) test-coverage
	@$(MAKE) security

pre-commit: ## Run pre-commit hooks on all files
	@echo "$(BLUE)Running pre-commit hooks...$(NC)"
	pre-commit run --all-files

clean: ## Clean build artifacts and cache files
	@echo "$(BLUE)Cleaning build artifacts...$(NC)"
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .eggs/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf coverage.xml
	rm -rf *.pyc
	rm -rf __pycache__/
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	@echo "$(GREEN)Cleanup complete!$(NC)"

build: clean ## Build distribution packages
	@echo "$(BLUE)Building distribution packages...$(NC)"
	python -m build
	@echo "$(GREEN)Build complete! Check dist/ directory$(NC)"

build-check: build ## Build and check package
	@echo "$(BLUE)Checking package...$(NC)"
	twine check dist/*

docs: ## Build documentation
	@echo "$(BLUE)Building documentation...$(NC)"
	cd docs && sphinx-build -W -b html . _build/html
	@echo "$(GREEN)Documentation built! Open docs/_build/html/index.html$(NC)"

docs-serve: ## Serve documentation locally
	@echo "$(BLUE)Serving documentation...$(NC)"
	python -m http.server --directory docs/_build/html 8000

docs-clean: ## Clean documentation build
	@echo "$(BLUE)Cleaning documentation...$(NC)"
	cd docs && rm -rf _build/

validate: ## Validate all configuration files
	@echo "$(BLUE)Validating configuration files...$(NC)"
	python -c "import yaml; yaml.safe_load(open('.github/workflows/security-tests.yml'))" && echo "security-tests.yml: OK"
	python -c "import yaml; yaml.safe_load(open('.github/workflows/code-quality.yml'))" && echo "code-quality.yml: OK"
	python -c "import tomli; tomli.load(open('pyproject.toml', 'rb'))" && echo "pyproject.toml: OK" || pip install tomli && python -c "import tomli; tomli.load(open('pyproject.toml', 'rb'))" && echo "pyproject.toml: OK"
	@echo "$(GREEN)All configuration files are valid!$(NC)"

release-check: ## Check if ready for release
	@echo "$(BLUE)Checking release readiness...$(NC)"
	@$(MAKE) clean
	@$(MAKE) quality
	@$(MAKE) build-check
	@echo "$(GREEN)Ready for release!$(NC)"

venv: ## Create virtual environment
	@echo "$(BLUE)Creating virtual environment...$(NC)"
	python -m venv venv
	@echo "$(GREEN)Virtual environment created! Activate with: source venv/bin/activate$(NC)"

upgrade-deps: ## Upgrade all dependencies to latest versions
	@echo "$(BLUE)Upgrading dependencies...$(NC)"
	pip list --outdated --format=columns
	pip install --upgrade -r requirements.txt
	pip install --upgrade -r requirements-dev.txt

freeze-deps: ## Freeze current dependencies to requirements files
	@echo "$(BLUE)Freezing dependencies...$(NC)"
	pip freeze > requirements-frozen.txt
	@echo "$(GREEN)Dependencies frozen to requirements-frozen.txt$(NC)"

init: ## Initialize development environment
	@echo "$(BLUE)Initializing development environment...$(NC)"
	@$(MAKE) install-all
	@$(MAKE) validate
	@echo "$(GREEN)Development environment ready!$(NC)"

all: ## Run all checks and build
	@echo "$(BLUE)Running all tasks...$(NC)"
	@$(MAKE) clean
	@$(MAKE) format
	@$(MAKE) quality
	@$(MAKE) build
	@echo "$(GREEN)All tasks completed successfully!$(NC)"

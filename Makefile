SHELL := /bin/bash
IMAGE_NAME ?= ghcr.io/lusoris/fileflows-real-image
TAG ?= latest

.PHONY: help build build-all build-intel build-amd build-cuda build-cuda13 \
        test test-unit test-docs test-image test-all coverage lint lint-hadolint lint-yaml lint-shell \
        docs-serve docs-build clean

help: ## Show this help message
	@echo "FileFlows Real Image — Build & Development Targets"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

build: ## Build default universal image (:latest / :all)
	docker build -t $(IMAGE_NAME):$(TAG) --build-arg FLAVOR=all .

build-all: build build-intel build-amd build-cuda build-cuda13 ## Build all 5 image flavors

build-intel: ## Build Intel QuickSync & Arc flavor (:intel)
	docker build -t $(IMAGE_NAME):intel --build-arg FLAVOR=intel .

build-amd: ## Build AMD Radeon & Ryzen APU flavor (:amd)
	docker build -t $(IMAGE_NAME):amd --build-arg FLAVOR=amd .

build-cuda: ## Build host-based NVIDIA flavor (:cuda)
	docker build -t $(IMAGE_NAME):cuda --build-arg FLAVOR=cuda .

build-cuda13: ## Build minimal CUDA 13.4 runtime flavor (:cuda13)
	docker build -t $(IMAGE_NAME):cuda13 --build-arg FLAVOR=cuda13 .

test: test-unit ## Run all offline test suites

test-unit: ## Run all offline test suites (docs, dockerfile, workflows, skills, badges, compose)
	pytest tests/test_docs_consistency.py tests/test_dockerfile.py tests/test_workflows.py tests/test_agent_skills.py tests/test_badges.py tests/test_compose.py -v --tb=short

coverage: ## Run offline tests with code coverage report
	pytest --cov=tests tests/test_docs_consistency.py tests/test_dockerfile.py tests/test_workflows.py tests/test_agent_skills.py tests/test_badges.py tests/test_compose.py

test-docs: ## Run documentation and anchor consistency tests
	pytest tests/test_docs_consistency.py -v --tb=short

test-image: ## Run full container assertion suite against local image
	TEST_IMAGE=$(IMAGE_NAME):$(TAG) pytest tests/ -v --tb=short

test-all: test-unit test-image ## Run offline unit tests followed by live container tests

lint: lint-hadolint lint-yaml lint-shell ## Run all linters (Hadolint, Yamllint, ShellCheck)

lint-hadolint: ## Run Hadolint on Dockerfile
	hadolint --config .hadolint.yaml Dockerfile

lint-yaml: ## Run Yamllint on YAML files
	yamllint -c .yamllint.yml .

lint-shell: ## Run ShellCheck on scripts
	shellcheck tests/run_tests.sh

docs-serve: ## Start local MkDocs live-reload server
	mkdocs serve

docs-build: ## Build documentation site strictly
	mkdocs build --strict

clean: ## Clean local build artifacts and caches
	rm -rf build-docs/site .pytest_cache __pycache__ tests/__pycache__

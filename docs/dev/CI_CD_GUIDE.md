# CI/CD Guide

## Overview

This document provides a comprehensive guide for the CI/CD pipeline of the Newsletter Generator project.

## GitHub Actions Workflows

### 1. CI Workflow (`ci.yml`)
- **Triggers**: Push to main, Pull Request
- **Python Versions**: 3.10, 3.11 (matrix testing)
- **Steps**:
  - Fast testing with minimal dependencies
  - Black code formatting check
  - Basic tests without external dependencies
  - Integration tests with mocked APIs

### 2. Code Quality Workflow (`code-quality.yml`)
- **Triggers**: Push to main, Pull Request
- **Checks**:
  - Black code formatting
  - isort import sorting
  - flake8 linting
  - mypy type checking (optional)

### 3. Tools Test Workflow (`test-tools.yml`)
- **Triggers**: Changes to specific files (`newsletter/tools.py`, `tests/test_tools.py`, `requirements.txt`)
- **Purpose**: Test tool module imports and basic functionality

### 4. Newsletter Workflow (`newsletter.yml`)
- **Triggers**: Schedule (daily at UTC 23:00), Manual dispatch
- **Purpose**: Generate actual newsletters and deploy to GitHub Pages

## Dependency Management

The project uses multiple dependency files for different purposes:

- `requirements.txt`: Full production dependencies
- `requirements-dev.txt`: Development and testing tools
- `requirements-minimal.txt`: Minimal dependencies for fast CI testing
- `pyproject.toml`: Modern Python packaging configuration

## Local Development Setup

```bash
# 1. Clone repository
git clone https://github.com/your-org/newsletter-generator.git
cd newsletter-generator

# 2. Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate     # Windows

# 3. Install development dependencies
pip install -r requirements-dev.txt
pip install -e .

# 4. Set up environment variables
cp .env.example .env
# Edit .env file with your API keys

# 5. Run tests
python run_tests.py dev
```

## Code Quality Tools

```bash
# Code formatting
black newsletter tests

# Import sorting
isort newsletter tests

# Linting
flake8 newsletter tests

# Type checking
mypy newsletter
```

## Pull Request Checklist

Before creating a Pull Request:

- [ ] All tests pass: `python run_tests.py ci`
- [ ] Code formatting is correct: `black --check newsletter tests`
- [ ] New features have tests
- [ ] Documentation updated (if needed)
- [ ] CHANGELOG.md updated (if needed)

## Deployment Process

1. **Development**: Work on feature branch
2. **Testing**: Local validation with `python run_tests.py ci`
3. **Pull Request**: Create PR to main branch
4. **CI Validation**: Automated tests run on GitHub Actions
5. **Code Review**: Team review and approval
6. **Merge**: Merge to main branch
7. **Auto Deploy**: Automatic deployment to GitHub Pages

## Troubleshooting

### CI Failures
1. Test locally with same Python version
2. Check dependency version conflicts
3. Verify environment variable settings
4. Check test data and mocking configuration

### Common Issues
- **gRPC errors**: Set `GOOGLE_API_USE_REST=true`
- **Dependency conflicts**: `pip install --upgrade pip` then reinstall
- **Test timeouts**: Check network connection and API response times

## Environment Variables for CI

```bash
# gRPC Configuration
GRPC_DNS_RESOLVER=native
GRPC_POLL_STRATEGY=epoll1
GOOGLE_API_USE_REST=true
GRPC_ENABLE_FORK_SUPPORT=0

# Testing
GEMINI_API_KEY=dummy_key_for_testing
SERPER_API_KEY=dummy_key_for_testing
```

## File Structure

```
.github/workflows/
├── ci.yml                 # Main CI workflow
├── code-quality.yml       # Code quality checks
├── test-tools.yml         # Tools testing
└── newsletter.yml         # Newsletter generation

tests/
├── test_ci.py             # CI testing script
├── test_minimal.py        # Minimal tests for CI
├── test_tools.py          # Tools testing
└── ...                    # Other test files

docs/dev/
├── CI_CD_GUIDE.md         # This file
├── CODE_QUALITY.md        # Code quality guidelines
└── langsmith_setup.md     # LangSmith integration guide
```

## Performance Metrics

- **Test execution time**: ~50% reduction with dependency optimization
- **CI stability**: External dependency removal improves reliability
- **Development efficiency**: Automated code quality checks 
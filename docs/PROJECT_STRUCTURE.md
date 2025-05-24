# Project Structure

This document outlines the organized file structure of the Newsletter Generator project.

## Root Directory

```
newsletter-generator/
├── 📁 .github/workflows/        # GitHub Actions CI/CD workflows
│   ├── ci.yml                   # Main CI workflow
│   ├── code-quality.yml         # Code quality checks
│   ├── test-tools.yml           # Tools testing
│   └── newsletter.yml           # Newsletter generation & deployment
├── 📁 .vscode/                  # VS Code configuration
├── 📁 config/                   # Configuration files
├── 📁 debug_archives/           # Debug files archive
├── 📁 docs/                     # Documentation
│   ├── 📁 dev/                  # Development documentation
│   │   ├── CI_CD_GUIDE.md       # CI/CD comprehensive guide
│   │   ├── CODE_QUALITY.md      # Code quality guidelines  
│   │   └── langsmith_setup.md   # LangSmith integration guide
│   └── UNIFIED_ARCHITECTURE_SUMMARY.md  # Architecture overview
├── 📁 newsletter/               # Main application code
├── 📁 output/                   # Generated newsletters
├── 📁 templates/                # HTML/text templates
├── 📁 tests/                    # Test files
│   ├── 📁 api_tests/            # API integration tests
│   ├── 📁 unit_tests/           # Unit tests
│   ├── 📁 test_data/            # Test data files
│   ├── test_ci.py               # CI testing script
│   ├── test_minimal.py          # Minimal tests for CI
│   ├── test_tools.py            # Tools testing
│   └── ...                      # Other test files
├── 📄 CHANGELOG.md              # Version history
├── 📄 README.md                 # Main project documentation
├── 📄 PRD.md                    # Product Requirements Document
├── 📄 architecture.md           # Technical architecture
├── 📄 pyproject.toml            # Modern Python packaging config
├── 📄 setup.py                  # Legacy setup (minimal)
├── 📄 requirements.txt          # Production dependencies
├── 📄 requirements-dev.txt      # Development dependencies
├── 📄 requirements-minimal.txt  # Minimal CI dependencies
├── 📄 run_tests.py              # Test runner script
└── 📄 config.yml                # Application configuration
```

## Key Directories

### `.github/workflows/`
Contains GitHub Actions workflows for automated CI/CD:
- **ci.yml**: Main CI with Python matrix testing
- **code-quality.yml**: Code formatting and linting
- **test-tools.yml**: Tool-specific testing 
- **newsletter.yml**: Newsletter generation and GitHub Pages deployment

### `docs/`
Documentation organized by purpose:
- **dev/**: Developer-focused documentation
  - CI/CD guides, code quality standards, integration setup
- **Root**: User and architecture documentation

### `tests/`
Comprehensive testing structure:
- **api_tests/**: External API integration tests
- **unit_tests/**: Pure unit tests without external dependencies  
- **test_data/**: Test fixtures and data files
- **Root**: Core test files including CI scripts

### `newsletter/`
Main application source code (see architecture.md for details)

## File Organization Principles

1. **Separation of Concerns**: Development docs in `docs/dev/`, user docs in root
2. **Testing Structure**: Organized by test type (unit, integration, API)
3. **CI/CD Integration**: Dedicated workflow files with clear purposes
4. **Dependency Management**: Multiple requirements files for different use cases
5. **Clean Root**: Minimal files in root, organized subdirectories

## Dependency Files

- **requirements.txt**: Full production dependencies for running the application
- **requirements-dev.txt**: Development tools (testing, linting, formatting)
- **requirements-minimal.txt**: Minimal dependencies for fast CI testing
- **pyproject.toml**: Modern Python packaging with tool configurations

## Recent Changes (v0.3.0)

1. **Moved** `scripts/test_ci.py` → `tests/test_ci.py`
2. **Organized** development documentation under `docs/dev/`
3. **Archived** temporary debug files to `debug_archives/`
4. **Removed** empty `scripts/` directory
5. **Added** comprehensive CI/CD documentation

This structure supports:
- ✅ Clear separation between user and developer documentation
- ✅ Efficient CI/CD with minimal dependencies
- ✅ Organized testing by purpose and scope
- ✅ Modern Python packaging standards
- ✅ Developer-friendly project navigation 
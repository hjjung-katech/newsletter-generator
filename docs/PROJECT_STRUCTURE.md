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
├── 📁 docs/                     # 📚 All Documentation
│   ├── 📁 dev/                  # Development documentation
│   │   ├── DEVELOPMENT_GUIDE.md # Comprehensive development guide
│   │   ├── CI_CD_GUIDE.md       # CI/CD comprehensive guide
│   │   ├── CODE_QUALITY.md      # Code quality guidelines  
│   │   └── langsmith_setup.md   # LangSmith integration guide
│   ├── 📁 setup/                # Setup and installation guides
│   │   └── INSTALLATION.md      # Installation and configuration
│   ├── 📁 user/                 # User documentation
│   │   ├── USER_GUIDE.md        # Comprehensive user manual
│   │   └── CLI_REFERENCE.md     # CLI command reference
│   ├── 📄 README.md             # Documentation navigation
│   ├── 📄 PRD.md                # Product Requirements Document
│   ├── 📄 ARCHITECTURE.md       # System architecture
│   ├── 📄 UNIFIED_ARCHITECTURE.md # Unified architecture details
│   ├── 📄 CHANGELOG.md          # Version history
│   └── 📄 PROJECT_STRUCTURE.md  # This file
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
├── 📄 README.md                 # Main project entry point
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

### `docs/` - Centralized Documentation Hub
All project documentation is organized under this directory:

#### `docs/dev/` - Developer Documentation
- **DEVELOPMENT_GUIDE.md**: Complete development setup and contribution guide
- **CI_CD_GUIDE.md**: CI/CD pipeline configuration and usage
- **CODE_QUALITY.md**: Code quality standards and tools
- **langsmith_setup.md**: LangSmith integration for cost tracking

#### `docs/setup/` - Installation & Configuration
- **INSTALLATION.md**: Detailed installation and setup instructions

#### `docs/user/` - User Documentation  
- **USER_GUIDE.md**: Comprehensive user manual with workflows
- **CLI_REFERENCE.md**: Complete CLI command reference

#### `docs/` Root - Core Project Documentation
- **README.md**: Documentation navigation and overview
- **PRD.md**: Product Requirements Document
- **ARCHITECTURE.md**: System architecture and design
- **UNIFIED_ARCHITECTURE.md**: Unified architecture implementation details
- **CHANGELOG.md**: Version history and release notes
- **PROJECT_STRUCTURE.md**: This file - project organization

### `tests/`
Comprehensive testing structure:
- **api_tests/**: External API integration tests
- **unit_tests/**: Pure unit tests without external dependencies  
- **test_data/**: Test fixtures and data files
- **Root**: Core test files including CI scripts

### `newsletter/`
Main application source code (see docs/ARCHITECTURE.md for details)

## Documentation Organization Principles

1. **Centralized**: All documentation under `docs/` directory
2. **User-Focused**: Clear separation by user type (end-user, developer, admin)
3. **Hierarchical**: Logical grouping with clear navigation
4. **Self-Contained**: Each document can be read independently
5. **Cross-Referenced**: Systematic linking between related documents

## File Organization Principles

1. **Clean Root**: Minimal files in root, focused on project entry point
2. **Separation of Concerns**: Documentation, code, tests, and config clearly separated
3. **Testing Structure**: Organized by test type (unit, integration, API)
4. **CI/CD Integration**: Dedicated workflow files with clear purposes
5. **Dependency Management**: Multiple requirements files for different use cases

## Dependency Files

- **requirements.txt**: Full production dependencies for running the application
- **requirements-dev.txt**: Development tools (testing, linting, formatting)
- **requirements-minimal.txt**: Minimal dependencies for fast CI testing
- **pyproject.toml**: Modern Python packaging with tool configurations

## Documentation Workflow

1. **Entry Point**: README.md provides project overview and quick start
2. **Navigation Hub**: docs/README.md guides users to appropriate documentation
3. **Specialized Docs**: Each subdirectory contains focused documentation
4. **Cross-References**: Documents link to related information
5. **Maintenance**: CHANGELOG.md tracks all changes including documentation

## Recent Changes (v0.4.0)

1. **Consolidated** all documentation under `docs/` directory
2. **Reorganized** documentation by user type and purpose
3. **Enhanced** README.md as focused project entry point
4. **Improved** docs/README.md as comprehensive navigation hub
5. **Established** systematic cross-referencing between documents
6. **Updated** all internal links to reflect new structure

This structure supports:
- ✅ Centralized documentation management
- ✅ Clear user journey from discovery to contribution
- ✅ Efficient maintenance and updates
- ✅ Systematic organization by purpose and audience
- ✅ Modern documentation best practices 
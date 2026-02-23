# Project Structure

> Note: 이 문서는 구조 이력/스냅샷 성격의 문서입니다.
> 최신 구조 정책과 실행 기준은 아래 SSOT를 우선합니다.
> - `docs/dev/LONG_TERM_REPO_STRATEGY.md`
> - `docs/dev/REPO_HYGIENE_POLICY.md`

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
├── 📁 debug_files/              # 🆕 Debug files (moved from root)
├── 📁 docs/                     # 📚 All Documentation
│   ├── 📁 dev/                  # Development documentation
│   │   ├── DEVELOPMENT_GUIDE.md # Comprehensive development guide
│   │   ├── MULTI_LLM_IMPLEMENTATION_SUMMARY.md # 🆕 Multi-LLM implementation report
│   │   ├── CI_CD_GUIDE.md       # CI/CD comprehensive guide
│   │   ├── CODE_QUALITY.md      # Code quality guidelines
│   │   └── langsmith_setup.md   # LangSmith integration guide
│   ├── 📁 setup/                # Setup and installation guides
│   │   └── INSTALLATION.md      # Installation and configuration
│   ├── 📁 user/                 # User documentation
│   │   ├── USER_GUIDE.md        # Comprehensive user manual
│   │   ├── CLI_REFERENCE.md     # CLI command reference
│   │   └── MULTI_LLM_GUIDE.md   # 🆕 Multi-LLM setup and usage guide
│   ├── 📁 technical/            # Technical documentation
│   │   └── LLM_CONFIGURATION.md # 🆕 LLM configuration guide
│   ├── 📄 README.md             # Documentation navigation
│   ├── 📄 PRD.md                # Product Requirements Document
│   ├── 📄 ARCHITECTURE.md       # System architecture (updated with Multi-LLM)
│   ├── 📄 UNIFIED_ARCHITECTURE.md # Unified architecture details
│   ├── 📄 CHANGELOG.md          # Version history
│   └── 📄 PROJECT_STRUCTURE.md  # This file
├── 📁 newsletter/               # Main application code
│   ├── __init__.py
│   ├── cli.py                   # CLI interface
│   ├── llm_factory.py           # 🆕 Multi-LLM factory system
│   ├── cost_tracking.py         # 🆕 Enhanced cost tracking
│   ├── graph.py                 # LangGraph workflows
│   ├── chains.py                # LangChain chains
│   ├── collect.py               # News collection
│   ├── compose.py               # Newsletter composition
│   ├── scoring.py               # 🆕 AI-based article scoring
│   ├── article_filter.py        # Article filtering
│   ├── sources.py               # News sources
│   ├── tools.py                 # Utility tools
│   ├── deliver.py               # Email/Drive delivery
│   ├── summarize.py             # Article summarization
│   ├── template_manager.py      # Template management
│   ├── date_utils.py            # Date utilities
│   ├── config.py                # Configuration management
│   └── utils/                   # Utility modules
├── 📁 output/                   # Generated newsletters
├── 📁 templates/                # HTML/text templates
├── 📁 tests/                    # Test files
│   ├── 📁 api_tests/            # API integration tests
│   ├── 📁 unit_tests/           # Unit tests
│   ├── 📁 test_data/            # Test data files
│   ├── test_llm.py              # 🆕 Basic LLM system tests
│   ├── test_llm_providers.py    # 🆕 LLM provider tests
│   ├── test_email_integration.py # Email integration tests
│   ├── test_ci.py               # CI testing script
│   ├── test_minimal.py          # Minimal tests for CI
│   ├── test_tools.py            # Tools testing
│   └── ...                      # Other test files
├── 📄 README.md                 # Main project entry point
├── 📄 .env.example              # 🆕 Environment variables example
├── 📄 pyproject.toml            # Modern Python packaging config
├── 📄 setup.py                  # Legacy setup (minimal)
├── 📄 requirements.txt          # Production dependencies
├── 📄 requirements-dev.txt      # Development dependencies
├── 📄 requirements-minimal.txt  # Minimal CI dependencies
├── 📄 scripts/devtools/run_tests.py              # Test runner script
└── 📄 config.yml                # Application configuration (updated with Multi-LLM)
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
- **MULTI_LLM_IMPLEMENTATION_SUMMARY.md**: 🆕 Multi-LLM system implementation completion report
- **CI_CD_GUIDE.md**: CI/CD pipeline configuration and usage
- **CODE_QUALITY.md**: Code quality standards and tools
- **langsmith_setup.md**: LangSmith integration for cost tracking

#### `docs/setup/` - Installation & Configuration
- **INSTALLATION.md**: Detailed installation and setup instructions

#### `docs/user/` - User Documentation
- **USER_GUIDE.md**: Comprehensive user manual with workflows
- **CLI_REFERENCE.md**: Complete CLI command reference
- **MULTI_LLM_GUIDE.md**: 🆕 Multi-LLM provider setup and usage guide

#### `docs/technical/` - Technical Documentation
- **LLM_CONFIGURATION.md**: 🆕 LLM configuration and optimization guide

#### `docs/` Root - Core Project Documentation
- **README.md**: Documentation navigation and overview
- **PRD.md**: Product Requirements Document
- **ARCHITECTURE.md**: System architecture and design (updated with Multi-LLM)
- **UNIFIED_ARCHITECTURE.md**: Unified architecture implementation details
- **CHANGELOG.md**: Version history and release notes
- **PROJECT_STRUCTURE.md**: This file - project organization

### `newsletter/` - Main Application Code

#### 🆕 Multi-LLM System Components
- **llm_factory.py**: LLM Factory pattern with provider abstraction
- **cost_tracking.py**: Enhanced cost tracking for multiple providers

#### Core Application Files
- **cli.py**: Typer-based CLI interface
- **graph.py**: LangGraph workflow definitions
- **chains.py**: LangChain chain implementations
- **collect.py**: News collection from multiple sources
- **compose.py**: Newsletter composition
- **scoring.py**: 🆕 AI-based article scoring system
- **article_filter.py**: Article filtering and deduplication
- **sources.py**: News source management
- **tools.py**: Utility tools and helpers
- **deliver.py**: Email and Drive delivery
- **config.py**: Configuration management

### `tests/`
Comprehensive testing structure:
- **api_tests/**: External API integration tests
- **unit_tests/**: Pure unit tests without external dependencies
- **test_data/**: Test fixtures and data files
- **test_llm.py**: 🆕 Basic LLM system testing
- **test_llm_providers.py**: 🆕 Multi-provider LLM testing
- **test_email_integration.py**: Comprehensive email testing
- **Root**: Core test files including CI scripts

### `debug_files/` - Debug Archive
🆕 Moved all debug files to separate directory for cleaner project root

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

1. **🆕 Multi-LLM System Implementation**
   - Added `llm_factory.py` for Multi-LLM provider management
   - Enhanced `cost_tracking.py` for multiple provider cost monitoring
   - Added `scoring.py` for AI-based article scoring
   - Updated `config.yml` with comprehensive LLM settings

2. **📚 Documentation Enhancements**
   - Added `MULTI_LLM_GUIDE.md` for user guidance on multi-provider setup
   - Added `MULTI_LLM_IMPLEMENTATION_SUMMARY.md` for development completion report
   - Added `LLM_CONFIGURATION.md` for technical configuration guidance
   - Updated `ARCHITECTURE.md` with Multi-LLM system details

3. **🧪 Testing Infrastructure**
   - Added `test_llm.py` for basic LLM system testing
   - Added `test_llm_providers.py` for multi-provider testing
   - Enhanced `test_email_integration.py` for comprehensive email testing

4. **🔧 Project Organization**
   - Created `debug_files/` directory and moved all debug files
   - Added `.env.example` for environment variables guidance
   - Updated `.gitignore` to include debug_files directory
   - Enhanced project structure documentation

5. **⚙️ Configuration Management**
   - Updated `config.yml` with provider-specific LLM settings
   - Added function-specific LLM optimization configurations
   - Enhanced fallback system configuration

This structure now supports:
- ✅ Multi-LLM provider integration (Gemini, OpenAI, Anthropic)
- ✅ Automatic fallback system for API quota management
- ✅ Function-specific LLM optimization
- ✅ Comprehensive cost tracking across providers
- ✅ Enhanced testing infrastructure
- ✅ Cleaner project organization
- ✅ Centralized documentation management
- ✅ Clear user journey from discovery to contribution
- ✅ Efficient maintenance and updates
- ✅ Systematic organization by purpose and audience
- ✅ Modern documentation best practices

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Newsletter Generator** - an AI-powered Python CLI/Web application that collects, summarizes, and delivers personalized newsletters. The system uses multiple LLM providers (Gemini, OpenAI, Anthropic) with automatic fallback, collects news from various sources, and delivers newsletters via email using Postmark or stores them on Google Drive.

## Development Commands

### Core Commands

```bash
# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run CLI newsletter generation
python -m newsletter run --keywords "AI,tech" --to user@example.com

# Generate newsletter with domain-based keyword suggestion
python -m newsletter run --domain "인공지능" --suggest-count 10

# Interactive keyword review mode (NEW!)
python -m newsletter run --domain "AI" --interactive

# Generate keywords only (for review)
python -m newsletter suggest --domain "블록체인" --count 8

# Start web interface for development
python test_server.py
# Or from web directory
cd web && python app.py

# Test email configuration
python -m newsletter test-email --to your@email.com

# Environment setup (interactive)
python setup_env.py
```

### Testing Commands

```bash
# Run all tests
pytest

# Run specific test categories
pytest tests/test_api.py -v                    # API tests
pytest tests/unit_tests/ -v                    # Unit tests
pytest tests/integration/ -v                   # Integration tests
pytest tests/e2e/ -v                          # End-to-end tests

# Run with coverage
pytest --cov=newsletter --cov-report=html

# Run specific markers
pytest -m "unit"                              # Unit tests only
pytest -m "integration"                       # Integration tests only
pytest -m "real_api"                          # Tests requiring real APIs
pytest -m "mock_api"                          # Tests with mocked APIs
```

### Code Quality Commands

```bash
# Format code
black newsletter tests web
isort --profile black newsletter tests web

# Lint code
flake8 newsletter tests web --max-line-length=88 --ignore=E203,W503

# Type checking
mypy newsletter

# Security scanning
detect-secrets scan --all-files
bandit -r newsletter

# Pre-commit hooks (install once)
pre-commit install
pre-commit run --all-files
```

### Build Commands

```bash
# Install in development mode
pip install -e .

# Build wheel
python -m build

# Create PyInstaller executable (Windows) - Enhanced with hooks
python build_web_exe_enhanced.py

# Note: The build process now uses PyInstaller hooks for better dependency management
# All hidden imports and data files are managed centrally in pyinstaller_hooks/hook-newsletter.py
```

## High-Level Architecture

### Core System Architecture

The system follows a modular architecture with clear separation of concerns:

1. **CLI Interface** (`newsletter/cli.py`) - Main command-line interface using Typer
2. **Web Interface** (`web/app.py`) - Flask-based web application 
3. **Core Processing Pipeline**:
   - **Collection** (`newsletter/collect.py`) - News gathering from multiple sources
   - **Processing** (`newsletter/chains.py`, `newsletter/graph.py`) - LangGraph workflows for AI processing
   - **Composition** (`newsletter/compose.py`) - HTML newsletter generation
   - **Delivery** (`newsletter/deliver.py`) - Email sending and file storage

### Multi-LLM System

The system supports multiple LLM providers with automatic fallback:

- **LLM Factory** (`newsletter/llm_factory.py`) - Central LLM provider management
- **Supported Providers**: Google Gemini, OpenAI GPT, Anthropic Claude
- **Task Optimization**: Different models optimized for specific tasks (summarization, HTML generation, scoring)
- **Auto-Fallback**: Automatic switching between providers on quota limits or failures
- **Cost Tracking** (`newsletter/cost_tracking.py`) - Real-time usage and cost monitoring

### Configuration System

- **Centralized Settings** (`newsletter/centralized_settings.py`) - Type-safe Pydantic-based configuration
- **Environment Variables**: Primary configuration method with `.env` file support
- **YAML Config** (`config.yml`) - LLM-specific model configurations
- **Settings Migration**: Backward compatibility with legacy environment variable access

## Key Directories and Files

### Core Application (`newsletter/`)
- `cli.py` - Main CLI interface with Typer
- `main.py` - Core business logic and orchestration
- `llm_factory.py` - Multi-LLM provider factory and management
- `collect.py` - News collection from Serper API, RSS, Naver
- `compose.py` - HTML newsletter generation with Jinja2 templates
- `deliver.py` - Email delivery via Postmark, Google Drive storage
- `chains.py` - LangChain chain definitions
- `graph.py` - LangGraph workflow orchestration
- `sources.py` - News source configuration and management
- `tools.py` - Utility functions for AI operations
- `centralized_settings.py` - Type-safe configuration management

### Web Interface (`web/`)
- `app.py` - Main Flask application
- `tasks.py` - Background job processing with Redis/RQ
- `mail.py` - Email functionality integration
- `templates/` - Jinja2 templates for web interface
- `static/` - CSS, JS, and image assets

### Testing (`tests/`)
- `unit_tests/` - Unit tests for individual components
- `integration/` - Integration tests for system interactions
- `api_tests/` - API endpoint and functionality tests
- `e2e/` - End-to-end workflow tests
- `deployment/` - Deployment and smoke tests

### Documentation (`docs/`)
- `ARCHITECTURE.md` - Detailed system architecture
- `user/` - User guides and CLI reference
- `dev/` - Development guides and contribution info
- `technical/` - Technical implementation details

## Important Implementation Details

### Environment Variables Management
- Use `newsletter.centralized_settings.get_settings()` for accessing configuration
- Avoid direct `os.getenv()` calls - use `newsletter.compat_env.getenv_compat()` for compatibility
- Environment variables are validated at startup with proper error messages

### LLM Provider Integration
- Always use `newsletter.llm_factory.LLMFactory` for LLM operations
- Implement proper fallback handling for API quota limits
- Track costs using `newsletter.cost_tracking.CostTracker`
- Each LLM task should specify appropriate model selection criteria

### Korean Language Support
- System includes comprehensive Unicode/UTF-8 handling for Windows
- Korean text processing optimized for news content
- Proper encoding handling in file operations and API calls

### PyInstaller Build System
- Build system uses PyInstaller hooks for centralized dependency management
- All hidden imports, data files, and binaries are defined in `pyinstaller_hooks/hook-newsletter.py`
- This approach reduces maintenance burden by eliminating manual hidden-import lists in build scripts
- Hook file automatically collects dependencies from key packages (LangChain, web modules, etc.)
- Build script (`build_web_exe_enhanced.py`) is now much simpler and focuses on build configuration
- To modify dependencies: edit `pyinstaller_hooks/hook-newsletter.py` instead of the main build script
- Hook system provides better error handling and dependency discovery compared to manual lists

### PyInstaller Logging Control
- **Build-time debug mode**: Set `PYI_DEBUG=true` environment variable to enable `--debug imports` during build
- **Runtime log level**: Built executables use `ERROR` log level by default to minimize PyiFrozenFinder output
- **Runtime log control**: Set `PYINSTALLER_LOG_LEVEL=ERROR` when running the exe to suppress verbose import logs
- **For debugging imports**: Use `PYI_DEBUG=true python build_web_exe_enhanced.py` to enable detailed import analysis
- **Clean console output**: Default configuration eliminates console spam while preserving error messages

### Testing Strategy
- Tests are categorized with pytest markers (`unit`, `integration`, `real_api`, `mock_api`)
- Mock mode available for development (`MOCK_MODE=true`)
- Separate test environments for different deployment scenarios

### Security Considerations
- Secrets management through environment variables only
- API keys masked in logs and debug output
- Input validation for all user-provided data
- CSRF protection in web interface

### Error Handling
- Comprehensive error handling with informative messages
- Automatic retry mechanisms for transient failures
- Graceful degradation when services are unavailable
- Detailed logging for debugging and monitoring

## Enhanced Domain and Keyword Features (2024-12)

The system now provides improved domain-based keyword generation with interactive editing capabilities:

### CLI Interactive Mode

```bash
# Interactive keyword review and editing
newsletter run --domain "AI" --interactive

# This allows you to:
# - Review generated keywords before newsletter creation
# - Edit individual keywords (e <number>)
# - Add new keywords (a)
# - Delete keywords (d <number>)
# - Regenerate all keywords (r)
# - Continue with current keywords (Enter)
```

### Web Interface Enhancements

The web interface now supports:

1. **Inline Keyword Editing**: Generated keywords are displayed as editable tags
2. **Individual Keyword Management**: Click to edit, hover to delete
3. **Add New Keywords**: Plus button to add custom keywords
4. **Two Generation Modes**:
   - **Review Mode**: Edit keywords before newsletter generation
   - **Direct Mode**: Generate newsletter directly from domain (like CLI)

### API Endpoints

```bash
# Keyword suggestion API
POST /api/suggest
{
  "domain": "artificial intelligence",
  "count": 10
}

# Newsletter generation with domain or keywords
POST /api/generate
{
  "domain": "AI",           // Direct domain-based generation
  "keywords": ["AI", "ML"], // Or use specific keywords
  "template_style": "compact",
  "email_compatible": false
}
```

### Usage Patterns

**For Quick Generation:**
```bash
newsletter run --domain "fintech"
```

**For Reviewed Generation:**
```bash
newsletter run --domain "fintech" --interactive
```

**For Keyword-Only Generation:**
```bash
newsletter suggest --domain "fintech" --count 15
```

## Common Development Tasks

### Adding a New LLM Provider
1. Create provider class in `newsletter/llm_factory.py`
2. Add configuration in `newsletter/centralized_settings.py`
3. Update cost tracking in `newsletter/cost_tracking.py`
4. Add tests in `tests/unit_tests/test_llm_providers.py`

### Adding New News Sources
1. Implement source in `newsletter/sources.py`
2. Update collection logic in `newsletter/collect.py`
3. Add source configuration to settings
4. Test with integration tests in `tests/api_tests/`

### Modifying Newsletter Templates
1. Edit templates in `newsletter/templates/`
2. Update template logic in `newsletter/compose.py`
3. Test email compatibility with `tests/test_email_compatibility.py`
4. Validate HTML output in various email clients

### Managing PyInstaller Dependencies
1. **Adding new dependencies**: Edit `pyinstaller_hooks/hook-newsletter.py` and add modules to appropriate category lists
2. **Adding data files**: Update the `datas` list in the hook file with new template or config files
3. **Adding binary dependencies**: Add to `binaries` list or use `collect_dynamic_libs()` for packages
4. **Excluding unnecessary modules**: Add to `excludes` list to reduce bundle size
5. **Testing build**: Run `python build_web_exe_enhanced.py` and check for missing dependencies
6. **Debug mode**: Use `PYI_DEBUG=true python build_web_exe_enhanced.py` for detailed import analysis (generates verbose output)
7. **Troubleshooting**: Check PyInstaller warnings and add missing modules to hook file

### Debugging Common Issues
- **Email delivery issues**: Check `newsletter/deliver.py` and Postmark configuration
- **LLM quota errors**: Verify fallback logic in `newsletter/llm_factory.py`
- **Unicode/encoding issues**: Check Windows UTF-8 handling in `newsletter/cli.py`
- **Web interface errors**: Debug Flask app in `web/app.py`
- **PyInstaller build issues**: Check `pyinstaller_hooks/hook-newsletter.py` and add missing dependencies; review build warnings for "Hidden import not found" messages
- **Excessive console output in exe**: PyInstaller logging is now minimized by default; use `PYINSTALLER_LOG_LEVEL=ERROR` if still experiencing verbose output
- **Import debugging needed**: Enable build-time debug with `PYI_DEBUG=true` environment variable (expect verbose console output)

Remember to run the full test suite and linting before making any changes, and ensure all environment variables are properly configured for development.
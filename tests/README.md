# Newsletter Generator Tests

This directory contains tests for the Newsletter Generator system.

## Test Directory Structure

- **Main Tests**: Tests in the root directory that cover general functionality
- **API Tests**: Tests in the `api_tests/` directory that require API keys
- **Unit Tests**: Tests in the `unit_tests/` directory for isolated unit testing
- **Backup Tests**: Tests in the `_backup/` directory (deprecated or archived tests)

## Running Tests

### Using the Automated Test Runner

The easiest way to run tests is using the automated test runner script:

```bash
# Run all main tests (excluding backup)
python run_tests.py --all

# Run only unit tests
python run_tests.py --unit

# Run only API tests
python run_tests.py --api

# List available tests
python run_tests.py --list

# List all tests including unit, API, and backup tests
python run_tests.py --list-all

# Run a specific test
python run_tests.py --test serper_api

# Format code and run tests
python run_tests.py --format --all
```

### Manual Test Execution

You can also run tests manually using Python's unittest or pytest:

```bash
# Using pytest to run all tests
pytest tests/

# Run a specific test file
python -m pytest tests/test_newsletter.py

# Run tests in a specific directory
python -m pytest tests/unit_tests/
```

## Test Files

### Main Tests (Root Directory)

| Test File | Description |
|-----------|-------------|
| `test_article_filter.py` | Tests article filtering functionality including duplicate detection and keyword grouping |
| `test_chains.py` | Tests LangChain/LangGraph chains for content generation |
| `test_compose.py` | Tests newsletter composition and formatting |
| `test_graph_date_parser.py` | Tests date parsing functionality for graphs and timelines |
| `test_isolate_tools.py` | Tests isolation of various tools and utilities |
| `test_minimal.py` | Minimal tests for core functionality |
| `test_news_integration.py` | Tests integration with news sources |
| `test_newsletter.py` | Tests end-to-end newsletter generation |
| `test_serper_api.py` | Tests Serper.dev API integration |
| `test_template.py` | Tests HTML template loading functionality |
| `test_tools.py` | Tests utility functions and tools |

### API Tests (`api_tests/` Directory)

| Test File | Description |
|-----------|-------------|
| `test_article_filter_integration.py` | Integration tests for article filtering with real API data |
| `test_collect.py` | Tests article collection functionality using APIs |
| `test_improved_search.py` | Tests enhanced search functionality with APIs |
| `test_news_integration_enhanced.py` | Enhanced tests for news collection using multiple APIs |
| `test_search_improved.py` | Tests improved search methods with real API calls |
| `test_serper_direct.py` | Tests direct Serper.dev API calls and response handling |
| `test_sources.py` | Tests various news sources and their API interfaces |
| `test_summarize.py` | Tests article summarization using AI APIs |

### Unit Tests (`unit_tests/` Directory)

| Test File | Description |
|-----------|-------------|
| `test_date_utils.py` | Tests date utility functions for parsing and formatting |
| `test_new_newsletter.py` | Tests new newsletter creation functionality |
| `test_new_newsletter_with_weeks.py` | Tests newsletter creation with week-based scheduling |
| `test_real_newsletter.py` | Tests realistic newsletter generation scenarios |
| `test_scrape_dates.py` | Tests date scraping from article content |
| `test_weeks_ago.py` | Tests functionality related to calculating weeks ago dates |

## Test Writing Guide

When adding new functionality, please follow these principles when writing tests:

1. **Unit Tests**: Test the core functionality of each function and class.
   - Place in `unit_tests/` directory if it tests isolated functionality
   - Should not require external API keys or internet connectivity

2. **API Tests**: Test functionality that requires API calls.
   - Place in `api_tests/` directory
   - May require API keys to be set in environment variables

3. **Integration Tests**: Test how different components work together.
   - Place in the main directory if it integrates multiple components
   - May require mocking for external services

4. **Edge Case Tests**: Test exceptional situations and boundary conditions.
   - Include tests for error handling, unusual inputs, and edge cases

5. **Mocking**: Mock external API calls appropriately to ensure test stability.
   - Use the provided mock files for common services

## Test Utilities

Several utility files are provided to support testing:

- `conftest.py` - Contains pytest fixtures and configurations
- `dependencies.py` - Manages test dependencies
- `helpers.py` - Contains helper functions for tests
- `mock_google_generativeai.py` - Mocks Google AI APIs
- `mock_langchain_google_genai.py` - Mocks LangChain integration with Google AI
- `tools_minimal.py` - Provides minimal implementations of tools for testing

## Test Data

Test data required for tests is stored in suitable fixtures. Temporary files generated during tests are automatically cleaned up after test completion.

# Newsletter Generator Tests

This directory contains tests for the Newsletter Generator system.

## Running Tests

### Template Loading Tests
```powershell
cd ..
python -m tests.test_template
```

### Newsletter Generation Tests
```powershell
cd ..
python -m tests.test_newsletter
```

### Running All Tests
You can run all tests using pytest:
```powershell
pip install pytest
pytest .\tests\
```

## Test Files

### Core Functionality Tests
- `test_template.py` - Tests HTML template loading functionality
- `test_newsletter.py` - Tests end-to-end newsletter generation
- `test_collect.py` - Tests article collection functionality
- `test_compose.py` - Tests newsletter composition
- `test_summarize.py` - Tests article summarization
- `test_tools.py` - Tests utility functions and tools

### API and Search Tests
- `test_serper_api.py` - Tests Serper.dev API integration 
- `test_serper_direct.py` - Tests direct Serper.dev API calls and response handling
- `test_search_improved.py` - Tests improved search functionality
- `test_news_integration.py` - Tests news collection integration
- `test_improved_search.py` - Tests search functionality with improved methods

### Data Processing Tests
- `test_graph_date_parser.py` - Tests date parsing functionality for graphs

### Filtering and Grouping Tests
- `test_article_filter.py` - Unit tests for article filtering module
- `test_article_filter_integration.py` - Integration tests for filtering functionality

## Test Execution

### Filtering and Grouping Tests
- Run unit tests for filtering module:
```bash
python -m unittest tests.test_article_filter
```
- Run integration tests for filtering functionality:
```bash
python -m unittest tests.test_article_filter_integration
```

### API and Search Tests
- Run API-related tests:
```bash
python -m unittest tests.test_serper_api
python -m unittest tests.test_sources
```

### Core Functionality Tests
- `test_collect.py` - Tests article collection functionality
- `test_summarize.py` - Tests article summarization
- `test_template.py` - Tests HTML template loading functionality
- `test_compose.py` - Tests newsletter composition
- `test_graph_date_parser.py` - Tests date parsing functionality for graphs

### Comprehensive Tests
- `test_newsletter.py` - Tests comprehensive newsletter functionality

## Automated Testing

To make testing easier, automated scripts are provided:

```bash
# Run all tests
python run_tests.py --all

# List available tests
python run_tests.py --list

# Run specific test
python run_tests.py --test article_filter

# Run filtering and grouping tests
python run_tests.py --test filter

# Run formatting check and then tests
python run_tests.py --format --test filter
```

## Test Writing Guide

When adding new functionality, please follow these principles when writing tests:

1. **Unit Tests**: Test the core functionality of each function and class.
2. **Integration Tests**: Test how different components work together.
3. **Edge Case Tests**: Test exceptional situations and boundary conditions.
4. **Mocking**: Mock external API calls appropriately to ensure test stability.

## Test Data

Test data required for tests is stored in the `tests/fixtures` directory. Temporary files generated during tests are automatically cleaned up after test completion.

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

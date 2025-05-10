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

- `test_template.py` - Tests HTML template loading functionality
- `test_newsletter.py` - Tests end-to-end newsletter generation
- `test_collect.py` - Tests article collection functionality
- `test_compose.py` - Tests newsletter composition
- `test_summarize.py` - Tests article summarization

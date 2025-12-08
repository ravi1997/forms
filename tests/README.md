# Tests

This directory contains all test files for the application.

## Directory Structure

- `models/` - Tests for database models
- `routes/` - Tests for API routes
- `schemas/` - Tests for data schemas
- `conftest.py` - Test configuration and fixtures

## Running Tests

To run all tests:
```bash
pytest
```

To run tests with coverage:
```bash
pytest --cov=app
```

To run tests with verbose output:
```bash
pytest -v
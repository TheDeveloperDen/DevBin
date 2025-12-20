# Testing Guide

This guide explains how to run tests locally and in CI/CD.

## Quick Start

### 1. Install Test Dependencies

```bash
uv sync --extra test
```

### 2. Start Test Database

```bash
# Start PostgreSQL test database in Docker
./scripts/setup_test_db.sh
```

This will:
- Start PostgreSQL 16 in Docker on port 5433
- Create the `devbin_test` database
- Wait for the database to be ready

### 3. Run Tests

```bash
# Run all tests
uv run pytest

# Run only unit tests (no database required)
uv run pytest tests/unit/ -v

# Run with coverage report
uv run pytest --cov=app --cov-report=html

# Run in parallel (faster)
uv run pytest -n auto

# Run specific test file
uv run pytest tests/unit/test_token_utils.py -v
```

## Test Structure

```
tests/
├── unit/              # Fast tests, no external dependencies
├── integration/       # Tests with database and file system
├── api/              # Full API endpoint tests
└── security/         # Security-focused tests
```

## Local Development

### Managing Test Database

```bash
# Start test database
docker-compose -f docker-compose.test.yml up -d

# Stop test database
docker-compose -f docker-compose.test.yml down

# Clean up database and volumes
docker-compose -f docker-compose.test.yml down -v

# View logs
docker-compose -f docker-compose.test.yml logs -f
```

### Test Database Connection

- **Host**: localhost
- **Port**: 5433 (to avoid conflicts with dev database on 5432)
- **Database**: devbin_test
- **User**: postgres
- **Password**: postgres
- **Connection String**: `postgresql://postgres:postgres@localhost:5433/devbin_test`

### Environment Variables

Tests use environment variables from `pytest.ini` by default:

```ini
APP_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5433/devbin_test
APP_BASE_FOLDER_PATH=/tmp/devbin_test_files
APP_DEBUG=true
APP_ALLOW_CORS_WILDCARD=true
```

You can override these by setting environment variables before running tests:

```bash
export APP_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/my_test_db
uv run pytest
```

## CI/CD Setup

### GitHub Actions

The test database is automatically configured in `.github/workflows/test.yml`:

```yaml
services:
  postgres:
    image: postgres:16
    env:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: devbin_test
    ports:
      - 5432:5432
```

In CI, tests use port 5432 (the default PostgreSQL port in the service container).

### Running Tests in CI

```bash
# CI sets APP_DATABASE_URL to use the service container
pytest -v --cov=app --cov-report=xml
coverage report --fail-under=80
```

## Test Categories

### Unit Tests (Fast, Isolated)

```bash
pytest tests/unit/ -m unit
```

- No database or file system
- Mock external dependencies
- < 1ms per test
- Test utilities, validators, pure functions

### Integration Tests

```bash
pytest tests/integration/ -m integration
```

- Real database with transaction rollback
- File system operations (temp directories)
- 10-100ms per test
- Test service layer

### API Tests

```bash
pytest tests/api/
```

- Full HTTP request/response cycle
- All middleware included
- 50-200ms per test
- Test endpoints, rate limiting, caching

## Coverage Reports

### View HTML Coverage Report

```bash
uv run pytest --cov=app --cov-report=html
open htmlcov/index.html  # or xdg-open on Linux
```

### Coverage Targets

- Overall: 80%+ (enforced in CI)
- Critical modules: 90%+
  - `app/services/paste_service.py`
  - `app/utils/token_utils.py`
  - `app/api/subroutes/pastes.py`

## Troubleshooting

### Database Connection Errors

**Problem**: `connection refused` or `could not connect to server`

**Solution**:
1. Check if test database is running: `docker ps | grep devbin_test`
2. Start database: `./scripts/setup_test_db.sh`
3. Check database logs: `docker-compose -f docker-compose.test.yml logs`

### Port Already in Use

**Problem**: Port 5433 is already in use

**Solution**:
1. Change port in `docker-compose.test.yml`
2. Update `pytest.ini` to match
3. Restart database

### Tests Fail Randomly

**Problem**: Tests pass sometimes, fail other times (flaky tests)

**Solution**:
1. Check if tests are properly isolated (no shared state)
2. Verify database cleanup between tests
3. Check for timing issues (use `freezegun` for time-based tests)

### Slow Tests

**Problem**: Tests take too long to run

**Solution**:
1. Run tests in parallel: `pytest -n auto`
2. Run only unit tests: `pytest tests/unit/`
3. Run specific test file instead of entire suite
4. Check for N+1 query issues in integration tests

## Best Practices

### Writing New Tests

1. **Use descriptive names**: `test_create_paste_with_valid_data_returns_200`
2. **Test one thing**: Each test should verify one specific behavior
3. **Use fixtures**: Reuse common setup via pytest fixtures
4. **Clean up**: Tests should not leave artifacts (files, DB records)
5. **Mark tests**: Use `@pytest.mark.unit` or `@pytest.mark.integration`

### Test Data

- Use `faker` for realistic test data (IPs, user agents, names)
- Use `sample_paste_data` fixture for consistent paste creation
- Create factory functions for complex test objects

### Mocking

- **Mock external services**: Time, disk usage checks, network calls
- **Use real implementations**: Database, file system (with temp dirs)
- **Mock sparingly**: Real implementations catch more bugs

## Continuous Integration

Tests run automatically on:
- Push to `master` or `develop`
- Pull requests

### CI Requirements

- All tests must pass
- Coverage must not decrease
- Coverage must be >= 80%
- Linting must pass (ruff)

### Viewing CI Results

1. Go to GitHub Actions tab
2. Click on the latest workflow run
3. View test results and coverage report

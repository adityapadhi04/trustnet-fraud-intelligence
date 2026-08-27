# TRUSTNET - Testing Environment

This directory holds unit and integration tests for TRUSTNET's ML and API pipelines.

## Frameworks
- **Framework**: `pytest`
- **Coverage**: `pytest-cov`

## Test Execution
Once packages are configured in future steps, run the test suite using:
```bash
pytest
```
- **Unit Tests**: Verifying preprocessing logic, graph metrics calculations, and model score normalization.
- **Integration Tests**: Simulating API calls to FastAPI endpoint, testing mock database connections, and validation of response payloads.

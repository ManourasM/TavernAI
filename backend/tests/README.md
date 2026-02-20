# TavernAI Backend Test Suite

This directory contains comprehensive tests for the TavernAI backend covering:

- **Order submission flow** (HTTP integration tests)
- **NLP classification behavior** (unit tests with Greek inputs)
- **Table state management** (in-memory state handling)
- **Quantity and unit parsing** (liters, kilograms, milliliters)
- **Edge cases and error handling** (invalid inputs, boundary conditions)
- **WebSocket broadcasting** (mocked to avoid real connections)

## Running Tests

### First Time Setup

```bash
cd backend
pip install -r requirements-test.txt
```

### Run All Tests

```bash
pytest tests -v
```

### Run with Coverage Report

```bash
pytest tests -v --cov=app --cov-report=html
```

Then open `htmlcov/index.html` in a browser.

### Run Specific Test File

```bash
pytest tests/test_nlp_classification.py -v
```

### Run Specific Test

```bash
pytest tests/test_order_submission.py::test_submit_basic_greek_order -v
```

### Run Only Fast Tests

```bash
pytest tests -v -m "not slow"
```

## Test Files

| File | Purpose |
|------|---------|
| `conftest.py` | Shared fixtures (async client, state reset, mocks) |
| `test_order_submission.py` | HTTP flow tests for order creation |
| `test_nlp_classification.py` | Greek NLP and classification logic |
| `test_quantity_parsing.py` | Quantity/unit parsing (kg, liters, ml) |
| `test_table_management.py` | In-memory state and table operations |
| `test_edge_cases.py` | Error handling and boundary conditions |
| `test_websocket_mock.py` | Broadcast behavior (mocked) |

## Key Test Patterns

### Greek Input Testing
All tests use real Greek characters:
```python
payload = {"order_text": "2 σουβλάκια\n1 μπύρα"}
```

### State Isolation
Each test uses the `reset_app_state` fixture to clear in-memory state:
```python
def test_something(reset_app_state):
    # In-memory dicts are clean
    assert orders_by_table == {}
```

### WebSocket Mocking
Broadcast functions are mocked to avoid real WebSocket connections:
```python
def test_broadcast(mock_broadcast_to_station):
    # Verify broadcast was called without opening real socket
    assert mock_broadcast_to_station.call_count > 0
```

## Coverage Goals

- **Backend logic**: 80%+
- **Parsing helpers**: 100%

Run `pytest tests --cov=app --cov-report=term-missing` to see what's not covered.

## Discovered Issues

During test development, the following areas were identified as needing attention:

1. **Unicode edge cases** - Very long Greek strings or emoji may need validation
2. **State cleanup** - Ensure WebSocket connections are properly closed
3. **Greek stemming** - Some plural forms may not match expected menu items
4. **Quantity overflow** - No validation on very large quantities (999999+)

## Debugging Tests

Add `pytest -v -s` to see print statements and debug output.

For a single failing test with full traceback:
```bash
pytest tests/test_nlp_classification.py::test_classify_kitchen_item -vv
```

## Notes

- Tests do NOT modify production code (fixtures handle isolation)
- No external dependencies (mocks replace WebSocket/DB calls)
- All fixtures are async-compatible with `pytest-asyncio`
- Uses real Greek menu items and order text throughout

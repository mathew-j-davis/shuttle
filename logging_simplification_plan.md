# Logging Simplification Plan

## Goal
Remove the `logging_options` parameter from all function signatures, simplifying the codebase while maintaining functionality.

## Current State
- `logging_options` parameter is passed through most functions but never used
- `get_logger()` has already been updated to take no parameters ✓
- Global logging configuration is set via `configure_logging()`
- Hierarchy logging has been temporarily disabled (commented out)
- Need to decide whether to re-enable hierarchy logging or remove it completely

## Completed Changes

### 1. Core Logger Injection Module (`logger_injection.py`) ✓
- `get_logger()` now takes no parameters
- Auto-detects function name and module from call stack
- Uses only global configuration via `_resolve_logging_options()`
- Simplified `_get_logger_name_from_context()` to not use instance parameter

### 2. Places Where `logging_options` Must Be Retained

#### a. Test-specific logger setup
For tests that need special logging configuration, they should:
1. Call `configure_logging()` at test setup
2. Call `reset_logging_config()` at test teardown
3. Or directly use `setup_logging()` from `logging_setup.py` if they need a specific logger

#### b. Initial configuration
- `shuttle.py` in `_setup_logging()` - calls `configure_logging()`
- This is the only place that sets up global logging options

### 3. Migration Strategy

Since `get_logger()` already takes no parameters, we just need to:

#### Step 1: Remove `logging_options` parameters from function signatures ✓ ALREADY DONE
Since no calls to `get_logger()` pass any parameters, this means the parameter is already unused everywhere.

#### Step 2: Remove `logging_options` from function signatures
From:
```python
def some_function(arg1, arg2, logging_options=None):
    """Docstring mentioning logging_options parameter"""
    logger = get_logger()  # Already takes no params
```

To:
```python
def some_function(arg1, arg2):
    """Docstring with logging_options reference removed"""
    logger = get_logger()
```

#### Step 3: Update function calls
Remove `logging_options` from all function calls:
From:
```python
result = some_function(x, y, logging_options=logging_options)
```

To:
```python
result = some_function(x, y)
```

Note: Need to check if any functions pass `logging_options` to other functions even though they don't use it themselves.

### 4. Files to Update

#### High-level modules (update first):
1. `shuttle.py` - Keep `configure_logging()` in `_setup_logging()`
2. `scanning.py` - Remove all `logging_options` parameters
3. `post_scan_processing.py` - Remove all `logging_options` parameters
4. `throttle_utils.py` - Remove all `logging_options` parameters
5. `daily_processing_tracker.py` - Remove all `logging_options` parameters
6. `throttler.py` - Remove all `logging_options` parameters

#### Shared library modules:
1. `files.py` - Remove all `logging_options` parameters
2. `scan_utils.py` - Remove all `logging_options` parameters
3. `config.py` - Remove all `logging_options` parameters
4. `notifier.py` - Remove all `logging_options` parameters
5. `ledger.py` - Remove all `logging_options` parameters

#### Defender test app:
1. `shuttle_defender_test.py` - Keep `configure_logging()` in main setup
   - **Bug found**: Line 237 calls `create_test_files(logging_options)` but function takes no params
2. `read_write_ledger.py` - Remove all `logging_options` parameters

### 5. Test Updates

Current state: Some tests create `LoggingOptions` objects but don't actually use them (e.g., `test_daily_processing_tracker.py` line 21).

For tests, we have two options:

#### Option A: Use default console logging (RECOMMENDED)
Simply remove any LoggingOptions creation and let `get_logger()` use its default fallback:

```python
class TestSomething(unittest.TestCase):
    def setUp(self):
        # No logging setup needed - get_logger() will use console logging
        pass
    
    def test_something(self):
        # Functions under test will use get_logger() which defaults to console
        result = some_function()
```

#### Option B: Create test-specific loggers (if needed for debugging)
```python
from shuttle_common.logging_setup import setup_logging, LoggingOptions
import logging

class TestSomething(unittest.TestCase):
    def setUp(self):
        # Only if you need to capture/verify log output in tests
        self.test_logger = setup_logging(
            "test_something",
            LoggingOptions(filePath=None, level=logging.DEBUG)
        )
```

Note: Tests should NOT use `configure_logging()` as that sets global state.

### 6. Documentation Updates

After code changes, update:
1. `CLAUDE.md` - Remove references to `logging_options` parameter
2. `readme.md` - Update logging section
3. `docs/readme_development.md` - Update logging patterns
4. `docs/readme_modules.md` - Update module descriptions
5. Example code in `logger_injection.py` docstring

### 7. Benefits

1. **Simpler function signatures** - No need to pass `logging_options` everywhere
2. **Cleaner code** - Less boilerplate in function definitions and calls
3. **Easier testing** - Tests can configure logging globally
4. **Maintains functionality** - Hierarchy logging and function context still work
5. **Better separation** - Logging configuration is truly global, not passed around

### 8. Risks and Mitigation

1. **Risk**: Tests might interfere with each other if run in parallel
   - **Mitigation**: Tests should always reset logging config in tearDown

2. **Risk**: Some edge cases might need special logging
   - **Mitigation**: They can still use `setup_logging()` directly if needed

3. **Risk**: Breaking existing tests
   - **Mitigation**: Run all tests after each module update

### 9. Specific Functions to Update

Let me identify which functions currently have `logging_options` parameters:

#### To Analyze:
1. Use grep to find all functions with `logging_options` parameter
2. Check which functions call other functions with `logging_options`
3. Update docstrings that mention the parameter

### 10. Implementation Order

1. ✓ Update `logger_injection.py` first (DONE)
2. Update high-level modules (shuttle.py, scanning.py, etc.)
3. Update shared library modules
4. Update tests
5. Update documentation
6. Run full test suite
7. Commit changes

### 10. Verification

After implementation:
1. All tests should pass
2. Logging should still work with hierarchy
3. No `logging_options` parameters except in `configure_logging()`
4. Code should be cleaner and easier to read
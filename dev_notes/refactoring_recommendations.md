# Shuttle Refactoring Recommendations

## Executive Summary

This document provides prioritized refactoring recommendations that offer the best "bang for buck" - maximum improvement with minimal effort. All suggestions maintain existing functionality while improving code organization, maintainability, and testability.

## Top 5 High-Impact Refactoring Opportunities

### 1. **Logger Instance Management** (2-3 hours effort, HIGH impact)

**Current Issue**: 40+ functions create their own logger instance with identical pattern:
```python
logger = setup_logging('shuttle.module.function', logging_options)
```

**Proposed Solution**:
```python
# Option A: Class-based approach with logger mixin
class LoggerMixin:
    def __init__(self):
        self.logger = setup_logging(self.__class__.__module__ + '.' + self.__class__.__name__, 
                                   self.logging_options)

# Option B: Decorator approach
def with_logging(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger = setup_logging(f'{func.__module__}.{func.__name__}', 
                             kwargs.get('logging_options', {}))
        kwargs['logger'] = logger
        return func(*args, **kwargs)
    return wrapper
```

**Benefits**:
- Eliminate 40+ duplicate logger setup lines
- Consistent logger naming
- Easier to change logging behavior globally
- Reduces function parameter count

### 2. **Parameter Object Pattern** (3-4 hours effort, HIGH impact)

**Current Issue**: Multiple functions with 8-12 parameters, making them hard to test and maintain.

**Proposed Solution**:
```python
# Before:
def scan_and_process_file(paths, hazard_encryption_key_file_path, 
    hazard_archive_path, delete_source_files, on_demand_defender, 
    on_demand_clam_av, defender_handles_suspect_files, logging_options)

# After:
@dataclass
class ScanContext:
    paths: PathConfig
    hazard_config: HazardConfig
    scan_config: ScanConfig
    logging_options: LoggingOptions

def scan_and_process_file(file_path: str, context: ScanContext):
    # Much cleaner function signature
```

**Benefits**:
- Dramatically improves readability
- Easier to add new parameters without breaking interfaces
- Enables better testing with mock contexts
- Groups related parameters logically

### 3. **Split `scanning.py` Module** (4-5 hours effort, HIGH impact)

**Current Issue**: `scanning.py` has 600+ lines handling multiple responsibilities.

**Proposed Structure**:
```
shuttle/
├── file_discovery.py      # File finding and validation
├── quarantine_manager.py  # Quarantine operations
├── scan_orchestrator.py   # Scan coordination
├── scan_executor.py       # Actual scanning logic
└── cleanup_manager.py     # Source file cleanup
```

**Implementation**:
```python
# quarantine_manager.py
class QuarantineManager:
    def __init__(self, quarantine_path: str, logger):
        self.quarantine_path = quarantine_path
        self.logger = logger
    
    def quarantine_file(self, source_path: str) -> QuarantineResult:
        # Move quarantine logic here
        pass

# scan_orchestrator.py
class ScanOrchestrator:
    def __init__(self, quarantine_mgr, scan_executor, tracker):
        self.quarantine_mgr = quarantine_mgr
        self.scan_executor = scan_executor
        self.tracker = tracker
    
    def process_files(self, files: List[str]) -> ScanResults:
        # Coordinate the workflow
        pass
```

**Benefits**:
- Each module has single responsibility
- Easier to test individual components
- Better code navigation
- Enables parallel development

### 4. **Unified Error Handling** (2-3 hours effort, MEDIUM-HIGH impact)

**Current Issue**: Inconsistent error handling patterns throughout codebase.

**Proposed Solution**:
```python
# shuttle_common/exceptions.py
class ShuttleError(Exception):
    """Base exception for all Shuttle errors"""
    pass

class ConfigurationError(ShuttleError):
    """Configuration-related errors"""
    pass

class ScanError(ShuttleError):
    """Scanning-related errors"""
    pass

class ThrottlingError(ShuttleError):
    """Throttling limit exceeded"""
    pass

# Use throughout codebase
try:
    result = scanner.scan(file_path)
except ScanError as e:
    logger.error(f"Scan failed: {e}")
    tracker.mark_failed(file_path, str(e))
    raise  # Re-raise for caller to handle
```

**Benefits**:
- Consistent error handling patterns
- Better error categorization
- Easier debugging
- Enables specific error recovery strategies

### 5. **Configuration Access Refactoring** (3-4 hours effort, MEDIUM impact)

**Current Issue**: 30+ direct accesses to `self.config.*` throughout Shuttle class.

**Proposed Solution**:
```python
# Create focused configuration objects
@dataclass
class PathConfiguration:
    source: str
    destination: str
    quarantine: str
    hazard_archive: str
    
    def validate(self):
        # Validate all paths exist and are accessible
        pass

@dataclass
class ThrottleConfiguration:
    max_file_count_per_day: int
    max_volume_per_day_mb: int
    min_free_space_gb: float
    check_pending_volume: bool

# In Shuttle class
class Shuttle:
    def __init__(self, config: ShuttleConfig):
        self.paths = PathConfiguration(
            source=config.source_path,
            destination=config.destination_path,
            quarantine=config.quarantine_path,
            hazard_archive=config.hazard_archive_path
        )
        self.throttle_config = ThrottleConfiguration(...)
        # etc.
```

**Benefits**:
- Logical grouping of related configuration
- Validation in one place
- Easier to pass subsets of config to functions
- Reduces coupling to main config object

## Implementation Strategy

### Phase 1 (Week 1)
1. Implement logger management (affects entire codebase positively)
2. Create parameter objects for most complex functions

### Phase 2 (Week 2)
3. Split scanning.py into focused modules
4. Implement unified error handling

### Phase 3 (Week 3)
5. Refactor configuration access
6. Update tests to match new structure

## Expected Benefits

1. **Reduced Code Duplication**: ~30% reduction in boilerplate code
2. **Improved Testability**: Easier to mock dependencies and test in isolation
3. **Better Maintainability**: Clear module boundaries and responsibilities
4. **Enhanced Readability**: Cleaner function signatures and logical grouping
5. **Easier Debugging**: Consistent patterns and better error messages

## Risk Mitigation

- All refactoring maintains existing public interfaces
- Changes can be implemented incrementally
- Each phase is independently valuable
- Comprehensive test coverage ensures no functionality breaks

## Additional Quick Wins

1. **Extract Magic Numbers** (30 minutes)
   - Default thread count, timeouts, buffer sizes
   - Create `constants.py` module

2. **Standardize Return Types** (1 hour)
   - Use consistent Result types or exceptions
   - Document return value contracts

3. **Remove Dead Code** (30 minutes)
   - Unused imports and variables
   - Commented-out code blocks

These refactoring suggestions focus on structural improvements that will make the codebase more maintainable and easier to work with, without changing any functionality.
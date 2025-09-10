# Design Document

## Overview

The test suite stabilization addresses 308 failing tests through a systematic approach that categorizes failures by root cause and implements targeted fixes. The design prioritizes fixing foundational issues first (imports, signatures) before addressing higher-level functionality (display, performance).

## Architecture

### Failure Analysis Strategy
The 308 test failures can be categorized into these primary groups:
1. **Method Signature Mismatches** (~50 tests) - Missing parameters in method calls
2. **Import/Reference Errors** (~40 tests) - Missing imports, undefined names
3. **Pydantic Validation Errors** (~35 tests) - Model validation failures
4. **Mock Configuration Issues** (~60 tests) - Async mock problems, incorrect mock setup
5. **Contract Test Failures** (~25 tests) - API interface mismatches
6. **CSV Export Issues** (~30 tests) - Data structure and formatting problems
7. **Display/Formatting Issues** (~45 tests) - UI component test failures
8. **Performance/Integration Issues** (~23 tests) - Complex workflow test failures

### Fix Prioritization
1. **Foundation Layer**: Imports and method signatures (enables other tests to run)
2. **Data Layer**: Pydantic models and validation (enables data flow)
3. **Mock Layer**: Async mocks and test doubles (enables isolated testing)
4. **Contract Layer**: API interfaces and backward compatibility
5. **Feature Layer**: CSV export, display, and performance tests

## Components and Interfaces

### 1. Method Signature Analyzer
**Purpose**: Identify and fix method signature mismatches
**Interface**:
```python
class MethodSignatureAnalyzer:
    def analyze_failures(self, test_output: str) -> List[SignatureMismatch]
    def generate_fixes(self, mismatches: List[SignatureMismatch]) -> List[CodeFix]
    def validate_fixes(self, fixes: List[CodeFix]) -> bool
```

**Key Fixes Needed**:
- `_fetch_commits_concurrently()` missing `base_owner` and `base_repo` parameters
- `_show_comprehensive_fork_data()` missing `show_commits` parameter
- Various display service methods with changed signatures

### 2. Import Resolution System
**Purpose**: Fix missing imports and undefined names
**Interface**:
```python
class ImportResolver:
    def find_missing_imports(self, test_files: List[str]) -> Dict[str, List[str]]
    def resolve_import_paths(self, missing_imports: Dict) -> Dict[str, str]
    def update_import_statements(self, fixes: Dict[str, str]) -> None
```

**Key Fixes Needed**:
- `CLIError` - Import from `forkscout.exceptions`
- `table_context` - Define or import from appropriate module
- `CommitDataFormatter` - Update import path or create if missing
- `ForkQualificationResult` - Fix import path

### 3. Pydantic Model Validator
**Purpose**: Ensure test data matches current model schemas
**Interface**:
```python
class ModelValidator:
    def validate_test_data(self, model_class: Type, test_data: dict) -> ValidationResult
    def generate_valid_test_data(self, model_class: Type) -> dict
    def update_test_fixtures(self, model_updates: Dict[Type, dict]) -> None
```

**Key Fixes Needed**:
- `Repository` models missing required `url`, `html_url`, `clone_url` fields
- `Commit` models missing required `url` field
- `ForkQualificationMetrics` validation errors
- Model field name changes and requirements

### 4. Async Mock Configuration Manager
**Purpose**: Fix async mock setup and coroutine handling
**Interface**:
```python
class AsyncMockManager:
    def configure_async_mocks(self, mock_specs: Dict[str, Type]) -> Dict[str, AsyncMock]
    def fix_coroutine_warnings(self, test_files: List[str]) -> None
    def validate_mock_interfaces(self, mocks: Dict[str, AsyncMock]) -> bool
```

**Key Fixes Needed**:
- Replace `Mock` with `AsyncMock` for async methods
- Fix "coroutine was never awaited" warnings
- Ensure mock return values match expected types
- Configure proper async context managers

### 5. Contract Test Updater
**Purpose**: Update contract tests to match current API interfaces
**Interface**:
```python
class ContractUpdater:
    def analyze_contract_failures(self, failures: List[str]) -> List[ContractMismatch]
    def update_contract_expectations(self, mismatches: List[ContractMismatch]) -> None
    def validate_backward_compatibility(self, changes: List[ContractChange]) -> bool
```

**Key Fixes Needed**:
- Update method signature contracts
- Fix model field requirement contracts
- Update API response format expectations
- Ensure backward compatibility where required

### 6. CSV Export Test Fixer
**Purpose**: Fix CSV export functionality tests
**Interface**:
```python
class CSVTestFixer:
    def analyze_csv_failures(self, failures: List[str]) -> List[CSVIssue]
    def fix_column_mappings(self, issues: List[CSVIssue]) -> None
    def update_data_structures(self, new_format: dict) -> None
```

**Key Fixes Needed**:
- Update column name expectations (`fork_name` vs `Fork URL`)
- Fix data structure access patterns
- Handle special character escaping
- Update CSV configuration expectations

## Data Models

### Test Failure Classification
```python
@dataclass
class TestFailure:
    test_name: str
    failure_type: FailureType
    error_message: str
    file_path: str
    line_number: int
    priority: int  # 1=critical, 5=low

class FailureType(Enum):
    METHOD_SIGNATURE = "method_signature"
    IMPORT_ERROR = "import_error"
    VALIDATION_ERROR = "validation_error"
    MOCK_CONFIGURATION = "mock_configuration"
    CONTRACT_MISMATCH = "contract_mismatch"
    CSV_FORMAT = "csv_format"
    DISPLAY_FORMAT = "display_format"
    PERFORMANCE = "performance"
```

### Fix Strategy
```python
@dataclass
class FixStrategy:
    failure_type: FailureType
    fix_order: int
    batch_size: int  # Number of tests to fix in one batch
    validation_method: str
    rollback_strategy: str
```

## Error Handling

### Fix Validation
- Each fix must be validated before proceeding to the next
- Failed fixes should be rolled back automatically
- Test suite should remain runnable after each batch of fixes

### Dependency Management
- Method signature fixes must be applied before mock configuration fixes
- Import fixes must be applied before any code execution fixes
- Model validation fixes must be applied before data-dependent tests

### Progress Tracking
- Track fix success rate by category
- Monitor test pass rate improvement
- Identify and handle regression issues

## Testing Strategy

### Incremental Fix Validation
1. **Fix Batch**: Apply fixes to 10-20 tests at a time
2. **Validate**: Run affected tests to ensure fixes work
3. **Regression Check**: Run previously passing tests to ensure no regressions
4. **Progress**: Move to next batch only if current batch is stable

### Test Categories for Fixing
```bash
# Foundation fixes (run first)
uv run pytest tests/unit/test_cli.py -v  # Import and signature issues

# Data model fixes
uv run pytest tests/contract/ -v  # Model validation issues

# Mock configuration fixes
uv run pytest tests/unit/test_repository_display_service.py -v

# Feature-specific fixes
uv run pytest tests/unit/test_csv_export*.py -v  # CSV issues
uv run pytest tests/unit/test_step_specific_displays.py -v  # Display issues
```

### Success Metrics
- **Phase 1**: Reduce failures from 308 to <200 (foundation fixes)
- **Phase 2**: Reduce failures from <200 to <100 (data and mock fixes)
- **Phase 3**: Reduce failures from <100 to <50 (feature fixes)
- **Phase 4**: Reduce failures from <50 to <10 (edge cases and optimization)

## Implementation Plan

### Phase 1: Foundation Fixes (Priority 1)
1. **Import Resolution**: Fix all `NameError` and `ImportError` exceptions
2. **Method Signatures**: Update all method calls to match current signatures
3. **Basic Mock Setup**: Fix critical async mock configuration issues

### Phase 2: Data Model Fixes (Priority 2)
1. **Pydantic Validation**: Fix all model validation errors
2. **Contract Updates**: Update contract tests to match current interfaces
3. **Test Data**: Update test fixtures to match current model requirements

### Phase 3: Feature Fixes (Priority 3)
1. **CSV Export**: Fix all CSV-related test failures
2. **Display/Formatting**: Fix UI component test failures
3. **Mock Refinement**: Fix remaining mock configuration issues

### Phase 4: Integration and Performance (Priority 4)
1. **Integration Tests**: Fix complex workflow test failures
2. **Performance Tests**: Update performance expectations and benchmarks
3. **End-to-End**: Fix complete user workflow tests

### Phase 5: Optimization and Cleanup (Priority 5)
1. **Test Efficiency**: Optimize slow-running tests
2. **Flaky Test Elimination**: Fix intermittent test failures
3. **Documentation**: Update test documentation and examples

## Monitoring and Validation

### Continuous Validation
- Run test subset after each fix batch
- Monitor test execution time to prevent regressions
- Track test stability over multiple runs

### Quality Gates
- No fix batch should reduce overall test pass rate
- Each phase should achieve its target failure reduction
- Test execution time should not increase significantly

### Rollback Procedures
- Maintain git commits for each fix batch
- Automated rollback if validation fails
- Manual review process for complex fixes

This systematic approach ensures that the 308 test failures are addressed efficiently while maintaining test suite stability and preventing regressions.
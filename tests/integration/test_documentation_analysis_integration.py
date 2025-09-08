"""
Integration tests for documentation analysis functionality.
"""

import json
import tempfile
from pathlib import Path

import pytest

from forklift.analysis.documentation_analyzer import DocumentationAnalyzer
from forklift.analysis.documentation_report_generator import DocumentationReportGenerator


class TestDocumentationAnalysisIntegration:
    """Integration tests for documentation analysis."""
    
    @pytest.fixture
    def realistic_project(self):
        """Create a realistic project structure for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            
            # Create directory structure
            (project_root / "src" / "myproject").mkdir(parents=True)
            (project_root / "src" / "myproject" / "submodule").mkdir()
            (project_root / "tests" / "unit").mkdir(parents=True)
            (project_root / "tests" / "integration").mkdir()
            (project_root / "docs").mkdir()
            
            # Create comprehensive README
            readme_content = """# MyProject

A comprehensive test project for documentation analysis.

## Description

This project demonstrates various documentation patterns and completeness levels.

## Installation

### Prerequisites

- Python 3.8+
- uv package manager

### Install

```bash
# Clone the repository
git clone https://github.com/user/myproject.git
cd myproject

# Install with uv
uv sync
```

## Usage

Basic usage:

```python
import myproject
result = myproject.process_data("input")
print(result)
```

Advanced usage:

```bash
uv run myproject --config config.yaml --verbose
```

## Configuration

Create a `config.yaml` file:

```yaml
database:
  url: "sqlite:///data.db"
  timeout: 30

logging:
  level: INFO
  file: "app.log"
```

## Examples

See the `examples/` directory for complete examples.

## Troubleshooting

### Common Issues

**Issue**: Import errors
**Solution**: Ensure all dependencies are installed with `uv sync`

**Issue**: Configuration not found
**Solution**: Create config.yaml in the project root

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

## Testing

Run tests with:

```bash
uv run pytest
```

## License

MIT License - see LICENSE file for details.
"""
            (project_root / "README.md").write_text(readme_content)
            
            # Create main module with mixed documentation
            main_content = '''"""
Main module for MyProject.

This module provides the core functionality for data processing
and analysis operations.
"""

import logging
from typing import Dict, List, Optional, Union

logger = logging.getLogger(__name__)


class DataProcessor:
    """Processes various types of data with configurable options.
    
    This class provides methods for data transformation, validation,
    and analysis with support for multiple input formats.
    
    Args:
        config: Configuration dictionary for processor settings
        debug: Enable debug logging if True
        
    Example:
        >>> processor = DataProcessor({"timeout": 30})
        >>> result = processor.process(["data1", "data2"])
        >>> print(result)
        {'processed': 2, 'errors': 0}
    """
    
    def __init__(self, config: Dict = None, debug: bool = False):
        """Initialize the data processor."""
        self.config = config or {}
        self.debug = debug
        self._setup_logging()
    
    def process(self, data: List[str]) -> Dict[str, int]:
        """Process a list of data items.
        
        Args:
            data: List of data items to process
            
        Returns:
            Dictionary with processing results including counts
            
        Raises:
            ValueError: If data is empty or invalid
            
        Example:
            >>> processor = DataProcessor()
            >>> result = processor.process(["item1", "item2"])
            >>> result["processed"]
            2
        """
        if not data:
            raise ValueError("Data cannot be empty")
        
        processed = 0
        errors = 0
        
        for item in data:
            try:
                self._process_item(item)
                processed += 1
            except Exception as e:
                logger.error(f"Error processing {item}: {e}")
                errors += 1
        
        return {"processed": processed, "errors": errors}
    
    def _process_item(self, item: str) -> str:
        """Process a single data item (private method)."""
        return item.upper()
    
    def _setup_logging(self):
        """Setup logging configuration (private method)."""
        if self.debug:
            logging.basicConfig(level=logging.DEBUG)
    
    def validate_data(self, data):
        # Missing docstring - should be detected
        return isinstance(data, list) and len(data) > 0
    
    def get_stats(self):
        # Missing docstring and type hints - should be detected
        return {"version": "1.0", "status": "active"}


def process_file(filename: str, processor: DataProcessor = None) -> bool:
    """Process data from a file.
    
    Args:
        filename: Path to the file to process
        processor: Optional DataProcessor instance to use
        
    Returns:
        True if processing succeeded, False otherwise
    """
    if not processor:
        processor = DataProcessor()
    
    try:
        with open(filename, 'r') as f:
            data = f.readlines()
        
        result = processor.process(data)
        return result["errors"] == 0
    except Exception:
        return False


def undocumented_function(x, y):
    # This function has no docstring - should be detected
    return x + y


class UndocumentedClass:
    # This class has no docstring - should be detected
    
    def __init__(self, value):
        self.value = value
    
    def get_value(self):
        # Missing docstring - should be detected
        return self.value
    
    def set_value(self, value):
        """Set the value (only documented method)."""
        self.value = value
'''
            (project_root / "src" / "myproject" / "__init__.py").write_text(main_content)
            
            # Create submodule with poor documentation
            submodule_content = '''# Submodule with minimal documentation

def helper_function():
    pass

def another_helper():
    pass

class HelperClass:
    def method1(self):
        pass
    
    def method2(self):
        pass
'''
            (project_root / "src" / "myproject" / "submodule" / "helpers.py").write_text(submodule_content)
            
            # Create well-documented utility module
            utils_content = '''"""
Utility functions for MyProject.

This module provides common utility functions used throughout
the application for various helper operations.
"""

from typing import Any, Dict, List, Optional


def format_output(data: Any, format_type: str = "json") -> str:
    """Format data for output in specified format.
    
    Args:
        data: Data to format (any JSON-serializable type)
        format_type: Output format ("json", "yaml", "csv")
        
    Returns:
        Formatted string representation of the data
        
    Raises:
        ValueError: If format_type is not supported
        
    Example:
        >>> format_output({"key": "value"}, "json")
        '{"key": "value"}'
    """
    if format_type == "json":
        import json
        return json.dumps(data)
    elif format_type == "yaml":
        import yaml
        return yaml.dump(data)
    elif format_type == "csv":
        # Simple CSV formatting
        if isinstance(data, list) and data:
            return ",".join(str(item) for item in data)
        return str(data)
    else:
        raise ValueError(f"Unsupported format: {format_type}")


def validate_config(config: Dict[str, Any]) -> bool:
    """Validate configuration dictionary.
    
    Args:
        config: Configuration dictionary to validate
        
    Returns:
        True if configuration is valid, False otherwise
        
    Example:
        >>> validate_config({"database": {"url": "sqlite:///test.db"}})
        True
    """
    required_keys = ["database"]
    return all(key in config for key in required_keys)


class ConfigManager:
    """Manages application configuration with validation and defaults.
    
    This class handles loading, validating, and providing access to
    application configuration with support for environment overrides.
    
    Args:
        config_path: Path to configuration file
        
    Example:
        >>> manager = ConfigManager("config.yaml")
        >>> db_url = manager.get("database.url")
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize configuration manager.
        
        Args:
            config_path: Optional path to configuration file
        """
        self.config_path = config_path
        self.config = {}
        if config_path:
            self.load_config()
    
    def load_config(self) -> None:
        """Load configuration from file.
        
        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If config file is invalid
        """
        if not self.config_path:
            return
        
        import yaml
        with open(self.config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        if not validate_config(self.config):
            raise ValueError("Invalid configuration")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key.
        
        Args:
            key: Configuration key (supports dot notation)
            default: Default value if key not found
            
        Returns:
            Configuration value or default
            
        Example:
            >>> manager.get("database.url", "sqlite:///default.db")
            "sqlite:///data.db"
        """
        keys = key.split(".")
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
'''
            (project_root / "src" / "myproject" / "utils.py").write_text(utils_content)
            
            # Create configuration files
            env_example_content = """# Environment Configuration
GITHUB_TOKEN=your_github_token_here
OPENAI_API_KEY=your_openai_key_here
DATABASE_URL=sqlite:///data.db
DEBUG=False
LOG_LEVEL=INFO
"""
            (project_root / ".env.example").write_text(env_example_content)
            
            config_example_content = """# Example configuration file
database:
  url: "sqlite:///example.db"
  timeout: 30
  pool_size: 5

logging:
  level: INFO
  file: "app.log"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

features:
  enable_caching: true
  cache_ttl: 3600
  max_workers: 4
"""
            (project_root / "config.example.yaml").write_text(config_example_content)
            
            # Create some documentation files
            (project_root / "docs" / "USAGE.md").write_text("# Usage Guide\n\nDetailed usage instructions...")
            (project_root / "docs" / "API.md").write_text("# API Reference\n\nAPI documentation...")
            
            # Create CONTRIBUTING.md
            contributing_content = """# Contributing to MyProject

## Development Setup

1. Clone the repository
2. Install dependencies: `uv sync --dev`
3. Install pre-commit hooks: `uv run pre-commit install`

## Testing

Run tests with:
```bash
uv run pytest
```

Run with coverage:
```bash
uv run pytest --cov=src
```

## Code Style

We use:
- Black for code formatting
- Ruff for linting
- mypy for type checking

Format code before committing:
```bash
uv run black src/ tests/
uv run ruff check src/ tests/
```

## Pull Requests

1. Create a feature branch
2. Make your changes
3. Add tests for new functionality
4. Ensure all tests pass
5. Update documentation if needed
6. Submit a pull request

## Code Review

All pull requests require review before merging.
"""
            (project_root / "CONTRIBUTING.md").write_text(contributing_content)
            
            yield project_root
    
    def test_full_documentation_analysis(self, realistic_project):
        """Test complete documentation analysis on realistic project."""
        analyzer = DocumentationAnalyzer(str(realistic_project))
        assessment = analyzer.analyze_documentation()
        
        # Verify assessment structure
        assert assessment.overall_score > 0
        assert assessment.overall_score <= 100
        
        # README should score well (comprehensive)
        assert assessment.readme_assessment["exists"] is True
        assert assessment.readme_assessment["completeness_score"] > 80
        assert assessment.readme_assessment["accuracy_score"] > 80
        
        # API documentation should show mixed results
        assert len(assessment.api_documentation) >= 3  # __init__.py, helpers.py, utils.py
        
        # Find the main module (should have good documentation)
        main_module = None
        helpers_module = None
        utils_module = None
        
        for path, doc in assessment.api_documentation.items():
            if "__init__.py" in path:
                main_module = doc
            elif "helpers.py" in path:
                helpers_module = doc
            elif "utils.py" in path:
                utils_module = doc
        
        # Main module should have mixed documentation
        assert main_module is not None
        assert main_module.total_functions > 0
        assert main_module.total_classes > 0
        assert main_module.overall_coverage < 100  # Has some undocumented items
        
        # Helpers module should have poor documentation
        assert helpers_module is not None
        assert helpers_module.overall_coverage < 50  # Mostly undocumented
        
        # Utils module should have excellent documentation
        assert utils_module is not None
        assert utils_module.overall_coverage > 90  # Well documented
        
        # User guides should be partially present
        assert assessment.user_guide_assessment["score"] > 0
        assert len(assessment.user_guide_assessment["guides_found"]) >= 2
        
        # Contributor docs should score well
        assert assessment.contributor_docs_assessment["contributing_file"] is True
        assert assessment.contributor_docs_assessment["score"] > 80
        
        # Examples should validate well
        assert assessment.example_validation["config_examples"][".env.example"]["exists"] is True
        assert assessment.example_validation["score"] > 50
        
        # Should identify some gaps
        assert len(assessment.documentation_gaps) > 0
        
        # Should have recommendations
        assert len(assessment.recommendations) > 0
    
    def test_report_generation_markdown(self, realistic_project):
        """Test markdown report generation."""
        analyzer = DocumentationAnalyzer(str(realistic_project))
        assessment = analyzer.analyze_documentation()
        
        report_generator = DocumentationReportGenerator()
        markdown_report = report_generator.generate_markdown_report(assessment)
        
        # Verify report structure
        assert "# Documentation Completeness Assessment Report" in markdown_report
        assert "## Executive Summary" in markdown_report
        assert "## README Assessment" in markdown_report
        assert "## API Documentation Coverage" in markdown_report
        assert "## User Guide Assessment" in markdown_report
        assert "## Contributor Documentation Assessment" in markdown_report
        assert "## Example and Configuration Validation" in markdown_report
        assert "## Documentation Gaps and Issues" in markdown_report
        assert "## Recommendations" in markdown_report
        
        # Verify content includes scores
        assert f"Overall Score:** {assessment.overall_score}/100" in markdown_report
        
        # Verify tables are present
        assert "| Section | Present | Status |" in markdown_report
        assert "| File | Functions | Classes | Methods | Overall |" in markdown_report
        
        # Verify recommendations are included
        for recommendation in assessment.recommendations:
            assert recommendation in markdown_report
    
    def test_report_generation_json(self, realistic_project):
        """Test JSON report generation."""
        analyzer = DocumentationAnalyzer(str(realistic_project))
        assessment = analyzer.analyze_documentation()
        
        report_generator = DocumentationReportGenerator()
        json_report = report_generator.generate_json_report(assessment)
        
        # Verify JSON is valid
        report_data = json.loads(json_report)
        
        # Verify structure
        assert "generated_at" in report_data
        assert "overall_score" in report_data
        assert "readme_assessment" in report_data
        assert "api_documentation" in report_data
        assert "user_guide_assessment" in report_data
        assert "contributor_docs_assessment" in report_data
        assert "example_validation" in report_data
        assert "documentation_gaps" in report_data
        assert "recommendations" in report_data
        
        # Verify data types
        assert isinstance(report_data["overall_score"], (int, float))
        assert isinstance(report_data["api_documentation"], dict)
        assert isinstance(report_data["documentation_gaps"], list)
        assert isinstance(report_data["recommendations"], list)
        
        # Verify API documentation structure
        for file_path, file_data in report_data["api_documentation"].items():
            assert "file_path" in file_data
            assert "total_functions" in file_data
            assert "documented_functions" in file_data
            assert "overall_coverage" in file_data
            assert "docstrings" in file_data
            assert isinstance(file_data["docstrings"], list)
    
    def test_save_report_markdown(self, realistic_project):
        """Test saving markdown report to file."""
        analyzer = DocumentationAnalyzer(str(realistic_project))
        assessment = analyzer.analyze_documentation()
        
        report_generator = DocumentationReportGenerator()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "documentation_report.md"
            report_generator.save_report(assessment, str(output_path), "markdown")
            
            assert output_path.exists()
            content = output_path.read_text(encoding='utf-8')
            assert "# Documentation Completeness Assessment Report" in content
            assert f"Overall Score:** {assessment.overall_score}/100" in content
    
    def test_save_report_json(self, realistic_project):
        """Test saving JSON report to file."""
        analyzer = DocumentationAnalyzer(str(realistic_project))
        assessment = analyzer.analyze_documentation()
        
        report_generator = DocumentationReportGenerator()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "documentation_report.json"
            report_generator.save_report(assessment, str(output_path), "json")
            
            assert output_path.exists()
            content = output_path.read_text(encoding='utf-8')
            report_data = json.loads(content)
            assert report_data["overall_score"] == assessment.overall_score
    
    def test_edge_cases_empty_project(self):
        """Test analysis on empty project."""
        with tempfile.TemporaryDirectory() as temp_dir:
            analyzer = DocumentationAnalyzer(temp_dir)
            assessment = analyzer.analyze_documentation()
            
            # Should handle empty project gracefully
            assert assessment.overall_score >= 0
            assert assessment.readme_assessment["exists"] is False
            assert len(assessment.api_documentation) == 0
            assert len(assessment.documentation_gaps) > 0
            assert len(assessment.recommendations) > 0
    
    def test_edge_cases_broken_python_files(self):
        """Test analysis with broken Python files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            (project_root / "src").mkdir()
            
            # Create broken Python file
            broken_content = """
def broken_function(
    # Missing closing parenthesis and other syntax errors
    return "broken"

class BrokenClass
    # Missing colon
    def method(self):
        pass
"""
            (project_root / "src" / "broken.py").write_text(broken_content)
            
            analyzer = DocumentationAnalyzer(str(project_root))
            assessment = analyzer.analyze_documentation()
            
            # Should handle broken files gracefully
            assert assessment.overall_score >= 0
            # Broken file should not appear in API docs or should have empty analysis
            if "src/broken.py" in assessment.api_documentation:
                broken_doc = assessment.api_documentation["src/broken.py"]
                assert broken_doc.total_functions == 0
                assert broken_doc.total_classes == 0
    
    def test_performance_large_project(self):
        """Test performance on larger project structure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            
            # Create larger project structure
            for i in range(10):
                module_dir = project_root / "src" / f"module_{i}"
                module_dir.mkdir(parents=True)
                
                for j in range(5):
                    file_content = f'''"""Module {i} file {j}."""

def function_{j}_1():
    """Documented function."""
    pass

def function_{j}_2():
    # Undocumented function
    pass

class Class_{j}:
    """Documented class."""
    
    def method_1(self):
        """Documented method."""
        pass
    
    def method_2(self):
        # Undocumented method
        pass
'''
                    (module_dir / f"file_{j}.py").write_text(file_content)
            
            # Create README
            (project_root / "README.md").write_text("# Large Project\n\nTest project.")
            
            import time
            start_time = time.time()
            
            analyzer = DocumentationAnalyzer(str(project_root))
            assessment = analyzer.analyze_documentation()
            
            end_time = time.time()
            analysis_time = end_time - start_time
            
            # Should complete in reasonable time (< 10 seconds for this size)
            assert analysis_time < 10.0
            
            # Should analyze all files
            assert len(assessment.api_documentation) == 50  # 10 modules * 5 files each
            
            # Should have consistent results
            assert assessment.overall_score > 0
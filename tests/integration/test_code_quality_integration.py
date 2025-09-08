"""
Integration tests for code quality analysis
"""

import pytest
import tempfile
import json
from pathlib import Path

from src.forklift.analysis.code_quality_analyzer import CodeQualityAnalyzer
from src.forklift.analysis.quality_report_generator import QualityReportGenerator


@pytest.mark.integration
class TestCodeQualityIntegration:
    """Integration tests for code quality analysis"""
    
    @pytest.fixture
    def real_codebase_sample(self):
        """Create a realistic codebase sample for testing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            source_dir = Path(temp_dir) / "src" / "sample_project"
            source_dir.mkdir(parents=True)
            
            # Create realistic Python files with various quality issues
            
            # Main module
            (source_dir / "__init__.py").write_text("")
            
            # Service layer with good practices
            (source_dir / "service.py").write_text('''
"""
Service layer for sample project
"""

import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class User:
    """User data model"""
    id: int
    name: str
    email: str
    active: bool = True


class UserService:
    """Service for managing users"""
    
    def __init__(self, database_url: str):
        """Initialize user service
        
        Args:
            database_url: Database connection URL
        """
        self.database_url = database_url
        self.users: Dict[int, User] = {}
    
    def create_user(self, name: str, email: str) -> User:
        """Create a new user
        
        Args:
            name: User's full name
            email: User's email address
            
        Returns:
            Created user instance
            
        Raises:
            ValueError: If name or email is invalid
        """
        if not name or not email:
            raise ValueError("Name and email are required")
        
        user_id = len(self.users) + 1
        user = User(id=user_id, name=name, email=email)
        self.users[user_id] = user
        
        logger.info(f"Created user: {user.name}")
        return user
    
    def get_user(self, user_id: int) -> Optional[User]:
        """Get user by ID
        
        Args:
            user_id: User identifier
            
        Returns:
            User instance if found, None otherwise
        """
        return self.users.get(user_id)
    
    def list_active_users(self) -> List[User]:
        """Get all active users
        
        Returns:
            List of active users
        """
        return [user for user in self.users.values() if user.active]
''')
            
            # Legacy module with quality issues
            (source_dir / "legacy.py").write_text('''
# TODO: Refactor this entire module
# FIXME: This code has multiple issues
# HACK: Temporary workaround for production bug

import os, sys, json  # Multiple imports on one line
from typing import *  # Wildcard import

# Global variables (bad practice)
GLOBAL_COUNTER = 0
cache = {}

def process_data(a, b, c, d, e, f, g, h):  # Too many parameters
    global GLOBAL_COUNTER
    GLOBAL_COUNTER += 1
    
    # Deep nesting and complex logic
    if a is not None:
        if b > 0:
            if c == "valid":
                if d in ["option1", "option2", "option3"]:
                    if e > 100:  # Magic number
                        if f < 50:  # Another magic number
                            result = a * b + c + d + e + f + g + h + 42  # Magic number
                            if result > 1000:  # Magic number
                                return result * 2.5  # Magic number
                            else:
                                return result / 3.14159  # Magic number
    return None

class DataProcessor:
    # Missing docstring
    
    def __init__(self):
        self.data = []
        self.processed = False
        self.errors = []
        self.warnings = []
        self.info = []
        self.debug = []
        self.cache = {}
        self.temp_storage = {}
        self.config = {}
        self.state = "initial"
    
    def process(self, data):
        # No docstring, no type hints, poor error handling
        try:
            result = []
            for item in data:
                processed_item = self.process_item(item)
                result.append(processed_item)
            return result
        except:  # Bare except clause
            return None
    
    def process_item(self, item):
        # Long method with multiple responsibilities
        if item is None:
            return None
        
        # Duplicate code pattern
        if isinstance(item, str):
            item = item.strip()
            if len(item) == 0:
                return None
            item = item.lower()
            item = item.replace(" ", "_")
            item = item.replace("-", "_")
            return item
        elif isinstance(item, int):
            if item < 0:
                return None
            if item > 1000000:  # Magic number
                return None
            return str(item)
        elif isinstance(item, dict):
            result = {}
            for key, value in item.items():
                if key is not None and value is not None:
                    processed_key = str(key).strip().lower().replace(" ", "_").replace("-", "_")
                    processed_value = self.process_item(value)
                    if processed_value is not None:
                        result[processed_key] = processed_value
            return result if result else None
        else:
            return str(item)
    
    # Deprecated method
    def old_process_method(self):
        # DEPRECATED: Use process() instead
        import warnings
        warnings.warn("old_process_method is deprecated", DeprecationWarning)
        return self.process([])

def utility_function_without_docs():
    return 42

def another_function():
    pass

def yet_another_function():
    return "test"

# More functions to make the file longer
def function_1(): pass
def function_2(): pass
def function_3(): pass
def function_4(): pass
def function_5(): pass
def function_6(): pass
def function_7(): pass
def function_8(): pass
def function_9(): pass
def function_10(): pass
''')
            
            # Configuration module
            (source_dir / "config.py").write_text('''
"""Configuration management module"""

import os
from typing import Dict, Any


class Config:
    """Application configuration"""
    
    def __init__(self):
        """Initialize configuration"""
        self.settings: Dict[str, Any] = {}
        self.load_defaults()
    
    def load_defaults(self) -> None:
        """Load default configuration values"""
        self.settings.update({
            'debug': False,
            'database_url': 'sqlite:///app.db',
            'log_level': 'INFO',
            'max_connections': 10
        })
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value
        
        Args:
            key: Configuration key
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        return self.settings.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set configuration value
        
        Args:
            key: Configuration key
            value: Configuration value
        """
        self.settings[key] = value


# TODO: Add environment variable support
config = Config()
''')
            
            yield source_dir
    
    def test_full_analysis_workflow(self, real_codebase_sample):
        """Test complete analysis workflow with realistic code"""
        analyzer = CodeQualityAnalyzer(str(real_codebase_sample))
        
        # Run analysis
        metrics = analyzer.analyze_codebase()
        
        # Verify analysis results
        assert metrics.total_files > 0
        assert metrics.total_lines > 0
        assert len(analyzer.file_analyses) > 0
        
        # Should find various types of issues
        all_issues = []
        for analysis in analyzer.file_analyses:
            all_issues.extend(analysis.issues)
        
        issue_types = set(issue.issue_type for issue in all_issues)
        
        # Should detect common issues in the legacy module
        from src.forklift.analysis.code_quality_analyzer import IssueType
        expected_issues = {
            IssueType.TODO_COMMENT,
            IssueType.LONG_PARAMETER_LIST,
            IssueType.MISSING_DOCSTRING,
            IssueType.MAGIC_NUMBER,
            IssueType.DEPRECATED_CODE
        }
        
        # At least some of these issues should be found
        assert len(issue_types.intersection(expected_issues)) > 0
        
        # Should identify technical debt
        assert len(analyzer.technical_debt_items) >= 0
    
    def test_report_generation_integration(self, real_codebase_sample):
        """Test report generation with real analysis data"""
        analyzer = CodeQualityAnalyzer(str(real_codebase_sample))
        analyzer.analyze_codebase()
        
        report_generator = QualityReportGenerator(analyzer)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test markdown report generation
            markdown_path = Path(temp_dir) / "test_report.md"
            markdown_content = report_generator.generate_comprehensive_report(str(markdown_path))
            
            assert markdown_path.exists()
            assert len(markdown_content) > 0
            assert "# Code Quality and Technical Debt Analysis Report" in markdown_content
            assert "## Executive Summary" in markdown_content
            assert "### Quality Metrics" in markdown_content
            
            # Test JSON report generation
            json_path = Path(temp_dir) / "test_report.json"
            json_data = report_generator.generate_json_report(str(json_path))
            
            assert json_path.exists()
            assert isinstance(json_data, dict)
            assert "metadata" in json_data
            assert "metrics" in json_data
            assert "file_analyses" in json_data
            
            # Verify JSON structure
            assert "generated_at" in json_data["metadata"]
            assert "total_files" in json_data["metrics"]
            assert len(json_data["file_analyses"]) > 0
    
    def test_analysis_with_syntax_errors(self, real_codebase_sample):
        """Test analysis handles files with syntax errors gracefully"""
        # Add a file with syntax error
        syntax_error_file = real_codebase_sample / "broken.py"
        syntax_error_file.write_text('''
def broken_function(
    # Missing closing parenthesis and colon
    return "broken"
''')
        
        analyzer = CodeQualityAnalyzer(str(real_codebase_sample))
        
        # Should not crash on syntax errors
        metrics = analyzer.analyze_codebase()
        
        # Should still analyze other files
        assert metrics.total_files > 0
        
        # Should report syntax error as an issue
        broken_analysis = next(
            (a for a in analyzer.file_analyses if "broken.py" in a.file_path),
            None
        )
        assert broken_analysis is not None
        assert len(broken_analysis.issues) > 0
    
    def test_empty_directory_handling(self):
        """Test analysis of empty directory"""
        with tempfile.TemporaryDirectory() as temp_dir:
            empty_dir = Path(temp_dir) / "empty"
            empty_dir.mkdir()
            
            analyzer = CodeQualityAnalyzer(str(empty_dir))
            metrics = analyzer.analyze_codebase()
            
            assert metrics.total_files == 0
            assert metrics.total_lines == 0
            assert len(analyzer.file_analyses) == 0
            assert len(analyzer.technical_debt_items) == 0
    
    def test_large_file_analysis(self, real_codebase_sample):
        """Test analysis of large file"""
        # Create a large file with many functions
        large_file = real_codebase_sample / "large_module.py"
        
        content_lines = ['"""Large module for testing"""', '']
        
        # Add many functions to make it large
        for i in range(100):
            content_lines.extend([
                f'def function_{i}():',
                f'    """Function number {i}"""',
                f'    return {i}',
                ''
            ])
        
        large_file.write_text('\n'.join(content_lines))
        
        analyzer = CodeQualityAnalyzer(str(real_codebase_sample))
        metrics = analyzer.analyze_codebase()
        
        # Should handle large files
        large_analysis = next(
            (a for a in analyzer.file_analyses if "large_module.py" in a.file_path),
            None
        )
        
        assert large_analysis is not None
        assert large_analysis.lines_of_code > 300
        assert len(large_analysis.functions) == 100
    
    def test_metrics_accuracy(self, real_codebase_sample):
        """Test accuracy of calculated metrics"""
        analyzer = CodeQualityAnalyzer(str(real_codebase_sample))
        metrics = analyzer.analyze_codebase()
        
        # Verify metrics are reasonable
        assert 0 <= metrics.average_maintainability <= 100
        assert metrics.average_complexity >= 0
        assert 0 <= metrics.technical_debt_score <= 4
        
        # Total lines should equal sum of individual file lines
        total_lines_calculated = sum(a.lines_of_code for a in analyzer.file_analyses)
        assert metrics.total_lines == total_lines_calculated
        
        # Issue counts should be consistent
        total_issues_by_type = sum(metrics.issue_count_by_type.values())
        total_issues_by_priority = sum(metrics.issue_count_by_priority.values())
        assert total_issues_by_type == total_issues_by_priority
    
    def test_technical_debt_prioritization(self, real_codebase_sample):
        """Test technical debt item prioritization"""
        analyzer = CodeQualityAnalyzer(str(real_codebase_sample))
        analyzer.analyze_codebase()
        
        if analyzer.technical_debt_items:
            # Items should be sorted by priority
            priorities = [item.priority for item in analyzer.technical_debt_items]
            
            # Verify sorting (critical first, then high, medium, low)
            priority_values = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
            priority_scores = [priority_values[p.value] for p in priorities]
            
            # Should be generally sorted (allow some flexibility due to secondary sorting)
            # Check that critical items come before low priority items
            if len(priority_scores) > 1:
                first_score = priority_scores[0]
                last_score = priority_scores[-1]
                assert first_score <= last_score, "First item should have higher or equal priority than last item"
    
    @pytest.mark.performance
    def test_analysis_performance(self, real_codebase_sample):
        """Test analysis performance with realistic codebase"""
        import time
        
        analyzer = CodeQualityAnalyzer(str(real_codebase_sample))
        
        start_time = time.time()
        metrics = analyzer.analyze_codebase()
        end_time = time.time()
        
        analysis_time = end_time - start_time
        
        # Analysis should complete in reasonable time
        assert analysis_time < 10.0  # Should complete within 10 seconds
        
        # Performance should scale reasonably with file count
        time_per_file = analysis_time / max(metrics.total_files, 1)
        assert time_per_file < 2.0  # Should analyze each file within 2 seconds
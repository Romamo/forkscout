"""Unit tests for CSV escaping and special character handling."""

import csv
import io
from datetime import datetime

import pytest

from forkscout.models.analysis import Feature, FeatureCategory, ForkAnalysis, ForkMetrics
from forkscout.models.github import Commit, Fork, Repository, User
from forkscout.reporting.csv_exporter import CSVExportConfig, CSVExporter


class TestCSVEscaping:
    """Test comprehensive CSV escaping functionality."""

    @pytest.fixture
    def exporter(self):
        """Create a CSV exporter with default config."""
        return CSVExporter()

    @pytest.fixture
    def exporter_no_escape(self):
        """Create a CSV exporter with newline escaping disabled."""
        config = CSVExportConfig(escape_newlines=False)
        return CSVExporter(config)

    @pytest.fixture
    def sample_repository(self):
        """Create a sample repository."""
        return Repository(
            id=123,
            owner="testowner",
            name="testrepo",
            full_name="testowner/testrepo",
            url="https://api.github.com/repos/testowner/testrepo",
            html_url="https://github.com/testowner/testrepo",
            clone_url="https://github.com/testowner/testrepo.git",
            stars=100,
            forks_count=20,
            language="Python",
            description="Test repository",
            created_at=datetime(2023, 1, 1, 12, 0, 0),
            updated_at=datetime(2023, 6, 1, 12, 0, 0),
            pushed_at=datetime(2023, 6, 15, 12, 0, 0),
        )

    @pytest.fixture
    def sample_user(self):
        """Create a sample user."""
        return User(
            id=456,
            login="testuser",
            name="Test User",
            html_url="https://github.com/testuser",
        )

    @pytest.fixture
    def sample_fork(self, sample_repository, sample_user):
        """Create a sample fork."""
        fork_repo = Repository(
            id=789,
            owner="testuser",
            name="testrepo",
            full_name="testuser/testrepo",
            url="https://api.github.com/repos/testuser/testrepo",
            html_url="https://github.com/testuser/testrepo",
            clone_url="https://github.com/testuser/testrepo.git",
            stars=5,
            forks_count=1,
            language="Python",
            description="Forked repository",
            is_fork=True,
            created_at=datetime(2023, 2, 1, 12, 0, 0),
            updated_at=datetime(2023, 6, 10, 12, 0, 0),
            pushed_at=datetime(2023, 6, 20, 12, 0, 0),
        )

        return Fork(
            repository=fork_repo,
            parent=sample_repository,
            owner=sample_user,
            last_activity=datetime(2023, 6, 20, 12, 0, 0),
            commits_ahead=3,
            commits_behind=1,
            is_active=True,
        )

    def test_clean_text_for_csv_basic(self, exporter):
        """Test basic text cleaning for CSV output."""
        text = "Simple text without special characters"
        result = exporter._clean_text_for_csv(text)
        assert result == text

    def test_clean_text_for_csv_newlines(self, exporter):
        """Test cleaning text with newlines and carriage returns."""
        text = "Line 1\nLine 2\rLine 3\r\nLine 4"
        result = exporter._clean_text_for_csv(text)
        assert result == "Line 1 Line 2 Line 3 Line 4"

    def test_clean_text_for_csv_tabs_and_whitespace(self, exporter):
        """Test cleaning text with tabs and various whitespace characters."""
        text = "Text\twith\ttabs\vand\fother\twhitespace"
        result = exporter._clean_text_for_csv(text)
        assert result == "Text with tabs and other whitespace"

    def test_clean_text_for_csv_multiple_spaces(self, exporter):
        """Test cleaning text with multiple consecutive spaces."""
        text = "Text   with    multiple     spaces"
        result = exporter._clean_text_for_csv(text)
        assert result == "Text with multiple spaces"

    def test_clean_text_for_csv_control_characters(self, exporter):
        """Test cleaning text with control characters."""
        # Include some control characters (ASCII < 32)
        text = "Text\x01with\x02control\x03characters"
        result = exporter._clean_text_for_csv(text)
        assert result == "Textwithcontrolcharacters"

    def test_clean_text_for_csv_empty_and_none(self, exporter):
        """Test cleaning empty and None text."""
        assert exporter._clean_text_for_csv("") == ""
        assert exporter._clean_text_for_csv(None) == ""

    def test_clean_text_for_csv_quotes_and_commas(self, exporter):
        """Test that quotes and commas are preserved (CSV writer handles them)."""
        text = 'Text with "quotes" and, commas'
        result = exporter._clean_text_for_csv(text)
        assert result == text  # Should be unchanged, CSV writer handles escaping

    def test_escape_commit_message_comprehensive(self, exporter):
        """Test comprehensive commit message escaping."""
        message = """This is a commit message with:
        - Multiple lines
        - Tabs\tand\tspaces
        - "Quotes" and, commas
        - Control characters\x01\x02
        - Various\r\nline\nendings"""
        
        result = exporter._escape_commit_message(message)
        
        # Should be cleaned but not truncated
        assert len(result) > 0
        assert "\n" not in result
        assert "\r" not in result
        assert "\t" not in result
        assert "Multiple lines" in result
        assert "Quotes" in result
        assert "commas" in result

    def test_escape_commit_message_very_long(self, exporter):
        """Test that very long commit messages are not truncated."""
        # Create a very long message (over 1000 characters)
        long_message = "This is a very long commit message. " * 50
        
        result = exporter._escape_commit_message(long_message)
        
        # Should not be truncated
        assert len(result) > 1000
        assert "very long commit message" in result

    def test_escape_commit_message_unicode(self, exporter):
        """Test escaping commit messages with Unicode characters."""
        message = "Commit with émojis 🚀 and ünïcödé characters"
        result = exporter._escape_commit_message(message)
        
        # Unicode should be preserved
        assert "émojis" in result
        assert "🚀" in result
        assert "ünïcödé" in result

    def test_escape_row_values_with_escaping_enabled(self, exporter):
        """Test row value escaping with newline escaping enabled."""
        row = {
            "field1": "Normal text",
            "field2": "Text\nwith\nnewlines",
            "field3": "Text\rwith\rcarriage\rreturns",
            "field4": 123,  # Non-string value
            "field5": None,
        }
        
        result = exporter._escape_row_values(row)
        
        assert result["field1"] == "Normal text"
        assert result["field2"] == "Text\\nwith\\nnewlines"
        assert result["field3"] == "Text\\rwith\\rcarriage\\rreturns"
        assert result["field4"] == 123  # Unchanged
        assert result["field5"] is None  # Unchanged

    def test_escape_row_values_with_escaping_disabled(self, exporter_no_escape):
        """Test row value escaping with newline escaping disabled."""
        row = {
            "field1": "Normal text",
            "field2": "Text\nwith\nnewlines",
            "field3": "Text\rwith\rcarriage\rreturns",
            "field4": "Text\twith\ttabs",
        }
        
        result = exporter_no_escape._escape_row_values(row)
        
        assert result["field1"] == "Normal text"
        assert result["field2"] == "Text\nwith\nnewlines"  # Preserved as-is
        assert result["field3"] == "Text\rwith\rcarriage\rreturns"  # Preserved as-is
        assert result["field4"] == "Text\twith\ttabs"  # Preserved as-is

    def test_validate_csv_compatibility_valid_csv(self, exporter):
        """Test CSV compatibility validation with valid CSV."""
        csv_content = """name,owner,stars
repo1,user1,100
repo2,user2,200"""
        
        result = exporter.validate_csv_compatibility(csv_content)
        
        assert result["is_valid"] is True
        assert len(result["issues"]) == 0
        assert result["statistics"]["total_rows"] == 3
        assert result["statistics"]["total_columns"] == 3

    def test_validate_csv_compatibility_with_quotes_and_commas(self, exporter):
        """Test CSV compatibility validation with quotes and commas."""
        csv_content = '''name,description,stars
"repo, with comma","Description with ""quotes""",100
normal_repo,Simple description,200'''
        
        result = exporter.validate_csv_compatibility(csv_content)
        
        assert result["is_valid"] is True
        assert result["statistics"]["fields_with_quotes"] > 0
        assert result["statistics"]["fields_with_commas"] > 0

    def test_validate_csv_compatibility_with_newlines(self, exporter):
        """Test CSV compatibility validation with problematic newlines."""
        csv_content = """name,description,stars
repo1,"Description with
newline",100"""
        
        result = exporter.validate_csv_compatibility(csv_content)
        
        assert result["is_valid"] is False
        assert any("newlines" in issue for issue in result["issues"])
        assert result["statistics"]["fields_with_newlines"] > 0

    def test_validate_csv_compatibility_inconsistent_columns(self, exporter):
        """Test CSV compatibility validation with inconsistent column counts."""
        csv_content = """name,owner,stars
repo1,user1,100
repo2,user2"""  # Missing third column
        
        result = exporter.validate_csv_compatibility(csv_content)
        
        assert result["is_valid"] is False
        assert any("Inconsistent column counts" in issue for issue in result["issues"])

    def test_validate_csv_compatibility_empty_csv(self, exporter):
        """Test CSV compatibility validation with empty CSV."""
        csv_content = ""
        
        result = exporter.validate_csv_compatibility(csv_content)
        
        assert result["is_valid"] is False
        assert any("empty" in issue.lower() for issue in result["issues"])

    def test_validate_csv_compatibility_very_long_field(self, exporter):
        """Test CSV compatibility validation with very long field."""
        # Create a field longer than Excel's limit
        long_field = "x" * 40000
        csv_content = f"name,description\nrepo1,{long_field}"
        
        result = exporter.validate_csv_compatibility(csv_content)
        
        assert result["is_valid"] is False
        assert any("32,767 character limit" in issue for issue in result["issues"])
        assert result["statistics"]["max_field_length"] > 32767

    def test_validate_csv_compatibility_control_characters(self, exporter):
        """Test CSV compatibility validation with control characters."""
        csv_content = "name,description\nrepo1,Description\x01with\x02control"
        
        result = exporter.validate_csv_compatibility(csv_content)
        
        assert result["is_valid"] is False
        assert any("control characters" in issue for issue in result["issues"])

    def test_end_to_end_csv_escaping_with_special_characters(self, exporter, sample_fork, sample_user):
        """Test end-to-end CSV generation with various special characters."""
        # Create a commit with lots of special characters
        commit = Commit(
            sha="abc123def456789012345678901234567890abcd",
            message="""Fix critical bug in authentication system

This commit addresses several issues:
- Fixed SQL injection vulnerability in login form
- Added proper input validation with "quotes" and, commas
- Improved error handling for edge cases
- Updated documentation with examples

The fix involves:
1. Sanitizing user input\twith\ttabs
2. Using parameterized queries
3. Adding comprehensive tests

Co-authored-by: John "The Fixer" Doe <john@example.com>""",
            author=sample_user,
            date=datetime(2023, 6, 20, 10, 30, 0),
            files_changed=["auth.py", "tests/test_auth.py"],
            additions=50,
            deletions=10,
        )

        feature = Feature(
            id="feat_1",
            title="Authentication Fix",
            description="Critical security fix",
            category=FeatureCategory.BUG_FIX,
            commits=[commit],
            files_affected=["auth.py"],
            source_fork=sample_fork,
        )

        analysis = ForkAnalysis(
            fork=sample_fork,
            features=[feature],
            metrics=ForkMetrics(
                stars=5,
                forks=1,
                contributors=1,
                last_activity=datetime(2023, 6, 20, 12, 0, 0),
                commit_frequency=0.5,
            ),
            analysis_date=datetime(2023, 6, 21, 12, 0, 0),
        )

        # Export to CSV
        csv_output = exporter.export_fork_analyses([analysis])

        # Validate the CSV can be parsed correctly
        reader = csv.DictReader(io.StringIO(csv_output))
        rows = list(reader)

        assert len(rows) == 1
        row = rows[0]

        # Check that special characters are handled properly
        commit_description = row["commit_description"]
        assert "Fix critical bug" in commit_description
        assert "SQL injection" in commit_description
        assert "quotes" in commit_description
        assert "commas" in commit_description
        assert "Co-authored-by" in commit_description
        
        # Should not contain unescaped newlines
        assert "\n" not in commit_description
        assert "\r" not in commit_description
        assert "\t" not in commit_description

        # Validate CSV compatibility
        validation_result = exporter.validate_csv_compatibility(csv_output)
        assert validation_result["is_valid"] is True, f"CSV validation failed: {validation_result['issues']}"

    def test_csv_compatibility_with_major_spreadsheet_formats(self, exporter, sample_fork, sample_user):
        """Test CSV output compatibility with major spreadsheet applications."""
        # Create commits with various edge cases that might cause issues
        commits = [
            Commit(
                sha="abc123def456789012345678901234567890abcd",
                message="Simple commit message",
                author=sample_user,
                date=datetime(2023, 6, 20, 10, 30, 0),
                files_changed=["file1.py"],
                additions=10,
                deletions=5,
            ),
            Commit(
                sha="def456abc789012345678901234567890abcdef1",
                message='Commit with "quotes", commas, and other special chars!',
                author=sample_user,
                date=datetime(2023, 6, 21, 11, 0, 0),
                files_changed=["file2.py"],
                additions=20,
                deletions=3,
            ),
            Commit(
                sha="789012345678901234567890abcdef456abc1234",
                message="Commit with émojis 🚀 and ünïcödé characters",
                author=sample_user,
                date=datetime(2023, 6, 22, 12, 0, 0),
                files_changed=["file3.py"],
                additions=15,
                deletions=8,
            ),
        ]

        features = []
        for i, commit in enumerate(commits):
            feature = Feature(
                id=f"feat_{i+1}",
                title=f"Feature {i+1}",
                description=f"Description {i+1}",
                category=FeatureCategory.NEW_FEATURE,
                commits=[commit],
                files_affected=[f"file{i+1}.py"],
                source_fork=sample_fork,
            )
            features.append(feature)

        analysis = ForkAnalysis(
            fork=sample_fork,
            features=features,
            metrics=ForkMetrics(
                stars=5,
                forks=1,
                contributors=1,
                last_activity=datetime(2023, 6, 22, 12, 0, 0),
                commit_frequency=1.5,
            ),
            analysis_date=datetime(2023, 6, 23, 12, 0, 0),
        )

        # Export to CSV
        csv_output = exporter.export_fork_analyses([analysis])

        # Test that the CSV can be parsed by Python's csv module (standard compliance)
        reader = csv.DictReader(io.StringIO(csv_output))
        rows = list(reader)
        assert len(rows) == 3

        # Test each row for proper escaping
        for i, row in enumerate(rows):
            # All fields should be strings or convertible to strings
            for key, value in row.items():
                assert value is not None
                if isinstance(value, str):
                    # Should not contain unescaped newlines or control characters
                    assert "\n" not in value or key == "commit_description"  # Allow in description if properly escaped
                    assert "\r" not in value
                    assert all(ord(char) >= 32 or char in [" "] for char in value)

        # Validate overall CSV compatibility
        validation_result = exporter.validate_csv_compatibility(csv_output)
        assert validation_result["is_valid"] is True, f"CSV validation failed: {validation_result['issues']}"

        # Test statistics
        stats = validation_result["statistics"]
        assert stats["total_rows"] == 4  # 3 data rows + 1 header
        assert stats["total_columns"] > 0
        assert stats["max_field_length"] > 0

    def test_special_character_combinations(self, exporter):
        """Test various combinations of special characters."""
        test_cases = [
            ("Normal text", "Normal text"),
            ("Text\nwith\nnewlines", "Text with newlines"),
            ("Text\rwith\rcarriage\rreturns", "Text with carriage returns"),
            ("Text\twith\ttabs", "Text with tabs"),
            ("Text\n\r\twith\n\r\tmixed", "Text with mixed"),
            ("Text   with    multiple     spaces", "Text with multiple spaces"),
            ("Text\x01\x02\x03with\x04control", "Textwithcontrol"),
            ("", ""),
            ("Single word", "Single word"),
            ("Text with \"quotes\" and, commas", "Text with \"quotes\" and, commas"),
            ("Unicode: émojis 🚀 ünïcödé", "Unicode: émojis 🚀 ünïcödé"),
        ]

        for input_text, expected_pattern in test_cases:
            result = exporter._clean_text_for_csv(input_text)
            
            # Check that the result contains the expected pattern
            if expected_pattern:
                # For non-empty expected patterns, check key words are present
                key_words = [word for word in expected_pattern.split() if len(word) > 2]
                for word in key_words:
                    assert word in result, f"Expected '{word}' in result '{result}' for input '{input_text}'"
            else:
                assert result == "", f"Expected empty result for input '{input_text}', got '{result}'"
            
            # Check that problematic characters are removed
            assert "\n" not in result
            assert "\r" not in result
            assert "\t" not in result
            assert not any(ord(char) < 32 and char != " " for char in result)
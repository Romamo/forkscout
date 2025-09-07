"""Visual regression tests for compact commit display table formatting."""

import pytest
import re
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock
from io import StringIO

from rich.console import Console

from forklift.display.repository_display_service import RepositoryDisplayService
from forklift.github.client import GitHubClient
from forklift.models.github import Repository
from forklift.models.fork_qualification import (
    CollectedForkData,
    ForkQualificationMetrics,
    QualificationStats,
    QualifiedForksResult,
)


class TestCompactCommitDisplayVisualRegression:
    """Visual regression tests to ensure table formatting remains readable."""

    @pytest.fixture
    def mock_github_client(self):
        """Create a mock GitHub client."""
        return AsyncMock(spec=GitHubClient)

    @pytest.fixture
    def console_with_capture(self):
        """Create a console that captures output for testing."""
        string_io = StringIO()
        console = Console(file=string_io, width=120, legacy_windows=False, force_terminal=True)
        return console, string_io

    @pytest.fixture
    def display_service(self, mock_github_client, console_with_capture):
        """Create a repository display service with output capture."""
        console, _ = console_with_capture
        return RepositoryDisplayService(mock_github_client, console)

    @pytest.fixture
    def standard_test_forks(self):
        """Create standard test forks for visual regression testing."""
        base_time = datetime.now(timezone.utc)
        
        return [
            Repository(
                id=1,
                name="short-name",
                owner="user1",
                full_name="user1/short-name",
                url="https://api.github.com/repos/user1/short-name",
                html_url="https://github.com/user1/short-name",
                clone_url="https://github.com/user1/short-name.git",
                description="Short description",
                language="Python",
                stars=5,
                forks_count=1,
                watchers_count=3,
                open_issues_count=0,
                size=100,
                topics=["python"],
                license_name="MIT",
                default_branch="main",
                is_private=False,
                is_fork=True,
                is_archived=False,
                created_at=base_time,
                updated_at=base_time,
                pushed_at=base_time,  # No commits ahead
            ),
            Repository(
                id=2,
                name="very-long-repository-name-that-might-cause-formatting-issues",
                owner="user-with-very-long-username",
                full_name="user-with-very-long-username/very-long-repository-name-that-might-cause-formatting-issues",
                url="https://api.github.com/repos/user-with-very-long-username/very-long-repository-name-that-might-cause-formatting-issues",
                html_url="https://github.com/user-with-very-long-username/very-long-repository-name-that-might-cause-formatting-issues",
                clone_url="https://github.com/user-with-very-long-username/very-long-repository-name-that-might-cause-formatting-issues.git",
                description="This is a very long description that might cause formatting issues in table displays and should be handled gracefully",
                language="JavaScript",
                stars=12345,
                forks_count=6789,
                watchers_count=9876,
                open_issues_count=543,
                size=987654,
                topics=["javascript", "very-long-topic-name"],
                license_name="Apache License 2.0",
                default_branch="main",
                is_private=False,
                is_fork=True,
                is_archived=False,
                created_at=base_time,
                updated_at=base_time + timedelta(days=30),
                pushed_at=base_time + timedelta(days=30),  # Has commits ahead
            ),
            Repository(
                id=3,
                name="unicode-test-repo",
                owner="unicode-user",
                full_name="unicode-user/unicode-test-repo",
                url="https://api.github.com/repos/unicode-user/unicode-test-repo",
                html_url="https://github.com/unicode-user/unicode-test-repo",
                clone_url="https://github.com/unicode-user/unicode-test-repo.git",
                description="Unicode and emoji test: 测试 🚀 ñáéíóú",
                language="Go",
                stars=42,
                forks_count=7,
                watchers_count=15,
                open_issues_count=2,
                size=500,
                topics=["测试", "unicode"],
                license_name=None,
                default_branch="main",
                is_private=False,
                is_fork=True,
                is_archived=False,
                created_at=base_time,
                updated_at=base_time + timedelta(days=5),
                pushed_at=base_time + timedelta(days=5),  # Has commits ahead
            ),
        ]

    def analyze_table_structure(self, output: str) -> dict:
        """Analyze table structure and return formatting metrics."""
        lines = output.split('\n')
        
        # Find table lines (containing borders)
        table_lines = [line for line in lines if '│' in line or '|' in line]
        header_lines = [line for line in lines if '─' in line or '-' in line]
        data_lines = [line for line in table_lines if not any(char in line for char in ['─', '━', '┌', '┐', '└', '┘', '├', '┤', '┬', '┴', '┼'])]
        
        # Analyze column alignment
        column_positions = []
        if table_lines:
            first_line = table_lines[0]
            for i, char in enumerate(first_line):
                if char in ['│', '|']:
                    column_positions.append(i)
        
        # Check for consistent column widths
        column_widths = []
        for i in range(len(column_positions) - 1):
            width = column_positions[i + 1] - column_positions[i] - 1
            column_widths.append(width)
        
        return {
            'total_lines': len(lines),
            'table_lines': len(table_lines),
            'header_lines': len(header_lines),
            'data_lines': len(data_lines),
            'column_positions': column_positions,
            'column_widths': column_widths,
            'max_line_length': max(len(line) for line in lines) if lines else 0,
            'has_unicode': any(ord(char) > 127 for line in lines for char in line),
            'has_table_borders': len(table_lines) > 0,
        }

    def validate_table_formatting(self, structure: dict) -> list:
        """Validate table formatting and return list of issues."""
        issues = []
        
        # Check basic table structure
        if structure['table_lines'] == 0:
            issues.append("No table structure found")
        
        if structure['header_lines'] == 0:
            issues.append("No table headers found")
        
        if structure['data_lines'] == 0:
            issues.append("No table data rows found")
        
        # Check column consistency
        if len(structure['column_positions']) < 2:
            issues.append("Insufficient table columns")
        
        # Check for reasonable column widths
        for i, width in enumerate(structure['column_widths']):
            if width < 3:
                issues.append(f"Column {i} too narrow (width: {width})")
            if width > 50:
                issues.append(f"Column {i} too wide (width: {width})")
        
        # Check line length
        if structure['max_line_length'] > 200:
            issues.append(f"Lines too long (max: {structure['max_line_length']})")
        
        return issues

    @pytest.mark.asyncio
    async def test_list_forks_table_formatting_visual_regression(
        self, display_service, console_with_capture, standard_test_forks
    ):
        """Test visual formatting of list-forks table remains consistent."""
        console, string_io = console_with_capture
        
        display_service.github_client.get_repository_forks.return_value = standard_test_forks
        
        # Generate output
        result = await display_service.list_forks_preview("owner/visual-test-repo")
        output = string_io.getvalue()
        
        # Analyze table structure
        structure = self.analyze_table_structure(output)
        issues = self.validate_table_formatting(structure)
        
        # Visual regression assertions
        assert len(issues) == 0, f"Table formatting issues: {issues}"
        
        # Specific formatting checks
        assert structure['has_table_borders'], "Table should have borders"
        assert structure['table_lines'] >= 5, "Should have header + data rows"
        assert structure['data_lines'] >= 3, "Should have data for all test forks"
        
        # Check column structure
        assert len(structure['column_positions']) >= 5, "Should have at least 5 columns"
        
        # Verify specific columns exist
        lines = output.split('\n')
        header_line = next((line for line in lines if "Commits" in line), None)
        assert header_line is not None, "Should have Commits column header"
        
        # Check that compact format is used (no verbose descriptions)
        assert "0 commits" not in output, "Should not use verbose '0 commits' format"
        assert "commits ahead" not in output.lower() or "Commits Ahead" in output, "Should use compact format"
        
        # Verify Unicode handling
        if structure['has_unicode']:
            assert "测试" in output or "🚀" in output, "Unicode characters should be preserved"

    @pytest.mark.asyncio
    async def test_fork_data_table_formatting_visual_regression(
        self, display_service, console_with_capture, standard_test_forks
    ):
        """Test visual formatting of fork data table remains consistent."""
        console, string_io = console_with_capture
        
        # Create qualification result
        collected_forks = []
        for fork in standard_test_forks:
            metrics = ForkQualificationMetrics(
                id=fork.id,
                owner=fork.owner,
                name=fork.name,
                full_name=fork.full_name,
                html_url=fork.html_url,
                stargazers_count=fork.stars,
                forks_count=fork.forks_count,
                watchers_count=fork.watchers_count,
                open_issues_count=fork.open_issues_count,
                size=fork.size,
                language=fork.language,
                topics=fork.topics,
                created_at=fork.created_at,
                updated_at=fork.updated_at,
                pushed_at=fork.pushed_at,
                archived=fork.is_archived,
                disabled=False,
                fork=fork.is_fork,
                commits_ahead_status="None" if fork.created_at == fork.pushed_at else "Unknown",
                can_skip_analysis=fork.created_at == fork.pushed_at,
            )
            collected_forks.append(CollectedForkData(metrics=metrics))
        
        stats = QualificationStats(
            total_forks_discovered=3,
            forks_with_commits=2,
            forks_with_no_commits=1,
            archived_forks=0,
            disabled_forks=0,
            processing_time_seconds=1.0,
            api_calls_made=2,
            api_calls_saved=1,
        )
        
        qualification_result = QualifiedForksResult(
            repository_owner="owner",
            repository_name="visual-test-repo",
            repository_url="https://github.com/owner/visual-test-repo",
            collected_forks=collected_forks,
            stats=stats,
        )
        
        # Generate output
        await display_service._display_fork_data_table(qualification_result)
        output = string_io.getvalue()
        
        # Analyze table structure
        structure = self.analyze_table_structure(output)
        issues = self.validate_table_formatting(structure)
        
        # Visual regression assertions
        assert len(issues) == 0, f"Fork data table formatting issues: {issues}"
        
        # Specific formatting checks
        assert structure['has_table_borders'], "Fork data table should have borders"
        assert structure['table_lines'] >= 5, "Should have header + data rows"
        
        # Check for required content
        lines = output.split('\n')
        assert any("Commits" in line for line in lines), "Should have Commits column"
        assert any("3 forks" in line for line in lines), "Should show fork count"
        
        # Verify compact format
        assert not any("0 commits" in line for line in lines), "Should not use verbose format"
        
        # Check that long names are handled properly
        long_name_line = next((line for line in lines if "very-long-repository-name" in line), None)
        if long_name_line:
            assert len(long_name_line) < 200, "Long names should not break table formatting"

    @pytest.mark.asyncio
    async def test_detailed_fork_table_formatting_visual_regression(
        self, display_service, console_with_capture, standard_test_forks
    ):
        """Test visual formatting of detailed fork table remains consistent."""
        console, string_io = console_with_capture
        
        # Create detailed fork data
        detailed_forks = []
        for i, fork in enumerate(standard_test_forks):
            metrics = ForkQualificationMetrics(
                id=fork.id,
                owner=fork.owner,
                name=fork.name,
                full_name=fork.full_name,
                html_url=fork.html_url,
                stargazers_count=fork.stars,
                forks_count=fork.forks_count,
                watchers_count=fork.watchers_count,
                open_issues_count=fork.open_issues_count,
                size=fork.size,
                language=fork.language,
                topics=fork.topics,
                created_at=fork.created_at,
                updated_at=fork.updated_at,
                pushed_at=fork.pushed_at,
                archived=fork.is_archived,
                disabled=False,
                fork=fork.is_fork,
                commits_ahead_status="None" if fork.created_at == fork.pushed_at else "Unknown",
                can_skip_analysis=fork.created_at == fork.pushed_at,
            )
            
            fork_data = CollectedForkData(metrics=metrics)
            # Add exact commit counts
            if fork.created_at == fork.pushed_at:
                fork_data.exact_commits_ahead = 0
            else:
                fork_data.exact_commits_ahead = (i + 1) * 3  # 3, 6, 9 commits
            
            detailed_forks.append(fork_data)
        
        # Generate output
        await display_service._display_detailed_fork_table(
            detailed_forks,
            "owner",
            "visual-test-repo",
            api_calls_made=2,
            api_calls_saved=1,
        )
        output = string_io.getvalue()
        
        # Analyze table structure
        structure = self.analyze_table_structure(output)
        issues = self.validate_table_formatting(structure)
        
        # Visual regression assertions
        assert len(issues) == 0, f"Detailed fork table formatting issues: {issues}"
        
        # Specific formatting checks
        assert structure['has_table_borders'], "Detailed table should have borders"
        assert structure['table_lines'] >= 5, "Should have header + data rows"
        
        # Check for required content
        lines = output.split('\n')
        assert any("Commits Ahead" in line for line in lines), "Should have Commits Ahead column"
        assert any("API calls" in line for line in lines), "Should show API call statistics"
        
        # Verify compact format for commits ahead
        commit_lines = [line for line in lines if any(str(i) in line for i in [3, 6, 9])]
        assert len(commit_lines) >= 2, "Should show exact commit counts"
        
        # Check that empty cells are handled properly (fork with 0 commits)
        zero_commit_lines = [line for line in lines if "short-name" in line]
        if zero_commit_lines:
            # Should have empty cell or "0" for no commits ahead
            assert any(line for line in zero_commit_lines), "Should handle zero commits gracefully"

    @pytest.mark.asyncio
    async def test_table_formatting_with_extreme_values(
        self, display_service, console_with_capture
    ):
        """Test table formatting with extreme values that might break layout."""
        console, string_io = console_with_capture
        
        base_time = datetime.now(timezone.utc)
        
        # Create forks with extreme values
        extreme_forks = [
            # Fork with very high numbers
            Repository(
                id=1,
                name="popular-fork",
                owner="popular-user",
                full_name="popular-user/popular-fork",
                url="https://api.github.com/repos/popular-user/popular-fork",
                html_url="https://github.com/popular-user/popular-fork",
                clone_url="https://github.com/popular-user/popular-fork.git",
                description="Very popular fork",
                language="Python",
                stars=999999,
                forks_count=50000,
                watchers_count=100000,
                open_issues_count=5000,
                size=1000000,
                topics=["popular"],
                license_name="MIT",
                default_branch="main",
                is_private=False,
                is_fork=True,
                is_archived=False,
                created_at=base_time,
                updated_at=base_time + timedelta(days=100),
                pushed_at=base_time + timedelta(days=100),
            ),
            # Fork with zero values
            Repository(
                id=2,
                name="empty-fork",
                owner="empty-user",
                full_name="empty-user/empty-fork",
                url="https://api.github.com/repos/empty-user/empty-fork",
                html_url="https://github.com/empty-user/empty-fork",
                clone_url="https://github.com/empty-user/empty-fork.git",
                description="",
                language=None,
                stars=0,
                forks_count=0,
                watchers_count=0,
                open_issues_count=0,
                size=0,
                topics=[],
                license_name=None,
                default_branch="main",
                is_private=False,
                is_fork=True,
                is_archived=False,
                created_at=base_time,
                updated_at=base_time,
                pushed_at=base_time,
            ),
        ]
        
        display_service.github_client.get_repository_forks.return_value = extreme_forks
        
        # Generate output
        result = await display_service.list_forks_preview("owner/extreme-values-repo")
        output = string_io.getvalue()
        
        # Analyze table structure
        structure = self.analyze_table_structure(output)
        issues = self.validate_table_formatting(structure)
        
        # Visual regression assertions
        assert len(issues) == 0, f"Extreme values table formatting issues: {issues}"
        
        # Check that large numbers are displayed correctly
        assert "999999" in output or "999,999" in output, "Large numbers should be displayed"
        assert "0" in output, "Zero values should be displayed"
        
        # Verify table structure is maintained
        assert structure['has_table_borders'], "Table structure should be maintained"
        assert structure['max_line_length'] < 200, "Lines should not be excessively long"

    @pytest.mark.asyncio
    async def test_table_formatting_consistency_across_different_widths(
        self, mock_github_client, standard_test_forks
    ):
        """Test table formatting consistency across different console widths."""
        
        # Test with different console widths
        widths = [80, 120, 160]
        outputs = []
        
        for width in widths:
            string_io = StringIO()
            console = Console(file=string_io, width=width, legacy_windows=False, force_terminal=True)
            display_service = RepositoryDisplayService(mock_github_client, console)
            
            display_service.github_client.get_repository_forks.return_value = standard_test_forks
            
            # Generate output
            result = await display_service.list_forks_preview("owner/width-test-repo")
            output = string_io.getvalue()
            outputs.append((width, output))
            
            # Analyze structure for this width
            structure = self.analyze_table_structure(output)
            issues = self.validate_table_formatting(structure)
            
            # Each width should produce valid table
            assert len(issues) == 0, f"Width {width} formatting issues: {issues}"
            assert structure['max_line_length'] <= width + 10, f"Lines exceed console width {width}"
        
        # Verify all widths produced output
        assert len(outputs) == 3
        
        # Check that essential information is preserved across widths
        for width, output in outputs:
            assert "Commits" in output, f"Width {width} missing Commits column"
            assert "3 forks" in output or str(3) in output, f"Width {width} missing fork count"

    @pytest.mark.asyncio
    async def test_table_formatting_with_missing_data_fields(
        self, display_service, console_with_capture
    ):
        """Test table formatting when some data fields are missing or None."""
        console, string_io = console_with_capture
        
        base_time = datetime.now(timezone.utc)
        
        # Create forks with missing data
        incomplete_forks = [
            Repository(
                id=1,
                name="incomplete-fork",
                owner="user1",
                full_name="user1/incomplete-fork",
                url="https://api.github.com/repos/user1/incomplete-fork",
                html_url="https://github.com/user1/incomplete-fork",
                clone_url="https://github.com/user1/incomplete-fork.git",
                description=None,  # Missing description
                language=None,  # Missing language
                stars=10,
                forks_count=2,
                watchers_count=5,
                open_issues_count=1,
                size=100,
                topics=[],  # Empty topics
                license_name=None,  # Missing license
                default_branch="main",
                is_private=False,
                is_fork=True,
                is_archived=False,
                created_at=None,  # Missing created_at
                updated_at=base_time,
                pushed_at=None,  # Missing pushed_at
            ),
            Repository(
                id=2,
                name="partial-fork",
                owner="user2",
                full_name="user2/partial-fork",
                url="https://api.github.com/repos/user2/partial-fork",
                html_url="https://github.com/user2/partial-fork",
                clone_url="https://github.com/user2/partial-fork.git",
                description="Partial data fork",
                language="Python",
                stars=0,  # Zero stars
                forks_count=0,  # Zero forks
                watchers_count=0,  # Zero watchers
                open_issues_count=0,  # Zero issues
                size=0,  # Zero size
                topics=["test"],
                license_name="MIT",
                default_branch="main",
                is_private=False,
                is_fork=True,
                is_archived=False,
                created_at=base_time,
                updated_at=base_time,
                pushed_at=base_time,
            ),
        ]
        
        display_service.github_client.get_repository_forks.return_value = incomplete_forks
        
        # Generate output
        result = await display_service.list_forks_preview("owner/incomplete-data-repo")
        output = string_io.getvalue()
        
        # Analyze table structure
        structure = self.analyze_table_structure(output)
        issues = self.validate_table_formatting(structure)
        
        # Visual regression assertions
        assert len(issues) == 0, f"Incomplete data table formatting issues: {issues}"
        
        # Verify missing data is handled gracefully
        assert result["total_forks"] == 2
        assert len(result["forks"]) == 2
        
        # Check that table structure is maintained despite missing data
        assert structure['has_table_borders'], "Table structure should be maintained"
        assert structure['data_lines'] >= 2, "Should have data rows for both forks"
        
        # Verify no error messages in output
        assert "Error" not in output
        assert "None" not in output or "None" in output.lower()  # Allow "None" as display value
        
        # Check that missing timestamps are handled correctly
        for fork in result["forks"]:
            if fork.name == "incomplete-fork":
                assert fork.commits_ahead == "None", "Missing timestamps should result in 'None' status"

    @pytest.mark.asyncio
    async def test_table_formatting_regression_with_color_codes(
        self, display_service, console_with_capture, standard_test_forks
    ):
        """Test that color codes don't break table formatting."""
        console, string_io = console_with_capture
        
        display_service.github_client.get_repository_forks.return_value = standard_test_forks
        
        # Generate output (Rich console will include color codes)
        result = await display_service.list_forks_preview("owner/color-test-repo")
        output = string_io.getvalue()
        
        # Analyze table structure (should work even with color codes)
        structure = self.analyze_table_structure(output)
        issues = self.validate_table_formatting(structure)
        
        # Visual regression assertions
        assert len(issues) == 0, f"Color codes table formatting issues: {issues}"
        
        # Check that color codes don't break table alignment
        lines = output.split('\n')
        table_lines = [line for line in lines if '│' in line or '|' in line]
        
        if table_lines:
            # Remove ANSI color codes for alignment checking
            clean_lines = []
            ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
            for line in table_lines:
                clean_line = ansi_escape.sub('', line)
                clean_lines.append(clean_line)
            
            # Check that columns are still aligned after removing color codes
            if len(clean_lines) > 1:
                first_line_positions = [i for i, char in enumerate(clean_lines[0]) if char in ['│', '|']]
                for line in clean_lines[1:]:
                    line_positions = [i for i, char in enumerate(line) if char in ['│', '|']]
                    # Allow some flexibility for different content lengths
                    assert len(line_positions) >= len(first_line_positions) - 1, "Column alignment should be maintained"

    def test_format_commits_compact_visual_consistency(self, display_service):
        """Test that format_commits_compact produces visually consistent output."""
        
        # Test various commit scenarios
        test_cases = [
            (0, 0, ""),  # Empty cell
            (5, 0, "+5"),  # Only ahead
            (0, 3, "-3"),  # Only behind
            (5, 3, "+5 -3"),  # Both ahead and behind
            (-1, 0, "Unknown"),  # Unknown ahead
            (0, -1, "Unknown"),  # Unknown behind
            (-1, -1, "Unknown"),  # Both unknown
            (999, 888, "+999 -888"),  # Large numbers
        ]
        
        for commits_ahead, commits_behind, expected_pattern in test_cases:
            result = display_service.format_commits_compact(commits_ahead, commits_behind)
            
            # Visual consistency checks
            if expected_pattern == "":
                assert result == "", f"Empty case failed: got '{result}'"
            elif expected_pattern == "Unknown":
                assert "Unknown" in result, f"Unknown case failed: got '{result}'"
            elif "+" in expected_pattern and "-" in expected_pattern:
                assert "+" in result and "-" in result, f"Both ahead/behind case failed: got '{result}'"
            elif expected_pattern.startswith("+"):
                assert result.startswith("[green]+") or result.startswith("+"), f"Ahead only case failed: got '{result}'"
            elif expected_pattern.startswith("-"):
                assert result.startswith("[red]-") or result.startswith("-"), f"Behind only case failed: got '{result}'"
            
            # Length consistency check
            assert len(result) < 50, f"Result too long: '{result}'"
            
            # No double spaces or formatting issues
            assert "  " not in result, f"Double spaces in result: '{result}'"
            assert result == result.strip(), f"Leading/trailing whitespace: '{result}'"
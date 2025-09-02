"""Unit tests for CSV exporter functionality."""

import csv
import io
from datetime import datetime

import pytest

from forklift.models.analysis import (
    CategoryType,
    CommitCategory,
    CommitExplanation,
    CommitWithExplanation,
    Feature,
    FeatureCategory,
    ForkAnalysis,
    ForkMetrics,
    ForkPreviewItem,
    ForksPreview,
    ImpactAssessment,
    ImpactLevel,
    MainRepoValue,
    RankedFeature,
)
from forklift.models.github import Commit, Fork, Repository, User
from forklift.reporting.csv_exporter import CSVExportConfig, CSVExporter


class TestCSVExportConfig:
    """Test CSV export configuration."""

    def test_default_config(self):
        """Test default configuration values."""
        config = CSVExportConfig()

        assert config.include_commits is False
        assert config.detail_mode is False
        assert config.include_explanations is False
        assert config.max_commits_per_fork == 10
        assert config.escape_newlines is True
        assert config.include_urls is True
        assert config.date_format == "%Y-%m-%d %H:%M:%S"

    def test_custom_config(self):
        """Test custom configuration values."""
        config = CSVExportConfig(
            include_commits=True,
            detail_mode=True,
            include_explanations=True,
            max_commits_per_fork=5,
            escape_newlines=False,
            include_urls=False,
            date_format="%Y-%m-%d"
        )

        assert config.include_commits is True
        assert config.detail_mode is True
        assert config.include_explanations is True
        assert config.max_commits_per_fork == 5
        assert config.escape_newlines is False
        assert config.include_urls is False
        assert config.date_format == "%Y-%m-%d"


class TestCSVExporter:
    """Test CSV exporter functionality."""

    @pytest.fixture
    def exporter(self):
        """Create a CSV exporter with default config."""
        return CSVExporter()

    @pytest.fixture
    def detailed_exporter(self):
        """Create a CSV exporter with detailed config."""
        config = CSVExportConfig(
            include_commits=True,
            detail_mode=True,
            include_explanations=True,
            include_urls=True
        )
        return CSVExporter(config)

    @pytest.fixture
    def minimal_exporter(self):
        """Create a CSV exporter with minimal config."""
        config = CSVExportConfig(
            include_commits=False,
            detail_mode=False,
            include_explanations=False,
            include_urls=False
        )
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
            pushed_at=datetime(2023, 6, 15, 12, 0, 0)
        )

    @pytest.fixture
    def sample_user(self):
        """Create a sample user."""
        return User(
            id=456,
            login="testuser",
            name="Test User",
            html_url="https://github.com/testuser"
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
            pushed_at=datetime(2023, 6, 20, 12, 0, 0)
        )

        return Fork(
            repository=fork_repo,
            parent=sample_repository,
            owner=sample_user,
            last_activity=datetime(2023, 6, 20, 12, 0, 0),
            commits_ahead=3,
            commits_behind=1,
            is_active=True
        )

    @pytest.fixture
    def sample_commit(self, sample_user):
        """Create a sample commit."""
        return Commit(
            sha="a1b2c3d4e5f6789012345678901234567890abcd",
            message="Add new feature\n\nThis commit adds a new feature to the repository.",
            author=sample_user,
            date=datetime(2023, 6, 20, 10, 30, 0),
            files_changed=["src/main.py", "tests/test_main.py"],
            additions=50,
            deletions=10
        )

    @pytest.fixture
    def sample_forks_preview(self):
        """Create a sample forks preview."""
        forks = [
            ForkPreviewItem(
                name="testrepo",
                owner="user1",
                stars=10,
                last_push_date=datetime(2023, 6, 15, 12, 0, 0),
                fork_url="https://github.com/user1/testrepo",
                activity_status="Active",
                commits_ahead="Unknown"
            ),
            ForkPreviewItem(
                name="testrepo",
                owner="user2",
                stars=5,
                last_push_date=datetime(2023, 5, 1, 12, 0, 0),
                fork_url="https://github.com/user2/testrepo",
                activity_status="Stale",
                commits_ahead="None"
            )
        ]

        return ForksPreview(total_forks=2, forks=forks)


class TestForksPreviewExport(TestCSVExporter):
    """Test forks preview CSV export."""

    def test_export_forks_preview_basic(self, exporter, sample_forks_preview):
        """Test basic forks preview export."""
        csv_output = exporter.export_forks_preview(sample_forks_preview)

        # Parse CSV to verify structure
        reader = csv.DictReader(io.StringIO(csv_output))
        rows = list(reader)

        assert len(rows) == 2

        # Check headers
        expected_headers = [
            "fork_name", "owner", "stars", "commits_ahead",
            "activity_status", "fork_url"
        ]
        assert reader.fieldnames == expected_headers

        # Check first row
        row1 = rows[0]
        assert row1["fork_name"] == "testrepo"
        assert row1["owner"] == "user1"
        assert row1["stars"] == "10"
        assert row1["commits_ahead"] == "Unknown"
        assert row1["activity_status"] == "Active"
        assert row1["fork_url"] == "https://github.com/user1/testrepo"

    def test_export_forks_preview_no_urls(self, minimal_exporter, sample_forks_preview):
        """Test forks preview export without URLs."""
        csv_output = minimal_exporter.export_forks_preview(sample_forks_preview)

        reader = csv.DictReader(io.StringIO(csv_output))

        # Check headers don't include URL
        expected_headers = [
            "fork_name", "owner", "stars", "commits_ahead", "activity_status"
        ]
        assert reader.fieldnames == expected_headers

    def test_export_forks_preview_detail_mode(self, detailed_exporter, sample_forks_preview):
        """Test forks preview export in detail mode."""
        csv_output = detailed_exporter.export_forks_preview(sample_forks_preview)

        reader = csv.DictReader(io.StringIO(csv_output))

        # Check headers include detail fields
        assert "last_push_date" in reader.fieldnames
        assert "created_date" in reader.fieldnames
        assert "updated_date" in reader.fieldnames

    def test_export_forks_preview_with_commits_header(self, detailed_exporter, sample_forks_preview):
        """Test forks preview export includes recent_commits header when include_commits is True."""
        csv_output = detailed_exporter.export_forks_preview(sample_forks_preview)

        reader = csv.DictReader(io.StringIO(csv_output))

        # Check that recent_commits header is included when include_commits=True
        assert "recent_commits" in reader.fieldnames

    def test_export_forks_preview_without_commits_header(self, exporter, sample_forks_preview):
        """Test forks preview export excludes recent_commits header when include_commits is False."""
        csv_output = exporter.export_forks_preview(sample_forks_preview)

        reader = csv.DictReader(io.StringIO(csv_output))

        # Check that recent_commits header is NOT included when include_commits=False
        assert "recent_commits" not in reader.fieldnames

    def test_export_empty_forks_preview(self, exporter):
        """Test export of empty forks preview."""
        empty_preview = ForksPreview(total_forks=0, forks=[])
        csv_output = exporter.export_forks_preview(empty_preview)

        reader = csv.DictReader(io.StringIO(csv_output))
        rows = list(reader)

        assert len(rows) == 0
        assert reader.fieldnames is not None  # Headers should still be present


class TestForkAnalysisExport(TestCSVExporter):
    """Test fork analysis CSV export."""

    @pytest.fixture
    def sample_fork_analysis(self, sample_fork, sample_commit):
        """Create a sample fork analysis."""
        feature = Feature(
            id="feat_1",
            title="New Authentication",
            description="Adds JWT authentication",
            category=FeatureCategory.NEW_FEATURE,
            commits=[sample_commit],
            files_affected=["src/auth.py", "tests/test_auth.py"],
            source_fork=sample_fork
        )

        metrics = ForkMetrics(
            stars=5,
            forks=1,
            contributors=2,
            last_activity=datetime(2023, 6, 20, 12, 0, 0),
            commit_frequency=0.5
        )

        return ForkAnalysis(
            fork=sample_fork,
            features=[feature],
            metrics=metrics,
            analysis_date=datetime(2023, 6, 21, 12, 0, 0)
        )

    def test_export_fork_analysis_basic(self, exporter, sample_fork_analysis):
        """Test basic fork analysis export."""
        csv_output = exporter.export_fork_analyses([sample_fork_analysis])

        reader = csv.DictReader(io.StringIO(csv_output))
        rows = list(reader)

        assert len(rows) == 1

        row = rows[0]
        assert row["fork_name"] == "testrepo"
        assert row["owner"] == "testuser"
        assert row["stars"] == "5"
        assert row["features_count"] == "1"
        assert row["is_active"] == "True"

    def test_export_fork_analysis_with_commits(self, detailed_exporter, sample_fork_analysis):
        """Test fork analysis export with commits."""
        csv_output = detailed_exporter.export_fork_analyses([sample_fork_analysis])

        reader = csv.DictReader(io.StringIO(csv_output))
        rows = list(reader)

        # Should have one row per commit
        assert len(rows) == 1

        row = rows[0]
        assert row["commit_sha"] == "a1b2c3d4e5f6789012345678901234567890abcd"
        assert row["commit_message"] == "Add new feature\\n\\nThis commit adds a new feature to the repository."
        assert row["commit_author"] == "testuser"
        assert "commit_url" in row

    def test_export_fork_analysis_detail_mode(self, detailed_exporter, sample_fork_analysis):
        """Test fork analysis export in detail mode."""
        csv_output = detailed_exporter.export_fork_analyses([sample_fork_analysis])

        reader = csv.DictReader(io.StringIO(csv_output))

        # Check detail headers are present
        assert "language" in reader.fieldnames
        assert "description" in reader.fieldnames
        assert "last_activity" in reader.fieldnames
        assert "size_kb" in reader.fieldnames


class TestRankedFeaturesExport(TestCSVExporter):
    """Test ranked features CSV export."""

    @pytest.fixture
    def sample_ranked_feature(self, sample_fork, sample_commit):
        """Create a sample ranked feature."""
        feature = Feature(
            id="feat_1",
            title="Authentication System",
            description="JWT-based authentication",
            category=FeatureCategory.NEW_FEATURE,
            commits=[sample_commit],
            files_affected=["src/auth.py", "tests/test_auth.py"],
            source_fork=sample_fork
        )

        return RankedFeature(
            feature=feature,
            score=85.5,
            ranking_factors={
                "code_quality": 90.0,
                "community_engagement": 80.0,
                "recency": 85.0
            },
            similar_implementations=[]
        )

    def test_export_ranked_features_basic(self, exporter, sample_ranked_feature):
        """Test basic ranked features export."""
        csv_output = exporter.export_ranked_features([sample_ranked_feature])

        reader = csv.DictReader(io.StringIO(csv_output))
        rows = list(reader)

        assert len(rows) == 1

        row = rows[0]
        assert row["feature_id"] == "feat_1"
        assert row["title"] == "Authentication System"
        assert row["category"] == "new_feature"
        assert row["score"] == "85.5"
        assert row["source_fork"] == "testuser/testrepo"
        assert row["commits_count"] == "1"
        assert row["files_affected_count"] == "2"

    def test_export_ranked_features_detail_mode(self, detailed_exporter, sample_ranked_feature):
        """Test ranked features export in detail mode."""
        csv_output = detailed_exporter.export_ranked_features([sample_ranked_feature])

        reader = csv.DictReader(io.StringIO(csv_output))
        rows = list(reader)

        row = rows[0]
        assert "ranking_factors" in row
        assert "code_quality=90.0" in row["ranking_factors"]
        assert row["files_affected"] == "src/auth.py; tests/test_auth.py"


class TestCommitExplanationsExport(TestCSVExporter):
    """Test commit explanations CSV export."""

    @pytest.fixture
    def sample_commit_explanation(self, sample_commit):
        """Create a sample commit explanation."""
        category = CommitCategory(
            category_type=CategoryType.FEATURE,
            confidence=0.9,
            reasoning="Adds new functionality"
        )

        impact = ImpactAssessment(
            impact_level=ImpactLevel.MEDIUM,
            change_magnitude=60.0,
            file_criticality=0.7,
            quality_factors={"test_coverage": 0.8},
            reasoning="Moderate impact with good test coverage"
        )

        explanation = CommitExplanation(
            commit_sha=sample_commit.sha,
            category=category,
            impact_assessment=impact,
            what_changed="Added JWT authentication system",
            main_repo_value=MainRepoValue.YES,
            explanation="This commit adds JWT authentication which would be valuable for the main repository",
            is_complex=False,
            github_url=f"https://github.com/testuser/testrepo/commit/{sample_commit.sha}",
            generated_at=datetime(2023, 6, 21, 12, 0, 0)
        )

        return CommitWithExplanation(
            commit=sample_commit,
            explanation=explanation
        )

    def test_export_commit_explanations_basic(
        self,
        exporter,
        sample_commit_explanation,
        sample_repository
    ):
        """Test basic commit explanations export."""
        csv_output = exporter.export_commits_with_explanations(
            [sample_commit_explanation],
            sample_repository
        )

        reader = csv.DictReader(io.StringIO(csv_output))
        rows = list(reader)

        assert len(rows) == 1

        row = rows[0]
        assert row["commit_sha"] == "a1b2c3d4e5f6789012345678901234567890abcd"
        assert row["author"] == "testuser"
        assert row["files_changed"] == "2"
        assert row["additions"] == "50"
        assert row["deletions"] == "10"

    def test_export_commit_explanations_with_explanations(
        self,
        detailed_exporter,
        sample_commit_explanation,
        sample_repository
    ):
        """Test commit explanations export with explanation details."""
        csv_output = detailed_exporter.export_commits_with_explanations(
            [sample_commit_explanation],
            sample_repository
        )

        reader = csv.DictReader(io.StringIO(csv_output))
        rows = list(reader)

        row = rows[0]
        assert row["category"] == "feature"
        assert row["impact_level"] == "medium"
        assert row["main_repo_value"] == "yes"
        assert row["what_changed"] == "Added JWT authentication system"
        assert row["is_complex"] == "False"

    def test_export_commit_without_explanation(
        self,
        detailed_exporter,
        sample_commit,
        sample_repository
    ):
        """Test export of commit without explanation."""
        commit_without_explanation = CommitWithExplanation(
            commit=sample_commit,
            explanation=None,
            explanation_error="Failed to generate explanation"
        )

        csv_output = detailed_exporter.export_commits_with_explanations(
            [commit_without_explanation],
            sample_repository
        )

        reader = csv.DictReader(io.StringIO(csv_output))
        rows = list(reader)

        row = rows[0]
        assert row["category"] == ""
        assert row["explanation"] == "Failed to generate explanation"


class TestCSVFormatting(TestCSVExporter):
    """Test CSV formatting and escaping."""

    def test_newline_escaping(self, exporter):
        """Test that newlines are properly escaped."""
        fork_item = ForkPreviewItem(
            name="test\nrepo",
            owner="test\nuser",
            stars=10,
            last_push_date=datetime(2023, 6, 15, 12, 0, 0),
            fork_url="https://github.com/testuser/testrepo",
            activity_status="Active\nStatus",
            commits_ahead="Unknown"
        )

        preview = ForksPreview(total_forks=1, forks=[fork_item])
        csv_output = exporter.export_forks_preview(preview)

        # Check that newlines are escaped
        assert "test\\nrepo" in csv_output
        assert "test\\nuser" in csv_output
        assert "Active\\nStatus" in csv_output

    def test_no_newline_escaping_when_disabled(self, minimal_exporter):
        """Test that newline escaping can be disabled."""
        # Create exporter with escaping disabled
        config = CSVExportConfig(escape_newlines=False)
        exporter = CSVExporter(config)

        fork_item = ForkPreviewItem(
            name="test\nrepo",
            owner="testuser",
            stars=10,
            last_push_date=datetime(2023, 6, 15, 12, 0, 0),
            fork_url="https://github.com/testuser/testrepo",
            activity_status="Active",
            commits_ahead="Unknown"
        )

        preview = ForksPreview(total_forks=1, forks=[fork_item])
        csv_output = exporter.export_forks_preview(preview)

        # Newlines should not be escaped
        assert "test\nrepo" in csv_output

    def test_datetime_formatting(self, exporter):
        """Test datetime formatting in CSV output."""
        test_date = datetime(2023, 6, 15, 14, 30, 45)
        formatted = exporter._format_datetime(test_date)

        assert formatted == "2023-06-15 14:30:45"

    def test_datetime_formatting_none(self, exporter):
        """Test datetime formatting with None value."""
        formatted = exporter._format_datetime(None)
        assert formatted == ""

    def test_custom_date_format(self):
        """Test custom date format configuration."""
        config = CSVExportConfig(date_format="%Y-%m-%d")
        exporter = CSVExporter(config)

        test_date = datetime(2023, 6, 15, 14, 30, 45)
        formatted = exporter._format_datetime(test_date)

        assert formatted == "2023-06-15"

    def test_dict_formatting(self, exporter):
        """Test dictionary formatting for CSV output."""
        test_dict = {"key1": "value1", "key2": 42, "key3": 3.14}
        formatted = exporter._format_dict(test_dict)

        assert "key1=value1" in formatted
        assert "key2=42" in formatted
        assert "key3=3.14" in formatted
        assert formatted.count(";") == 2  # Two separators for three items

    def test_empty_dict_formatting(self, exporter):
        """Test empty dictionary formatting."""
        formatted = exporter._format_dict({})
        assert formatted == ""


class TestCSVExportGeneric(TestCSVExporter):
    """Test generic CSV export functionality."""

    def test_export_to_csv_forks_preview(self, exporter, sample_forks_preview):
        """Test generic export with forks preview."""
        csv_output = exporter.export_to_csv(sample_forks_preview)

        # Should be same as direct method
        expected = exporter.export_forks_preview(sample_forks_preview)
        assert csv_output == expected

    def test_export_to_csv_unsupported_type(self, exporter):
        """Test export with unsupported data type."""
        with pytest.raises(ValueError, match="Unsupported data type"):
            exporter.export_to_csv("invalid_data")

    def test_export_to_csv_empty_list(self, exporter):
        """Test export with empty list."""
        csv_output = exporter.export_to_csv([])
        assert "No data to export" in csv_output

    def test_export_to_csv_commit_explanations_missing_repository(self, exporter, sample_commit):
        """Test export of commit explanations without required repository parameter."""
        commit_with_explanation = CommitWithExplanation(commit=sample_commit, explanation=None)

        with pytest.raises(ValueError, match="repository parameter required"):
            exporter.export_to_csv([commit_with_explanation])

    def test_export_to_csv_file_output(self, exporter, sample_forks_preview, tmp_path):
        """Test export to file."""
        output_file = tmp_path / "test_export.csv"

        csv_output = exporter.export_to_csv(sample_forks_preview, str(output_file))

        # Check file was created and contains expected content
        assert output_file.exists()
        file_content = output_file.read_text()
        # Normalize line endings for comparison (CSV module may use different line endings)
        normalized_file_content = file_content.replace("\r\n", "\n").replace("\r", "\n")
        normalized_csv_output = csv_output.replace("\r\n", "\n").replace("\r", "\n")
        assert normalized_file_content == normalized_csv_output
        assert "fork_name,owner,stars" in file_content

    def test_export_to_csv_file_object(self, exporter, sample_forks_preview):
        """Test export to file object."""
        output_buffer = io.StringIO()

        csv_output = exporter.export_to_csv(sample_forks_preview, output_buffer)

        # Check buffer contains expected content
        buffer_content = output_buffer.getvalue()
        assert buffer_content == csv_output


class TestCSVCommitFormatting(TestCSVExporter):
    """Test commit data formatting for CSV export."""

    def test_format_commit_data_basic(self, exporter):
        """Test basic commit data formatting."""
        commit_data = "Fix bug in authentication; Add new feature"
        formatted = exporter._format_commit_data_for_csv(commit_data)

        assert formatted == "Fix bug in authentication; Add new feature"

    def test_format_commit_data_with_newlines(self, exporter):
        """Test commit data formatting with newlines."""
        commit_data = "Fix bug\nAdd feature\r\nUpdate docs"
        formatted = exporter._format_commit_data_for_csv(commit_data)

        assert formatted == "Fix bug Add feature Update docs"
        assert "\n" not in formatted
        assert "\r" not in formatted

    def test_format_commit_data_with_quotes(self, exporter):
        """Test commit data formatting with quotes."""
        commit_data = 'Fix "authentication" bug; Add "new" feature'
        formatted = exporter._format_commit_data_for_csv(commit_data)

        assert formatted == 'Fix "authentication" bug; Add "new" feature'

    def test_format_commit_data_with_commas(self, exporter):
        """Test commit data formatting with commas."""
        commit_data = "Fix bug, add feature, update docs"
        formatted = exporter._format_commit_data_for_csv(commit_data)

        assert formatted == "Fix bug, add feature, update docs"

    def test_format_commit_data_empty(self, exporter):
        """Test commit data formatting with empty/None data."""
        assert exporter._format_commit_data_for_csv(None) == ""
        assert exporter._format_commit_data_for_csv("") == ""
        assert exporter._format_commit_data_for_csv("   ") == ""

    def test_format_commit_data_with_extra_whitespace(self, exporter):
        """Test commit data formatting removes extra whitespace."""
        commit_data = "Fix   bug    in     authentication"
        formatted = exporter._format_commit_data_for_csv(commit_data)

        assert formatted == "Fix bug in authentication"

    def test_export_forks_with_commits_formatting(self, detailed_exporter):
        """Test forks export with commit data formatting."""
        fork_item = ForkPreviewItem(
            name="testrepo",
            owner="testuser",
            stars=10,
            last_push_date=datetime(2023, 6, 15, 12, 0, 0),
            fork_url="https://github.com/testuser/testrepo",
            activity_status="Active",
            commits_ahead="3",
            recent_commits='Fix "auth" bug\nAdd new feature, update docs\r\nRefactor code'
        )

        preview = ForksPreview(total_forks=1, forks=[fork_item])
        csv_output = detailed_exporter.export_forks_preview(preview)

        reader = csv.DictReader(io.StringIO(csv_output))
        rows = list(reader)

        assert len(rows) == 1
        row = rows[0]

        # Check that commit data is properly formatted
        assert "recent_commits" in row
        commits = row["recent_commits"]
        assert commits == 'Fix "auth" bug Add new feature, update docs Refactor code'
        assert "\n" not in commits
        assert "\r" not in commits

    def test_export_forks_with_date_hash_message_format(self, detailed_exporter):
        """Test forks export with new date-hash-message format for commits."""
        # Test the new format: "YYYY-MM-DD hash message; YYYY-MM-DD hash message"
        fork_item = ForkPreviewItem(
            name="testrepo",
            owner="testuser",
            stars=10,
            last_push_date=datetime(2023, 6, 15, 12, 0, 0),
            fork_url="https://github.com/testuser/testrepo",
            activity_status="Active",
            commits_ahead="2",
            recent_commits='2024-01-15 abc1234 Fix authentication bug; 2024-01-14 def5678 Add new feature'
        )

        preview = ForksPreview(total_forks=1, forks=[fork_item])
        csv_output = detailed_exporter.export_forks_preview(preview)

        reader = csv.DictReader(io.StringIO(csv_output))
        rows = list(reader)

        assert len(rows) == 1
        row = rows[0]

        # Check that commit data includes date, hash, and message
        assert "recent_commits" in row
        commits = row["recent_commits"]
        assert "2024-01-15 abc1234 Fix authentication bug" in commits
        assert "2024-01-14 def5678 Add new feature" in commits
        assert ";" in commits  # Multiple commits separated by semicolon

    def test_export_forks_with_fallback_hash_message_format(self, detailed_exporter):
        """Test forks export with fallback hash:message format when no date."""
        # Test the fallback format: "hash: message; hash: message"
        fork_item = ForkPreviewItem(
            name="testrepo",
            owner="testuser",
            stars=10,
            last_push_date=datetime(2023, 6, 15, 12, 0, 0),
            fork_url="https://github.com/testuser/testrepo",
            activity_status="Active",
            commits_ahead="2",
            recent_commits='abc1234: Fix authentication bug; def5678: Add new feature'
        )

        preview = ForksPreview(total_forks=1, forks=[fork_item])
        csv_output = detailed_exporter.export_forks_preview(preview)

        reader = csv.DictReader(io.StringIO(csv_output))
        rows = list(reader)

        assert len(rows) == 1
        row = rows[0]

        # Check that commit data includes hash and message in fallback format
        assert "recent_commits" in row
        commits = row["recent_commits"]
        assert "abc1234: Fix authentication bug" in commits
        assert "def5678: Add new feature" in commits
        assert ";" in commits  # Multiple commits separated by semicolon

    def test_export_forks_with_mixed_commit_formats(self, detailed_exporter):
        """Test forks export with mixed date and fallback formats."""
        # Test mixed format: some commits with dates, some without
        fork_item = ForkPreviewItem(
            name="testrepo",
            owner="testuser",
            stars=10,
            last_push_date=datetime(2023, 6, 15, 12, 0, 0),
            fork_url="https://github.com/testuser/testrepo",
            activity_status="Active",
            commits_ahead="3",
            recent_commits='2024-01-15 abc1234 Fix auth bug; def5678: Add feature; 2024-01-13 ghi9012 Update docs'
        )

        preview = ForksPreview(total_forks=1, forks=[fork_item])
        csv_output = detailed_exporter.export_forks_preview(preview)

        reader = csv.DictReader(io.StringIO(csv_output))
        rows = list(reader)

        assert len(rows) == 1
        row = rows[0]

        # Check that both formats are preserved
        commits = row["recent_commits"]
        assert "2024-01-15 abc1234 Fix auth bug" in commits
        assert "def5678: Add feature" in commits
        assert "2024-01-13 ghi9012 Update docs" in commits
        assert commits.count(";") == 2  # Two separators for three commits


class TestCSVExporterEdgeCases(TestCSVExporter):
    """Test edge cases and error conditions."""

    def test_export_with_special_characters(self, exporter):
        """Test export with special characters in data."""
        fork_item = ForkPreviewItem(
            name='repo"with"quotes',
            owner="user,with,commas",
            stars=10,
            last_push_date=datetime(2023, 6, 15, 12, 0, 0),
            fork_url="https://github.com/testuser/testrepo",
            activity_status="Active; Status",
            commits_ahead="Unknown"
        )

        preview = ForksPreview(total_forks=1, forks=[fork_item])
        csv_output = exporter.export_forks_preview(preview)

        # Should be valid CSV despite special characters
        reader = csv.DictReader(io.StringIO(csv_output))
        rows = list(reader)

        assert len(rows) == 1
        assert rows[0]["fork_name"] == 'repo"with"quotes'
        assert rows[0]["owner"] == "user,with,commas"

    def test_export_with_unicode_characters(self, exporter):
        """Test export with Unicode characters."""
        fork_item = ForkPreviewItem(
            name="repo-测试",
            owner="用户",
            stars=10,
            last_push_date=datetime(2023, 6, 15, 12, 0, 0),
            fork_url="https://github.com/testuser/testrepo",
            activity_status="Active",
            commits_ahead="Unknown"
        )

        preview = ForksPreview(total_forks=1, forks=[fork_item])
        csv_output = exporter.export_forks_preview(preview)

        # Should handle Unicode properly
        reader = csv.DictReader(io.StringIO(csv_output))
        rows = list(reader)

        assert len(rows) == 1
        assert rows[0]["fork_name"] == "repo-测试"
        assert rows[0]["owner"] == "用户"

    def test_export_with_none_values(self, exporter, sample_repository, sample_user):
        """Test export with None values in data."""
        # Create repository with None values (different from parent to satisfy Fork validation)
        repo_with_nones = Repository(
            owner="testuser",  # Different owner to make it a valid fork
            name="testrepo",
            full_name="testuser/testrepo",  # Different full_name
            url="https://api.github.com/repos/testuser/testrepo",
            html_url="https://github.com/testuser/testrepo",
            clone_url="https://github.com/testuser/testrepo.git",
            language=None,  # None value
            description=None,  # None value
            created_at=None,  # None value
            updated_at=None,  # None value
            pushed_at=None,   # None value
            is_fork=True  # Required for Fork validation
        )

        fork = Fork(
            repository=repo_with_nones,
            parent=sample_repository,
            owner=sample_user,
            last_activity=None,  # None value
            commits_ahead=0,
            commits_behind=0,
            is_active=True
        )

        metrics = ForkMetrics(
            stars=0,
            forks=0,
            contributors=0,
            last_activity=None,  # None value
            commit_frequency=0.0
        )

        analysis = ForkAnalysis(
            fork=fork,
            features=[],
            metrics=metrics
        )

        # Should handle None values gracefully
        csv_output = exporter.export_fork_analyses([analysis])

        reader = csv.DictReader(io.StringIO(csv_output))
        rows = list(reader)

        assert len(rows) == 1
        # None values should be converted to empty strings
        row = rows[0]
        assert row["fork_name"] == "testrepo"
        assert row["owner"] == "testuser"

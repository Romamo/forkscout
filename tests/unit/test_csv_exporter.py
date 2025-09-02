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
        assert config.commit_date_format == "%Y-%m-%d"

    def test_custom_config(self):
        """Test custom configuration values."""
        config = CSVExportConfig(
            include_commits=True,
            detail_mode=True,
            include_explanations=True,
            max_commits_per_fork=5,
            escape_newlines=False,
            include_urls=False,
            date_format="%Y-%m-%d",
            commit_date_format="%Y-%m-%d %H:%M",
        )

        assert config.include_commits is True
        assert config.detail_mode is True
        assert config.include_explanations is True
        assert config.max_commits_per_fork == 5
        assert config.escape_newlines is False
        assert config.include_urls is False
        assert config.date_format == "%Y-%m-%d"
        assert config.commit_date_format == "%Y-%m-%d %H:%M"

    def test_commit_date_format_validation_valid(self):
        """Test that valid commit date formats are accepted."""
        valid_formats = [
            "%Y-%m-%d",
            "%Y-%m-%d %H:%M:%S",
            "%d/%m/%Y",
            "%B %d, %Y",
            "%Y%m%d",
        ]

        for date_format in valid_formats:
            config = CSVExportConfig(commit_date_format=date_format)
            assert config.commit_date_format == date_format

    def test_commit_date_format_validation_invalid(self):
        """Test that invalid commit date formats raise ValueError."""
        # Test None specifically (raises TypeError)
        with pytest.raises(ValueError, match="Invalid commit_date_format"):
            CSVExportConfig(commit_date_format=None)

        # Test format strings that actually cause strftime to raise ValueError
        # Note: Most format strings don't raise errors, they just produce unexpected output
        # We'll test the validation mechanism with None which does raise TypeError

    def test_date_format_validation_valid(self):
        """Test that valid date formats are accepted."""
        valid_formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
            "%d/%m/%Y %H:%M",
            "%B %d, %Y %I:%M %p",
        ]

        for date_format in valid_formats:
            config = CSVExportConfig(date_format=date_format)
            assert config.date_format == date_format

    def test_date_format_validation_invalid(self):
        """Test that invalid date formats raise ValueError."""
        # Test None specifically (raises TypeError)
        with pytest.raises(ValueError, match="Invalid date_format"):
            CSVExportConfig(date_format=None)

    def test_both_date_formats_validation(self):
        """Test validation when both date formats are invalid."""
        with pytest.raises(ValueError, match="Invalid date_format"):
            CSVExportConfig(date_format=None, commit_date_format="%Y-%m-%d")

        with pytest.raises(ValueError, match="Invalid commit_date_format"):
            CSVExportConfig(date_format="%Y-%m-%d", commit_date_format=None)

    def test_config_with_all_options(self):
        """Test configuration with all options set."""
        config = CSVExportConfig(
            include_commits=True,
            detail_mode=True,
            include_explanations=True,
            max_commits_per_fork=15,
            escape_newlines=False,
            include_urls=False,
            date_format="%d/%m/%Y %H:%M:%S",
            commit_date_format="%d/%m/%Y",
        )

        assert config.include_commits is True
        assert config.detail_mode is True
        assert config.include_explanations is True
        assert config.max_commits_per_fork == 15
        assert config.escape_newlines is False
        assert config.include_urls is False
        assert config.date_format == "%d/%m/%Y %H:%M:%S"
        assert config.commit_date_format == "%d/%m/%Y"


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
            include_urls=True,
        )
        return CSVExporter(config)

    @pytest.fixture
    def minimal_exporter(self):
        """Create a CSV exporter with minimal config."""
        config = CSVExportConfig(
            include_commits=False,
            detail_mode=False,
            include_explanations=False,
            include_urls=False,
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
            deletions=10,
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
                commits_ahead="Unknown",
            ),
            ForkPreviewItem(
                name="testrepo",
                owner="user2",
                stars=5,
                last_push_date=datetime(2023, 5, 1, 12, 0, 0),
                fork_url="https://github.com/user2/testrepo",
                activity_status="Stale",
                commits_ahead="None",
            ),
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
            "fork_name",
            "owner",
            "stars",
            "commits_ahead",
            "activity_status",
            "fork_url",
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
            "fork_name",
            "owner",
            "stars",
            "commits_ahead",
            "activity_status",
        ]
        assert reader.fieldnames == expected_headers

    def test_export_forks_preview_detail_mode(
        self, detailed_exporter, sample_forks_preview
    ):
        """Test forks preview export in detail mode."""
        csv_output = detailed_exporter.export_forks_preview(sample_forks_preview)

        reader = csv.DictReader(io.StringIO(csv_output))

        # Check headers include detail fields
        assert "last_push_date" in reader.fieldnames
        assert "created_date" in reader.fieldnames
        assert "updated_date" in reader.fieldnames

    def test_export_forks_preview_with_commits_header(
        self, detailed_exporter, sample_forks_preview
    ):
        """Test forks preview export includes recent_commits header when include_commits is True."""
        csv_output = detailed_exporter.export_forks_preview(sample_forks_preview)

        reader = csv.DictReader(io.StringIO(csv_output))

        # Check that recent_commits header is included when include_commits=True
        assert "recent_commits" in reader.fieldnames

    def test_export_forks_preview_without_commits_header(
        self, exporter, sample_forks_preview
    ):
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
            source_fork=sample_fork,
        )

        metrics = ForkMetrics(
            stars=5,
            forks=1,
            contributors=2,
            last_activity=datetime(2023, 6, 20, 12, 0, 0),
            commit_frequency=0.5,
        )

        return ForkAnalysis(
            fork=sample_fork,
            features=[feature],
            metrics=metrics,
            analysis_date=datetime(2023, 6, 21, 12, 0, 0),
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

    def test_export_fork_analysis_with_commits(
        self, detailed_exporter, sample_fork_analysis
    ):
        """Test fork analysis export with commits."""
        csv_output = detailed_exporter.export_fork_analyses([sample_fork_analysis])

        reader = csv.DictReader(io.StringIO(csv_output))
        rows = list(reader)

        # Should have one row per commit
        assert len(rows) == 1

        row = rows[0]
        assert row["commit_sha"] == "a1b2c3d"  # 7-character short SHA
        assert (
            row["commit_description"]  # Changed from commit_message to commit_description
            == "Add new feature This commit adds a new feature to the repository."  # Newlines replaced with spaces
        )
        assert "commit_url" in row

    def test_export_fork_analysis_detail_mode(
        self, detailed_exporter, sample_fork_analysis
    ):
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
            source_fork=sample_fork,
        )

        return RankedFeature(
            feature=feature,
            score=85.5,
            ranking_factors={
                "code_quality": 90.0,
                "community_engagement": 80.0,
                "recency": 85.0,
            },
            similar_implementations=[],
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

    def test_export_ranked_features_detail_mode(
        self, detailed_exporter, sample_ranked_feature
    ):
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
            reasoning="Adds new functionality",
        )

        impact = ImpactAssessment(
            impact_level=ImpactLevel.MEDIUM,
            change_magnitude=60.0,
            file_criticality=0.7,
            quality_factors={"test_coverage": 0.8},
            reasoning="Moderate impact with good test coverage",
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
            generated_at=datetime(2023, 6, 21, 12, 0, 0),
        )

        return CommitWithExplanation(commit=sample_commit, explanation=explanation)

    def test_export_commit_explanations_basic(
        self, exporter, sample_commit_explanation, sample_repository
    ):
        """Test basic commit explanations export."""
        csv_output = exporter.export_commits_with_explanations(
            [sample_commit_explanation], sample_repository
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
        self, detailed_exporter, sample_commit_explanation, sample_repository
    ):
        """Test commit explanations export with explanation details."""
        csv_output = detailed_exporter.export_commits_with_explanations(
            [sample_commit_explanation], sample_repository
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
        self, detailed_exporter, sample_commit, sample_repository
    ):
        """Test export of commit without explanation."""
        commit_without_explanation = CommitWithExplanation(
            commit=sample_commit,
            explanation=None,
            explanation_error="Failed to generate explanation",
        )

        csv_output = detailed_exporter.export_commits_with_explanations(
            [commit_without_explanation], sample_repository
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
            commits_ahead="Unknown",
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
            commits_ahead="Unknown",
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

    def test_commit_date_format_usage(self):
        """Test that commit_date_format is available for use."""
        config = CSVExportConfig(commit_date_format="%d/%m/%Y")
        exporter = CSVExporter(config)

        # Verify the config is set correctly
        assert exporter.config.commit_date_format == "%d/%m/%Y"

        # Test that the format can be used to format dates
        test_date = datetime(2023, 6, 15, 14, 30, 45)
        formatted = test_date.strftime(exporter.config.commit_date_format)

        assert formatted == "15/06/2023"

    def test_different_date_formats_for_commits_and_general(self):
        """Test using different formats for commit dates vs general dates."""
        config = CSVExportConfig(
            date_format="%Y-%m-%d %H:%M:%S", commit_date_format="%Y-%m-%d"
        )
        exporter = CSVExporter(config)

        test_date = datetime(2023, 6, 15, 14, 30, 45)

        # General date format (for timestamps)
        general_formatted = exporter._format_datetime(test_date)
        assert general_formatted == "2023-06-15 14:30:45"

        # Commit date format (for commit dates)
        commit_formatted = test_date.strftime(exporter.config.commit_date_format)
        assert commit_formatted == "2023-06-15"

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

    def test_export_to_csv_commit_explanations_missing_repository(
        self, exporter, sample_commit
    ):
        """Test export of commit explanations without required repository parameter."""
        commit_with_explanation = CommitWithExplanation(
            commit=sample_commit, explanation=None
        )

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


class TestEnhancedHeaderGeneration(TestCSVExporter):
    """Test enhanced column header generation for multi-row format."""

    def test_generate_enhanced_fork_analysis_headers_basic(self, exporter):
        """Test basic enhanced header generation."""
        headers = exporter._generate_enhanced_fork_analysis_headers()

        # Check essential fork metadata columns are present
        expected_base_headers = [
            "fork_name",
            "owner",
            "stars",
            "forks_count",
            "commits_ahead",
            "commits_behind",
            "is_active",
            "features_count"
        ]

        for header in expected_base_headers:
            assert header in headers

        # Check commit-specific columns are present (replaces recent_commits)
        expected_commit_headers = [
            "commit_date",
            "commit_sha",
            "commit_description"
        ]

        for header in expected_commit_headers:
            assert header in headers

        # Verify recent_commits column is NOT present
        assert "recent_commits" not in headers

        # Check URL columns are included by default
        assert "fork_url" in headers
        assert "owner_url" in headers
        assert "commit_url" in headers

    def test_generate_enhanced_headers_without_urls(self):
        """Test enhanced header generation without URLs."""
        config = CSVExportConfig(include_urls=False)
        exporter = CSVExporter(config)

        headers = exporter._generate_enhanced_fork_analysis_headers()

        # URL columns should not be present
        assert "fork_url" not in headers
        assert "owner_url" not in headers
        assert "commit_url" not in headers

        # But commit columns should still be present
        assert "commit_date" in headers
        assert "commit_sha" in headers
        assert "commit_description" in headers

    def test_generate_enhanced_headers_with_detail_mode(self):
        """Test enhanced header generation with detail mode enabled."""
        config = CSVExportConfig(detail_mode=True)
        exporter = CSVExporter(config)

        headers = exporter._generate_enhanced_fork_analysis_headers()

        # Check detail mode columns are present
        expected_detail_headers = [
            "language",
            "description",
            "last_activity",
            "created_date",
            "updated_date",
            "pushed_date",
            "size_kb",
            "open_issues",
            "is_archived",
            "is_private"
        ]

        for header in expected_detail_headers:
            assert header in headers

        # Commit columns should still be present
        assert "commit_date" in headers
        assert "commit_sha" in headers
        assert "commit_description" in headers

    def test_generate_enhanced_headers_minimal_config(self):
        """Test enhanced header generation with minimal configuration."""
        config = CSVExportConfig(
            include_urls=False,
            detail_mode=False
        )
        exporter = CSVExporter(config)

        headers = exporter._generate_enhanced_fork_analysis_headers()

        # Should have essential columns plus commit columns
        expected_minimal_headers = [
            "fork_name",
            "owner",
            "stars",
            "forks_count",
            "commits_ahead",
            "commits_behind",
            "is_active",
            "features_count",
            "commit_date",
            "commit_sha",
            "commit_description"
        ]

        assert headers == expected_minimal_headers

    def test_enhanced_headers_vs_traditional_headers(self, exporter):
        """Test that enhanced headers differ from traditional headers appropriately."""
        traditional_headers = exporter._generate_fork_analysis_headers()
        enhanced_headers = exporter._generate_enhanced_fork_analysis_headers()

        # Both should have the same base fork metadata columns
        base_columns = [
            "fork_name",
            "owner",
            "stars",
            "forks_count",
            "commits_ahead",
            "commits_behind",
            "is_active",
            "features_count"
        ]

        for col in base_columns:
            assert col in traditional_headers
            assert col in enhanced_headers

        # Enhanced format should have new commit columns
        assert "commit_date" in enhanced_headers
        assert "commit_sha" in enhanced_headers
        assert "commit_description" in enhanced_headers

        # Traditional format should not have these when include_commits=False
        assert "commit_date" not in traditional_headers
        assert "commit_sha" not in traditional_headers
        assert "commit_description" not in traditional_headers

    def test_enhanced_headers_consistency_with_data_structure(self, exporter):
        """Test that enhanced headers are consistent with expected data row structure."""
        headers = exporter._generate_enhanced_fork_analysis_headers()

        # Verify header order matches expected data structure
        # Fork metadata should come first
        fork_metadata_start = headers.index("fork_name")
        features_count_index = headers.index("features_count")

        # Commit data should come after fork metadata
        commit_date_index = headers.index("commit_date")
        commit_sha_index = headers.index("commit_sha")
        commit_description_index = headers.index("commit_description")

        # Verify ordering
        assert fork_metadata_start < features_count_index < commit_date_index
        assert commit_date_index < commit_sha_index < commit_description_index

    def test_enhanced_headers_all_configurations(self):
        """Test enhanced headers with all configuration combinations."""
        # Test all combinations of include_urls and detail_mode
        configs = [
            (True, True),   # URLs + Detail
            (True, False),  # URLs only
            (False, True),  # Detail only
            (False, False)  # Minimal
        ]

        for include_urls, detail_mode in configs:
            config = CSVExportConfig(
                include_urls=include_urls,
                detail_mode=detail_mode
            )
            exporter = CSVExporter(config)
            headers = exporter._generate_enhanced_fork_analysis_headers()

            # Essential columns should always be present
            assert "fork_name" in headers
            assert "commit_date" in headers
            assert "commit_sha" in headers
            assert "commit_description" in headers

            # URL columns should match configuration
            if include_urls:
                assert "fork_url" in headers
                assert "commit_url" in headers
            else:
                assert "fork_url" not in headers
                assert "commit_url" not in headers

            # Detail columns should match configuration
            if detail_mode:
                assert "language" in headers
                assert "size_kb" in headers
            else:
                assert "language" not in headers
                assert "size_kb" not in headers


class TestMultiRowExportMethod(TestCSVExporter):
    """Test updated export method with multi-row format."""

    @pytest.fixture
    def sample_fork_analysis_with_commits(self, sample_fork, sample_commit, sample_user):
        """Create a sample fork analysis with multiple commits."""
        # Create additional commits
        commit2 = Commit(
            sha="b2c3d4e5f6789012345678901234567890abcdef",
            message="Fix authentication bug",
            author=sample_user,
            date=datetime(2023, 6, 19, 15, 45, 0),
            files_changed=["src/auth.py"],
            additions=10,
            deletions=5,
        )

        feature = Feature(
            id="feat_1",
            title="New Authentication",
            description="Adds JWT authentication",
            category=FeatureCategory.NEW_FEATURE,
            commits=[sample_commit, commit2],
            files_affected=["src/auth.py", "tests/test_auth.py"],
            source_fork=sample_fork,
        )

        metrics = ForkMetrics(
            stars=5,
            forks=1,
            contributors=2,
            last_activity=datetime(2023, 6, 20, 12, 0, 0),
            commit_frequency=0.5,
        )

        return ForkAnalysis(
            fork=sample_fork,
            features=[feature],
            metrics=metrics,
            analysis_date=datetime(2023, 6, 21, 12, 0, 0),
        )

    def test_export_fork_analyses_uses_multi_row_format(self, exporter, sample_fork_analysis_with_commits):
        """Test that export_fork_analyses uses the new multi-row format by default."""
        csv_output = exporter.export_fork_analyses([sample_fork_analysis_with_commits])

        reader = csv.DictReader(io.StringIO(csv_output))
        rows = list(reader)

        # Should have one row per commit (2 commits)
        assert len(rows) == 2

        # Check that headers use the new format
        expected_headers = [
            "fork_name", "owner", "stars", "forks_count", "commits_ahead",
            "commits_behind", "is_active", "features_count", "fork_url",
            "owner_url", "commit_date", "commit_sha", "commit_description", "commit_url"
        ]
        assert reader.fieldnames == expected_headers

        # Verify recent_commits column is NOT present
        assert "recent_commits" not in reader.fieldnames

        # Check first commit row
        row1 = rows[0]
        assert row1["fork_name"] == "testrepo"
        assert row1["owner"] == "testuser"
        assert row1["commit_sha"] == "a1b2c3d"  # 7-char SHA
        assert row1["commit_date"] == "2023-06-20"  # YYYY-MM-DD format
        assert "Add new feature" in row1["commit_description"]

        # Check second commit row
        row2 = rows[1]
        assert row2["fork_name"] == "testrepo"  # Repository info repeated
        assert row2["owner"] == "testuser"  # Repository info repeated
        assert row2["commit_sha"] == "b2c3d4e"  # 7-char SHA
        assert row2["commit_date"] == "2023-06-19"  # YYYY-MM-DD format
        assert "Fix authentication bug" in row2["commit_description"]

    def test_export_fork_analyses_with_no_commits(self, exporter, sample_fork):
        """Test export with fork that has no commits."""
        # Create fork analysis with no commits
        metrics = ForkMetrics(
            stars=5,
            forks=1,
            contributors=1,
            last_activity=datetime(2023, 6, 20, 12, 0, 0),
            commit_frequency=0.0,
        )

        analysis = ForkAnalysis(
            fork=sample_fork,
            features=[],  # No features, so no commits
            metrics=metrics,
            analysis_date=datetime(2023, 6, 21, 12, 0, 0),
        )

        csv_output = exporter.export_fork_analyses([analysis])

        reader = csv.DictReader(io.StringIO(csv_output))
        rows = list(reader)

        # Should have one row with empty commit columns
        assert len(rows) == 1

        row = rows[0]
        assert row["fork_name"] == "testrepo"
        assert row["owner"] == "testuser"
        assert row["commit_date"] == ""
        assert row["commit_sha"] == ""
        assert row["commit_description"] == ""
        assert row["commit_url"] == ""

    def test_export_fork_analyses_without_urls(self, sample_fork_analysis_with_commits):
        """Test export without URLs enabled."""
        config = CSVExportConfig(include_urls=False)
        exporter = CSVExporter(config)

        csv_output = exporter.export_fork_analyses([sample_fork_analysis_with_commits])

        reader = csv.DictReader(io.StringIO(csv_output))

        # URL columns should not be present
        assert "fork_url" not in reader.fieldnames
        assert "owner_url" not in reader.fieldnames
        assert "commit_url" not in reader.fieldnames

        # But commit columns should be present
        assert "commit_date" in reader.fieldnames
        assert "commit_sha" in reader.fieldnames
        assert "commit_description" in reader.fieldnames

    def test_export_fork_analyses_with_detail_mode(self, sample_fork_analysis_with_commits):
        """Test export with detail mode enabled."""
        config = CSVExportConfig(detail_mode=True)
        exporter = CSVExporter(config)

        csv_output = exporter.export_fork_analyses([sample_fork_analysis_with_commits])

        reader = csv.DictReader(io.StringIO(csv_output))
        rows = list(reader)

        # Detail columns should be present
        assert "language" in reader.fieldnames
        assert "description" in reader.fieldnames
        assert "size_kb" in reader.fieldnames

        # Repository info should be repeated on each commit row
        for row in rows:
            assert row["language"] == "Python"
            assert row["description"] == "Forked repository"

    def test_export_fork_analyses_commit_message_escaping(self, exporter, sample_fork, sample_user):
        """Test that commit messages are properly escaped."""
        # Create commit with special characters
        commit_with_special_chars = Commit(
            sha="c3d4e5f6789012345678901234567890abcdef01",
            message="Fix bug\nAdd feature\r\nUpdate docs",
            author=sample_user,
            date=datetime(2023, 6, 20, 10, 30, 0),
            files_changed=["src/main.py"],
            additions=20,
            deletions=5,
        )

        feature = Feature(
            id="feat_1",
            title="Bug Fix",
            description="Fixes various bugs",
            category=FeatureCategory.BUG_FIX,
            commits=[commit_with_special_chars],
            files_affected=["src/main.py"],
            source_fork=sample_fork,
        )

        metrics = ForkMetrics(
            stars=5,
            forks=1,
            contributors=1,
            last_activity=datetime(2023, 6, 20, 12, 0, 0),
            commit_frequency=0.5,
        )

        analysis = ForkAnalysis(
            fork=sample_fork,
            features=[feature],
            metrics=metrics,
            analysis_date=datetime(2023, 6, 21, 12, 0, 0),
        )

        csv_output = exporter.export_fork_analyses([analysis])

        reader = csv.DictReader(io.StringIO(csv_output))
        rows = list(reader)

        row = rows[0]
        # Newlines should be replaced with spaces
        assert row["commit_description"] == "Fix bug Add feature Update docs"
        assert "\n" not in row["commit_description"]
        assert "\r" not in row["commit_description"]

    def test_export_fork_analyses_multiple_forks(self, exporter, sample_fork_analysis_with_commits, sample_user, sample_repository):
        """Test export with multiple fork analyses."""
        # Create second fork analysis
        second_repo = Repository(
            id=999,
            owner="testuser",  # Fork owner
            name="secondrepo",
            full_name="testuser/secondrepo",
            url="https://api.github.com/repos/testuser/secondrepo",
            html_url="https://github.com/testuser/secondrepo",
            clone_url="https://github.com/testuser/secondrepo.git",
            stars=50,
            forks_count=10,
            language="JavaScript",
            description="Second test repository",
            is_fork=True,  # Mark as fork
            created_at=datetime(2023, 3, 1, 12, 0, 0),
            updated_at=datetime(2023, 6, 5, 12, 0, 0),
            pushed_at=datetime(2023, 6, 10, 12, 0, 0),
        )

        second_fork = Fork(
            repository=second_repo,
            parent=sample_repository,  # Use sample_repository as parent
            owner=sample_user,
            last_activity=datetime(2023, 6, 10, 12, 0, 0),
            commits_ahead=1,
            commits_behind=0,
            is_active=True,
        )

        second_commit = Commit(
            sha="d4e5f6789012345678901234567890abcdef0123",
            message="Add new component",
            author=sample_user,
            date=datetime(2023, 6, 10, 14, 0, 0),
            files_changed=["src/component.js"],
            additions=30,
            deletions=0,
        )

        second_feature = Feature(
            id="feat_2",
            title="New Component",
            description="Adds new UI component",
            category=FeatureCategory.NEW_FEATURE,
            commits=[second_commit],
            files_affected=["src/component.js"],
            source_fork=second_fork,
        )

        second_metrics = ForkMetrics(
            stars=50,
            forks=10,
            contributors=3,
            last_activity=datetime(2023, 6, 10, 12, 0, 0),
            commit_frequency=0.8,
        )

        second_analysis = ForkAnalysis(
            fork=second_fork,
            features=[second_feature],
            metrics=second_metrics,
            analysis_date=datetime(2023, 6, 21, 12, 0, 0),
        )

        csv_output = exporter.export_fork_analyses([sample_fork_analysis_with_commits, second_analysis])

        reader = csv.DictReader(io.StringIO(csv_output))
        rows = list(reader)

        # Should have 3 rows total (2 commits from first fork + 1 commit from second fork)
        assert len(rows) == 3

        # Check that each fork's data is properly separated
        first_fork_rows = [row for row in rows if row["fork_name"] == "testrepo"]
        second_fork_rows = [row for row in rows if row["fork_name"] == "secondrepo"]

        assert len(first_fork_rows) == 2
        assert len(second_fork_rows) == 1

        # Verify second fork data
        second_row = second_fork_rows[0]
        assert second_row["owner"] == "testuser"
        assert second_row["stars"] == "50"
        assert second_row["commit_sha"] == "d4e5f67"
        assert "Add new component" in second_row["commit_description"]


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
            recent_commits='Fix "auth" bug\nAdd new feature, update docs\r\nRefactor code',
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
            recent_commits="2024-01-15 abc1234 Fix authentication bug; 2024-01-14 def5678 Add new feature",
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
            recent_commits="abc1234: Fix authentication bug; def5678: Add new feature",
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
            recent_commits="2024-01-15 abc1234 Fix auth bug; def5678: Add feature; 2024-01-13 ghi9012 Update docs",
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
            commits_ahead="Unknown",
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
            commits_ahead="Unknown",
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
            pushed_at=None,  # None value
            is_fork=True,  # Required for Fork validation
        )

        fork = Fork(
            repository=repo_with_nones,
            parent=sample_repository,
            owner=sample_user,
            last_activity=None,  # None value
            commits_ahead=0,
            commits_behind=0,
            is_active=True,
        )

        metrics = ForkMetrics(
            stars=0,
            forks=0,
            contributors=0,
            last_activity=None,  # None value
            commit_frequency=0.0,
        )

        analysis = ForkAnalysis(fork=fork, features=[], metrics=metrics)

        # Should handle None values gracefully
        csv_output = exporter.export_fork_analyses([analysis])

        reader = csv.DictReader(io.StringIO(csv_output))
        rows = list(reader)

        assert len(rows) == 1
        # None values should be converted to empty strings
        row = rows[0]
        assert row["fork_name"] == "testrepo"
        assert row["owner"] == "testuser"

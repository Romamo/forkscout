"""Unit tests for fork qualification data models."""

from datetime import datetime, timedelta

import pytest
from pydantic import ValidationError

from src.forklift.models.fork_qualification import (
    CollectedForkData,
    ForkQualificationMetrics,
    QualificationStats,
    QualifiedForksResult,
)


class TestForkQualificationMetrics:
    """Test ForkQualificationMetrics model."""

    def test_create_fork_qualification_metrics_with_required_fields(self):
        """Test creating ForkQualificationMetrics with required fields."""
        now = datetime.utcnow()

        metrics = ForkQualificationMetrics(
            id=12345,
            name="test-repo",
            full_name="owner/test-repo",
            owner="owner",
            html_url="https://github.com/owner/test-repo",
            created_at=now - timedelta(days=100),
            updated_at=now - timedelta(days=10),
            pushed_at=now - timedelta(days=5),
        )

        assert metrics.id == 12345
        assert metrics.name == "test-repo"
        assert metrics.full_name == "owner/test-repo"
        assert metrics.owner == "owner"
        assert metrics.html_url == "https://github.com/owner/test-repo"
        assert metrics.stargazers_count == 0  # Default value
        assert metrics.forks_count == 0  # Default value
        assert metrics.fork is True  # Default value

    def test_create_fork_qualification_metrics_with_all_fields(self):
        """Test creating ForkQualificationMetrics with all fields."""
        now = datetime.utcnow()

        metrics = ForkQualificationMetrics(
            id=12345,
            name="test-repo",
            full_name="owner/test-repo",
            owner="owner",
            html_url="https://github.com/owner/test-repo",
            stargazers_count=50,
            forks_count=10,
            watchers_count=25,
            size=1024,
            language="Python",
            topics=["web", "api", "python"],
            open_issues_count=5,
            created_at=now - timedelta(days=100),
            updated_at=now - timedelta(days=10),
            pushed_at=now - timedelta(days=5),
            archived=False,
            disabled=False,
            fork=True,
            license_key="mit",
            license_name="MIT License",
            description="A test repository",
            homepage="https://example.com",
            default_branch="main",
        )

        assert metrics.stargazers_count == 50
        assert metrics.language == "Python"
        assert metrics.topics == ["web", "api", "python"]
        assert metrics.license_key == "mit"
        assert metrics.description == "A test repository"

    def test_computed_field_days_since_creation(self):
        """Test days_since_creation computed field."""
        created_date = datetime.utcnow() - timedelta(days=30)

        metrics = ForkQualificationMetrics(
            id=12345,
            name="test-repo",
            full_name="owner/test-repo",
            owner="owner",
            html_url="https://github.com/owner/test-repo",
            created_at=created_date,
            updated_at=datetime.utcnow(),
            pushed_at=datetime.utcnow(),
        )

        # Should be approximately 30 days (allowing for small timing differences)
        assert 29 <= metrics.days_since_creation <= 31

    def test_computed_field_commits_ahead_status_no_commits(self):
        """Test commits_ahead_status when created_at >= pushed_at (no commits)."""
        now = datetime.utcnow()

        metrics = ForkQualificationMetrics(
            id=12345,
            name="test-repo",
            full_name="owner/test-repo",
            owner="owner",
            html_url="https://github.com/owner/test-repo",
            created_at=now,
            updated_at=now,
            pushed_at=now - timedelta(minutes=1),  # Pushed before creation
        )

        assert metrics.commits_ahead_status == "No commits ahead"
        assert metrics.can_skip_analysis is True

    def test_computed_field_commits_ahead_status_has_commits(self):
        """Test commits_ahead_status when pushed_at > created_at (has commits)."""
        now = datetime.utcnow()

        metrics = ForkQualificationMetrics(
            id=12345,
            name="test-repo",
            full_name="owner/test-repo",
            owner="owner",
            html_url="https://github.com/owner/test-repo",
            created_at=now - timedelta(days=10),
            updated_at=now - timedelta(days=5),
            pushed_at=now - timedelta(days=1),  # Pushed after creation
        )

        assert metrics.commits_ahead_status == "Has commits"
        assert metrics.can_skip_analysis is False

    def test_computed_field_activity_ratio(self):
        """Test activity_ratio computed field."""
        now = datetime.utcnow()

        # Repository created 100 days ago, last push 20 days ago
        metrics = ForkQualificationMetrics(
            id=12345,
            name="test-repo",
            full_name="owner/test-repo",
            owner="owner",
            html_url="https://github.com/owner/test-repo",
            created_at=now - timedelta(days=100),
            updated_at=now - timedelta(days=20),
            pushed_at=now - timedelta(days=20),
        )

        # Activity ratio should be (100 - 20) / 100 = 0.8
        expected_ratio = 80 / 100
        assert abs(metrics.activity_ratio - expected_ratio) < 0.01

    def test_computed_field_engagement_score(self):
        """Test engagement_score computed field."""
        metrics = ForkQualificationMetrics(
            id=12345,
            name="test-repo",
            full_name="owner/test-repo",
            owner="owner",
            html_url="https://github.com/owner/test-repo",
            stargazers_count=30,  # Weight: 3
            forks_count=10,  # Weight: 2
            watchers_count=6,  # Weight: 1
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            pushed_at=datetime.utcnow(),
        )

        # Expected: (30*3 + 10*2 + 6*1) / 6 = (90 + 20 + 6) / 6 = 116/6 ≈ 19.33
        expected_score = (30 * 3 + 10 * 2 + 6) / 6
        assert abs(metrics.engagement_score - expected_score) < 0.01

    def test_engagement_score_capped_at_100(self):
        """Test that engagement_score is capped at 100."""
        metrics = ForkQualificationMetrics(
            id=12345,
            name="test-repo",
            full_name="owner/test-repo",
            owner="owner",
            html_url="https://github.com/owner/test-repo",
            stargazers_count=1000,  # Very high values
            forks_count=500,
            watchers_count=200,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            pushed_at=datetime.utcnow(),
        )

        assert metrics.engagement_score == 100.0

    def test_from_github_api_complete_data(self):
        """Test creating ForkQualificationMetrics from GitHub API data."""
        github_data = {
            "id": 12345,
            "name": "test-repo",
            "full_name": "owner/test-repo",
            "owner": {"login": "owner"},
            "html_url": "https://github.com/owner/test-repo",
            "stargazers_count": 25,
            "forks_count": 5,
            "watchers_count": 15,
            "size": 2048,
            "language": "JavaScript",
            "topics": ["web", "frontend"],
            "open_issues_count": 3,
            "created_at": "2023-01-01T00:00:00Z",
            "updated_at": "2023-12-01T00:00:00Z",
            "pushed_at": "2023-12-15T00:00:00Z",
            "archived": False,
            "disabled": False,
            "fork": True,
            "license": {"key": "apache-2.0", "name": "Apache License 2.0"},
            "description": "Test repository",
            "homepage": "https://test.example.com",
            "default_branch": "main",
        }

        metrics = ForkQualificationMetrics.from_github_api(github_data)

        assert metrics.id == 12345
        assert metrics.name == "test-repo"
        assert metrics.owner == "owner"
        assert metrics.stargazers_count == 25
        assert metrics.language == "JavaScript"
        assert metrics.topics == ["web", "frontend"]
        assert metrics.license_key == "apache-2.0"
        assert metrics.license_name == "Apache License 2.0"
        assert metrics.description == "Test repository"

    def test_from_github_api_minimal_data(self):
        """Test creating ForkQualificationMetrics from minimal GitHub API data."""
        github_data = {
            "id": 12345,
            "name": "test-repo",
            "full_name": "owner/test-repo",
            "owner": {"login": "owner"},
            "html_url": "https://github.com/owner/test-repo",
            "created_at": "2023-01-01T00:00:00Z",
            "updated_at": "2023-12-01T00:00:00Z",
            "pushed_at": "2023-12-15T00:00:00Z",
        }

        metrics = ForkQualificationMetrics.from_github_api(github_data)

        assert metrics.id == 12345
        assert metrics.stargazers_count == 0  # Default
        assert metrics.language is None
        assert metrics.topics == []
        assert metrics.license_key is None

    def test_validation_negative_counts(self):
        """Test validation fails for negative counts."""
        with pytest.raises(ValidationError):
            ForkQualificationMetrics(
                id=12345,
                name="test-repo",
                full_name="owner/test-repo",
                owner="owner",
                html_url="https://github.com/owner/test-repo",
                stargazers_count=-1,  # Invalid negative value
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                pushed_at=datetime.utcnow(),
            )


class TestCollectedForkData:
    """Test CollectedForkData model."""

    def test_create_collected_fork_data(self):
        """Test creating CollectedForkData."""
        metrics = ForkQualificationMetrics(
            id=12345,
            name="test-repo",
            full_name="owner/test-repo",
            owner="owner",
            html_url="https://github.com/owner/test-repo",
            created_at=datetime.utcnow() - timedelta(days=30),
            updated_at=datetime.utcnow() - timedelta(days=5),
            pushed_at=datetime.utcnow() - timedelta(days=2),
        )

        fork_data = CollectedForkData(metrics=metrics)

        assert fork_data.metrics == metrics
        assert isinstance(fork_data.collection_timestamp, datetime)

    def test_activity_summary_very_active(self):
        """Test activity_summary for very active fork."""
        metrics = ForkQualificationMetrics(
            id=12345,
            name="test-repo",
            full_name="owner/test-repo",
            owner="owner",
            html_url="https://github.com/owner/test-repo",
            created_at=datetime.utcnow() - timedelta(days=30),
            updated_at=datetime.utcnow() - timedelta(days=1),
            pushed_at=datetime.utcnow() - timedelta(days=3),  # 3 days ago
        )

        fork_data = CollectedForkData(metrics=metrics)
        assert fork_data.activity_summary == "Very Active (< 1 week)"

    def test_activity_summary_inactive(self):
        """Test activity_summary for inactive fork."""
        metrics = ForkQualificationMetrics(
            id=12345,
            name="test-repo",
            full_name="owner/test-repo",
            owner="owner",
            html_url="https://github.com/owner/test-repo",
            created_at=datetime.utcnow() - timedelta(days=500),
            updated_at=datetime.utcnow() - timedelta(days=400),
            pushed_at=datetime.utcnow() - timedelta(days=400),  # Over 1 year ago
        )

        fork_data = CollectedForkData(metrics=metrics)
        assert fork_data.activity_summary == "Inactive (> 1 year)"

    def test_qualification_summary(self):
        """Test qualification_summary computed field."""
        metrics = ForkQualificationMetrics(
            id=12345,
            name="test-repo",
            full_name="owner/test-repo",
            owner="owner",
            html_url="https://github.com/owner/test-repo",
            stargazers_count=15,
            created_at=datetime.utcnow() - timedelta(days=30),
            updated_at=datetime.utcnow() - timedelta(days=5),
            pushed_at=datetime.utcnow() - timedelta(days=2),
        )

        fork_data = CollectedForkData(metrics=metrics)
        summary = fork_data.qualification_summary

        assert "15 stars" in summary
        assert "Has commits" in summary
        assert "Very Active" in summary


class TestQualificationStats:
    """Test QualificationStats model."""

    def test_create_qualification_stats(self):
        """Test creating QualificationStats."""
        stats = QualificationStats(
            total_forks_discovered=100,
            forks_with_no_commits=30,
            forks_with_commits=70,
            archived_forks=5,
            disabled_forks=2,
            api_calls_made=50,
            api_calls_saved=150,
            processing_time_seconds=45.5,
        )

        assert stats.total_forks_discovered == 100
        assert stats.forks_with_no_commits == 30
        assert stats.forks_with_commits == 70
        assert stats.api_calls_made == 50
        assert stats.api_calls_saved == 150

    def test_efficiency_percentage(self):
        """Test efficiency_percentage computed field."""
        stats = QualificationStats(
            api_calls_made=50,
            api_calls_saved=150,
        )

        # Efficiency = 150 / (50 + 150) * 100 = 75%
        assert stats.efficiency_percentage == 75.0

    def test_efficiency_percentage_no_calls(self):
        """Test efficiency_percentage when no calls made."""
        stats = QualificationStats()
        assert stats.efficiency_percentage == 0.0

    def test_skip_rate_percentage(self):
        """Test skip_rate_percentage computed field."""
        stats = QualificationStats(
            total_forks_discovered=100,
            forks_with_no_commits=25,
        )

        assert stats.skip_rate_percentage == 25.0

    def test_analysis_candidate_percentage(self):
        """Test analysis_candidate_percentage computed field."""
        stats = QualificationStats(
            total_forks_discovered=100,
            forks_with_commits=75,
        )

        assert stats.analysis_candidate_percentage == 75.0

    def test_percentages_with_zero_forks(self):
        """Test percentage calculations with zero forks."""
        stats = QualificationStats(
            total_forks_discovered=0,
            forks_with_no_commits=0,
            forks_with_commits=0,
        )

        assert stats.skip_rate_percentage == 0.0
        assert stats.analysis_candidate_percentage == 0.0


class TestQualifiedForksResult:
    """Test QualifiedForksResult model."""

    def test_create_qualified_forks_result(self):
        """Test creating QualifiedForksResult."""
        stats = QualificationStats(
            total_forks_discovered=10,
            forks_with_no_commits=3,
            forks_with_commits=7,
        )

        result = QualifiedForksResult(
            repository_owner="owner",
            repository_name="repo",
            repository_url="https://github.com/owner/repo",
            stats=stats,
        )

        assert result.repository_owner == "owner"
        assert result.repository_name == "repo"
        assert result.stats == stats
        assert result.collected_forks == []

    def test_forks_needing_analysis(self):
        """Test forks_needing_analysis computed field."""
        # Create forks with different commits ahead status
        fork_with_commits = CollectedForkData(
            metrics=ForkQualificationMetrics(
                id=1,
                name="fork1",
                full_name="user1/fork1",
                owner="user1",
                html_url="https://github.com/user1/fork1",
                created_at=datetime.utcnow() - timedelta(days=10),
                updated_at=datetime.utcnow() - timedelta(days=5),
                pushed_at=datetime.utcnow() - timedelta(days=1),  # Has commits
            )
        )

        fork_no_commits = CollectedForkData(
            metrics=ForkQualificationMetrics(
                id=2,
                name="fork2",
                full_name="user2/fork2",
                owner="user2",
                html_url="https://github.com/user2/fork2",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                pushed_at=datetime.utcnow() - timedelta(minutes=1),  # No commits
            )
        )

        result = QualifiedForksResult(
            repository_owner="owner",
            repository_name="repo",
            repository_url="https://github.com/owner/repo",
            collected_forks=[fork_with_commits, fork_no_commits],
            stats=QualificationStats(),
        )

        needing_analysis = result.forks_needing_analysis
        assert len(needing_analysis) == 1
        assert needing_analysis[0] == fork_with_commits

    def test_forks_to_skip(self):
        """Test forks_to_skip computed field."""
        fork_with_commits = CollectedForkData(
            metrics=ForkQualificationMetrics(
                id=1,
                name="fork1",
                full_name="user1/fork1",
                owner="user1",
                html_url="https://github.com/user1/fork1",
                created_at=datetime.utcnow() - timedelta(days=10),
                updated_at=datetime.utcnow() - timedelta(days=5),
                pushed_at=datetime.utcnow() - timedelta(days=1),  # Has commits
            )
        )

        fork_no_commits = CollectedForkData(
            metrics=ForkQualificationMetrics(
                id=2,
                name="fork2",
                full_name="user2/fork2",
                owner="user2",
                html_url="https://github.com/user2/fork2",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                pushed_at=datetime.utcnow() - timedelta(minutes=1),  # No commits
            )
        )

        result = QualifiedForksResult(
            repository_owner="owner",
            repository_name="repo",
            repository_url="https://github.com/owner/repo",
            collected_forks=[fork_with_commits, fork_no_commits],
            stats=QualificationStats(),
        )

        to_skip = result.forks_to_skip
        assert len(to_skip) == 1
        assert to_skip[0] == fork_no_commits

    def test_active_forks(self):
        """Test active_forks computed field."""
        active_fork = CollectedForkData(
            metrics=ForkQualificationMetrics(
                id=1,
                name="active-fork",
                full_name="user1/active-fork",
                owner="user1",
                html_url="https://github.com/user1/active-fork",
                created_at=datetime.utcnow() - timedelta(days=100),
                updated_at=datetime.utcnow() - timedelta(days=10),
                pushed_at=datetime.utcnow()
                - timedelta(days=30),  # 30 days ago (active)
            )
        )

        inactive_fork = CollectedForkData(
            metrics=ForkQualificationMetrics(
                id=2,
                name="inactive-fork",
                full_name="user2/inactive-fork",
                owner="user2",
                html_url="https://github.com/user2/inactive-fork",
                created_at=datetime.utcnow() - timedelta(days=200),
                updated_at=datetime.utcnow() - timedelta(days=150),
                pushed_at=datetime.utcnow()
                - timedelta(days=150),  # 150 days ago (inactive)
            )
        )

        result = QualifiedForksResult(
            repository_owner="owner",
            repository_name="repo",
            repository_url="https://github.com/owner/repo",
            collected_forks=[active_fork, inactive_fork],
            stats=QualificationStats(),
        )

        active = result.active_forks
        assert len(active) == 1
        assert active[0] == active_fork

    def test_popular_forks(self):
        """Test popular_forks computed field."""
        popular_fork = CollectedForkData(
            metrics=ForkQualificationMetrics(
                id=1,
                name="popular-fork",
                full_name="user1/popular-fork",
                owner="user1",
                html_url="https://github.com/user1/popular-fork",
                stargazers_count=10,  # Popular (>= 5 stars)
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                pushed_at=datetime.utcnow(),
            )
        )

        unpopular_fork = CollectedForkData(
            metrics=ForkQualificationMetrics(
                id=2,
                name="unpopular-fork",
                full_name="user2/unpopular-fork",
                owner="user2",
                html_url="https://github.com/user2/unpopular-fork",
                stargazers_count=2,  # Not popular (< 5 stars)
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                pushed_at=datetime.utcnow(),
            )
        )

        result = QualifiedForksResult(
            repository_owner="owner",
            repository_name="repo",
            repository_url="https://github.com/owner/repo",
            collected_forks=[popular_fork, unpopular_fork],
            stats=QualificationStats(),
        )

        popular = result.popular_forks
        assert len(popular) == 1
        assert popular[0] == popular_fork

    def test_get_forks_by_language(self):
        """Test get_forks_by_language method."""
        python_fork = CollectedForkData(
            metrics=ForkQualificationMetrics(
                id=1,
                name="python-fork",
                full_name="user1/python-fork",
                owner="user1",
                html_url="https://github.com/user1/python-fork",
                language="Python",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                pushed_at=datetime.utcnow(),
            )
        )

        js_fork = CollectedForkData(
            metrics=ForkQualificationMetrics(
                id=2,
                name="js-fork",
                full_name="user2/js-fork",
                owner="user2",
                html_url="https://github.com/user2/js-fork",
                language="JavaScript",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                pushed_at=datetime.utcnow(),
            )
        )

        result = QualifiedForksResult(
            repository_owner="owner",
            repository_name="repo",
            repository_url="https://github.com/owner/repo",
            collected_forks=[python_fork, js_fork],
            stats=QualificationStats(),
        )

        python_forks = result.get_forks_by_language("Python")
        assert len(python_forks) == 1
        assert python_forks[0] == python_fork

    def test_get_forks_with_topics(self):
        """Test get_forks_with_topics method."""
        web_fork = CollectedForkData(
            metrics=ForkQualificationMetrics(
                id=1,
                name="web-fork",
                full_name="user1/web-fork",
                owner="user1",
                html_url="https://github.com/user1/web-fork",
                topics=["web", "frontend", "react"],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                pushed_at=datetime.utcnow(),
            )
        )

        api_fork = CollectedForkData(
            metrics=ForkQualificationMetrics(
                id=2,
                name="api-fork",
                full_name="user2/api-fork",
                owner="user2",
                html_url="https://github.com/user2/api-fork",
                topics=["api", "backend", "python"],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                pushed_at=datetime.utcnow(),
            )
        )

        result = QualifiedForksResult(
            repository_owner="owner",
            repository_name="repo",
            repository_url="https://github.com/owner/repo",
            collected_forks=[web_fork, api_fork],
            stats=QualificationStats(),
        )

        web_forks = result.get_forks_with_topics(["web", "frontend"])
        assert len(web_forks) == 1
        assert web_forks[0] == web_fork

        backend_forks = result.get_forks_with_topics(["backend"])
        assert len(backend_forks) == 1
        assert backend_forks[0] == api_fork

    def test_get_summary_report(self):
        """Test get_summary_report method."""
        # Create sample fork data
        fork_with_commits = CollectedForkData(
            metrics=ForkQualificationMetrics(
                id=1,
                name="fork1",
                full_name="user1/fork1",
                owner="user1",
                html_url="https://github.com/user1/fork1",
                stargazers_count=10,  # Popular fork
                created_at=datetime.utcnow() - timedelta(days=10),
                updated_at=datetime.utcnow() - timedelta(days=5),
                pushed_at=datetime.utcnow() - timedelta(days=1),  # Has commits, active
            )
        )

        fork_no_commits = CollectedForkData(
            metrics=ForkQualificationMetrics(
                id=2,
                name="fork2",
                full_name="user2/fork2",
                owner="user2",
                html_url="https://github.com/user2/fork2",
                created_at=datetime.utcnow() - timedelta(days=100),
                updated_at=datetime.utcnow() - timedelta(days=100),
                pushed_at=datetime.utcnow()
                - timedelta(days=150),  # Pushed before creation = no commits
            )
        )

        stats = QualificationStats(
            total_forks_discovered=10,
            forks_with_no_commits=3,
            forks_with_commits=7,
            api_calls_made=20,
            api_calls_saved=80,
            processing_time_seconds=15.5,
        )

        result = QualifiedForksResult(
            repository_owner="owner",
            repository_name="test-repo",
            repository_url="https://github.com/owner/test-repo",
            collected_forks=[fork_with_commits, fork_no_commits],
            stats=stats,
        )

        report = result.get_summary_report()

        assert "owner/test-repo" in report
        assert "Total Forks: 10" in report
        assert "Need Analysis: 1" in report  # Only fork_with_commits needs analysis
        assert "Can Skip: 1" in report  # Only fork_no_commits can be skipped
        assert "Active (90 days): 1" in report  # Only fork_with_commits is active
        assert "Popular (5+ stars): 1" in report  # Only fork_with_commits is popular
        assert "80.0% calls saved" in report
        assert "15.50 seconds" in report

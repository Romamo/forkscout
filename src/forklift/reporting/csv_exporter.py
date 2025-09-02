"""CSV export functionality for fork analysis results."""

import csv
import io
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, TextIO

from forklift.models.analysis import (
    CommitWithExplanation,
    ForkAnalysis,
    ForkPreviewItem,
    ForksPreview,
    RankedFeature,
)
from forklift.models.github import Commit, Fork, Repository

logger = logging.getLogger(__name__)


@dataclass
class CSVExportConfig:
    """Configuration for CSV export operations."""

    include_commits: bool = False
    """Whether to include commit information in the export."""

    detail_mode: bool = False
    """Whether to include detailed information (more columns)."""

    include_explanations: bool = False
    """Whether to include commit explanations if available."""

    max_commits_per_fork: int = 10
    """Maximum number of commits to include per fork."""

    escape_newlines: bool = True
    """Whether to escape newlines in text fields."""

    include_urls: bool = True
    """Whether to include GitHub URLs in the export."""

    date_format: str = "%Y-%m-%d %H:%M:%S"
    """Date format for timestamp fields."""

    commit_date_format: str = "%Y-%m-%d"
    """Date format for commit dates in CSV output."""

    def __post_init__(self) -> None:
        """Validate configuration options after initialization."""
        self._validate_date_formats()

    def _validate_date_formats(self) -> None:
        """Validate that date format strings are valid."""
        test_date = datetime(2023, 1, 1, 12, 0, 0)

        try:
            test_date.strftime(self.date_format)
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid date_format '{self.date_format}': {e}") from e

        try:
            test_date.strftime(self.commit_date_format)
        except (ValueError, TypeError) as e:
            raise ValueError(
                f"Invalid commit_date_format '{self.commit_date_format}': {e}"
            ) from e


class CSVExporter:
    """Handles CSV export of fork analysis data."""

    def __init__(self, config: CSVExportConfig | None = None):
        """Initialize the CSV exporter.

        Args:
            config: Export configuration. Uses defaults if None.
        """
        self.config = config or CSVExportConfig()

    def export_forks_preview(self, preview: ForksPreview) -> str:
        """Export forks preview data to CSV format.

        Args:
            preview: Forks preview data to export

        Returns:
            CSV formatted string
        """
        logger.info(f"Exporting {len(preview.forks)} forks to CSV format")

        output = io.StringIO()
        headers = self._generate_forks_preview_headers()

        writer = csv.DictWriter(output, fieldnames=headers, quoting=csv.QUOTE_MINIMAL)
        writer.writeheader()

        for fork in preview.forks:
            row = self._format_fork_preview_row(fork)
            writer.writerow(row)

        return output.getvalue()

    def export_fork_analyses(self, analyses: list[ForkAnalysis]) -> str:
        """Export fork analysis results to CSV format.

        Args:
            analyses: List of fork analysis results to export

        Returns:
            CSV formatted string
        """
        logger.info(f"Exporting {len(analyses)} fork analyses to CSV format")

        output = io.StringIO()
        headers = self._generate_fork_analysis_headers()

        writer = csv.DictWriter(output, fieldnames=headers, quoting=csv.QUOTE_MINIMAL)
        writer.writeheader()

        for analysis in analyses:
            if self.config.include_commits and analysis.fork.repository:
                # Export one row per commit if including commits
                commits = self._get_commits_for_export(analysis)
                if commits:
                    for commit in commits:
                        row = self._format_fork_analysis_commit_row(analysis, commit)
                        writer.writerow(row)
                else:
                    # No commits, export fork info only
                    row = self._format_fork_analysis_row(analysis)
                    writer.writerow(row)
            else:
                # Export one row per fork
                row = self._format_fork_analysis_row(analysis)
                writer.writerow(row)

        return output.getvalue()

    def export_ranked_features(self, features: list[RankedFeature]) -> str:
        """Export ranked features to CSV format.

        Args:
            features: List of ranked features to export

        Returns:
            CSV formatted string
        """
        logger.info(f"Exporting {len(features)} ranked features to CSV format")

        output = io.StringIO()
        headers = self._generate_ranked_features_headers()

        writer = csv.DictWriter(output, fieldnames=headers, quoting=csv.QUOTE_MINIMAL)
        writer.writeheader()

        for feature in features:
            row = self._format_ranked_feature_row(feature)
            writer.writerow(row)

        return output.getvalue()

    def export_commits_with_explanations(
        self,
        commits: list[CommitWithExplanation],
        repository: Repository,
        fork: Fork | None = None,
    ) -> str:
        """Export commits with explanations to CSV format.

        Args:
            commits: List of commits with explanations to export
            repository: Repository context
            fork: Fork context (optional)

        Returns:
            CSV formatted string
        """
        logger.info(f"Exporting {len(commits)} commits with explanations to CSV format")

        output = io.StringIO()
        headers = self._generate_commits_explanations_headers()

        writer = csv.DictWriter(output, fieldnames=headers, quoting=csv.QUOTE_MINIMAL)
        writer.writeheader()

        for commit_with_explanation in commits:
            row = self._format_commit_explanation_row(
                commit_with_explanation, repository, fork
            )
            writer.writerow(row)

        return output.getvalue()

    def export_to_csv(
        self,
        data: (
            ForksPreview
            | list[ForkAnalysis]
            | list[RankedFeature]
            | list[CommitWithExplanation]
        ),
        output_file: str | TextIO | None = None,
        **kwargs,
    ) -> str:
        """Export data to CSV format with automatic type detection.

        Args:
            data: Data to export (various supported types)
            output_file: Optional file path or file object to write to
            **kwargs: Additional arguments for specific export types

        Returns:
            CSV formatted string

        Raises:
            ValueError: If data type is not supported
        """
        # Determine export method based on data type
        if isinstance(data, ForksPreview):
            csv_content = self.export_forks_preview(data)
        elif isinstance(data, list) and len(data) > 0:
            first_item = data[0]
            if isinstance(first_item, ForkAnalysis):
                csv_content = self.export_fork_analyses(data)
            elif isinstance(first_item, RankedFeature):
                csv_content = self.export_ranked_features(data)
            elif isinstance(first_item, CommitWithExplanation):
                repository = kwargs.get("repository")
                fork = kwargs.get("fork")
                if not repository:
                    raise ValueError(
                        "repository parameter required for CommitWithExplanation export"
                    )
                csv_content = self.export_commits_with_explanations(
                    data, repository, fork
                )
            else:
                raise ValueError(f"Unsupported data type: {type(first_item)}")
        elif isinstance(data, list) and len(data) == 0:
            # Empty list - create minimal CSV with just headers
            csv_content = "# No data to export\n"
        else:
            raise ValueError(f"Unsupported data type: {type(data)}")

        # Write to file if specified
        if output_file:
            if isinstance(output_file, str):
                with open(output_file, "w", newline="", encoding="utf-8") as f:
                    f.write(csv_content)
                logger.info(f"CSV exported to file: {output_file}")
            else:
                output_file.write(csv_content)
                logger.info("CSV exported to file object")

        return csv_content

    def _generate_forks_preview_headers(self) -> list[str]:
        """Generate CSV headers for forks preview export."""
        headers = ["fork_name", "owner", "stars", "commits_ahead", "activity_status"]

        if self.config.include_urls:
            headers.append("fork_url")

        if self.config.detail_mode:
            headers.extend(["last_push_date", "created_date", "updated_date"])

        if self.config.include_commits:
            headers.append("recent_commits")

        return headers

    def _generate_fork_analysis_headers(self) -> list[str]:
        """Generate CSV headers for fork analysis export."""
        headers = [
            "fork_name",
            "owner",
            "stars",
            "forks_count",
            "commits_ahead",
            "commits_behind",
            "is_active",
            "features_count",
        ]

        if self.config.include_urls:
            headers.extend(["fork_url", "owner_url"])

        if self.config.detail_mode:
            headers.extend(
                [
                    "language",
                    "description",
                    "last_activity",
                    "created_date",
                    "updated_date",
                    "pushed_date",
                    "size_kb",
                    "open_issues",
                    "is_archived",
                    "is_private",
                ]
            )

        if self.config.include_commits:
            headers.extend(
                [
                    "commit_sha",
                    "commit_message",
                    "commit_author",
                    "commit_date",
                    "files_changed",
                    "additions",
                    "deletions",
                ]
            )

            if self.config.include_urls:
                headers.append("commit_url")

        return headers

    def _generate_enhanced_fork_analysis_headers(self) -> list[str]:
        """Generate CSV headers for multi-row fork analysis export format.

        This method creates headers for the enhanced format where each commit
        gets its own row with separate columns for commit_date, commit_sha,
        and commit_description instead of a single recent_commits column.

        Returns:
            List of column header names for the enhanced multi-row format
        """
        # Start with essential fork metadata columns
        headers = [
            "fork_name",
            "owner",
            "stars",
            "forks_count",
            "commits_ahead",
            "commits_behind",
            "is_active",
            "features_count"
        ]

        # Add optional URL fields based on configuration
        if self.config.include_urls:
            headers.extend(["fork_url", "owner_url"])

        # Add detail mode fields based on configuration
        if self.config.detail_mode:
            headers.extend([
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
            ])

        # Add commit-specific columns (replaces recent_commits column)
        headers.extend([
            "commit_date",
            "commit_sha",
            "commit_description"
        ])

        # Add commit URL if URLs are enabled
        if self.config.include_urls:
            headers.append("commit_url")

        return headers

    def _generate_ranked_features_headers(self) -> list[str]:
        """Generate CSV headers for ranked features export."""
        headers = [
            "feature_id",
            "title",
            "category",
            "score",
            "description",
            "source_fork",
            "source_owner",
            "commits_count",
            "files_affected_count",
        ]

        if self.config.include_urls:
            headers.extend(["source_fork_url", "source_owner_url"])

        if self.config.detail_mode:
            headers.extend(
                ["ranking_factors", "similar_implementations_count", "files_affected"]
            )

        return headers

    def _generate_commits_explanations_headers(self) -> list[str]:
        """Generate CSV headers for commits with explanations export."""
        headers = [
            "commit_sha",
            "commit_message",
            "author",
            "commit_date",
            "files_changed",
            "additions",
            "deletions",
        ]

        if self.config.include_urls:
            headers.extend(["commit_url", "github_url"])

        if self.config.include_explanations:
            headers.extend(
                [
                    "category",
                    "impact_level",
                    "main_repo_value",
                    "what_changed",
                    "explanation",
                    "is_complex",
                ]
            )

        if self.config.detail_mode:
            headers.extend(
                [
                    "repository_name",
                    "fork_name",
                    "category_confidence",
                    "impact_reasoning",
                    "explanation_generated_at",
                ]
            )

        return headers

    def _format_fork_preview_row(self, fork: ForkPreviewItem) -> dict[str, Any]:
        """Format a fork preview item as a CSV row."""
        row = {
            "fork_name": fork.name,
            "owner": fork.owner,
            "stars": fork.stars,
            "commits_ahead": fork.commits_ahead,
            "activity_status": fork.activity_status,
        }

        if self.config.include_urls:
            row["fork_url"] = fork.fork_url

        if self.config.detail_mode:
            row["last_push_date"] = self._format_datetime(fork.last_push_date)
            # Note: ForkPreviewItem doesn't have created/updated dates
            row["created_date"] = ""
            row["updated_date"] = ""

        if self.config.include_commits:
            # Format commit data consistently with table display
            row["recent_commits"] = self._format_commit_data_for_csv(
                fork.recent_commits
            )

        return self._escape_row_values(row)

    def _format_fork_analysis_row(self, analysis: ForkAnalysis) -> dict[str, Any]:
        """Format a fork analysis as a CSV row."""
        fork = analysis.fork
        repo = fork.repository

        row = {
            "fork_name": repo.name,
            "owner": fork.owner.login,
            "stars": repo.stars,
            "forks_count": repo.forks_count,
            "commits_ahead": fork.commits_ahead,
            "commits_behind": fork.commits_behind,
            "is_active": fork.is_active,
            "features_count": len(analysis.features),
        }

        if self.config.include_urls:
            row["fork_url"] = repo.html_url
            row["owner_url"] = fork.owner.html_url

        if self.config.detail_mode:
            row.update(
                {
                    "language": repo.language or "",
                    "description": repo.description or "",
                    "last_activity": self._format_datetime(fork.last_activity),
                    "created_date": self._format_datetime(repo.created_at),
                    "updated_date": self._format_datetime(repo.updated_at),
                    "pushed_date": self._format_datetime(repo.pushed_at),
                    "size_kb": repo.size,
                    "open_issues": repo.open_issues_count,
                    "is_archived": repo.is_archived,
                    "is_private": repo.is_private,
                }
            )

        # Add empty commit fields if including commits but no specific commit
        if self.config.include_commits:
            row.update(
                {
                    "commit_sha": "",
                    "commit_message": "",
                    "commit_author": "",
                    "commit_date": "",
                    "files_changed": "",
                    "additions": "",
                    "deletions": "",
                }
            )

            if self.config.include_urls:
                row["commit_url"] = ""

        return self._escape_row_values(row)

    def _format_fork_analysis_commit_row(
        self, analysis: ForkAnalysis, commit: Commit
    ) -> dict[str, Any]:
        """Format a fork analysis with specific commit as a CSV row."""
        # Start with fork analysis row
        row = self._format_fork_analysis_row(analysis)

        # Override commit-specific fields
        if self.config.include_commits:
            row.update(
                {
                    "commit_sha": commit.sha,
                    "commit_message": commit.message,
                    "commit_author": commit.author.login,
                    "commit_date": self._format_datetime(commit.date),
                    "files_changed": len(commit.files_changed),
                    "additions": commit.additions,
                    "deletions": commit.deletions,
                }
            )

            if self.config.include_urls:
                repo_url = analysis.fork.repository.html_url
                row["commit_url"] = f"{repo_url}/commit/{commit.sha}"

        return self._escape_row_values(row)

    def _format_ranked_feature_row(self, feature: RankedFeature) -> dict[str, Any]:
        """Format a ranked feature as a CSV row."""
        feat = feature.feature
        source_repo = feat.source_fork.repository
        source_owner = feat.source_fork.owner

        row = {
            "feature_id": feat.id,
            "title": feat.title,
            "category": feat.category.value,
            "score": round(feature.score, 2),
            "description": feat.description,
            "source_fork": source_repo.full_name,
            "source_owner": source_owner.login,
            "commits_count": len(feat.commits),
            "files_affected_count": len(feat.files_affected),
        }

        if self.config.include_urls:
            row["source_fork_url"] = source_repo.html_url
            row["source_owner_url"] = source_owner.html_url

        if self.config.detail_mode:
            row.update(
                {
                    "ranking_factors": self._format_dict(feature.ranking_factors),
                    "similar_implementations_count": len(
                        feature.similar_implementations
                    ),
                    "files_affected": "; ".join(feat.files_affected),
                }
            )

        return self._escape_row_values(row)

    def _format_commit_explanation_row(
        self,
        commit_with_explanation: CommitWithExplanation,
        repository: Repository,
        fork: Fork | None = None,
    ) -> dict[str, Any]:
        """Format a commit with explanation as a CSV row."""
        commit = commit_with_explanation.commit
        explanation = commit_with_explanation.explanation

        row = {
            "commit_sha": commit.sha,
            "commit_message": commit.message,
            "author": commit.author.login,
            "commit_date": self._format_datetime(commit.date),
            "files_changed": len(commit.files_changed),
            "additions": commit.additions,
            "deletions": commit.deletions,
        }

        if self.config.include_urls:
            base_repo = fork.repository if fork else repository
            commit_url = f"{base_repo.html_url}/commit/{commit.sha}"
            row["commit_url"] = commit_url
            row["github_url"] = explanation.github_url if explanation else commit_url

        if self.config.include_explanations and explanation:
            row.update(
                {
                    "category": explanation.category.category_type.value,
                    "impact_level": explanation.impact_assessment.impact_level.value,
                    "main_repo_value": explanation.main_repo_value.value,
                    "what_changed": explanation.what_changed,
                    "explanation": explanation.explanation,
                    "is_complex": explanation.is_complex,
                }
            )
        elif self.config.include_explanations:
            # No explanation available
            row.update(
                {
                    "category": "",
                    "impact_level": "",
                    "main_repo_value": "",
                    "what_changed": "",
                    "explanation": commit_with_explanation.explanation_error
                    or "No explanation available",
                    "is_complex": "",
                }
            )

        if self.config.detail_mode:
            row.update(
                {
                    "repository_name": repository.full_name,
                    "fork_name": (
                        fork.repository.full_name if fork else repository.full_name
                    ),
                    "category_confidence": (
                        explanation.category.confidence if explanation else ""
                    ),
                    "impact_reasoning": (
                        explanation.impact_assessment.reasoning if explanation else ""
                    ),
                    "explanation_generated_at": (
                        self._format_datetime(explanation.generated_at)
                        if explanation
                        else ""
                    ),
                }
            )

        return self._escape_row_values(row)

    def _get_commits_for_export(self, analysis: ForkAnalysis) -> list[Commit]:
        """Get commits from fork analysis for export."""
        commits = []

        # Collect commits from features
        for feature in analysis.features:
            commits.extend(feature.commits)

        # Remove duplicates and limit
        seen_shas = set()
        unique_commits = []
        for commit in commits:
            if commit.sha not in seen_shas:
                seen_shas.add(commit.sha)
                unique_commits.append(commit)

        # Sort by date (newest first) and limit
        unique_commits.sort(key=lambda c: c.date, reverse=True)
        return unique_commits[: self.config.max_commits_per_fork]

    def _format_datetime(self, dt: datetime | None) -> str:
        """Format datetime for CSV output."""
        if dt is None:
            return ""
        return dt.strftime(self.config.date_format)

    def _format_dict(self, data: dict[str, Any]) -> str:
        """Format dictionary as string for CSV output."""
        if not data:
            return ""
        items = [f"{k}={v}" for k, v in data.items()]
        return "; ".join(items)

    def _format_commit_data_for_csv(self, commit_data: str | None) -> str:
        """Format commit data for CSV output with proper escaping.

        Args:
            commit_data: Raw commit data string or None

        Returns:
            Properly formatted and escaped commit data for CSV
        """
        if not commit_data:
            return ""

        # Handle commit data that may contain commas, quotes, and newlines
        formatted_data = commit_data

        # Replace newlines with spaces for better CSV readability
        formatted_data = formatted_data.replace("\n", " ").replace("\r", " ")

        # Remove extra whitespace
        formatted_data = " ".join(formatted_data.split())

        # The CSV writer will handle quote escaping automatically
        return formatted_data

    def _extract_base_fork_data(self, analysis: ForkAnalysis) -> dict[str, Any]:
        """Extract repository information that will be repeated across commit rows.

        Args:
            analysis: Fork analysis containing fork and repository data

        Returns:
            Dictionary containing base fork data for CSV export
        """
        fork = analysis.fork
        repo = fork.repository

        # Essential fork metadata (always included)
        base_data = {
            "fork_name": repo.name,
            "owner": fork.owner.login,
            "stars": repo.stars,
            "forks_count": repo.forks_count,
            "commits_ahead": fork.commits_ahead,
            "commits_behind": fork.commits_behind,
            "is_active": fork.is_active,
            "features_count": len(analysis.features),
        }

        # Add optional URL fields based on configuration
        if self.config.include_urls:
            base_data.update({
                "fork_url": repo.html_url,
                "owner_url": fork.owner.html_url,
            })

        # Add detail mode fields based on configuration
        if self.config.detail_mode:
            base_data.update({
                "language": repo.language or "",
                "description": repo.description or "",
                "last_activity": self._format_datetime(fork.last_activity),
                "created_date": self._format_datetime(repo.created_at),
                "updated_date": self._format_datetime(repo.updated_at),
                "pushed_date": self._format_datetime(repo.pushed_at),
                "size_kb": repo.size,
                "open_issues": repo.open_issues_count,
                "is_archived": repo.is_archived,
                "is_private": repo.is_private,
            })

        return base_data

    def _generate_fork_commit_rows(self, analysis: ForkAnalysis) -> list[dict[str, Any]]:
        """Generate multiple rows for a fork, one per commit.

        Args:
            analysis: Fork analysis containing fork and commit data

        Returns:
            List of dictionaries representing CSV rows, one per commit
        """
        base_fork_data = self._extract_base_fork_data(analysis)
        commits = self._get_commits_for_export(analysis)

        if not commits:
            # Create single row with empty commit columns
            return [self._create_empty_commit_row(base_fork_data)]

        rows = []
        for commit in commits:
            commit_row = self._create_commit_row(base_fork_data, commit)
            rows.append(commit_row)

        return rows

    def _create_commit_row(self, base_data: dict[str, Any], commit: Commit) -> dict[str, Any]:
        """Combine base fork data with individual commit information.

        Args:
            base_data: Base fork data dictionary
            commit: Commit object with commit information

        Returns:
            Dictionary representing a complete CSV row with fork and commit data
        """
        # Start with a copy of base fork data
        commit_row = base_data.copy()

        # Add commit-specific data
        commit_row.update({
            "commit_date": self._format_commit_date(commit.date),
            "commit_sha": self._format_commit_sha(commit.sha),
            "commit_description": self._escape_commit_message(commit.message)
        })

        return commit_row

    def _create_empty_commit_row(self, base_data: dict[str, Any]) -> dict[str, Any]:
        """Create a row for forks with no commits.

        Args:
            base_data: Base fork data dictionary

        Returns:
            Dictionary representing a CSV row with fork data and empty commit columns
        """
        # Start with a copy of base fork data
        empty_row = base_data.copy()

        # Add empty commit columns
        empty_row.update({
            "commit_date": "",
            "commit_sha": "",
            "commit_description": ""
        })

        return empty_row

    def _format_commit_date(self, date: datetime | None) -> str:
        """Format commit date using configurable date format (YYYY-MM-DD).

        Args:
            date: Commit date to format

        Returns:
            Formatted date string or empty string if date is None
        """
        if date is None:
            return ""
        return date.strftime(self.config.commit_date_format)

    def _format_commit_sha(self, sha: str) -> str:
        """Format commit SHA to use 7-character short SHA format.

        Args:
            sha: Full commit SHA

        Returns:
            7-character short SHA
        """
        return sha[:7] if sha else ""

    def _escape_commit_message(self, message: str) -> str:
        """Properly handle CSV special characters in commit messages.

        Args:
            message: Commit message to escape

        Returns:
            Escaped commit message suitable for CSV output
        """
        if not message:
            return ""

        # Remove or replace newlines and carriage returns
        cleaned_message = message.replace("\n", " ").replace("\r", " ")

        # Remove extra whitespace
        cleaned_message = " ".join(cleaned_message.split())

        # The CSV writer will handle quote escaping automatically
        return cleaned_message

    def _escape_row_values(self, row: dict[str, Any]) -> dict[str, Any]:
        """Escape special characters in row values for CSV output."""
        escaped_row = {}

        for key, value in row.items():
            if isinstance(value, str) and self.config.escape_newlines:
                # Replace newlines with literal \n for CSV compatibility
                value = value.replace("\n", "\\n").replace("\r", "\\r")

            escaped_row[key] = value

        return escaped_row

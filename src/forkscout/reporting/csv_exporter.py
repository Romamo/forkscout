"""CSV export functionality for fork analysis results."""

import csv
import io
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, TextIO

from forkscout.models.analysis import (
    CommitWithExplanation,
    ForkAnalysis,
    ForkPreviewItem,
    ForksPreview,
    RankedFeature,
)
from forkscout.models.github import Commit, Fork, Repository

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
        """Export fork analysis results to CSV format using multi-row commit format.

        This method uses the enhanced multi-row format where each commit gets its own row
        with separate columns for commit_date, commit_sha, and commit_description.
        Repository information is repeated on each commit row for consistency.

        Handles errors gracefully to ensure export continues even when individual
        forks fail to process.

        Args:
            analyses: List of fork analysis results to export

        Returns:
            CSV formatted string with multi-row commit format
        """
        logger.info(f"Exporting {len(analyses)} fork analyses to CSV format (multi-row)")

        output = io.StringIO()
        headers = self._generate_enhanced_fork_analysis_headers()

        writer = csv.DictWriter(output, fieldnames=headers, quoting=csv.QUOTE_MINIMAL)
        writer.writeheader()

        successful_exports = 0
        failed_exports = 0

        for analysis in analyses:
            try:
                # Generate multiple rows for this fork (one per commit)
                commit_rows = self._generate_fork_commit_rows(analysis)
                for row in commit_rows:
                    try:
                        writer.writerow(row)
                    except Exception as e:
                        logger.warning(f"Failed to write CSV row: {e}")
                        # Continue with next row
                        continue
                successful_exports += 1
            except Exception as e:
                failed_exports += 1
                fork_name = getattr(analysis.fork.repository, 'full_name', 'unknown')
                logger.error(f"Failed to export fork analysis for {fork_name}: {e}")
                # Continue with next analysis
                continue

        if failed_exports > 0:
            logger.warning(f"Export completed with {failed_exports} failures out of {len(analyses)} total analyses")
        else:
            logger.info(f"Successfully exported {successful_exports} fork analyses")

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
        # New column structure: Fork URL first (always present), then Stars, Forks, Commits Ahead, Commits Behind
        headers = ["Fork URL", "Stars", "Forks", "Commits Ahead", "Commits Behind"]

        if self.config.detail_mode:
            headers.extend(["Last Push Date", "Created Date", "Updated Date"])

        if self.config.include_commits:
            headers.append("Recent Commits")

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
        # New column structure: Fork URL (always present), Stars, Forks, Commits Ahead, Commits Behind
        row = {
            "Fork URL": fork.fork_url if self.config.include_urls else "",
            "Stars": fork.stars,
            "Forks": fork.forks_count,
            "Commits Ahead": fork.commits_ahead,
            "Commits Behind": fork.commits_behind,
        }

        if self.config.detail_mode:
            row["Last Push Date"] = self._format_datetime(fork.last_push_date)
            # Note: ForkPreviewItem doesn't have created/updated dates
            row["Created Date"] = ""
            row["Updated Date"] = ""

        if self.config.include_commits:
            # Format commit data consistently with table display
            row["Recent Commits"] = self._format_commit_data_for_csv(
                fork.recent_commits
            )

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

        Ensures export continues when individual commits fail to process by handling
        errors gracefully and continuing with remaining commits.

        Args:
            analysis: Fork analysis containing fork and commit data

        Returns:
            List of dictionaries representing CSV rows, one per commit
        """
        try:
            base_fork_data = self._extract_base_fork_data(analysis)
        except Exception as e:
            logger.error(f"Failed to extract base fork data for {analysis.fork.repository.full_name}: {e}")
            # Return minimal row with empty data to ensure export continues
            return [self._create_minimal_empty_row()]

        commits = self._get_commits_for_export(analysis)

        if not commits:
            # Create single row with empty commit columns
            return [self._create_empty_commit_row(base_fork_data)]

        rows = []
        successful_commits = 0
        
        for commit in commits:
            try:
                commit_row = self._create_commit_row(base_fork_data, commit, analysis)
                rows.append(commit_row)
                successful_commits += 1
            except Exception as e:
                logger.warning(f"Failed to process commit {getattr(commit, 'sha', 'unknown')}: {e}")
                # Continue processing remaining commits
                continue

        # If no commits were successfully processed, return empty commit row
        if not rows:
            logger.warning(f"No commits could be processed for fork {analysis.fork.repository.full_name}")
            return [self._create_empty_commit_row(base_fork_data)]

        if successful_commits < len(commits):
            logger.info(f"Processed {successful_commits}/{len(commits)} commits for fork {analysis.fork.repository.full_name}")

        return rows

    def _create_commit_row(self, base_data: dict[str, Any], commit: Commit, analysis: ForkAnalysis) -> dict[str, Any]:
        """Combine base fork data with individual commit information.

        Handles missing or invalid commit data gracefully to ensure export continues.

        Args:
            base_data: Base fork data dictionary
            commit: Commit object with commit information
            analysis: Fork analysis for generating commit URL

        Returns:
            Dictionary representing a complete CSV row with fork and commit data
        """
        # Start with a copy of base fork data
        commit_row = base_data.copy()

        try:
            # Add commit-specific data with error handling
            commit_row.update({
                "commit_date": self._format_commit_date(getattr(commit, 'date', None)),
                "commit_sha": self._format_commit_sha(getattr(commit, 'sha', None)),
                "commit_description": self._escape_commit_message(getattr(commit, 'message', None))
            })

            # Add commit URL if URLs are enabled and we have valid data
            if self.config.include_urls:
                try:
                    repo_url = analysis.fork.repository.html_url
                    commit_sha = getattr(commit, 'sha', '')
                    if repo_url and commit_sha:
                        commit_row["commit_url"] = f"{repo_url}/commit/{commit_sha}"
                    else:
                        commit_row["commit_url"] = ""
                except (AttributeError, TypeError) as e:
                    logger.warning(f"Failed to generate commit URL: {e}")
                    commit_row["commit_url"] = ""

        except Exception as e:
            logger.warning(f"Error processing commit data: {e}")
            # Ensure we still have the commit columns with empty values
            commit_row.update({
                "commit_date": "",
                "commit_sha": "",
                "commit_description": ""
            })
            if self.config.include_urls:
                commit_row["commit_url"] = ""

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

        # Add empty commit URL if URLs are enabled
        if self.config.include_urls:
            empty_row["commit_url"] = ""

        return empty_row

    def _create_minimal_empty_row(self) -> dict[str, Any]:
        """Create a minimal empty row when fork data extraction fails.

        Returns:
            Dictionary with minimal structure and empty values for all columns
        """
        # Create minimal row with empty values for all expected columns
        headers = self._generate_enhanced_fork_analysis_headers()
        return {header: "" for header in headers}

    def _format_commit_date(self, date: datetime | None) -> str:
        """Format commit date using configurable date format (YYYY-MM-DD).

        Handles missing or invalid commit dates gracefully by returning empty values.

        Args:
            date: Commit date to format

        Returns:
            Formatted date string or empty string if date is None or invalid
        """
        if date is None:
            return ""
        
        try:
            return date.strftime(self.config.commit_date_format)
        except (ValueError, AttributeError, TypeError) as e:
            logger.warning(f"Failed to format commit date {date}: {e}")
            return ""

    def _format_commit_sha(self, sha: str | None) -> str:
        """Format commit SHA to use 7-character short SHA format.

        Handles malformed commit SHAs gracefully by returning empty values.

        Args:
            sha: Full commit SHA or None

        Returns:
            7-character short SHA or empty string if SHA is invalid
        """
        if not sha:
            return ""
        
        try:
            # Ensure SHA is a string and has reasonable length
            if not isinstance(sha, str):
                logger.warning(f"Invalid commit SHA type: {type(sha)}")
                return ""
            
            # Handle very short SHAs gracefully
            if len(sha) < 7:
                logger.warning(f"Commit SHA too short: {sha}")
                return sha  # Return what we have
            
            return sha[:7]
        except (AttributeError, TypeError) as e:
            logger.warning(f"Failed to format commit SHA {sha}: {e}")
            return ""

    def _escape_commit_message(self, message: str | None) -> str:
        """Properly handle CSV special characters in commit messages.

        Handles missing or malformed commit messages gracefully and ensures proper
        escaping of special characters without truncation.

        Args:
            message: Commit message to escape or None

        Returns:
            Escaped commit message suitable for CSV output or empty string if invalid
        """
        if not message:
            return ""

        try:
            # Ensure message is a string
            if not isinstance(message, str):
                logger.warning(f"Invalid commit message type: {type(message)}")
                return str(message) if message is not None else ""

            # Handle very long commit messages without truncation
            # Always clean them up for CSV compatibility regardless of escape_newlines setting
            # since commit messages should always be CSV-safe
            cleaned_message = self._clean_text_for_csv(message)

            return cleaned_message
        except (AttributeError, TypeError) as e:
            logger.warning(f"Failed to escape commit message: {e}")
            return ""

    def _clean_text_for_csv(self, text: str) -> str:
        """Clean text for CSV output by handling special characters properly.

        This method handles newlines, carriage returns, and other special characters
        while preserving the full content without truncation.

        Args:
            text: Text to clean for CSV output

        Returns:
            Cleaned text suitable for CSV output
        """
        if not text:
            return ""

        # Replace newlines and carriage returns with spaces
        # This preserves readability while making it CSV-safe
        cleaned_text = text.replace("\n", " ").replace("\r", " ")

        # Replace other problematic whitespace characters
        cleaned_text = cleaned_text.replace("\t", " ")  # Replace tabs with spaces
        cleaned_text = cleaned_text.replace("\v", " ")  # Replace vertical tabs
        cleaned_text = cleaned_text.replace("\f", " ")  # Replace form feeds

        # Normalize multiple spaces to single spaces
        cleaned_text = " ".join(cleaned_text.split())

        # Handle other special characters that might cause issues
        # Remove or replace control characters (except common ones already handled)
        cleaned_text = "".join(char for char in cleaned_text if ord(char) >= 32 or char in [" "])

        # The CSV writer will automatically handle quotes and commas by quoting the field
        # No need to manually escape them as the csv module handles this correctly
        
        return cleaned_text

    def _escape_row_values(self, row: dict[str, Any]) -> dict[str, Any]:
        """Escape special characters in row values for CSV output.
        
        Applies text cleaning based on configuration settings to ensure
        proper CSV compatibility while respecting user preferences.
        
        Args:
            row: Dictionary representing a CSV row
            
        Returns:
            Dictionary with escaped values suitable for CSV output
        """
        escaped_row = {}

        for key, value in row.items():
            if isinstance(value, str):
                if self.config.escape_newlines:
                    # Use literal escaping for backward compatibility when enabled
                    escaped_value = value.replace("\n", "\\n").replace("\r", "\\r")
                else:
                    # When escape_newlines is False, preserve original behavior
                    # but still apply basic cleaning for CSV safety
                    escaped_value = value
                escaped_row[key] = escaped_value
            else:
                # Non-string values pass through unchanged
                escaped_row[key] = value

        return escaped_row

    def validate_csv_compatibility(self, csv_content: str) -> dict[str, Any]:
        """Validate CSV content for compatibility with major spreadsheet applications.
        
        This method checks the CSV content for common issues that might cause
        problems when importing into Excel, Google Sheets, or other applications.
        
        Args:
            csv_content: The CSV content string to validate
            
        Returns:
            Dictionary containing validation results and statistics
        """
        validation_results = {
            "is_valid": True,
            "issues": [],
            "statistics": {
                "total_rows": 0,
                "total_columns": 0,
                "max_field_length": 0,
                "fields_with_quotes": 0,
                "fields_with_commas": 0,
                "fields_with_newlines": 0,
            }
        }

        try:
            # Parse the CSV to check for structural issues
            reader = csv.reader(io.StringIO(csv_content))
            rows = list(reader)
            
            if not rows:
                validation_results["issues"].append("CSV is empty")
                validation_results["is_valid"] = False
                return validation_results
            
            validation_results["statistics"]["total_rows"] = len(rows)
            validation_results["statistics"]["total_columns"] = len(rows[0]) if rows else 0
            
            # Check each field for potential issues
            for row_idx, row in enumerate(rows):
                for field_idx, field in enumerate(row):
                    field_length = len(field)
                    validation_results["statistics"]["max_field_length"] = max(
                        validation_results["statistics"]["max_field_length"], 
                        field_length
                    )
                    
                    # Check for various special characters
                    if '"' in field:
                        validation_results["statistics"]["fields_with_quotes"] += 1
                    if ',' in field:
                        validation_results["statistics"]["fields_with_commas"] += 1
                    if '\n' in field or '\r' in field:
                        validation_results["statistics"]["fields_with_newlines"] += 1
                        validation_results["issues"].append(
                            f"Row {row_idx + 1}, Column {field_idx + 1}: Contains unescaped newlines"
                        )
                    
                    # Check for very long fields that might cause issues
                    if field_length > 32767:  # Excel's cell limit
                        validation_results["issues"].append(
                            f"Row {row_idx + 1}, Column {field_idx + 1}: Field exceeds Excel's 32,767 character limit"
                        )
                    
                    # Check for control characters that might cause issues
                    if any(ord(char) < 32 and char not in ['\t'] for char in field):
                        validation_results["issues"].append(
                            f"Row {row_idx + 1}, Column {field_idx + 1}: Contains control characters"
                        )
            
            # Check for inconsistent column counts
            column_counts = [len(row) for row in rows]
            if len(set(column_counts)) > 1:
                validation_results["issues"].append(
                    f"Inconsistent column counts: {set(column_counts)}"
                )
                validation_results["is_valid"] = False
            
        except csv.Error as e:
            validation_results["issues"].append(f"CSV parsing error: {e}")
            validation_results["is_valid"] = False
        except Exception as e:
            validation_results["issues"].append(f"Validation error: {e}")
            validation_results["is_valid"] = False
        
        # Set overall validity
        if validation_results["issues"]:
            validation_results["is_valid"] = False
        
        return validation_results
    def export_simple_forks_with_commits(self, fork_data_list: list[dict]) -> str:
        """Export simple fork data with commits in multi-row format using new column structure.
        
        This method creates a multi-row CSV format where each commit gets its own row,
        using the new column naming and structure from the CSV column restructure.
        
        Args:
            fork_data_list: List of dictionaries containing fork data and commits
            
        Returns:
            CSV formatted string with multi-row commit format and new column structure
        """
        logger.info(f"Exporting {len(fork_data_list)} forks to multi-row CSV format")
        
        output = io.StringIO()
        
        # Use new column structure: Fork URL first, proper title case, removed unnecessary columns
        headers = [
            "Fork URL",
            "Stars",
            "Forks", 
            "Commits Ahead",
            "Commits Behind",
            "Last Push Date",
            "Created Date",
            "Updated Date",
            "Commit Date",
            "Commit SHA", 
            "Commit Description"
        ]
        
        writer = csv.DictWriter(output, fieldnames=headers, quoting=csv.QUOTE_MINIMAL)
        writer.writeheader()
        
        for fork_data in fork_data_list:
            try:
                commits = fork_data.get('commits', [])
                
                if not commits:
                    # Create single row with empty commit columns using new structure
                    row = {
                        'Fork URL': fork_data.get('fork_url', ''),
                        'Stars': fork_data.get('stars', 0),
                        'Forks': fork_data.get('forks_count', 0),
                        'Commits Ahead': self._extract_commits_ahead(fork_data.get('commits_ahead', '')),
                        'Commits Behind': self._extract_commits_behind(fork_data.get('commits_ahead', '')),
                        'Last Push Date': fork_data.get('last_push_date', ''),
                        'Created Date': fork_data.get('created_date', ''),
                        'Updated Date': fork_data.get('updated_date', ''),
                        'Commit Date': '',
                        'Commit SHA': '',
                        'Commit Description': ''
                    }
                    writer.writerow(row)
                else:
                    # Create one row per commit using new structure
                    for commit in commits:
                        row = {
                            'Fork URL': fork_data.get('fork_url', ''),
                            'Stars': fork_data.get('stars', 0),
                            'Forks': fork_data.get('forks_count', 0),
                            'Commits Ahead': self._extract_commits_ahead(fork_data.get('commits_ahead', '')),
                            'Commits Behind': self._extract_commits_behind(fork_data.get('commits_ahead', '')),
                            'Last Push Date': fork_data.get('last_push_date', ''),
                            'Created Date': fork_data.get('created_date', ''),
                            'Updated Date': fork_data.get('updated_date', ''),
                            'Commit Date': commit.get('date', ''),
                            'Commit SHA': commit.get('sha', ''),
                            'Commit Description': commit.get('message', '')
                        }
                        writer.writerow(row)
                        
            except Exception as e:
                logger.error(f"Failed to export fork {fork_data.get('fork_name', 'unknown')}: {e}")
                continue
        
        return output.getvalue()

    def _extract_commits_ahead(self, commits_ahead_str: str) -> str:
        """Extract commits ahead count from combined format like '+5 -2' or '+5'."""
        if not commits_ahead_str:
            return ""
        
        # Handle formats like "+5 -2", "+5", "-2", or just "5"
        commits_ahead_str = str(commits_ahead_str).strip()
        
        if '+' in commits_ahead_str:
            # Extract the number after '+'
            parts = commits_ahead_str.split()
            for part in parts:
                if part.startswith('+'):
                    return part[1:]  # Remove the '+' sign
        elif commits_ahead_str.isdigit():
            return commits_ahead_str
        
        return ""

    def _extract_commits_behind(self, commits_ahead_str: str) -> str:
        """Extract commits behind count from combined format like '+5 -2' or '-2'."""
        if not commits_ahead_str:
            return ""
        
        # Handle formats like "+5 -2", "+5", "-2"
        commits_ahead_str = str(commits_ahead_str).strip()
        
        if '-' in commits_ahead_str:
            # Extract the number after '-'
            parts = commits_ahead_str.split()
            for part in parts:
                if part.startswith('-'):
                    return part[1:]  # Remove the '-' sign
        
        return ""
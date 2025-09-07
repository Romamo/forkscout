"""Validation handler for graceful error handling during data processing."""

import logging
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from .github import Repository

logger = logging.getLogger(__name__)


class ValidationSummary(BaseModel):
    """Summary of validation results during processing."""

    processed: int = Field(description="Number of successfully processed items")
    skipped: int = Field(description="Number of items skipped due to validation errors")
    errors: list[dict[str, Any]] = Field(description="List of validation errors encountered")

    def has_errors(self) -> bool:
        """Check if there were any validation errors."""
        return self.skipped > 0

    def get_error_summary(self) -> str:
        """Get a human-readable summary of validation errors."""
        if not self.has_errors():
            return "No validation errors"
        return f"{self.skipped} items skipped due to validation errors"


class ValidationHandler:
    """Handles validation errors gracefully during data processing."""

    def __init__(self) -> None:
        """Initialize the validation handler."""
        self.validation_errors: list[dict[str, Any]] = []
        self.processed_count: int = 0
        self.skipped_count: int = 0

    def safe_create_repository(self, data: dict[str, Any]) -> Repository | None:
        """
        Safely create Repository with error handling.

        Args:
            data: Dictionary containing repository data from GitHub API

        Returns:
            Repository instance if successful, None if validation failed
        """
        try:
            return Repository.from_github_api(data)
        except ValidationError as e:
            # Record the validation error for reporting
            error_record = {
                "repository": data.get("full_name", "unknown"),
                "error": str(e),
                "data": data
            }
            self.validation_errors.append(error_record)
            self.skipped_count += 1

            # Log the validation error for debugging
            repo_name = data.get("full_name", "unknown")
            logger.warning(
                f"Validation error for repository {repo_name}: {e}",
                extra={
                    "repository": repo_name,
                    "validation_error": str(e),
                    "error_type": type(e).__name__
                }
            )

            return None
        except Exception as e:
            # Handle any other unexpected errors during repository creation
            error_record = {
                "repository": data.get("full_name", "unknown"),
                "error": f"Unexpected error: {e!s}",
                "data": data
            }
            self.validation_errors.append(error_record)
            self.skipped_count += 1

            # Log the unexpected error
            repo_name = data.get("full_name", "unknown")
            logger.error(
                f"Unexpected error creating repository {repo_name}: {e}",
                extra={
                    "repository": repo_name,
                    "error": str(e),
                    "error_type": type(e).__name__
                },
                exc_info=True
            )

            return None

    def get_summary(self) -> ValidationSummary:
        """
        Get processing summary.

        Returns:
            ValidationSummary with processing statistics and error details
        """
        return ValidationSummary(
            processed=self.processed_count,
            skipped=self.skipped_count,
            errors=self.validation_errors.copy()  # Return a copy to prevent external modification
        )

    def reset(self) -> None:
        """Reset the handler state for reuse."""
        self.validation_errors.clear()
        self.processed_count = 0
        self.skipped_count = 0

    def log_summary(self, max_errors_to_log: int = 5) -> None:
        """
        Log a summary of validation results.

        Args:
            max_errors_to_log: Maximum number of individual errors to log in detail
        """
        summary = self.get_summary()

        if summary.processed > 0:
            logger.info(f"Successfully processed {summary.processed} repositories")

        if summary.has_errors():
            logger.warning(f"Skipped {summary.skipped} repositories due to validation errors")

            # Log first few errors in detail
            errors_to_log = min(len(summary.errors), max_errors_to_log)
            for i, error in enumerate(summary.errors[:errors_to_log]):
                logger.warning(
                    f"Validation error {i+1}: {error['repository']} - {error['error']}"
                )

            # If there are more errors, log a summary
            if len(summary.errors) > max_errors_to_log:
                remaining = len(summary.errors) - max_errors_to_log
                logger.warning(f"... and {remaining} more validation errors")
        else:
            logger.info("No validation errors encountered")

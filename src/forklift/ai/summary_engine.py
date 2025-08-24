"""AI commit summary engine with prompt generation and batch processing."""

import asyncio
import logging
import time
from collections.abc import Callable

from forklift.ai.client import OpenAIClient
from forklift.ai.error_handler import OpenAIErrorHandler
from forklift.models.ai_summary import (
    AISummary,
    AISummaryConfig,
    AIUsageStats,
    AIUsageTracker,
)
from forklift.models.github import Commit, Repository

logger = logging.getLogger(__name__)


class AICommitSummaryEngine:
    """Orchestrates AI-powered commit summary generation workflow."""

    def __init__(
        self,
        openai_client: OpenAIClient,
        config: AISummaryConfig | None = None,
        error_handler: OpenAIErrorHandler | None = None
    ):
        """Initialize AI commit summary engine.

        Args:
            openai_client: OpenAI client for API calls
            config: AI summary configuration (optional)
            error_handler: Error handler for API errors (optional)
        """
        self.openai_client = openai_client
        self.config = config or AISummaryConfig()
        self.error_handler = error_handler or OpenAIErrorHandler(
            max_retries=self.config.retry_attempts
        )
        self.usage_tracker = AIUsageTracker(config=self.config)

    def create_summary_prompt(self, commit_message: str, diff_text: str) -> str:
        """Create concise prompt for commit analysis.

        Args:
            commit_message: The commit message
            diff_text: The diff content (may be truncated)

        Returns:
            Formatted prompt string for OpenAI API
        """
        # Truncate diff if it's too long
        truncated_diff = self.truncate_diff_for_tokens(diff_text)

        if self.config.compact_mode:
            # Ultra-compact prompt for minimal output
            prompt = f"""Brief summary: {commit_message}

{truncated_diff}

One sentence: what changed and why."""
        else:
            # Standard prompt
            prompt = f"""Summarize this commit: what changed, why, impact

Commit: {commit_message}

Diff:
{truncated_diff}"""

        return prompt

    def truncate_diff_for_tokens(self, diff_text: str, max_chars: int | None = None) -> str:
        """Truncate diff to stay within OpenAI token limits.

        Args:
            diff_text: Original diff text
            max_chars: Maximum characters allowed (uses config default if None)

        Returns:
            Truncated diff text with indicator if truncated
        """
        max_chars = max_chars or self.config.max_diff_chars

        if len(diff_text) <= max_chars:
            return diff_text

        # Truncate and add indicator
        truncated = diff_text[:max_chars - 50]  # Leave room for truncation message
        return truncated + "\n\n[... diff truncated for length ...]"

    async def generate_commit_summary(
        self,
        commit: Commit,
        diff_text: str,
        repository: Repository | None = None
    ) -> AISummary:
        """Generate AI summary for a single commit.

        Args:
            commit: Commit object to summarize
            diff_text: Diff content for the commit
            repository: Repository context (optional)

        Returns:
            AISummary object with generated summary or error information

        Raises:
            Exception: If summary generation fails and error is not recoverable
        """
        start_time = time.time()

        try:
            # Create prompt
            prompt = self.create_summary_prompt(commit.message, diff_text)

            # Check cost limits before making request
            estimated_cost = self.config.estimate_request_cost(prompt, self.config.max_tokens)

            if not self.usage_tracker.check_session_cost_limit():
                error_msg = f"Session cost limit exceeded (${self.config.max_cost_per_session_usd:.2f})"
                logger.warning(f"Skipping commit {commit.sha[:8]}: {error_msg}")

                self.usage_tracker.record_request(
                    success=False,
                    processing_time_ms=(time.time() - start_time) * 1000,
                    error=error_msg
                )

                return AISummary(
                    commit_sha=commit.sha,
                    summary_text="",
                    processing_time_ms=(time.time() - start_time) * 1000,
                    error=error_msg
                )

            if not self.usage_tracker.check_request_cost_limit(estimated_cost):
                error_msg = f"Request cost limit exceeded (${self.config.max_cost_per_request_usd:.2f})"
                logger.warning(f"Skipping commit {commit.sha[:8]}: {error_msg}")

                self.usage_tracker.record_request(
                    success=False,
                    processing_time_ms=(time.time() - start_time) * 1000,
                    error=error_msg
                )

                return AISummary(
                    commit_sha=commit.sha,
                    summary_text="",
                    processing_time_ms=(time.time() - start_time) * 1000,
                    error=error_msg
                )

            # Warn about cost if threshold reached
            if self.usage_tracker.should_warn_about_cost():
                logger.warning(
                    f"Cost warning: ${self.usage_tracker.stats.total_cost_usd:.4f} spent "
                    f"(threshold: ${self.config.cost_warning_threshold_usd:.2f})"
                )

            # Prepare messages for OpenAI API
            messages = [
                {"role": "user", "content": prompt}
            ]

            if self.config.usage_logging_enabled:
                logger.debug(
                    f"Generating AI summary for commit {commit.sha[:8]} "
                    f"(estimated cost: ${estimated_cost:.4f})"
                )

            # Adjust max tokens for compact mode
            max_tokens = min(100, self.config.max_tokens) if self.config.compact_mode else self.config.max_tokens
            
            # Make API call with retry logic
            response = await self.openai_client.create_completion_with_retry(
                messages=messages,
                max_tokens=max_tokens,
                temperature=self.config.temperature,
                model=self.config.model
            )

            processing_time = (time.time() - start_time) * 1000

            # Extract token usage from response
            usage = response.usage
            input_tokens = usage.get("prompt_tokens", 0)
            output_tokens = usage.get("completion_tokens", 0)
            total_tokens = usage.get("total_tokens", input_tokens + output_tokens)

            # Record usage statistics
            self.usage_tracker.record_request(
                success=True,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                processing_time_ms=processing_time
            )

            # Log performance metrics if enabled
            if self.config.performance_logging_enabled:
                actual_cost = self.config.calculate_total_cost(input_tokens, output_tokens)
                logger.info(
                    f"Generated AI summary for commit {commit.sha[:8]} - "
                    f"Time: {processing_time:.0f}ms, "
                    f"Tokens: {total_tokens} ({input_tokens} in, {output_tokens} out), "
                    f"Cost: ${actual_cost:.4f}"
                )

            return AISummary(
                commit_sha=commit.sha,
                summary_text=response.text.strip(),
                model_used=response.model,
                tokens_used=total_tokens,
                processing_time_ms=processing_time
            )

        except Exception as e:
            processing_time = (time.time() - start_time) * 1000

            # Log error with context
            self.error_handler.log_error(
                e,
                commit_sha=commit.sha,
                context="generate_commit_summary"
            )

            # Record failed request
            self.usage_tracker.record_request(
                success=False,
                processing_time_ms=processing_time,
                error=str(e)
            )

            # Create error summary
            error_message = self.error_handler.get_user_friendly_message(e)

            return AISummary(
                commit_sha=commit.sha,
                summary_text="",
                processing_time_ms=processing_time,
                error=error_message
            )

    async def generate_batch_summaries(
        self,
        commits_with_diffs: list[tuple[Commit, str]],
        repository: Repository | None = None,
        progress_callback: Callable | None = None
    ) -> list[AISummary]:
        """Generate AI summaries for multiple commits with rate limit management.

        Args:
            commits_with_diffs: List of (commit, diff_text) tuples
            repository: Repository context (optional)
            progress_callback: Callback function for progress updates (optional)

        Returns:
            List of AISummary objects in the same order as input
        """
        if not commits_with_diffs:
            return []

        logger.info(f"Generating AI summaries for {len(commits_with_diffs)} commits")

        summaries = []
        batch_size = self.config.batch_size

        # Process commits in batches to manage rate limits
        for i in range(0, len(commits_with_diffs), batch_size):
            batch = commits_with_diffs[i:i + batch_size]
            batch_number = (i // batch_size) + 1
            total_batches = (len(commits_with_diffs) + batch_size - 1) // batch_size

            logger.debug(f"Processing batch {batch_number}/{total_batches} ({len(batch)} commits)")

            # Process batch concurrently
            batch_tasks = [
                self.generate_commit_summary(commit, diff_text, repository)
                for commit, diff_text in batch
            ]

            try:
                batch_summaries = await asyncio.gather(*batch_tasks, return_exceptions=True)

                # Handle any exceptions in batch results
                for j, result in enumerate(batch_summaries):
                    if isinstance(result, Exception):
                        commit, _ = batch[j]
                        logger.error(f"Failed to generate summary for commit {commit.sha[:8]}: {result}")

                        # Create error summary
                        error_summary = AISummary(
                            commit_sha=commit.sha,
                            summary_text="",
                            error=str(result)
                        )
                        summaries.append(error_summary)
                    else:
                        summaries.append(result)

                # Update progress
                if progress_callback:
                    progress = len(summaries) / len(commits_with_diffs)
                    progress_callback(progress, len(summaries), len(commits_with_diffs))

                # Add delay between batches to respect rate limits
                if i + batch_size < len(commits_with_diffs):
                    delay = 1.0  # 1 second delay between batches
                    logger.debug(f"Waiting {delay}s before next batch")
                    await asyncio.sleep(delay)

            except Exception as e:
                logger.error(f"Batch processing failed: {e}")

                # Create error summaries for the entire batch
                for commit, _ in batch:
                    error_summary = AISummary(
                        commit_sha=commit.sha,
                        summary_text="",
                        error=f"Batch processing failed: {e}"
                    )
                    summaries.append(error_summary)

        logger.info(f"Completed AI summary generation for {len(summaries)} commits")

        # Log final usage summary
        self.log_usage_summary()

        return summaries



    def get_usage_stats(self) -> AIUsageStats:
        """Get current usage statistics.

        Returns:
            AIUsageStats object with current statistics
        """
        return self.usage_tracker.stats

    def get_usage_tracker(self) -> AIUsageTracker:
        """Get the usage tracker instance.

        Returns:
            AIUsageTracker object with current statistics and configuration
        """
        return self.usage_tracker

    def reset_usage_stats(self) -> None:
        """Reset usage statistics."""
        self.usage_tracker = AIUsageTracker(config=self.config)

    def get_usage_report(self) -> dict:
        """Get comprehensive usage report.

        Returns:
            Dictionary with detailed usage statistics and cost information
        """
        return self.usage_tracker.get_usage_report()

    def log_usage_summary(self) -> None:
        """Log a summary of current usage statistics."""
        if not self.config.usage_logging_enabled:
            return

        report = self.get_usage_report()
        session = report["session_summary"]
        tokens = report["token_usage"]
        costs = report["cost_breakdown"]

        logger.info(
            f"AI Usage Summary - "
            f"Requests: {session['total_requests']} "
            f"(Success: {session['success_rate_percent']:.1f}%), "
            f"Tokens: {tokens['total_tokens']}, "
            f"Cost: ${costs['total_cost_usd']:.4f}, "
            f"Duration: {session['duration_minutes']:.1f}min"
        )

    def estimate_batch_cost(self, commits_with_diffs: list[tuple[Commit, str]]) -> float:
        """Estimate cost for batch processing.

        Args:
            commits_with_diffs: List of (commit, diff_text) tuples

        Returns:
            Estimated cost in USD
        """
        if not commits_with_diffs:
            return 0.0

        total_chars = 0
        for commit, diff_text in commits_with_diffs:
            prompt = self.create_summary_prompt(commit.message, diff_text)
            total_chars += len(prompt)

        # Rough token estimation (4 chars per token)
        estimated_input_tokens = total_chars // 4

        # Estimate output tokens (assume average response length)
        estimated_output_tokens = len(commits_with_diffs) * (self.config.max_tokens // 2)

        # Cost calculation for GPT-4o-mini
        input_cost = estimated_input_tokens * (0.00015 / 1000)  # $0.00015 per 1K input tokens
        output_cost = estimated_output_tokens * (0.0006 / 1000)  # $0.0006 per 1K output tokens

        return input_cost + output_cost

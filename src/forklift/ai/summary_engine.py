"""AI commit summary engine with prompt generation and batch processing."""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Tuple

from forklift.ai.client import OpenAIClient
from forklift.ai.error_handler import OpenAIErrorHandler
from forklift.models.ai_summary import AISummary, AISummaryConfig, AIUsageStats
from forklift.models.github import Commit, Repository

logger = logging.getLogger(__name__)


class AICommitSummaryEngine:
    """Orchestrates AI-powered commit summary generation workflow."""

    def __init__(
        self,
        openai_client: OpenAIClient,
        config: Optional[AISummaryConfig] = None,
        error_handler: Optional[OpenAIErrorHandler] = None
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
        self.usage_stats = AIUsageStats()

    def create_summary_prompt(self, commit_message: str, diff_text: str) -> str:
        """Create structured prompt for commit analysis.

        Args:
            commit_message: The commit message
            diff_text: The diff content (may be truncated)

        Returns:
            Formatted prompt string for OpenAI API
        """
        # Truncate diff if it's too long
        truncated_diff = self.truncate_diff_for_tokens(diff_text)
        
        prompt = f"""You are a senior developer. Summarize the following Git commit into a clear, human-readable explanation. Include:
- What changed
- Why it changed  
- Potential side effects or considerations

Commit Message: {commit_message}

Diff:
{truncated_diff}

Please provide a concise summary that helps other developers understand the impact and purpose of this change."""

        return prompt

    def truncate_diff_for_tokens(self, diff_text: str, max_chars: Optional[int] = None) -> str:
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
        repository: Optional[Repository] = None
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
            
            # Prepare messages for OpenAI API
            messages = [
                {"role": "user", "content": prompt}
            ]
            
            logger.debug(f"Generating AI summary for commit {commit.sha[:8]}")
            
            # Make API call with retry logic
            response = await self.openai_client.create_completion_with_retry(
                messages=messages,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                model=self.config.model
            )
            
            processing_time = (time.time() - start_time) * 1000
            
            # Parse response into structured summary
            summary_parts = self._parse_summary_response(response.text)
            
            # Update usage statistics
            self._update_usage_stats(
                success=True,
                tokens_used=response.usage.get("total_tokens", 0),
                processing_time=processing_time
            )
            
            logger.info(f"Generated AI summary for commit {commit.sha[:8]} in {processing_time:.0f}ms")
            
            return AISummary(
                commit_sha=commit.sha,
                summary_text=response.text,
                what_changed=summary_parts["what_changed"],
                why_changed=summary_parts["why_changed"],
                potential_side_effects=summary_parts["potential_side_effects"],
                model_used=response.model,
                tokens_used=response.usage.get("total_tokens", 0),
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
            
            # Update usage statistics
            self._update_usage_stats(
                success=False,
                tokens_used=0,
                processing_time=processing_time
            )
            
            # Create error summary
            error_message = self.error_handler.get_user_friendly_message(e)
            
            return AISummary(
                commit_sha=commit.sha,
                summary_text="",
                what_changed="",
                why_changed="",
                potential_side_effects="",
                processing_time_ms=processing_time,
                error=error_message
            )

    async def generate_batch_summaries(
        self,
        commits_with_diffs: List[Tuple[Commit, str]],
        repository: Optional[Repository] = None,
        progress_callback: Optional[callable] = None
    ) -> List[AISummary]:
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
                            what_changed="",
                            why_changed="",
                            potential_side_effects="",
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
                        what_changed="",
                        why_changed="",
                        potential_side_effects="",
                        error=f"Batch processing failed: {e}"
                    )
                    summaries.append(error_summary)
        
        logger.info(f"Completed AI summary generation for {len(summaries)} commits")
        return summaries

    def _parse_summary_response(self, response_text: str) -> Dict[str, str]:
        """Parse AI response into structured components.

        Args:
            response_text: Raw response from OpenAI API

        Returns:
            Dictionary with parsed components
        """
        # Initialize with defaults
        parsed = {
            "what_changed": "",
            "why_changed": "",
            "potential_side_effects": ""
        }
        
        # Try to extract structured information from response
        lines = response_text.strip().split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Look for section headers
            lower_line = line.lower()
            if any(keyword in lower_line for keyword in ["what changed", "what:", "changes:"]):
                current_section = "what_changed"
                # Extract content after the header
                content = line.split(':', 1)
                if len(content) > 1:
                    parsed[current_section] = content[1].strip()
                continue
            elif any(keyword in lower_line for keyword in ["why", "reason", "purpose"]):
                current_section = "why_changed"
                content = line.split(':', 1)
                if len(content) > 1:
                    parsed[current_section] = content[1].strip()
                continue
            elif any(keyword in lower_line for keyword in ["side effects", "considerations", "impact"]):
                current_section = "potential_side_effects"
                content = line.split(':', 1)
                if len(content) > 1:
                    parsed[current_section] = content[1].strip()
                continue
            
            # Add content to current section
            if current_section and line:
                if parsed[current_section]:
                    parsed[current_section] += " " + line
                else:
                    parsed[current_section] = line
        
        # If no structured parsing worked, use the full response for what_changed
        if not any(parsed.values()):
            parsed["what_changed"] = response_text.strip()
        
        return parsed

    def _update_usage_stats(
        self,
        success: bool,
        tokens_used: int,
        processing_time: float
    ) -> None:
        """Update usage statistics.

        Args:
            success: Whether the request was successful
            tokens_used: Number of tokens consumed
            processing_time: Processing time in milliseconds
        """
        self.usage_stats.total_requests += 1
        
        if success:
            self.usage_stats.successful_requests += 1
        else:
            self.usage_stats.failed_requests += 1
        
        self.usage_stats.total_tokens_used += tokens_used
        from datetime import datetime
        self.usage_stats.last_request = datetime.utcnow()
        
        # Update average processing time
        if self.usage_stats.total_requests > 0:
            total_time = (
                self.usage_stats.average_processing_time_ms * (self.usage_stats.total_requests - 1) +
                processing_time
            )
            self.usage_stats.average_processing_time_ms = total_time / self.usage_stats.total_requests
        
        # Estimate cost (rough approximation for GPT-4o-mini)
        # GPT-4o-mini: ~$0.00015 per 1K tokens for input, ~$0.0006 per 1K tokens for output
        # Using average of $0.0003 per 1K tokens as rough estimate
        if tokens_used > 0:
            cost_per_token = 0.0003 / 1000
            self.usage_stats.total_cost_usd += tokens_used * cost_per_token

    def get_usage_stats(self) -> AIUsageStats:
        """Get current usage statistics.

        Returns:
            AIUsageStats object with current statistics
        """
        return self.usage_stats

    def reset_usage_stats(self) -> None:
        """Reset usage statistics."""
        self.usage_stats = AIUsageStats()

    def estimate_batch_cost(self, commits_with_diffs: List[Tuple[Commit, str]]) -> float:
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
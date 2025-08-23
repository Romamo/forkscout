"""Unit tests for AI commit summary engine."""

import asyncio
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

from forklift.ai.summary_engine import AICommitSummaryEngine
from forklift.ai.client import OpenAIClient, OpenAIResponse
from forklift.ai.error_handler import OpenAIErrorHandler
from forklift.models.ai_summary import AISummary, AISummaryConfig, AIUsageStats
from forklift.models.github import Commit, Repository, User


class TestAICommitSummaryEngine:
    """Test cases for AI commit summary engine."""

    def create_test_commit(self, sha_suffix: str = "1", message: str = "Test commit", author_name: str = "Test Author") -> Commit:
        """Create a valid test commit."""
        # Create a valid 40-character hex SHA
        base_sha = "abc123def4567890123456789012345678901234"
        # Replace the last few characters with the suffix (padded with zeros)
        suffix_hex = sha_suffix.zfill(4)[-4:]  # Take last 4 chars, pad with zeros
        # Ensure it's valid hex by replacing non-hex chars with 'a'
        suffix_hex = ''.join(c if c in '0123456789abcdef' else 'a' for c in suffix_hex.lower())
        sha = base_sha[:-4] + suffix_hex
        
        # Create a valid User object
        author = User(
            login=author_name.lower().replace(" ", "_"),
            html_url=f"https://github.com/{author_name.lower().replace(' ', '_')}"
        )
        
        return Commit(
            sha=sha,
            message=message,
            author=author,
            date=datetime.now(),
            files_changed=["test.py"],
            additions=1,
            deletions=0
        )

    def test_engine_initialization(self):
        """Test engine initialization with required parameters."""
        mock_client = Mock(spec=OpenAIClient)
        
        engine = AICommitSummaryEngine(mock_client)
        
        assert engine.openai_client == mock_client
        assert isinstance(engine.config, AISummaryConfig)
        assert isinstance(engine.error_handler, OpenAIErrorHandler)
        assert isinstance(engine.usage_stats, AIUsageStats)

    def test_engine_initialization_with_custom_config(self):
        """Test engine initialization with custom configuration."""
        mock_client = Mock(spec=OpenAIClient)
        config = AISummaryConfig(
            model="gpt-4",
            max_tokens=1000,
            batch_size=10
        )
        mock_error_handler = Mock(spec=OpenAIErrorHandler)
        
        engine = AICommitSummaryEngine(mock_client, config, mock_error_handler)
        
        assert engine.config == config
        assert engine.error_handler == mock_error_handler

    def test_create_summary_prompt(self):
        """Test prompt creation for commit analysis."""
        mock_client = Mock(spec=OpenAIClient)
        engine = AICommitSummaryEngine(mock_client)
        
        commit_message = "Fix authentication bug"
        diff_text = "- old_code\n+ new_code"
        
        prompt = engine.create_summary_prompt(commit_message, diff_text)
        
        assert "senior developer" in prompt.lower()
        assert "what changed" in prompt.lower()
        assert "why it changed" in prompt.lower()
        assert "potential side effects" in prompt.lower()
        assert commit_message in prompt
        assert diff_text in prompt

    def test_create_summary_prompt_with_long_diff(self):
        """Test prompt creation with diff that needs truncation."""
        mock_client = Mock(spec=OpenAIClient)
        config = AISummaryConfig(max_diff_chars=100)
        engine = AICommitSummaryEngine(mock_client, config)
        
        commit_message = "Test commit"
        long_diff = "a" * 200  # Longer than max_diff_chars
        
        prompt = engine.create_summary_prompt(commit_message, long_diff)
        
        assert "[... diff truncated for length ...]" in prompt
        assert len(prompt) < len(commit_message) + len(long_diff) + 500  # Should be truncated

    def test_truncate_diff_for_tokens(self):
        """Test diff truncation logic."""
        mock_client = Mock(spec=OpenAIClient)
        engine = AICommitSummaryEngine(mock_client)
        
        # Test with short diff (no truncation needed)
        short_diff = "short diff content"
        result = engine.truncate_diff_for_tokens(short_diff, max_chars=100)
        assert result == short_diff
        
        # Test with long diff (truncation needed)
        long_diff = "a" * 200
        result = engine.truncate_diff_for_tokens(long_diff, max_chars=100)
        assert len(result) <= 100
        assert "[... diff truncated for length ...]" in result

    def test_truncate_diff_for_tokens_uses_config_default(self):
        """Test that truncation uses config default when max_chars not specified."""
        mock_client = Mock(spec=OpenAIClient)
        config = AISummaryConfig(max_diff_chars=150)  # Use valid minimum value
        engine = AICommitSummaryEngine(mock_client, config)
        
        long_diff = "a" * 200
        result = engine.truncate_diff_for_tokens(long_diff)  # No max_chars specified
        
        assert len(result) <= 150
        assert "[... diff truncated for length ...]" in result

    @pytest.mark.asyncio
    async def test_generate_commit_summary_success(self):
        """Test successful commit summary generation."""
        mock_client = AsyncMock(spec=OpenAIClient)
        
        # Mock successful API response
        mock_response = OpenAIResponse(
            text="What changed: Fixed authentication bug\nWhy: To prevent unauthorized access\nSide effects: Users may need to re-login",
            usage={"total_tokens": 150, "prompt_tokens": 100, "completion_tokens": 50},
            model="gpt-4o-mini",
            finish_reason="stop"
        )
        mock_client.create_completion_with_retry.return_value = mock_response
        
        engine = AICommitSummaryEngine(mock_client)
        
        commit = self.create_test_commit(
            sha_suffix="auth",
            message="Fix authentication bug",
            author_name="John Doe"
        )
        diff_text = "- old_auth_code\n+ new_auth_code"
        
        summary = await engine.generate_commit_summary(commit, diff_text)
        
        assert isinstance(summary, AISummary)
        assert summary.commit_sha == commit.sha
        assert summary.summary_text == mock_response.text
        assert "Fixed authentication bug" in summary.what_changed
        assert "prevent unauthorized access" in summary.why_changed
        assert "re-login" in summary.potential_side_effects
        assert summary.model_used == "gpt-4o-mini"
        assert summary.tokens_used == 150
        assert summary.processing_time_ms > 0
        assert summary.error is None

    @pytest.mark.asyncio
    async def test_generate_commit_summary_api_error(self):
        """Test commit summary generation with API error."""
        mock_client = AsyncMock(spec=OpenAIClient)
        mock_error_handler = Mock(spec=OpenAIErrorHandler)
        
        # Mock API error
        api_error = Exception("API error")
        mock_client.create_completion_with_retry.side_effect = api_error
        mock_error_handler.get_user_friendly_message.return_value = "Friendly error message"
        
        engine = AICommitSummaryEngine(mock_client, error_handler=mock_error_handler)
        
        commit = self.create_test_commit(
            sha_suffix="test",
            message="Test commit",
            author_name="John Doe"
        )
        diff_text = "test diff"
        
        summary = await engine.generate_commit_summary(commit, diff_text)
        
        assert isinstance(summary, AISummary)
        assert summary.commit_sha == commit.sha
        assert summary.error == "Friendly error message"
        assert summary.summary_text == ""
        assert summary.what_changed == ""
        assert summary.why_changed == ""
        assert summary.potential_side_effects == ""
        
        # Verify error handling was called
        mock_error_handler.log_error.assert_called_once()
        mock_error_handler.get_user_friendly_message.assert_called_once_with(api_error)

    @pytest.mark.asyncio
    async def test_generate_batch_summaries_success(self):
        """Test successful batch summary generation."""
        mock_client = AsyncMock(spec=OpenAIClient)
        
        # Mock successful API responses
        mock_response1 = OpenAIResponse(
            text="Summary for commit 1",
            usage={"total_tokens": 100},
            model="gpt-4o-mini",
            finish_reason="stop"
        )
        mock_response2 = OpenAIResponse(
            text="Summary for commit 2",
            usage={"total_tokens": 120},
            model="gpt-4o-mini",
            finish_reason="stop"
        )
        
        mock_client.create_completion_with_retry.side_effect = [mock_response1, mock_response2]
        
        config = AISummaryConfig(batch_size=2)
        engine = AICommitSummaryEngine(mock_client, config)
        
        commits_with_diffs = [
            (
                self.create_test_commit(
                    sha_suffix="001",
                    message="First commit",
                    author_name="Author 1"
                ),
                "diff for commit 1"
            ),
            (
                self.create_test_commit(
                    sha_suffix="002",
                    message="Second commit",
                    author_name="Author 2"
                ),
                "diff for commit 2"
            )
        ]
        
        summaries = await engine.generate_batch_summaries(commits_with_diffs)
        
        assert len(summaries) == 2
        assert summaries[0].commit_sha == commits_with_diffs[0][0].sha
        assert summaries[0].summary_text == "Summary for commit 1"
        assert summaries[1].commit_sha == commits_with_diffs[1][0].sha
        assert summaries[1].summary_text == "Summary for commit 2"

    @pytest.mark.asyncio
    async def test_generate_batch_summaries_with_progress_callback(self):
        """Test batch summary generation with progress callback."""
        mock_client = AsyncMock(spec=OpenAIClient)
        
        # Mock successful API response
        mock_response = OpenAIResponse(
            text="Test summary",
            usage={"total_tokens": 100},
            model="gpt-4o-mini",
            finish_reason="stop"
        )
        mock_client.create_completion_with_retry.return_value = mock_response
        
        engine = AICommitSummaryEngine(mock_client)
        
        # Mock progress callback
        progress_callback = Mock()
        
        commits_with_diffs = [
            (
                self.create_test_commit(
                    sha_suffix="001",
                    message="Test commit",
                    author_name="Author"
                ),
                "test diff"
            )
        ]
        
        summaries = await engine.generate_batch_summaries(
            commits_with_diffs,
            progress_callback=progress_callback
        )
        
        assert len(summaries) == 1
        progress_callback.assert_called_once_with(1.0, 1, 1)  # 100% progress

    @pytest.mark.asyncio
    async def test_generate_batch_summaries_empty_list(self):
        """Test batch summary generation with empty list."""
        mock_client = Mock(spec=OpenAIClient)
        engine = AICommitSummaryEngine(mock_client)
        
        summaries = await engine.generate_batch_summaries([])
        
        assert summaries == []

    @pytest.mark.asyncio
    async def test_generate_batch_summaries_with_batching(self):
        """Test batch summary generation respects batch size."""
        mock_client = AsyncMock(spec=OpenAIClient)
        
        # Mock successful API response
        mock_response = OpenAIResponse(
            text="Test summary",
            usage={"total_tokens": 100},
            model="gpt-4o-mini",
            finish_reason="stop"
        )
        mock_client.create_completion_with_retry.return_value = mock_response
        
        config = AISummaryConfig(batch_size=2)  # Small batch size
        engine = AICommitSummaryEngine(mock_client, config)
        
        # Create 3 commits (will require 2 batches)
        commits_with_diffs = []
        for i in range(3):
            commit = self.create_test_commit(
                sha_suffix=f"{i:03d}",
                message=f"Commit {i}",
                author_name="Author"
            )
            commits_with_diffs.append((commit, f"diff {i}"))
        
        with patch("asyncio.sleep") as mock_sleep:  # Mock sleep to speed up test
            summaries = await engine.generate_batch_summaries(commits_with_diffs)
        
        assert len(summaries) == 3
        # Should have slept once between batches
        mock_sleep.assert_called_once_with(1.0)

    def test_parse_summary_response_structured(self):
        """Test parsing structured AI response."""
        mock_client = Mock(spec=OpenAIClient)
        engine = AICommitSummaryEngine(mock_client)
        
        response_text = """What changed: Fixed authentication bug in login system
Why: To prevent unauthorized access to user accounts
Side effects: Users may need to re-login after the update"""
        
        parsed = engine._parse_summary_response(response_text)
        
        assert "Fixed authentication bug" in parsed["what_changed"]
        assert "prevent unauthorized access" in parsed["why_changed"]
        assert "re-login" in parsed["potential_side_effects"]

    def test_parse_summary_response_unstructured(self):
        """Test parsing unstructured AI response."""
        mock_client = Mock(spec=OpenAIClient)
        engine = AICommitSummaryEngine(mock_client)
        
        response_text = "This commit fixes a bug in the authentication system that was allowing unauthorized access."
        
        parsed = engine._parse_summary_response(response_text)
        
        assert parsed["what_changed"] == response_text
        assert parsed["why_changed"] == ""
        assert parsed["potential_side_effects"] == ""

    def test_parse_summary_response_partial_structure(self):
        """Test parsing partially structured AI response."""
        mock_client = Mock(spec=OpenAIClient)
        engine = AICommitSummaryEngine(mock_client)
        
        response_text = """What: Fixed authentication bug
This change prevents unauthorized access to the system."""
        
        parsed = engine._parse_summary_response(response_text)
        
        assert "Fixed authentication bug" in parsed["what_changed"]
        assert "prevents unauthorized access" in parsed["what_changed"]

    def test_update_usage_stats_success(self):
        """Test usage statistics update for successful request."""
        mock_client = Mock(spec=OpenAIClient)
        engine = AICommitSummaryEngine(mock_client)
        
        initial_stats = engine.get_usage_stats()
        assert initial_stats.total_requests == 0
        assert initial_stats.successful_requests == 0
        assert initial_stats.total_tokens_used == 0
        
        engine._update_usage_stats(success=True, tokens_used=150, processing_time=1000.0)
        
        updated_stats = engine.get_usage_stats()
        assert updated_stats.total_requests == 1
        assert updated_stats.successful_requests == 1
        assert updated_stats.failed_requests == 0
        assert updated_stats.total_tokens_used == 150
        assert updated_stats.average_processing_time_ms == 1000.0
        assert updated_stats.total_cost_usd > 0  # Should have some cost

    def test_update_usage_stats_failure(self):
        """Test usage statistics update for failed request."""
        mock_client = Mock(spec=OpenAIClient)
        engine = AICommitSummaryEngine(mock_client)
        
        engine._update_usage_stats(success=False, tokens_used=0, processing_time=500.0)
        
        stats = engine.get_usage_stats()
        assert stats.total_requests == 1
        assert stats.successful_requests == 0
        assert stats.failed_requests == 1
        assert stats.total_tokens_used == 0
        assert stats.average_processing_time_ms == 500.0

    def test_update_usage_stats_multiple_requests(self):
        """Test usage statistics with multiple requests."""
        mock_client = Mock(spec=OpenAIClient)
        engine = AICommitSummaryEngine(mock_client)
        
        # First request
        engine._update_usage_stats(success=True, tokens_used=100, processing_time=1000.0)
        # Second request
        engine._update_usage_stats(success=True, tokens_used=200, processing_time=2000.0)
        
        stats = engine.get_usage_stats()
        assert stats.total_requests == 2
        assert stats.successful_requests == 2
        assert stats.total_tokens_used == 300
        assert stats.average_processing_time_ms == 1500.0  # Average of 1000 and 2000

    def test_get_usage_stats(self):
        """Test getting usage statistics."""
        mock_client = Mock(spec=OpenAIClient)
        engine = AICommitSummaryEngine(mock_client)
        
        stats = engine.get_usage_stats()
        
        assert isinstance(stats, AIUsageStats)
        assert stats.total_requests == 0
        assert stats.successful_requests == 0
        assert stats.failed_requests == 0

    def test_reset_usage_stats(self):
        """Test resetting usage statistics."""
        mock_client = Mock(spec=OpenAIClient)
        engine = AICommitSummaryEngine(mock_client)
        
        # Add some usage
        engine._update_usage_stats(success=True, tokens_used=100, processing_time=1000.0)
        
        # Verify stats are not zero
        stats = engine.get_usage_stats()
        assert stats.total_requests == 1
        
        # Reset stats
        engine.reset_usage_stats()
        
        # Verify stats are reset
        stats = engine.get_usage_stats()
        assert stats.total_requests == 0
        assert stats.successful_requests == 0
        assert stats.total_tokens_used == 0

    def test_estimate_batch_cost_empty_list(self):
        """Test cost estimation for empty batch."""
        mock_client = Mock(spec=OpenAIClient)
        engine = AICommitSummaryEngine(mock_client)
        
        cost = engine.estimate_batch_cost([])
        
        assert cost == 0.0

    def test_estimate_batch_cost_with_commits(self):
        """Test cost estimation for batch with commits."""
        mock_client = Mock(spec=OpenAIClient)
        engine = AICommitSummaryEngine(mock_client)
        
        commits_with_diffs = [
            (
                self.create_test_commit(
                    sha_suffix="001",
                    message="Test commit 1",
                    author_name="Author"
                ),
                "test diff 1"
            ),
            (
                self.create_test_commit(
                    sha_suffix="002",
                    message="Test commit 2",
                    author_name="Author"
                ),
                "test diff 2"
            )
        ]
        
        cost = engine.estimate_batch_cost(commits_with_diffs)
        
        assert cost > 0.0  # Should have some estimated cost
        assert isinstance(cost, float)

    def test_estimate_batch_cost_scales_with_size(self):
        """Test that cost estimation scales with batch size."""
        mock_client = Mock(spec=OpenAIClient)
        engine = AICommitSummaryEngine(mock_client)
        
        # Single commit
        single_commit = [
            (
                self.create_test_commit(
                    sha_suffix="001",
                    message="Test commit",
                    author_name="Author"
                ),
                "test diff"
            )
        ]
        
        # Double the commits
        double_commits = single_commit * 2
        
        single_cost = engine.estimate_batch_cost(single_commit)
        double_cost = engine.estimate_batch_cost(double_commits)
        
        # Double the commits should roughly double the cost
        assert double_cost > single_cost
        assert double_cost >= single_cost * 1.8  # Allow some variance
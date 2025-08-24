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
        assert hasattr(engine, 'usage_tracker')
        assert isinstance(engine.get_usage_stats(), AIUsageStats)

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
        
        # Check for concise prompt format
        assert "Summarize this commit: what changed, why, impact" in prompt
        assert "senior developer" not in prompt.lower()  # Should not contain buzzwords
        assert commit_message in prompt
        assert diff_text in prompt
        
        # Verify the prompt is concise - the base instruction should be under 50 chars
        base_instruction = "Summarize this commit: what changed, why, impact"
        assert len(base_instruction) < 50

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

    def test_create_summary_prompt_is_concise(self):
        """Test that the prompt instruction is concise and under 50 characters."""
        mock_client = Mock(spec=OpenAIClient)
        engine = AICommitSummaryEngine(mock_client)
        
        commit_message = "Test commit"
        diff_text = "test diff"
        
        prompt = engine.create_summary_prompt(commit_message, diff_text)
        
        # Extract the base instruction (first line)
        lines = prompt.split('\n')
        base_instruction = lines[0]
        
        # Verify it's the expected concise format
        assert base_instruction == "Summarize this commit: what changed, why, impact"
        
        # Verify it's under 50 characters
        assert len(base_instruction) < 50
        
        # Verify no verbose language or buzzwords
        assert "senior developer" not in prompt.lower()
        assert "clear, human-readable explanation" not in prompt.lower()
        assert "please provide" not in prompt.lower()
        assert "considerations" not in prompt.lower()

    def test_create_summary_prompt_compact_mode(self):
        """Test prompt creation in compact mode."""
        mock_client = Mock(spec=OpenAIClient)
        config = AISummaryConfig(compact_mode=True)
        engine = AICommitSummaryEngine(mock_client, config)
        
        commit_message = "feat: add user authentication"
        diff_text = "+def authenticate_user():\n+    return True"
        
        prompt = engine.create_summary_prompt(commit_message, diff_text)
        
        # Verify compact prompt format
        assert "Brief summary:" in prompt
        assert "One sentence: what changed and why." in prompt
        
        # Verify it doesn't contain standard prompt elements
        assert "Summarize this commit: what changed, why, impact" not in prompt
        
        # Verify commit message and diff are included
        assert commit_message in prompt
        assert diff_text in prompt

    def test_create_summary_prompt_standard_mode(self):
        """Test prompt creation in standard (non-compact) mode."""
        mock_client = Mock(spec=OpenAIClient)
        config = AISummaryConfig(compact_mode=False)
        engine = AICommitSummaryEngine(mock_client, config)
        
        commit_message = "feat: add user authentication"
        diff_text = "+def authenticate_user():\n+    return True"
        
        prompt = engine.create_summary_prompt(commit_message, diff_text)
        
        # Verify standard prompt format
        assert "Summarize this commit: what changed, why, impact" in prompt
        
        # Verify it doesn't contain compact prompt elements
        assert "Brief summary:" not in prompt
        assert "One sentence: what changed and why." not in prompt
        
        # Verify commit message and diff are included
        assert commit_message in prompt
        assert diff_text in prompt

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
            text="Fixed authentication bug to prevent unauthorized access. Users may need to re-login after the update.",
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
        assert summary.summary_text == mock_response.text.strip()
        assert "Fixed authentication bug" in summary.summary_text
        assert "prevent unauthorized access" in summary.summary_text
        assert "re-login" in summary.summary_text
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
        assert summaries[0].summary_text == "Summary for commit 1."
        assert summaries[1].commit_sha == commits_with_diffs[1][0].sha
        assert summaries[1].summary_text == "Summary for commit 2."

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

    def test_summary_response_processing(self):
        """Test that summary response is properly processed."""
        mock_client = Mock(spec=OpenAIClient)
        engine = AICommitSummaryEngine(mock_client)
        
        # Test that response text is stripped of whitespace
        response_text = "  This commit fixes a bug in the authentication system.  \n"
        expected_text = "This commit fixes a bug in the authentication system."
        
        # Since we no longer parse structured responses, we just verify the text is cleaned
        assert response_text.strip() == expected_text

    def test_simplified_response_handling(self):
        """Test that AI responses are handled as simple text without structured parsing."""
        mock_client = Mock(spec=OpenAIClient)
        engine = AICommitSummaryEngine(mock_client)
        
        # Test various response formats - all should be treated as simple text
        test_cases = [
            "Simple commit description",
            "What changed: Added feature\nWhy: For users\nImpact: None",  # Structured format
            "This commit does multiple things:\n- Adds feature A\n- Fixes bug B\n- Updates docs",
            "   Whitespace should be trimmed   \n\n"
        ]
        
        for response_text in test_cases:
            # All responses should just be stripped, no parsing
            processed = response_text.strip()
            assert isinstance(processed, str)
            assert processed == response_text.strip()

    def test_update_usage_stats_success(self):
        """Test usage statistics update for successful request."""
        mock_client = Mock(spec=OpenAIClient)
        engine = AICommitSummaryEngine(mock_client)
        
        initial_stats = engine.get_usage_stats()
        assert initial_stats.total_requests == 0
        assert initial_stats.successful_requests == 0
        assert initial_stats.total_tokens_used == 0
        
        engine.usage_tracker.record_request(
            success=True, 
            input_tokens=100, 
            output_tokens=50, 
            processing_time_ms=1000.0
        )
        
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
        
        engine.usage_tracker.record_request(
            success=False, 
            processing_time_ms=500.0,
            error="Test error"
        )
        
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
        engine.usage_tracker.record_request(
            success=True, 
            input_tokens=80, 
            output_tokens=20, 
            processing_time_ms=1000.0
        )
        # Second request
        engine.usage_tracker.record_request(
            success=True, 
            input_tokens=150, 
            output_tokens=50, 
            processing_time_ms=2000.0
        )
        
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
        engine.usage_tracker.record_request(
            success=True, 
            input_tokens=80, 
            output_tokens=20, 
            processing_time_ms=1000.0
        )
        
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

    def test_parse_summary_response_simple_text(self):
        """Test parsing simple summary response text."""
        mock_client = Mock(spec=OpenAIClient)
        engine = AICommitSummaryEngine(mock_client)
        
        # Test simple text
        response_text = "This commit adds user authentication functionality."
        parsed = engine._parse_summary_response(response_text)
        
        assert parsed == "This commit adds user authentication functionality."

    def test_parse_summary_response_with_whitespace(self):
        """Test parsing response with leading/trailing whitespace."""
        mock_client = Mock(spec=OpenAIClient)
        engine = AICommitSummaryEngine(mock_client)
        
        # Test text with whitespace
        response_text = "  \n  This commit fixes a bug in the login system.  \n  "
        parsed = engine._parse_summary_response(response_text)
        
        assert parsed == "This commit fixes a bug in the login system."

    def test_parse_summary_response_empty_text(self):
        """Test parsing empty response text."""
        mock_client = Mock(spec=OpenAIClient)
        engine = AICommitSummaryEngine(mock_client)
        
        # Test empty text
        parsed = engine._parse_summary_response("")
        assert parsed == ""
        
        # Test None
        parsed = engine._parse_summary_response(None)
        assert parsed == ""

    def test_parse_summary_response_multiline_text(self):
        """Test parsing multiline response text."""
        mock_client = Mock(spec=OpenAIClient)
        engine = AICommitSummaryEngine(mock_client)
        
        # Test multiline text (should be preserved as-is after stripping)
        response_text = "This commit adds authentication.\nIt includes JWT token support.\nUsers can now log in securely."
        parsed = engine._parse_summary_response(response_text)
        
        assert parsed == "This commit adds authentication. It includes JWT token support. Users can now log in securely."

    def test_parse_summary_response_no_structured_parsing(self):
        """Test that structured content is not parsed into sections."""
        mock_client = Mock(spec=OpenAIClient)
        engine = AICommitSummaryEngine(mock_client)
        
        # Test text that looks like structured format but should be treated as plain text
        response_text = """What changed: Added user authentication
Why changed: To improve security
Potential side effects: May require users to re-login"""
        
        parsed = engine._parse_summary_response(response_text)
        
        # Should return the entire text as-is, not parse it into sections
        assert "What changed: Added user authentication" in parsed
        assert "Why changed: To improve security" in parsed
        assert "Potential side effects: May require users to re-login" in parsed
        # The brevity enforcement will add punctuation but preserve newlines
        expected = "What changed: Added user authentication\nWhy changed: To improve security\nPotential side effects: May require users to re-login."
        assert parsed == expected

    @pytest.mark.asyncio
    async def test_generate_commit_summary_uses_parse_method(self):
        """Test that commit summary generation uses the parse method."""
        mock_client = AsyncMock(spec=OpenAIClient)
        
        # Mock successful API response with whitespace
        mock_response = OpenAIResponse(
            text="  This commit adds authentication functionality.  \n",
            usage={"total_tokens": 100, "prompt_tokens": 70, "completion_tokens": 30},
            model="gpt-4o-mini",
            finish_reason="stop"
        )
        mock_client.create_completion_with_retry.return_value = mock_response
        
        engine = AICommitSummaryEngine(mock_client)
        
        commit = self.create_test_commit(
            sha_suffix="parse",
            message="Add authentication",
            author_name="Test Author"
        )
        diff_text = "test diff content"
        
        summary = await engine.generate_commit_summary(commit, diff_text)
        
        # Verify the response was parsed (whitespace stripped)
        assert summary.summary_text == "This commit adds authentication functionality."
        assert summary.commit_sha == commit.sha

    @pytest.mark.asyncio
    async def test_generate_commit_summary_compact_mode_token_limit(self):
        """Test that compact mode uses reduced token limits."""
        mock_client = AsyncMock(spec=OpenAIClient)
        
        # Mock successful API response
        mock_response = OpenAIResponse(
            text="Brief summary of changes",
            usage={"total_tokens": 50, "prompt_tokens": 30, "completion_tokens": 20},
            model="gpt-4o-mini",
            finish_reason="stop"
        )
        mock_client.create_completion_with_retry.return_value = mock_response
        
        # Test with compact mode enabled
        config = AISummaryConfig(compact_mode=True, max_tokens=150)
        engine = AICommitSummaryEngine(mock_client, config)
        
        commit = self.create_test_commit()
        diff_text = "test diff content"
        
        summary = await engine.generate_commit_summary(commit, diff_text)
        
        # Verify API was called with reduced token limit (100 instead of 500)
        mock_client.create_completion_with_retry.assert_called_once()
        call_args = mock_client.create_completion_with_retry.call_args
        assert call_args[1]['max_tokens'] == 75  # Should be limited to 75 in compact mode
        
        # Verify summary was created successfully
        assert summary.commit_sha == commit.sha
        assert summary.summary_text == "Brief summary of changes."

    @pytest.mark.asyncio
    async def test_generate_commit_summary_standard_mode_token_limit(self):
        """Test that standard mode uses full token limits."""
        mock_client = AsyncMock(spec=OpenAIClient)
        
        # Mock successful API response
        mock_response = OpenAIResponse(
            text="Detailed summary of changes with full context",
            usage={"total_tokens": 200, "prompt_tokens": 100, "completion_tokens": 100},
            model="gpt-4o-mini",
            finish_reason="stop"
        )
        mock_client.create_completion_with_retry.return_value = mock_response
        
        # Test with compact mode disabled - note new default max_tokens is 150
        config = AISummaryConfig(compact_mode=False, max_tokens=150)
        engine = AICommitSummaryEngine(mock_client, config)
        
        commit = self.create_test_commit()
        diff_text = "test diff content"
        
        summary = await engine.generate_commit_summary(commit, diff_text)
        
        # Verify API was called with full token limit (150 in standard mode)
        mock_client.create_completion_with_retry.assert_called_once()
        call_args = mock_client.create_completion_with_retry.call_args
        assert call_args[1]['max_tokens'] == 150  # Should use full config limit
        
        # Verify summary was created successfully
        assert summary.commit_sha == commit.sha
        assert summary.summary_text == "Detailed summary of changes with full context."

    def test_enforce_brevity_within_limit(self):
        """Test brevity enforcement with text within sentence limit."""
        mock_client = Mock(spec=OpenAIClient)
        engine = AICommitSummaryEngine(mock_client)
        
        # Text with 2 sentences (within 3 sentence limit)
        text = "This commit adds authentication. It improves security."
        result = engine._enforce_brevity(text)
        
        assert result == text  # Should return unchanged

    def test_enforce_brevity_exceeds_limit(self):
        """Test brevity enforcement with text exceeding sentence limit."""
        mock_client = Mock(spec=OpenAIClient)
        engine = AICommitSummaryEngine(mock_client)
        
        # Text with 5 sentences (exceeds 3 sentence limit)
        text = "This commit adds authentication. It improves security. Users can now log in. The system is more robust. Performance is better."
        result = engine._enforce_brevity(text)
        
        # Should be limited to first 3 sentences
        expected = "This commit adds authentication. It improves security. Users can now log in."
        assert result == expected

    def test_enforce_brevity_empty_text(self):
        """Test brevity enforcement with empty text."""
        mock_client = Mock(spec=OpenAIClient)
        engine = AICommitSummaryEngine(mock_client)
        
        assert engine._enforce_brevity("") == ""
        assert engine._enforce_brevity(None) == ""

    def test_enforce_brevity_single_sentence(self):
        """Test brevity enforcement with single sentence."""
        mock_client = Mock(spec=OpenAIClient)
        engine = AICommitSummaryEngine(mock_client)
        
        text = "This commit adds user authentication functionality."
        result = engine._enforce_brevity(text)
        
        assert result == text  # Should return unchanged

    def test_enforce_brevity_custom_limit(self):
        """Test brevity enforcement with custom sentence limit."""
        mock_client = Mock(spec=OpenAIClient)
        engine = AICommitSummaryEngine(mock_client)
        
        text = "First sentence. Second sentence. Third sentence. Fourth sentence."
        result = engine._enforce_brevity(text, max_sentences=2)
        
        expected = "First sentence. Second sentence."
        assert result == expected

    def test_enforce_brevity_different_punctuation(self):
        """Test brevity enforcement with different sentence ending punctuation."""
        mock_client = Mock(spec=OpenAIClient)
        engine = AICommitSummaryEngine(mock_client)
        
        text = "This commit fixes a bug! It improves performance? The system is now stable. Additional changes were made."
        result = engine._enforce_brevity(text)
        
        # Should handle different punctuation and limit to 3 sentences
        expected = "This commit fixes a bug! It improves performance? The system is now stable."
        assert result == expected

    def test_enforce_brevity_adds_punctuation(self):
        """Test that brevity enforcement adds punctuation when needed."""
        mock_client = Mock(spec=OpenAIClient)
        engine = AICommitSummaryEngine(mock_client)
        
        # Text where the last kept sentence doesn't end with punctuation
        text = "First sentence. Second sentence. Third sentence without punctuation"
        result = engine._enforce_brevity(text)
        
        # Should add period at the end
        expected = "First sentence. Second sentence. Third sentence without punctuation."
        assert result == expected

    def test_validate_response_length_within_limit(self):
        """Test response length validation for text within limit."""
        mock_client = Mock(spec=OpenAIClient)
        engine = AICommitSummaryEngine(mock_client)
        
        # Text with 2 sentences
        text = "This commit adds authentication. It improves security."
        assert engine._validate_response_length(text) is True

    def test_validate_response_length_exceeds_limit(self):
        """Test response length validation for text exceeding limit."""
        mock_client = Mock(spec=OpenAIClient)
        engine = AICommitSummaryEngine(mock_client)
        
        # Text with 5 sentences
        text = "First. Second. Third. Fourth. Fifth."
        assert engine._validate_response_length(text) is False

    def test_validate_response_length_empty_text(self):
        """Test response length validation for empty text."""
        mock_client = Mock(spec=OpenAIClient)
        engine = AICommitSummaryEngine(mock_client)
        
        assert engine._validate_response_length("") is True
        assert engine._validate_response_length(None) is True

    def test_validate_response_length_exactly_at_limit(self):
        """Test response length validation for text exactly at limit."""
        mock_client = Mock(spec=OpenAIClient)
        engine = AICommitSummaryEngine(mock_client)
        
        # Text with exactly 3 sentences
        text = "First sentence. Second sentence. Third sentence."
        assert engine._validate_response_length(text) is True

    def test_parse_summary_response_enforces_brevity(self):
        """Test that parse method enforces brevity on long responses."""
        mock_client = Mock(spec=OpenAIClient)
        engine = AICommitSummaryEngine(mock_client)
        
        # Long response with 5 sentences
        response_text = "This commit adds authentication. It improves security. Users can log in. The system is robust. Performance is better."
        parsed = engine._parse_summary_response(response_text)
        
        # Should be limited to 3 sentences
        expected = "This commit adds authentication. It improves security. Users can log in."
        assert parsed == expected

    @pytest.mark.asyncio
    async def test_generate_commit_summary_compact_mode_reduced_tokens(self):
        """Test that compact mode uses even more reduced token limits for brevity."""
        mock_client = AsyncMock(spec=OpenAIClient)
        
        # Mock successful API response
        mock_response = OpenAIResponse(
            text="Brief summary",
            usage={"total_tokens": 30, "prompt_tokens": 20, "completion_tokens": 10},
            model="gpt-4o-mini",
            finish_reason="stop"
        )
        mock_client.create_completion_with_retry.return_value = mock_response
        
        # Test with compact mode enabled - should use 75 tokens instead of 100
        config = AISummaryConfig(compact_mode=True, max_tokens=150)
        engine = AICommitSummaryEngine(mock_client, config)
        
        commit = self.create_test_commit()
        diff_text = "test diff content"
        
        summary = await engine.generate_commit_summary(commit, diff_text)
        
        # Verify API was called with reduced token limit (75 instead of 150)
        mock_client.create_completion_with_retry.assert_called_once()
        call_args = mock_client.create_completion_with_retry.call_args
        assert call_args[1]['max_tokens'] == 75  # Should be limited to 75 in compact mode
        
        # Verify summary was created successfully
        assert summary.commit_sha == commit.sha
        assert summary.summary_text == "Brief summary."

    def test_default_max_tokens_reduced(self):
        """Test that default max_tokens is now 150 instead of 500."""
        config = AISummaryConfig()
        assert config.max_tokens == 150

    def test_brevity_enforcement_integration(self):
        """Test integration of brevity enforcement with response parsing."""
        mock_client = Mock(spec=OpenAIClient)
        engine = AICommitSummaryEngine(mock_client)
        
        # Test various scenarios
        test_cases = [
            # (input, expected_output)
            ("Short response.", "Short response."),
            ("First. Second. Third.", "First. Second. Third."),
            ("First. Second. Third. Fourth. Fifth.", "First. Second. Third."),
            ("  Whitespace and multiple sentences. Another one. Third one. Fourth.  ", "Whitespace and multiple sentences. Another one. Third one."),
            ("", ""),
        ]
        
        for input_text, expected in test_cases:
            result = engine._parse_summary_response(input_text)
            assert result == expected, f"Failed for input: {input_text}"
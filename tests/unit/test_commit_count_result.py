"""Unit tests for commit count result models."""

import pytest

from forkscout.models.commit_count_result import BatchCommitCountResult, CommitCountResult


class TestCommitCountResult:
    """Test CommitCountResult model."""

    def test_commit_count_result_creation(self):
        """Test creating CommitCountResult with both ahead and behind counts."""
        result = CommitCountResult(
            ahead_count=9,
            behind_count=11,
            is_limited=False,
            error=None
        )
        
        assert result.ahead_count == 9
        assert result.behind_count == 11
        assert result.is_limited is False
        assert result.error is None

    def test_has_ahead_commits_property(self):
        """Test has_ahead_commits property."""
        # Fork with ahead commits
        result = CommitCountResult(ahead_count=5, behind_count=0)
        assert result.has_ahead_commits is True
        
        # Fork without ahead commits
        result = CommitCountResult(ahead_count=0, behind_count=3)
        assert result.has_ahead_commits is False

    def test_has_behind_commits_property(self):
        """Test has_behind_commits property."""
        # Fork with behind commits
        result = CommitCountResult(ahead_count=0, behind_count=7)
        assert result.has_behind_commits is True
        
        # Fork without behind commits
        result = CommitCountResult(ahead_count=5, behind_count=0)
        assert result.has_behind_commits is False

    def test_is_diverged_property(self):
        """Test is_diverged property."""
        # Fork with both ahead and behind commits (diverged)
        result = CommitCountResult(ahead_count=9, behind_count=11)
        assert result.is_diverged is True
        
        # Fork with only ahead commits
        result = CommitCountResult(ahead_count=5, behind_count=0)
        assert result.is_diverged is False
        
        # Fork with only behind commits
        result = CommitCountResult(ahead_count=0, behind_count=3)
        assert result.is_diverged is False
        
        # Fork with no commits
        result = CommitCountResult(ahead_count=0, behind_count=0)
        assert result.is_diverged is False

    def test_commit_count_result_with_error(self):
        """Test CommitCountResult with error information."""
        result = CommitCountResult(
            ahead_count=0,
            behind_count=0,
            is_limited=False,
            error="Repository not found"
        )
        
        assert result.error == "Repository not found"
        assert result.has_ahead_commits is False
        assert result.has_behind_commits is False
        assert result.is_diverged is False


class TestBatchCommitCountResult:
    """Test BatchCommitCountResult model."""

    def test_batch_commit_count_result_creation(self):
        """Test creating BatchCommitCountResult."""
        results = {
            "owner1/repo1": CommitCountResult(ahead_count=5, behind_count=2),
            "owner2/repo2": CommitCountResult(ahead_count=0, behind_count=8),
            "owner3/repo3": CommitCountResult(ahead_count=12, behind_count=0),
        }
        
        batch_result = BatchCommitCountResult(
            results=results,
            total_api_calls=10,
            parent_calls_saved=3
        )
        
        assert len(batch_result.results) == 3
        assert batch_result.total_api_calls == 10
        assert batch_result.parent_calls_saved == 3
        
        # Check individual results
        assert batch_result.results["owner1/repo1"].ahead_count == 5
        assert batch_result.results["owner1/repo1"].behind_count == 2
        assert batch_result.results["owner2/repo2"].ahead_count == 0
        assert batch_result.results["owner2/repo2"].behind_count == 8

    def test_empty_batch_result(self):
        """Test BatchCommitCountResult with no results."""
        batch_result = BatchCommitCountResult(
            results={},
            total_api_calls=0,
            parent_calls_saved=0
        )
        
        assert len(batch_result.results) == 0
        assert batch_result.total_api_calls == 0
        assert batch_result.parent_calls_saved == 0
"""Tests for rate limit progress tracking."""

import asyncio
import time
from unittest.mock import AsyncMock, patch
from io import StringIO
import sys

import pytest

from forklift.github.rate_limit_progress import (
    RateLimitProgressTracker,
    RateLimitProgressManager,
    get_progress_manager
)


class TestRateLimitProgressTracker:
    """Test rate limit progress tracking functionality."""

    def test_format_duration_seconds(self):
        """Test duration formatting for seconds."""
        tracker = RateLimitProgressTracker()
        
        assert tracker._format_duration(30) == "30s"
        assert tracker._format_duration(59) == "59s"

    def test_format_duration_minutes(self):
        """Test duration formatting for minutes."""
        tracker = RateLimitProgressTracker()
        
        assert tracker._format_duration(60) == "1m 0s"
        assert tracker._format_duration(90) == "1m 30s"
        assert tracker._format_duration(3599) == "59m 59s"

    def test_format_duration_hours(self):
        """Test duration formatting for hours."""
        tracker = RateLimitProgressTracker()
        
        assert tracker._format_duration(3600) == "1h 0m"
        assert tracker._format_duration(3660) == "1h 1m"
        assert tracker._format_duration(7200) == "2h 0m"

    @pytest.mark.asyncio
    async def test_track_rate_limit_wait_short_duration_no_progress(self):
        """Test that short waits don't show progress."""
        tracker = RateLimitProgressTracker(show_progress=True)
        
        # Short wait should not start progress tracking
        await tracker.track_rate_limit_wait(2.0, operation_name="test")
        
        # Progress task should not be created for short waits
        assert tracker._progress_task is None

    @pytest.mark.asyncio
    async def test_track_rate_limit_wait_disabled_progress(self):
        """Test that progress tracking can be disabled."""
        tracker = RateLimitProgressTracker(show_progress=False)
        
        # Even long wait should not show progress when disabled
        await tracker.track_rate_limit_wait(60.0, operation_name="test")
        
        assert tracker._progress_task is None

    @pytest.mark.asyncio
    async def test_track_rate_limit_wait_with_reset_time(self):
        """Test progress tracking with reset time."""
        tracker = RateLimitProgressTracker(show_progress=True)
        
        reset_time = int(time.time()) + 10  # 10 seconds from now
        
        # Capture stdout to verify messages
        captured_output = StringIO()
        with patch('sys.stdout', captured_output):
            # Start tracking (but don't wait for completion)
            task = asyncio.create_task(
                tracker.track_rate_limit_wait(10.0, reset_time, "test operation")
            )
            
            # Give it a moment to start
            await asyncio.sleep(0.1)
            
            # Cancel the task
            task.cancel()
            
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        output = captured_output.getvalue()
        assert "GitHub API Rate Limit Reached" in output
        assert "Operation: test operation" in output
        assert "Reset time:" in output

    @pytest.mark.asyncio
    async def test_show_rate_limit_info(self):
        """Test showing rate limit information."""
        tracker = RateLimitProgressTracker(show_progress=True)
        
        reset_time = int(time.time()) + 3600  # 1 hour from now
        
        captured_output = StringIO()
        with patch('sys.stdout', captured_output):
            await tracker.show_rate_limit_info(
                remaining=100,
                limit=5000,
                reset_time=reset_time
            )
        
        output = captured_output.getvalue()
        assert "GitHub API Rate Limit Status" in output
        assert "Current quota: 100/5,000" in output
        assert "Reset time:" in output

    @pytest.mark.asyncio
    async def test_show_rate_limit_info_low_quota_warning(self):
        """Test warning message for low quota."""
        tracker = RateLimitProgressTracker(show_progress=True)
        
        captured_output = StringIO()
        with patch('sys.stdout', captured_output):
            await tracker.show_rate_limit_info(
                remaining=50,  # Low quota
                limit=5000
            )
        
        output = captured_output.getvalue()
        assert "WARNING: Low quota" in output

    @pytest.mark.asyncio
    async def test_show_completion_message(self):
        """Test completion message display."""
        tracker = RateLimitProgressTracker(show_progress=True)
        
        captured_output = StringIO()
        with patch('sys.stdout', captured_output):
            await tracker.show_completion_message("test operation")
        
        output = captured_output.getvalue()
        assert "Rate Limit Recovery Complete" in output
        assert "resuming operations" in output

    def test_cancel_progress(self):
        """Test cancelling progress tracking."""
        from unittest.mock import Mock
        
        tracker = RateLimitProgressTracker()
        
        # Create a mock task
        mock_task = Mock()
        mock_task.done.return_value = False
        tracker._progress_task = mock_task
        
        tracker.cancel_progress()
        
        assert tracker._cancelled is True
        mock_task.cancel.assert_called_once()


class TestRateLimitProgressManager:
    """Test rate limit progress manager."""

    def test_get_tracker_creates_new_tracker(self):
        """Test that get_tracker creates new trackers."""
        manager = RateLimitProgressManager()
        
        tracker1 = manager.get_tracker("operation1")
        tracker2 = manager.get_tracker("operation2")
        
        assert tracker1 is not tracker2
        assert len(manager._trackers) == 2

    def test_get_tracker_returns_existing_tracker(self):
        """Test that get_tracker returns existing tracker for same operation."""
        manager = RateLimitProgressManager()
        
        tracker1 = manager.get_tracker("operation1")
        tracker2 = manager.get_tracker("operation1")
        
        assert tracker1 is tracker2
        assert len(manager._trackers) == 1

    def test_get_tracker_with_show_progress_false(self):
        """Test creating tracker with progress disabled."""
        manager = RateLimitProgressManager()
        
        tracker = manager.get_tracker("operation1", show_progress=False)
        
        assert tracker.show_progress is False

    def test_cleanup_tracker(self):
        """Test cleaning up completed trackers."""
        manager = RateLimitProgressManager()
        
        # Create a tracker
        tracker = manager.get_tracker("operation1")
        assert "operation1" in manager._trackers
        
        # Clean it up
        manager.cleanup_tracker("operation1")
        assert "operation1" not in manager._trackers

    def test_cleanup_nonexistent_tracker(self):
        """Test cleaning up tracker that doesn't exist."""
        manager = RateLimitProgressManager()
        
        # Should not raise an error
        manager.cleanup_tracker("nonexistent")

    def test_cancel_all_progress(self):
        """Test cancelling all progress tracking."""
        from unittest.mock import Mock
        
        manager = RateLimitProgressManager()
        
        # Create multiple trackers
        tracker1 = manager.get_tracker("operation1")
        tracker2 = manager.get_tracker("operation2")
        
        # Mock their cancel methods
        tracker1.cancel_progress = Mock()
        tracker2.cancel_progress = Mock()
        
        manager.cancel_all_progress()
        
        tracker1.cancel_progress.assert_called_once()
        tracker2.cancel_progress.assert_called_once()


class TestGlobalProgressManager:
    """Test global progress manager functionality."""

    def test_get_progress_manager_returns_singleton(self):
        """Test that get_progress_manager returns the same instance."""
        manager1 = get_progress_manager()
        manager2 = get_progress_manager()
        
        assert manager1 is manager2

    def test_global_manager_is_rate_limit_progress_manager(self):
        """Test that global manager is correct type."""
        manager = get_progress_manager()
        
        assert isinstance(manager, RateLimitProgressManager)


class TestEnhancedProgressFeedback:
    """Test enhanced progress feedback functionality."""

    @pytest.mark.asyncio
    async def test_detailed_rate_limit_logging(self):
        """Test detailed logging of rate limit events."""
        tracker = RateLimitProgressTracker(show_progress=False)  # Disable output for test
        
        reset_time = int(time.time()) + 300  # 5 minutes from now
        
        with patch('forklift.github.rate_limit_progress.logger') as mock_logger:
            tracker._log_rate_limit_event(300.0, reset_time, "test operation")
            
            # Verify detailed logging was called
            mock_logger.info.assert_called_once()
            log_call = mock_logger.info.call_args[0][0]
            
            assert "rate_limit_hit" in log_call
            assert "test operation" in log_call
            assert "300.0" in log_call

    @pytest.mark.asyncio
    async def test_countdown_timer_display(self):
        """Test countdown timer display for long waits."""
        tracker = RateLimitProgressTracker(show_progress=True)
        
        captured_output = StringIO()
        with patch('sys.stdout', captured_output):
            # Start tracking a long wait
            task = asyncio.create_task(
                tracker.track_rate_limit_wait(120.0, operation_name="test operation")
            )
            
            # Let it start and show initial message
            await asyncio.sleep(0.2)
            
            # Cancel the task
            task.cancel()
            
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        output = captured_output.getvalue()
        
        # Verify enhanced initial message
        assert "GitHub API Rate Limit Reached" in output
        assert "What's happening:" in output
        assert "GitHub limits API requests" in output
        assert "will retry automatically" in output

    @pytest.mark.asyncio
    async def test_periodic_progress_updates_long_wait(self):
        """Test periodic progress updates for long waits (>60 seconds)."""
        tracker = RateLimitProgressTracker(show_progress=True)
        
        captured_output = StringIO()
        with patch('sys.stdout', captured_output):
            # Start tracking a long wait
            task = asyncio.create_task(
                tracker.track_rate_limit_wait(180.0, operation_name="long operation")
            )
            
            # Let it start and show some progress
            await asyncio.sleep(0.3)
            
            # Cancel the task
            task.cancel()
            
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        output = captured_output.getvalue()
        
        # Verify long wait handling
        assert "Progress (updates every 30 seconds)" in output
        assert "remaining" in output
        assert "elapsed" in output

    @pytest.mark.asyncio
    async def test_enhanced_completion_message(self):
        """Test enhanced completion message with timing information."""
        tracker = RateLimitProgressTracker(show_progress=True)
        
        # Set up timing information
        tracker._start_time = time.time() - 60  # Simulate 60 second wait
        tracker._total_wait_time = 65.0  # Expected 65 seconds
        
        captured_output = StringIO()
        with patch('sys.stdout', captured_output):
            with patch('forklift.github.rate_limit_progress.logger') as mock_logger:
                await tracker.show_completion_message("test operation")
        
        output = captured_output.getvalue()
        
        # Verify enhanced completion message
        assert "Rate Limit Recovery Complete" in output
        assert "API access restored" in output
        assert "Wait time:" in output
        assert "expected:" in output
        
        # Verify completion logging
        mock_logger.info.assert_called_once()
        log_call = mock_logger.info.call_args[0][0]
        assert "rate_limit_recovery" in log_call

    @pytest.mark.asyncio
    async def test_enhanced_rate_limit_info_display(self):
        """Test enhanced rate limit information display."""
        tracker = RateLimitProgressTracker(show_progress=True)
        
        reset_time = int(time.time()) + 1800  # 30 minutes from now
        
        captured_output = StringIO()
        with patch('sys.stdout', captured_output):
            with patch('forklift.github.rate_limit_progress.logger') as mock_logger:
                await tracker.show_rate_limit_info(
                    remaining=150,
                    limit=5000,
                    reset_time=reset_time
                )
        
        output = captured_output.getvalue()
        
        # Verify enhanced rate limit display
        assert "Current quota: 150/5,000" in output
        assert "Usage:" in output
        assert "4,850 requests" in output  # Used requests
        assert "97.0% of quota" in output  # Usage percentage
        assert "WARNING: Low quota" in output  # Warning for 150 remaining
        
        # Verify detailed logging
        mock_logger.info.assert_called_once()
        log_call = mock_logger.info.call_args[0][0]
        assert "rate_limit_status" in log_call

    @pytest.mark.asyncio
    async def test_rate_limit_recovery_progress(self):
        """Test rate limit recovery progress indicators."""
        tracker = RateLimitProgressTracker(show_progress=True)
        
        captured_output = StringIO()
        with patch('sys.stdout', captured_output):
            with patch('forklift.github.rate_limit_progress.logger') as mock_logger:
                await tracker.show_rate_limit_recovery_progress(
                    current_remaining=2500,
                    previous_remaining=100,
                    limit=5000,
                    operation_name="recovery test"
                )
        
        output = captured_output.getvalue()
        
        # Verify recovery progress display
        assert "Rate Limit Recovery Detected" in output
        assert "Quota recovered: +2400 requests" in output
        assert "Current quota: 2,500/5,000" in output
        assert "Recovery level: 50.0%" in output
        assert "Partial recovery" in output
        
        # Verify recovery logging
        mock_logger.info.assert_called_once()
        log_call = mock_logger.info.call_args[0][0]
        assert "rate_limit_recovery_progress" in log_call

    @pytest.mark.asyncio
    async def test_critical_rate_limit_warnings(self):
        """Test critical rate limit warning messages."""
        tracker = RateLimitProgressTracker(show_progress=True)
        
        # Test zero remaining requests
        captured_output = StringIO()
        with patch('sys.stdout', captured_output):
            await tracker.show_rate_limit_info(
                remaining=0,
                limit=5000
            )
        
        output = captured_output.getvalue()
        assert "CRITICAL: No requests remaining" in output
        assert "operations will be blocked" in output

    @pytest.mark.asyncio
    async def test_user_friendly_explanations(self):
        """Test user-friendly explanations in rate limit messages."""
        tracker = RateLimitProgressTracker(show_progress=True)
        
        captured_output = StringIO()
        with patch('sys.stdout', captured_output):
            # Test initial message explanation
            task = asyncio.create_task(
                tracker.track_rate_limit_wait(30.0, operation_name="explanation test")
            )
            
            await asyncio.sleep(0.1)
            task.cancel()
            
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        output = captured_output.getvalue()
        
        # Verify user-friendly explanations
        assert "What's happening:" in output
        assert "GitHub limits API requests to prevent server overload" in output
        assert "This is normal behavior" in output
        assert "helps maintain API stability" in output

    def test_format_duration_enhanced(self):
        """Test enhanced duration formatting."""
        tracker = RateLimitProgressTracker()
        
        # Test various durations
        assert tracker._format_duration(0) == "0s"
        assert tracker._format_duration(45) == "45s"
        assert tracker._format_duration(90) == "1m 30s"
        assert tracker._format_duration(3661) == "1h 1m"
        assert tracker._format_duration(7200) == "2h 0m"


class TestProgressIntegration:
    """Test integration scenarios for progress tracking."""

    @pytest.mark.asyncio
    async def test_multiple_operations_progress_tracking(self):
        """Test progress tracking for multiple concurrent operations."""
        manager = RateLimitProgressManager()
        
        # Start tracking multiple operations
        tracker1 = manager.get_tracker("operation1")
        tracker2 = manager.get_tracker("operation2")
        
        # Both should be different trackers
        assert tracker1 is not tracker2
        assert len(manager._trackers) == 2
        
        # Clean up one operation
        manager.cleanup_tracker("operation1")
        assert len(manager._trackers) == 1
        assert "operation2" in manager._trackers

    @pytest.mark.asyncio
    async def test_progress_tracking_with_cancellation(self):
        """Test progress tracking handles cancellation gracefully."""
        tracker = RateLimitProgressTracker(show_progress=True)
        
        # Start a long progress tracking task
        task = asyncio.create_task(
            tracker.track_rate_limit_wait(60.0, operation_name="test")
        )
        
        # Let it start
        await asyncio.sleep(0.1)
        
        # Cancel progress
        tracker.cancel_progress()
        
        # Cancel the task
        task.cancel()
        
        # Should handle cancellation gracefully
        try:
            await task
        except asyncio.CancelledError:
            pass  # Expected
        
        assert tracker._cancelled is True

    @pytest.mark.asyncio
    async def test_end_to_end_rate_limit_progress_flow(self):
        """Test complete rate limit progress flow from start to finish."""
        manager = RateLimitProgressManager()
        tracker = manager.get_tracker("e2e_test", show_progress=True)
        
        captured_output = StringIO()
        with patch('sys.stdout', captured_output):
            with patch('forklift.github.rate_limit_progress.logger') as mock_logger:
                # Show initial rate limit info
                await tracker.show_rate_limit_info(
                    remaining=0,
                    limit=5000,
                    reset_time=int(time.time()) + 60
                )
                
                # Start rate limit wait
                task = asyncio.create_task(
                    tracker.track_rate_limit_wait(10.0, operation_name="e2e_test")
                )
                
                # Let it run briefly
                await asyncio.sleep(0.2)
                
                # Cancel and complete
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                
                # Show completion
                await tracker.show_completion_message("e2e_test")
                
                # Show recovery
                await tracker.show_rate_limit_recovery_progress(
                    current_remaining=5000,
                    previous_remaining=0,
                    limit=5000,
                    operation_name="e2e_test"
                )
        
        output = captured_output.getvalue()
        
        # Verify complete flow
        assert "CRITICAL: No requests remaining" in output
        assert "GitHub API Rate Limit Reached" in output
        assert "Rate Limit Recovery Complete" in output
        assert "Rate Limit Recovery Detected" in output
        
        # Verify logging occurred at each step
        assert mock_logger.info.call_count >= 3  # Status, event, recovery logs
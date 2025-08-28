"""Progress feedback for rate limiting operations."""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)


class RateLimitProgressTracker:
    """Tracks and displays progress during rate limit waits."""

    def __init__(self, show_progress: bool = True):
        """Initialize progress tracker.
        
        Args:
            show_progress: Whether to show progress messages to user
        """
        self.show_progress = show_progress
        self._progress_task: Optional[asyncio.Task] = None
        self._cancelled = False

    async def track_rate_limit_wait(
        self,
        wait_seconds: float,
        reset_time: Optional[int] = None,
        operation_name: str = "API request"
    ) -> None:
        """Track progress during a rate limit wait.
        
        Args:
            wait_seconds: Number of seconds to wait
            reset_time: Unix timestamp when rate limit resets (optional)
            operation_name: Name of the operation being rate limited
        """
        if not self.show_progress or wait_seconds < 5:
            # Don't show progress for very short waits
            return

        self._cancelled = False
        
        # Start progress tracking task
        self._progress_task = asyncio.create_task(
            self._show_progress_updates(wait_seconds, reset_time, operation_name)
        )

    async def _show_progress_updates(
        self,
        wait_seconds: float,
        reset_time: Optional[int],
        operation_name: str
    ) -> None:
        """Show periodic progress updates during rate limit wait."""
        try:
            start_time = time.time()
            
            # Show initial message
            if reset_time:
                reset_datetime = datetime.fromtimestamp(reset_time)
                print(f"\n⏳ Rate limit reached for {operation_name}")
                print(f"   Waiting until {reset_datetime.strftime('%H:%M:%S')} ({wait_seconds:.0f} seconds)")
            else:
                print(f"\n⏳ Rate limit reached for {operation_name}")
                print(f"   Waiting {wait_seconds:.0f} seconds before retrying...")

            # Show countdown for waits longer than 60 seconds
            if wait_seconds > 60:
                await self._show_countdown(start_time, wait_seconds)
            else:
                # For shorter waits, just show a simple progress
                await self._show_simple_progress(start_time, wait_seconds)

        except asyncio.CancelledError:
            # Progress tracking was cancelled (normal when wait completes)
            pass
        except Exception as e:
            logger.debug(f"Error in progress tracking: {e}")

    async def _show_countdown(self, start_time: float, total_seconds: float) -> None:
        """Show countdown timer for long waits."""
        update_interval = 30  # Update every 30 seconds for long waits
        
        while not self._cancelled:
            elapsed = time.time() - start_time
            remaining = max(0, total_seconds - elapsed)
            
            if remaining <= 0:
                break
                
            # Format remaining time
            remaining_str = self._format_duration(remaining)
            progress_percent = (elapsed / total_seconds) * 100
            
            # Show progress bar
            bar_width = 30
            filled_width = int((progress_percent / 100) * bar_width)
            bar = "█" * filled_width + "░" * (bar_width - filled_width)
            
            print(f"\r   [{bar}] {progress_percent:.1f}% - {remaining_str} remaining", end="", flush=True)
            
            # Wait for next update or until completion
            await asyncio.sleep(min(update_interval, remaining))

    async def _show_simple_progress(self, start_time: float, total_seconds: float) -> None:
        """Show simple progress for shorter waits."""
        update_interval = 5  # Update every 5 seconds for short waits
        
        while not self._cancelled:
            elapsed = time.time() - start_time
            remaining = max(0, total_seconds - elapsed)
            
            if remaining <= 0:
                break
                
            remaining_str = self._format_duration(remaining)
            print(f"\r   ⏱️  {remaining_str} remaining...", end="", flush=True)
            
            await asyncio.sleep(min(update_interval, remaining))

    def _format_duration(self, seconds: float) -> str:
        """Format duration in human-readable format."""
        if seconds < 60:
            return f"{seconds:.0f}s"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{minutes}m {secs}s"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours}h {minutes}m"

    def cancel_progress(self) -> None:
        """Cancel progress tracking."""
        self._cancelled = True
        if self._progress_task and not self._progress_task.done():
            self._progress_task.cancel()

    async def show_completion_message(self, operation_name: str) -> None:
        """Show completion message when rate limit wait is over."""
        if self.show_progress:
            print(f"\n✅ Rate limit wait complete, resuming {operation_name}...")

    async def show_rate_limit_info(
        self,
        remaining: int,
        limit: int,
        reset_time: Optional[int] = None
    ) -> None:
        """Show current rate limit status information."""
        if not self.show_progress:
            return

        print(f"\n📊 GitHub API Rate Limit Status:")
        print(f"   Remaining: {remaining}/{limit} requests")
        
        if reset_time:
            reset_datetime = datetime.fromtimestamp(reset_time)
            time_until_reset = reset_time - time.time()
            if time_until_reset > 0:
                reset_str = self._format_duration(time_until_reset)
                print(f"   Resets in: {reset_str} (at {reset_datetime.strftime('%H:%M:%S')})")
            else:
                print(f"   Reset time: {reset_datetime.strftime('%H:%M:%S')} (should reset soon)")

        # Show warning if getting low
        if remaining < 100:
            print(f"   ⚠️  Warning: Low on API quota ({remaining} requests remaining)")
        elif remaining < 500:
            print(f"   ℹ️  Note: {remaining} requests remaining")


class RateLimitProgressManager:
    """Manages rate limit progress tracking across the application."""

    def __init__(self):
        """Initialize progress manager."""
        self._trackers: dict[str, RateLimitProgressTracker] = {}

    def get_tracker(self, operation_id: str, show_progress: bool = True) -> RateLimitProgressTracker:
        """Get or create a progress tracker for an operation.
        
        Args:
            operation_id: Unique identifier for the operation
            show_progress: Whether to show progress for this operation
            
        Returns:
            Progress tracker instance
        """
        if operation_id not in self._trackers:
            self._trackers[operation_id] = RateLimitProgressTracker(show_progress)
        return self._trackers[operation_id]

    def cancel_all_progress(self) -> None:
        """Cancel all active progress tracking."""
        for tracker in self._trackers.values():
            tracker.cancel_progress()

    def cleanup_tracker(self, operation_id: str) -> None:
        """Clean up a completed tracker."""
        if operation_id in self._trackers:
            self._trackers[operation_id].cancel_progress()
            del self._trackers[operation_id]


# Global progress manager instance
_progress_manager = RateLimitProgressManager()


def get_progress_manager() -> RateLimitProgressManager:
    """Get the global progress manager instance."""
    return _progress_manager
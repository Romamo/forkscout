"""Progress feedback for rate limiting operations."""

import asyncio
import logging
import time
from datetime import datetime

logger = logging.getLogger(__name__)


class RateLimitProgressTracker:
    """Tracks and displays progress during rate limit waits."""

    def __init__(self, show_progress: bool = True):
        """Initialize progress tracker.

        Args:
            show_progress: Whether to show progress messages to user
        """
        self.show_progress = show_progress
        self._progress_task: asyncio.Task | None = None
        self._cancelled = False
        self._start_time: float | None = None
        self._total_wait_time: float | None = None

    async def track_rate_limit_wait(
        self,
        wait_seconds: float,
        reset_time: int | None = None,
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
        self._start_time = time.time()
        self._total_wait_time = wait_seconds

        # Log detailed rate limit event
        self._log_rate_limit_event(wait_seconds, reset_time, operation_name)

        # Start progress tracking task
        self._progress_task = asyncio.create_task(
            self._show_progress_updates(wait_seconds, reset_time, operation_name)
        )

    def _log_rate_limit_event(
        self,
        wait_seconds: float,
        reset_time: int | None,
        operation_name: str
    ) -> None:
        """Log detailed rate limit event information.

        Args:
            wait_seconds: Number of seconds to wait
            reset_time: Unix timestamp when rate limit resets (optional)
            operation_name: Name of the operation being rate limited
        """
        log_data = {
            "event": "rate_limit_hit",
            "operation": operation_name,
            "wait_time_seconds": wait_seconds,
            "start_time": datetime.now().isoformat(),
        }

        if reset_time:
            reset_datetime = datetime.fromtimestamp(reset_time)
            log_data.update({
                "reset_time": reset_datetime.isoformat(),
                "reset_timestamp": reset_time,
                "time_until_reset": reset_time - time.time()
            })

        logger.info(f"Rate limit event: {log_data}")

    async def _show_progress_updates(
        self,
        wait_seconds: float,
        reset_time: int | None,
        operation_name: str
    ) -> None:
        """Show periodic progress updates during rate limit wait."""
        try:
            start_time = time.time()

            # Show initial user-friendly message with explanation
            self._show_initial_rate_limit_message(wait_seconds, reset_time, operation_name)

            # Show countdown for waits longer than 60 seconds
            if wait_seconds > 60:
                await self._show_countdown_with_periodic_updates(start_time, wait_seconds, operation_name)
            else:
                # For shorter waits, show enhanced simple progress
                await self._show_enhanced_simple_progress(start_time, wait_seconds, operation_name)

        except asyncio.CancelledError:
            # Progress tracking was cancelled (normal when wait completes)
            pass
        except Exception as e:
            logger.debug(f"Error in progress tracking: {e}")

    def _show_initial_rate_limit_message(
        self,
        wait_seconds: float,
        reset_time: int | None,
        operation_name: str
    ) -> None:
        """Show initial user-friendly rate limit message with explanation."""
        print("\n🚦 GitHub API Rate Limit Reached")
        print(f"   Operation: {operation_name}")
        print("   ")
        print("   📋 What's happening:")
        print("      GitHub limits API requests to prevent server overload.")
        print("      Your application has reached the current rate limit.")
        print("   ")

        if reset_time:
            reset_datetime = datetime.fromtimestamp(reset_time)
            current_time = datetime.now()

            print("   ⏰ Rate limit details:")
            print(f"      Current time: {current_time.strftime('%H:%M:%S')}")
            print(f"      Reset time:   {reset_datetime.strftime('%H:%M:%S')}")
            print(f"      Wait time:    {self._format_duration(wait_seconds)}")
            print("   ")
            print("   🔄 The application will automatically resume when the limit resets.")
        else:
            print(f"   ⏰ Estimated wait time: {self._format_duration(wait_seconds)}")
            print("   ")
            print("   🔄 Using exponential backoff - the application will retry automatically.")

        print("   💡 This is normal behavior and helps maintain API stability.")
        print("   ")

    async def _show_countdown_with_periodic_updates(
        self,
        start_time: float,
        total_seconds: float,
        operation_name: str
    ) -> None:
        """Show countdown timer with periodic updates for long waits."""
        update_interval = 30  # Update every 30 seconds for long waits
        last_update_time = start_time

        print("   ⏳ Progress (updates every 30 seconds):")

        while not self._cancelled:
            current_time = time.time()
            elapsed = current_time - start_time
            remaining = max(0, total_seconds - elapsed)

            if remaining <= 0:
                break

            # Format remaining time
            remaining_str = self._format_duration(remaining)
            elapsed_str = self._format_duration(elapsed)
            progress_percent = (elapsed / total_seconds) * 100

            # Show enhanced progress bar with countdown
            bar_width = 40
            filled_width = int((progress_percent / 100) * bar_width)
            bar = "█" * filled_width + "░" * (bar_width - filled_width)

            # Show periodic detailed update every 30 seconds
            if current_time - last_update_time >= update_interval or elapsed < 1:
                print(f"\r   [{bar}] {progress_percent:.1f}%", end="")
                print(f" | ⏱️  {remaining_str} remaining | ✅ {elapsed_str} elapsed")

                # Show encouraging message for very long waits
                if remaining > 300:  # More than 5 minutes
                    print("      💪 Hang tight! GitHub will restore API access soon.")
                elif remaining > 60:  # More than 1 minute
                    print("      🔜 Almost there! Rate limit will reset shortly.")

                last_update_time = current_time
            else:
                # Just update the progress bar without newline
                print(f"\r   [{bar}] {progress_percent:.1f}% | ⏱️  {remaining_str} remaining", end="", flush=True)

            # Wait for next update or until completion
            await asyncio.sleep(min(5, remaining))  # Check every 5 seconds, update display every 30

    async def _show_enhanced_simple_progress(
        self,
        start_time: float,
        total_seconds: float,
        operation_name: str
    ) -> None:
        """Show enhanced simple progress for shorter waits."""
        update_interval = 3  # Update every 3 seconds for short waits

        print("   ⏳ Countdown timer:")

        while not self._cancelled:
            current_time = time.time()
            elapsed = current_time - start_time
            remaining = max(0, total_seconds - elapsed)

            if remaining <= 0:
                break

            remaining_str = self._format_duration(remaining)
            progress_percent = (elapsed / total_seconds) * 100

            # Show simple progress bar for short waits
            bar_width = 20
            filled_width = int((progress_percent / 100) * bar_width)
            bar = "█" * filled_width + "░" * (bar_width - filled_width)

            print(f"\r      [{bar}] {progress_percent:.0f}% | ⏱️  {remaining_str} remaining", end="", flush=True)

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
            # Calculate actual wait time
            actual_wait_time = None
            if self._start_time and self._total_wait_time:
                actual_wait_time = time.time() - self._start_time

            print("\n")  # New line after progress bar
            print("✅ Rate Limit Recovery Complete!")
            print(f"   Operation: {operation_name}")

            if actual_wait_time:
                actual_wait_str = self._format_duration(actual_wait_time)
                expected_wait_str = self._format_duration(self._total_wait_time)
                print(f"   Wait time: {actual_wait_str} (expected: {expected_wait_str})")

            print("   Status: API access restored - resuming operations")
            print(f"   🚀 Continuing with {operation_name}...")

            # Log completion event
            completion_data = {
                "event": "rate_limit_recovery",
                "operation": operation_name,
                "completion_time": datetime.now().isoformat(),
            }

            if actual_wait_time:
                completion_data.update({
                    "actual_wait_seconds": actual_wait_time,
                    "expected_wait_seconds": self._total_wait_time,
                    "wait_accuracy": abs(actual_wait_time - self._total_wait_time)
                })

            logger.info(f"Rate limit recovery: {completion_data}")
            print("")

    async def show_rate_limit_info(
        self,
        remaining: int,
        limit: int,
        reset_time: int | None = None
    ) -> None:
        """Show current rate limit status information."""
        if not self.show_progress:
            return

        print("\n📊 GitHub API Rate Limit Status:")
        print(f"   Current quota: {remaining:,}/{limit:,} requests")

        # Calculate usage percentage
        used = limit - remaining
        usage_percent = (used / limit) * 100 if limit > 0 else 0

        print(f"   Usage: {used:,} requests ({usage_percent:.1f}% of quota)")

        if reset_time:
            reset_datetime = datetime.fromtimestamp(reset_time)
            current_time = datetime.now()
            time_until_reset = reset_time - time.time()

            if time_until_reset > 0:
                reset_str = self._format_duration(time_until_reset)
                print(f"   Reset time: {reset_datetime.strftime('%H:%M:%S')} ({reset_str} from now)")
                print(f"   Current time: {current_time.strftime('%H:%M:%S')}")
            else:
                print(f"   Reset time: {reset_datetime.strftime('%H:%M:%S')} (should reset momentarily)")

        # Enhanced warning messages with context
        if remaining == 0:
            print("   🚫 CRITICAL: No requests remaining - operations will be blocked")
            print("      All API calls will wait until quota resets")
        elif remaining < 50:
            print(f"   🔴 URGENT: Very low quota ({remaining} requests remaining)")
            print("      Consider reducing API usage or waiting for reset")
        elif remaining < 200:
            print(f"   🟡 WARNING: Low quota ({remaining} requests remaining)")
            print("      Monitor usage carefully to avoid hitting limits")
        elif remaining < 1000:
            print(f"   🟠 NOTICE: Moderate quota usage ({remaining} requests remaining)")
            print("      You have sufficient quota but consider pacing requests")
        else:
            print(f"   🟢 GOOD: Healthy quota level ({remaining:,} requests remaining)")

        # Log detailed rate limit status
        status_data = {
            "event": "rate_limit_status",
            "remaining": remaining,
            "limit": limit,
            "used": used,
            "usage_percent": usage_percent,
            "timestamp": datetime.now().isoformat(),
        }

        if reset_time:
            status_data.update({
                "reset_time": datetime.fromtimestamp(reset_time).isoformat(),
                "reset_timestamp": reset_time,
                "seconds_until_reset": time_until_reset
            })

        logger.info(f"Rate limit status: {status_data}")

    async def show_rate_limit_recovery_progress(
        self,
        current_remaining: int,
        previous_remaining: int,
        limit: int,
        operation_name: str
    ) -> None:
        """Show progress indicators for rate limit recovery.

        Args:
            current_remaining: Current number of remaining requests
            previous_remaining: Previous number of remaining requests
            limit: Total rate limit
            operation_name: Name of the operation
        """
        if not self.show_progress:
            return

        # Calculate recovery
        recovered_requests = current_remaining - previous_remaining

        if recovered_requests > 0:
            print("\n🔄 Rate Limit Recovery Detected!")
            print(f"   Operation: {operation_name}")
            print(f"   Quota recovered: +{recovered_requests} requests")
            print(f"   Current quota: {current_remaining:,}/{limit:,} requests")

            # Show recovery percentage
            recovery_percent = (current_remaining / limit) * 100 if limit > 0 else 0
            print(f"   Recovery level: {recovery_percent:.1f}% of full quota")

            # Show status based on recovery level
            if recovery_percent >= 90:
                print("   🟢 Status: Full quota restored - all operations available")
            elif recovery_percent >= 50:
                print("   🟡 Status: Partial recovery - operations can resume")
            else:
                print("   🟠 Status: Limited recovery - proceed with caution")

            print(f"   ✅ Resuming {operation_name}...")

            # Log recovery event
            recovery_data = {
                "event": "rate_limit_recovery_progress",
                "operation": operation_name,
                "recovered_requests": recovered_requests,
                "current_remaining": current_remaining,
                "previous_remaining": previous_remaining,
                "limit": limit,
                "recovery_percent": recovery_percent,
                "timestamp": datetime.now().isoformat(),
            }

            logger.info(f"Rate limit recovery progress: {recovery_data}")


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

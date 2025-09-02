"""Adaptive progress reporting system for different interaction modes."""

import sys
from abc import ABC, abstractmethod
from typing import TextIO

from .interaction_mode import InteractionMode, get_interaction_mode_detector


class ProgressReporter(ABC):
    """Abstract base class for progress reporting."""

    @abstractmethod
    def start_operation(self, operation_name: str, total_items: int | None = None) -> None:
        """Start a new operation with progress tracking.

        Args:
            operation_name: Name of the operation being performed
            total_items: Total number of items to process (if known)
        """
        pass

    @abstractmethod
    def update_progress(self, current: int, message: str | None = None) -> None:
        """Update the progress of the current operation.

        Args:
            current: Current number of items processed
            message: Optional status message
        """
        pass

    @abstractmethod
    def complete_operation(self, message: str | None = None) -> None:
        """Complete the current operation.

        Args:
            message: Optional completion message
        """
        pass

    @abstractmethod
    def log_message(self, message: str, level: str = "info") -> None:
        """Log a message during operation.

        Args:
            message: Message to log
            level: Log level (info, warning, error)
        """
        pass


class RichProgressReporter(ProgressReporter):
    """Progress reporter for fully interactive mode with rich progress bars."""

    def __init__(self):
        """Initialize the rich progress reporter."""
        self.current_operation: str | None = None
        self.total_items: int | None = None
        self.current_count: int = 0
        self._use_rich = self._check_rich_availability()

    def _check_rich_availability(self) -> bool:
        """Check if rich library is available."""
        try:
            import rich  # noqa: F401
            return True
        except ImportError:
            return False

    def start_operation(self, operation_name: str, total_items: int | None = None) -> None:
        """Start a new operation with rich progress tracking."""
        self.current_operation = operation_name
        self.total_items = total_items
        self.current_count = 0

        if self._use_rich:
            try:
                from rich.console import Console
                from rich.progress import (
                    BarColumn,
                    Progress,
                    SpinnerColumn,
                    TaskProgressColumn,
                    TextColumn,
                )

                self.console = Console(soft_wrap=False)
                self.progress = Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn() if total_items else TextColumn(""),
                    TaskProgressColumn() if total_items else TextColumn(""),
                    console=self.console
                )
                self.progress.start()
                self.task_id = self.progress.add_task(
                    operation_name,
                    total=total_items if total_items else None
                )
            except ImportError:
                self._use_rich = False
                self._fallback_start(operation_name, total_items)
        else:
            self._fallback_start(operation_name, total_items)

    def _fallback_start(self, operation_name: str, total_items: int | None = None) -> None:
        """Fallback start method when rich is not available."""
        total_text = f" (0/{total_items})" if total_items else ""
        print(f"Starting {operation_name}{total_text}", file=sys.stderr)

    def update_progress(self, current: int, message: str | None = None) -> None:
        """Update progress with rich display."""
        self.current_count = current

        if self._use_rich and hasattr(self, "progress"):
            try:
                description = self.current_operation or "Processing"
                if message:
                    description = f"{description}: {message}"

                self.progress.update(
                    self.task_id,
                    completed=current,
                    description=description
                )
            except Exception:
                self._fallback_update(current, message)
        else:
            self._fallback_update(current, message)

    def _fallback_update(self, current: int, message: str | None = None) -> None:
        """Fallback update method when rich is not available."""
        total_text = f"/{self.total_items}" if self.total_items else ""
        msg_text = f" - {message}" if message else ""
        print(f"Progress: {current}{total_text}{msg_text}", file=sys.stderr)

    def complete_operation(self, message: str | None = None) -> None:
        """Complete the operation with rich display."""
        if self._use_rich and hasattr(self, "progress"):
            try:
                if hasattr(self, "task_id"):
                    if self.total_items:
                        self.progress.update(self.task_id, completed=self.total_items)
                    final_message = message or f"Completed {self.current_operation}"
                    self.progress.update(self.task_id, description=final_message)
                self.progress.stop()
            except Exception:
                self._fallback_complete(message)
        else:
            self._fallback_complete(message)

        # Reset state
        self.current_operation = None
        self.total_items = None
        self.current_count = 0

    def _fallback_complete(self, message: str | None = None) -> None:
        """Fallback complete method when rich is not available."""
        final_message = message or f"Completed {self.current_operation}"
        print(final_message, file=sys.stderr)

    def log_message(self, message: str, level: str = "info") -> None:
        """Log a message with rich formatting."""
        if self._use_rich:
            try:
                from rich.console import Console
                console = Console(file=sys.stderr, soft_wrap=False)

                if level == "error":
                    console.print(f"[red]ERROR:[/red] {message}")
                elif level == "warning":
                    console.print(f"[yellow]WARNING:[/yellow] {message}")
                else:
                    console.print(f"[blue]INFO:[/blue] {message}")
            except Exception:
                self._fallback_log(message, level)
        else:
            self._fallback_log(message, level)

    def _fallback_log(self, message: str, level: str = "info") -> None:
        """Fallback log method when rich is not available."""
        prefix = level.upper()
        print(f"{prefix}: {message}", file=sys.stderr)


class PlainTextProgressReporter(ProgressReporter):
    """Progress reporter for non-interactive mode with simple text messages."""

    def __init__(self, output_stream: TextIO = sys.stderr):
        """Initialize the plain text progress reporter.

        Args:
            output_stream: Stream to write progress messages to
        """
        self.output_stream = output_stream
        self.current_operation: str | None = None
        self.total_items: int | None = None
        self.current_count: int = 0
        self.last_reported_percent: int = -1

    def start_operation(self, operation_name: str, total_items: int | None = None) -> None:
        """Start operation with simple text output."""
        self.current_operation = operation_name
        self.total_items = total_items
        self.current_count = 0
        self.last_reported_percent = -1

        total_text = f" ({total_items} items)" if total_items and total_items > 0 else ""
        print(f"Starting {operation_name}{total_text}", file=self.output_stream)
        self.output_stream.flush()

    def update_progress(self, current: int, message: str | None = None) -> None:
        """Update progress with periodic text updates."""
        self.current_count = current

        # Only report progress at certain intervals to avoid spam
        should_report = False

        if self.total_items and self.total_items > 0:
            percent = int((current / self.total_items) * 100)
            # Report every 10% or on significant milestones
            if percent != self.last_reported_percent and (
                percent % 10 == 0 or
                percent in [1, 5, 25, 50, 75, 90, 95, 99]
            ):
                should_report = True
                self.last_reported_percent = percent
        else:
            # For unknown totals, report every 10 items or on message changes
            if current % 10 == 0 or message:
                should_report = True

        # Always report if there's a message
        if message:
            should_report = True

        if should_report:
            if self.total_items and self.total_items > 0:
                percent = int((current / self.total_items) * 100)
                progress_text = f"Progress: {current}/{self.total_items} ({percent}%)"
            else:
                progress_text = f"Processing: {current} items"

            if message:
                progress_text += f" - {message}"

            print(progress_text, file=self.output_stream)
            self.output_stream.flush()

    def complete_operation(self, message: str | None = None) -> None:
        """Complete operation with final message."""
        final_message = message or f"Completed {self.current_operation}"
        if self.total_items and self.total_items > 0:
            final_message += f" ({self.total_items} items processed)"

        print(final_message, file=self.output_stream)
        self.output_stream.flush()

        # Reset state
        self.current_operation = None
        self.total_items = None
        self.current_count = 0
        self.last_reported_percent = -1

    def log_message(self, message: str, level: str = "info") -> None:
        """Log a message with simple text formatting."""
        prefix = level.upper()
        print(f"{prefix}: {message}", file=self.output_stream)
        self.output_stream.flush()


class StderrProgressReporter(ProgressReporter):
    """Progress reporter for output-redirected mode (progress to stderr, data to stdout)."""

    def __init__(self):
        """Initialize the stderr progress reporter."""
        self.progress_reporter = PlainTextProgressReporter(sys.stderr)

    def start_operation(self, operation_name: str, total_items: int | None = None) -> None:
        """Start operation with progress to stderr."""
        self.progress_reporter.start_operation(operation_name, total_items)

    def update_progress(self, current: int, message: str | None = None) -> None:
        """Update progress to stderr."""
        self.progress_reporter.update_progress(current, message)

    def complete_operation(self, message: str | None = None) -> None:
        """Complete operation with message to stderr."""
        self.progress_reporter.complete_operation(message)

    def log_message(self, message: str, level: str = "info") -> None:
        """Log message to stderr."""
        self.progress_reporter.log_message(message, level)


class ProgressReporterFactory:
    """Factory for creating appropriate progress reporters based on interaction mode."""

    @staticmethod
    def create_reporter() -> ProgressReporter:
        """Create the appropriate progress reporter for the current interaction mode.

        Returns:
            ProgressReporter instance suitable for the current mode
        """
        detector = get_interaction_mode_detector()
        mode = detector.get_interaction_mode()

        if mode == InteractionMode.FULLY_INTERACTIVE:
            return RichProgressReporter()
        elif mode == InteractionMode.OUTPUT_REDIRECTED:
            return StderrProgressReporter()
        elif mode == InteractionMode.INPUT_REDIRECTED:
            # Input redirected but output available - use rich if possible
            return RichProgressReporter()
        else:
            # NON_INTERACTIVE or PIPED - use plain text
            return PlainTextProgressReporter()

    @staticmethod
    def create_reporter_for_mode(mode: InteractionMode) -> ProgressReporter:
        """Create a progress reporter for a specific interaction mode.

        Args:
            mode: The interaction mode to create a reporter for

        Returns:
            ProgressReporter instance for the specified mode
        """
        if mode == InteractionMode.FULLY_INTERACTIVE:
            return RichProgressReporter()
        elif mode == InteractionMode.OUTPUT_REDIRECTED:
            return StderrProgressReporter()
        elif mode == InteractionMode.INPUT_REDIRECTED:
            return RichProgressReporter()
        else:
            return PlainTextProgressReporter()


# Global instance for easy access
_global_reporter: ProgressReporter | None = None


def get_progress_reporter() -> ProgressReporter:
    """Get the global progress reporter instance.

    Returns:
        The global ProgressReporter instance
    """
    global _global_reporter
    if _global_reporter is None:
        _global_reporter = ProgressReporterFactory.create_reporter()
    return _global_reporter


def reset_progress_reporter() -> None:
    """Reset the global progress reporter to force recreation."""
    global _global_reporter
    _global_reporter = None

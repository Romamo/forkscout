"""Terminal detection utilities for interactive mode detection."""

import os
import sys


class TerminalDetector:
    """Detect terminal capabilities and connection status."""

    @staticmethod
    def is_stdin_tty() -> bool:
        """Check if stdin is connected to a terminal."""
        return sys.stdin.isatty()

    @staticmethod
    def is_stdout_tty() -> bool:
        """Check if stdout is connected to a terminal."""
        return sys.stdout.isatty()

    @staticmethod
    def is_stderr_tty() -> bool:
        """Check if stderr is connected to a terminal."""
        return sys.stderr.isatty()

    @staticmethod
    def get_terminal_size() -> tuple[int, int] | None:
        """Get terminal dimensions if available.

        Returns:
            Tuple of (columns, lines) if terminal size can be determined, None otherwise.
        """
        try:
            size = os.get_terminal_size()
            return (size.columns, size.lines)
        except (OSError, ValueError):
            return None

    @staticmethod
    def has_color_support() -> bool:
        """Check if terminal supports color output.

        Returns:
            True if terminal likely supports color, False otherwise.
        """
        # Check common environment variables that indicate color support
        if os.getenv("NO_COLOR"):
            return False

        if os.getenv("FORCE_COLOR"):
            return True

        # Check TERM environment variable
        term = os.getenv("TERM", "").lower()
        if "color" in term or term in ["xterm", "xterm-256color", "screen", "tmux"]:
            return True

        # If stdout is not a TTY, assume no color support
        return TerminalDetector.is_stdout_tty()

    @staticmethod
    def get_parent_process_name() -> str | None:
        """Get the name of the parent process if available.

        Returns:
            Parent process name if detectable, None otherwise.
        """
        try:
            import psutil
            parent = psutil.Process().parent()
            return parent.name() if parent else None
        except (ImportError, Exception):
            # Fallback method using environment variables
            return os.getenv("_", "").split("/")[-1] if os.getenv("_") else None

    @classmethod
    def get_terminal_info(cls) -> dict:
        """Get comprehensive terminal information.

        Returns:
            Dictionary containing all terminal detection results.
        """
        return {
            "stdin_tty": cls.is_stdin_tty(),
            "stdout_tty": cls.is_stdout_tty(),
            "stderr_tty": cls.is_stderr_tty(),
            "terminal_size": cls.get_terminal_size(),
            "color_support": cls.has_color_support(),
            "parent_process": cls.get_parent_process_name(),
            "term_env": os.getenv("TERM"),
            "colorterm_env": os.getenv("COLORTERM"),
        }

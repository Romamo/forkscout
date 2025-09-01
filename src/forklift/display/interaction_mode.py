"""Interactive mode detection and classification system."""

import time
from enum import Enum

from .environment_detector import EnvironmentDetector
from .terminal_detector import TerminalDetector


class InteractionMode(Enum):
    """Enumeration of different interaction modes."""

    FULLY_INTERACTIVE = "fully_interactive"
    OUTPUT_REDIRECTED = "output_redirected"
    INPUT_REDIRECTED = "input_redirected"
    NON_INTERACTIVE = "non_interactive"
    PIPED = "piped"


class InteractiveModeDetector:
    """Detect and classify the current interaction mode."""

    def __init__(self):
        """Initialize the detector with caching."""
        self._cached_mode: InteractionMode | None = None
        self._cache_time: float | None = None
        self._cache_ttl: float = 60.0  # Cache for 60 seconds

    def get_interaction_mode(self) -> InteractionMode:
        """Get the current interaction mode with caching.

        Returns:
            The detected interaction mode.
        """
        current_time = time.time()

        # Check if we have a valid cached result
        if (self._cached_mode is not None and
            self._cache_time is not None and
            current_time - self._cache_time < self._cache_ttl):
            return self._cached_mode

        # Detect the mode
        mode = self._detect_interaction_mode()

        # Cache the result
        self._cached_mode = mode
        self._cache_time = current_time

        return mode

    def _detect_interaction_mode(self) -> InteractionMode:
        """Detect the interaction mode based on environment and terminal state.

        Detection priority:
        1. CI/automation environment -> NON_INTERACTIVE
        2. Both input and output redirected -> PIPED
        3. Only output redirected -> OUTPUT_REDIRECTED
        4. Only input redirected -> INPUT_REDIRECTED
        5. All TTYs available -> FULLY_INTERACTIVE

        Returns:
            The detected interaction mode.
        """
        # Priority 1: CI/automation environment
        if EnvironmentDetector.is_ci_environment() or EnvironmentDetector.is_automation_environment():
            return InteractionMode.NON_INTERACTIVE

        # Get TTY status
        stdin_tty = TerminalDetector.is_stdin_tty()
        stdout_tty = TerminalDetector.is_stdout_tty()
        stderr_tty = TerminalDetector.is_stderr_tty()

        # Priority 2: All TTYs available (fully interactive)
        if stdin_tty and stdout_tty:
            return InteractionMode.FULLY_INTERACTIVE

        # Priority 3: Only output redirected
        if stdin_tty and not stdout_tty:
            return InteractionMode.OUTPUT_REDIRECTED

        # Priority 4: Only input redirected
        if not stdin_tty and stdout_tty:
            return InteractionMode.INPUT_REDIRECTED

        # Priority 5: Both input and output redirected (piped) - but only if stderr is available
        if not stdin_tty and not stdout_tty and stderr_tty:
            return InteractionMode.PIPED

        # Fallback: assume non-interactive if we can't determine or no TTYs available
        return InteractionMode.NON_INTERACTIVE

    def is_interactive(self) -> bool:
        """Check if the current mode supports interactive features.

        Returns:
            True if interactive features should be enabled.
        """
        mode = self.get_interaction_mode()
        return mode in (InteractionMode.FULLY_INTERACTIVE, InteractionMode.INPUT_REDIRECTED)

    def supports_progress_bars(self) -> bool:
        """Check if the current mode supports progress bars.

        Returns:
            True if progress bars should be displayed.
        """
        mode = self.get_interaction_mode()
        return mode in (InteractionMode.FULLY_INTERACTIVE, InteractionMode.OUTPUT_REDIRECTED)

    def supports_user_prompts(self) -> bool:
        """Check if the current mode supports user prompts.

        Returns:
            True if user prompts should be displayed.
        """
        mode = self.get_interaction_mode()
        return mode in (InteractionMode.FULLY_INTERACTIVE, InteractionMode.OUTPUT_REDIRECTED)

    def should_use_colors(self) -> bool:
        """Check if the current mode supports colored output.

        Returns:
            True if colored output should be used.
        """
        mode = self.get_interaction_mode()
        if mode == InteractionMode.NON_INTERACTIVE:
            return False

        # Use terminal detector for color support
        return TerminalDetector.has_color_support()

    def get_output_stream_preference(self) -> str:
        """Get the preferred output stream for different content types.

        Returns:
            'stdout' for data output, 'stderr' for progress/status.
        """
        mode = self.get_interaction_mode()

        if mode == InteractionMode.OUTPUT_REDIRECTED:
            # When output is redirected, send progress to stderr
            return "stderr_for_progress"

        # Default: use stdout for everything
        return "stdout"

    def clear_cache(self):
        """Clear the cached interaction mode to force re-detection."""
        self._cached_mode = None
        self._cache_time = None

    def get_detection_info(self) -> dict:
        """Get detailed information about the detection process.

        Returns:
            Dictionary with detection details for debugging.
        """
        terminal_info = TerminalDetector.get_terminal_info()
        environment_info = EnvironmentDetector.get_environment_info()

        return {
            "detected_mode": self.get_interaction_mode().value,
            "is_interactive": self.is_interactive(),
            "supports_progress_bars": self.supports_progress_bars(),
            "supports_user_prompts": self.supports_user_prompts(),
            "should_use_colors": self.should_use_colors(),
            "output_stream_preference": self.get_output_stream_preference(),
            "terminal_info": terminal_info,
            "environment_info": environment_info,
            "cache_info": {
                "cached_mode": self._cached_mode.value if self._cached_mode else None,
                "cache_time": self._cache_time,
                "cache_ttl": self._cache_ttl,
            }
        }


# Global instance for easy access
_detector_instance: InteractiveModeDetector | None = None


def get_interaction_mode_detector() -> InteractiveModeDetector:
    """Get the global interaction mode detector instance.

    Returns:
        The global InteractiveModeDetector instance.
    """
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = InteractiveModeDetector()
    return _detector_instance


def get_current_interaction_mode() -> InteractionMode:
    """Get the current interaction mode using the global detector.

    Returns:
        The current interaction mode.
    """
    return get_interaction_mode_detector().get_interaction_mode()

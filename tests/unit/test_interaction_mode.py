"""Tests for interaction mode detection and classification."""

import time
from unittest.mock import patch, Mock
import pytest

from src.forklift.display.interaction_mode import (
    InteractionMode,
    InteractiveModeDetector,
    get_interaction_mode_detector,
    get_current_interaction_mode
)


class TestInteractionMode:
    """Test InteractionMode enum."""
    
    def test_interaction_mode_values(self):
        """Test that all interaction modes have correct values."""
        assert InteractionMode.FULLY_INTERACTIVE.value == "fully_interactive"
        assert InteractionMode.OUTPUT_REDIRECTED.value == "output_redirected"
        assert InteractionMode.INPUT_REDIRECTED.value == "input_redirected"
        assert InteractionMode.NON_INTERACTIVE.value == "non_interactive"
        assert InteractionMode.PIPED.value == "piped"


class TestInteractiveModeDetector:
    """Test InteractiveModeDetector class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.detector = InteractiveModeDetector()
    
    def test_init(self):
        """Test detector initialization."""
        assert self.detector._cached_mode is None
        assert self.detector._cache_time is None
        assert self.detector._cache_ttl == 60.0
    
    def test_ci_environment_detection(self):
        """Test detection in CI environment."""
        with patch('src.forklift.display.environment_detector.EnvironmentDetector.is_ci_environment', return_value=True), \
             patch('src.forklift.display.environment_detector.EnvironmentDetector.is_automation_environment', return_value=False):
            
            mode = self.detector._detect_interaction_mode()
            assert mode == InteractionMode.NON_INTERACTIVE
    
    def test_automation_environment_detection(self):
        """Test detection in automation environment."""
        with patch('src.forklift.display.environment_detector.EnvironmentDetector.is_ci_environment', return_value=False), \
             patch('src.forklift.display.environment_detector.EnvironmentDetector.is_automation_environment', return_value=True):
            
            mode = self.detector._detect_interaction_mode()
            assert mode == InteractionMode.NON_INTERACTIVE
    
    def test_piped_mode_detection(self):
        """Test detection when both input and output are redirected."""
        with patch('src.forklift.display.environment_detector.EnvironmentDetector.is_ci_environment', return_value=False), \
             patch('src.forklift.display.environment_detector.EnvironmentDetector.is_automation_environment', return_value=False), \
             patch('src.forklift.display.terminal_detector.TerminalDetector.is_stdin_tty', return_value=False), \
             patch('src.forklift.display.terminal_detector.TerminalDetector.is_stdout_tty', return_value=False), \
             patch('src.forklift.display.terminal_detector.TerminalDetector.is_stderr_tty', return_value=True):
            
            mode = self.detector._detect_interaction_mode()
            assert mode == InteractionMode.PIPED
    
    def test_output_redirected_detection(self):
        """Test detection when only output is redirected."""
        with patch('src.forklift.display.environment_detector.EnvironmentDetector.is_ci_environment', return_value=False), \
             patch('src.forklift.display.environment_detector.EnvironmentDetector.is_automation_environment', return_value=False), \
             patch('src.forklift.display.terminal_detector.TerminalDetector.is_stdin_tty', return_value=True), \
             patch('src.forklift.display.terminal_detector.TerminalDetector.is_stdout_tty', return_value=False), \
             patch('src.forklift.display.terminal_detector.TerminalDetector.is_stderr_tty', return_value=True):
            
            mode = self.detector._detect_interaction_mode()
            assert mode == InteractionMode.OUTPUT_REDIRECTED
    
    def test_input_redirected_detection(self):
        """Test detection when only input is redirected."""
        with patch('src.forklift.display.environment_detector.EnvironmentDetector.is_ci_environment', return_value=False), \
             patch('src.forklift.display.environment_detector.EnvironmentDetector.is_automation_environment', return_value=False), \
             patch('src.forklift.display.terminal_detector.TerminalDetector.is_stdin_tty', return_value=False), \
             patch('src.forklift.display.terminal_detector.TerminalDetector.is_stdout_tty', return_value=True), \
             patch('src.forklift.display.terminal_detector.TerminalDetector.is_stderr_tty', return_value=True):
            
            mode = self.detector._detect_interaction_mode()
            assert mode == InteractionMode.INPUT_REDIRECTED
    
    def test_fully_interactive_detection(self):
        """Test detection when all TTYs are available."""
        with patch('src.forklift.display.environment_detector.EnvironmentDetector.is_ci_environment', return_value=False), \
             patch('src.forklift.display.environment_detector.EnvironmentDetector.is_automation_environment', return_value=False), \
             patch('src.forklift.display.terminal_detector.TerminalDetector.is_stdin_tty', return_value=True), \
             patch('src.forklift.display.terminal_detector.TerminalDetector.is_stdout_tty', return_value=True), \
             patch('src.forklift.display.terminal_detector.TerminalDetector.is_stderr_tty', return_value=True):
            
            mode = self.detector._detect_interaction_mode()
            assert mode == InteractionMode.FULLY_INTERACTIVE
    
    def test_fallback_non_interactive(self):
        """Test fallback to non-interactive mode."""
        with patch('src.forklift.display.environment_detector.EnvironmentDetector.is_ci_environment', return_value=False), \
             patch('src.forklift.display.environment_detector.EnvironmentDetector.is_automation_environment', return_value=False), \
             patch('src.forklift.display.terminal_detector.TerminalDetector.is_stdin_tty', return_value=False), \
             patch('src.forklift.display.terminal_detector.TerminalDetector.is_stdout_tty', return_value=False), \
             patch('src.forklift.display.terminal_detector.TerminalDetector.is_stderr_tty', return_value=False):
            
            mode = self.detector._detect_interaction_mode()
            assert mode == InteractionMode.NON_INTERACTIVE
    
    def test_caching_mechanism(self):
        """Test that detection results are cached."""
        with patch.object(self.detector, '_detect_interaction_mode', return_value=InteractionMode.FULLY_INTERACTIVE) as mock_detect:
            # First call should trigger detection
            mode1 = self.detector.get_interaction_mode()
            assert mode1 == InteractionMode.FULLY_INTERACTIVE
            assert mock_detect.call_count == 1
            
            # Second call should use cache
            mode2 = self.detector.get_interaction_mode()
            assert mode2 == InteractionMode.FULLY_INTERACTIVE
            assert mock_detect.call_count == 1  # Still 1, not called again
            
            # Verify cache is set
            assert self.detector._cached_mode == InteractionMode.FULLY_INTERACTIVE
            assert self.detector._cache_time is not None
    
    def test_cache_expiration(self):
        """Test that cache expires after TTL."""
        with patch.object(self.detector, '_detect_interaction_mode', return_value=InteractionMode.FULLY_INTERACTIVE) as mock_detect:
            # Set a very short TTL for testing
            self.detector._cache_ttl = 0.1
            
            # First call
            mode1 = self.detector.get_interaction_mode()
            assert mock_detect.call_count == 1
            
            # Wait for cache to expire
            time.sleep(0.2)
            
            # Second call should trigger detection again
            mode2 = self.detector.get_interaction_mode()
            assert mock_detect.call_count == 2
    
    def test_clear_cache(self):
        """Test cache clearing functionality."""
        # Set up cache
        self.detector._cached_mode = InteractionMode.FULLY_INTERACTIVE
        self.detector._cache_time = time.time()
        
        # Clear cache
        self.detector.clear_cache()
        
        # Verify cache is cleared
        assert self.detector._cached_mode is None
        assert self.detector._cache_time is None
    
    def test_is_interactive_fully_interactive(self):
        """Test is_interactive for fully interactive mode."""
        with patch.object(self.detector, 'get_interaction_mode', return_value=InteractionMode.FULLY_INTERACTIVE):
            assert self.detector.is_interactive() is True
    
    def test_is_interactive_input_redirected(self):
        """Test is_interactive for input redirected mode."""
        with patch.object(self.detector, 'get_interaction_mode', return_value=InteractionMode.INPUT_REDIRECTED):
            assert self.detector.is_interactive() is True
    
    def test_is_interactive_non_interactive(self):
        """Test is_interactive for non-interactive mode."""
        with patch.object(self.detector, 'get_interaction_mode', return_value=InteractionMode.NON_INTERACTIVE):
            assert self.detector.is_interactive() is False
    
    def test_supports_progress_bars_fully_interactive(self):
        """Test supports_progress_bars for fully interactive mode."""
        with patch.object(self.detector, 'get_interaction_mode', return_value=InteractionMode.FULLY_INTERACTIVE):
            assert self.detector.supports_progress_bars() is True
    
    def test_supports_progress_bars_output_redirected(self):
        """Test supports_progress_bars for output redirected mode."""
        with patch.object(self.detector, 'get_interaction_mode', return_value=InteractionMode.OUTPUT_REDIRECTED):
            assert self.detector.supports_progress_bars() is True
    
    def test_supports_progress_bars_piped(self):
        """Test supports_progress_bars for piped mode."""
        with patch.object(self.detector, 'get_interaction_mode', return_value=InteractionMode.PIPED):
            assert self.detector.supports_progress_bars() is False
    
    def test_supports_user_prompts_fully_interactive(self):
        """Test supports_user_prompts for fully interactive mode."""
        with patch.object(self.detector, 'get_interaction_mode', return_value=InteractionMode.FULLY_INTERACTIVE):
            assert self.detector.supports_user_prompts() is True
    
    def test_supports_user_prompts_output_redirected(self):
        """Test supports_user_prompts for output redirected mode."""
        with patch.object(self.detector, 'get_interaction_mode', return_value=InteractionMode.OUTPUT_REDIRECTED):
            assert self.detector.supports_user_prompts() is True
    
    def test_supports_user_prompts_input_redirected(self):
        """Test supports_user_prompts for input redirected mode."""
        with patch.object(self.detector, 'get_interaction_mode', return_value=InteractionMode.INPUT_REDIRECTED):
            assert self.detector.supports_user_prompts() is False
    
    def test_should_use_colors_non_interactive(self):
        """Test should_use_colors for non-interactive mode."""
        with patch.object(self.detector, 'get_interaction_mode', return_value=InteractionMode.NON_INTERACTIVE):
            assert self.detector.should_use_colors() is False
    
    def test_should_use_colors_interactive_with_support(self):
        """Test should_use_colors for interactive mode with color support."""
        with patch.object(self.detector, 'get_interaction_mode', return_value=InteractionMode.FULLY_INTERACTIVE), \
             patch('src.forklift.display.terminal_detector.TerminalDetector.has_color_support', return_value=True):
            assert self.detector.should_use_colors() is True
    
    def test_should_use_colors_interactive_without_support(self):
        """Test should_use_colors for interactive mode without color support."""
        with patch.object(self.detector, 'get_interaction_mode', return_value=InteractionMode.FULLY_INTERACTIVE), \
             patch('src.forklift.display.terminal_detector.TerminalDetector.has_color_support', return_value=False):
            assert self.detector.should_use_colors() is False
    
    def test_get_output_stream_preference_output_redirected(self):
        """Test get_output_stream_preference for output redirected mode."""
        with patch.object(self.detector, 'get_interaction_mode', return_value=InteractionMode.OUTPUT_REDIRECTED):
            assert self.detector.get_output_stream_preference() == "stderr_for_progress"
    
    def test_get_output_stream_preference_default(self):
        """Test get_output_stream_preference for default modes."""
        with patch.object(self.detector, 'get_interaction_mode', return_value=InteractionMode.FULLY_INTERACTIVE):
            assert self.detector.get_output_stream_preference() == "stdout"
    
    def test_get_detection_info(self):
        """Test get_detection_info method."""
        mock_terminal_info = {"stdin_tty": True, "stdout_tty": True}
        mock_environment_info = {"is_ci": False, "is_automation": False}
        
        with patch.object(self.detector, 'get_interaction_mode', return_value=InteractionMode.FULLY_INTERACTIVE), \
             patch('src.forklift.display.terminal_detector.TerminalDetector.get_terminal_info', return_value=mock_terminal_info), \
             patch('src.forklift.display.environment_detector.EnvironmentDetector.get_environment_info', return_value=mock_environment_info):
            
            info = self.detector.get_detection_info()
            
            assert info["detected_mode"] == "fully_interactive"
            assert info["is_interactive"] is True
            assert info["supports_progress_bars"] is True
            assert info["supports_user_prompts"] is True
            assert info["output_stream_preference"] == "stdout"
            assert info["terminal_info"] == mock_terminal_info
            assert info["environment_info"] == mock_environment_info
            assert "cache_info" in info


class TestGlobalFunctions:
    """Test global utility functions."""
    
    def test_get_interaction_mode_detector_singleton(self):
        """Test that get_interaction_mode_detector returns singleton."""
        detector1 = get_interaction_mode_detector()
        detector2 = get_interaction_mode_detector()
        
        assert detector1 is detector2
        assert isinstance(detector1, InteractiveModeDetector)
    
    def test_get_current_interaction_mode(self):
        """Test get_current_interaction_mode function."""
        with patch('src.forklift.display.interaction_mode.get_interaction_mode_detector') as mock_get_detector:
            mock_detector = Mock()
            mock_detector.get_interaction_mode.return_value = InteractionMode.FULLY_INTERACTIVE
            mock_get_detector.return_value = mock_detector
            
            mode = get_current_interaction_mode()
            
            assert mode == InteractionMode.FULLY_INTERACTIVE
            mock_get_detector.assert_called_once()
            mock_detector.get_interaction_mode.assert_called_once()


class TestInteractionModeDetectorEdgeCases:
    """Test edge cases and complex scenarios."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.detector = InteractiveModeDetector()
    
    def test_detection_priority_ci_over_tty(self):
        """Test that CI environment takes priority over TTY status."""
        with patch('src.forklift.display.environment_detector.EnvironmentDetector.is_ci_environment', return_value=True), \
             patch('src.forklift.display.environment_detector.EnvironmentDetector.is_automation_environment', return_value=False), \
             patch('src.forklift.display.terminal_detector.TerminalDetector.is_stdin_tty', return_value=True), \
             patch('src.forklift.display.terminal_detector.TerminalDetector.is_stdout_tty', return_value=True), \
             patch('src.forklift.display.terminal_detector.TerminalDetector.is_stderr_tty', return_value=True):
            
            mode = self.detector._detect_interaction_mode()
            assert mode == InteractionMode.NON_INTERACTIVE
    
    def test_detection_priority_automation_over_tty(self):
        """Test that automation environment takes priority over TTY status."""
        with patch('src.forklift.display.environment_detector.EnvironmentDetector.is_ci_environment', return_value=False), \
             patch('src.forklift.display.environment_detector.EnvironmentDetector.is_automation_environment', return_value=True), \
             patch('src.forklift.display.terminal_detector.TerminalDetector.is_stdin_tty', return_value=True), \
             patch('src.forklift.display.terminal_detector.TerminalDetector.is_stdout_tty', return_value=True), \
             patch('src.forklift.display.terminal_detector.TerminalDetector.is_stderr_tty', return_value=True):
            
            mode = self.detector._detect_interaction_mode()
            assert mode == InteractionMode.NON_INTERACTIVE
    
    def test_all_modes_coverage(self):
        """Test that all interaction modes can be detected."""
        test_cases = [
            # (ci, automation, stdin, stdout, stderr, expected_mode)
            (True, False, True, True, True, InteractionMode.NON_INTERACTIVE),
            (False, True, True, True, True, InteractionMode.NON_INTERACTIVE),
            (False, False, False, False, True, InteractionMode.PIPED),
            (False, False, True, False, True, InteractionMode.OUTPUT_REDIRECTED),
            (False, False, False, True, True, InteractionMode.INPUT_REDIRECTED),
            (False, False, True, True, True, InteractionMode.FULLY_INTERACTIVE),
            (False, False, False, False, False, InteractionMode.NON_INTERACTIVE),  # Fallback
        ]
        
        for ci, automation, stdin, stdout, stderr, expected in test_cases:
            with patch('src.forklift.display.environment_detector.EnvironmentDetector.is_ci_environment', return_value=ci), \
                 patch('src.forklift.display.environment_detector.EnvironmentDetector.is_automation_environment', return_value=automation), \
                 patch('src.forklift.display.terminal_detector.TerminalDetector.is_stdin_tty', return_value=stdin), \
                 patch('src.forklift.display.terminal_detector.TerminalDetector.is_stdout_tty', return_value=stdout), \
                 patch('src.forklift.display.terminal_detector.TerminalDetector.is_stderr_tty', return_value=stderr):
                
                mode = self.detector._detect_interaction_mode()
                assert mode == expected, f"Failed for case: ci={ci}, automation={automation}, stdin={stdin}, stdout={stdout}, stderr={stderr}"
    
    def test_cache_with_different_ttl(self):
        """Test caching behavior with different TTL values."""
        # Test with very long TTL
        self.detector._cache_ttl = 3600.0  # 1 hour
        
        with patch.object(self.detector, '_detect_interaction_mode', return_value=InteractionMode.FULLY_INTERACTIVE) as mock_detect:
            mode1 = self.detector.get_interaction_mode()
            time.sleep(0.1)  # Short wait
            mode2 = self.detector.get_interaction_mode()
            
            assert mode1 == mode2 == InteractionMode.FULLY_INTERACTIVE
            assert mock_detect.call_count == 1  # Should only be called once
    
    def test_supports_methods_all_modes(self):
        """Test support methods for all interaction modes."""
        support_matrix = {
            InteractionMode.FULLY_INTERACTIVE: {
                'is_interactive': True,
                'supports_progress_bars': True,
                'supports_user_prompts': True,
            },
            InteractionMode.OUTPUT_REDIRECTED: {
                'is_interactive': False,
                'supports_progress_bars': True,
                'supports_user_prompts': True,
            },
            InteractionMode.INPUT_REDIRECTED: {
                'is_interactive': True,
                'supports_progress_bars': False,
                'supports_user_prompts': False,
            },
            InteractionMode.NON_INTERACTIVE: {
                'is_interactive': False,
                'supports_progress_bars': False,
                'supports_user_prompts': False,
            },
            InteractionMode.PIPED: {
                'is_interactive': False,
                'supports_progress_bars': False,
                'supports_user_prompts': False,
            },
        }
        
        for mode, expected_support in support_matrix.items():
            with patch.object(self.detector, 'get_interaction_mode', return_value=mode):
                assert self.detector.is_interactive() == expected_support['is_interactive'], f"is_interactive failed for {mode}"
                assert self.detector.supports_progress_bars() == expected_support['supports_progress_bars'], f"supports_progress_bars failed for {mode}"
                assert self.detector.supports_user_prompts() == expected_support['supports_user_prompts'], f"supports_user_prompts failed for {mode}"
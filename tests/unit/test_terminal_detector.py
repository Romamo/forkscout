"""Tests for terminal detection functionality."""

import os
import sys
from unittest.mock import Mock, patch, MagicMock, patch
import pytest

from src.forklift.display.terminal_detector import TerminalDetector


class TestTerminalDetector:
    """Test terminal detection methods."""
    
    def test_is_stdin_tty_true(self):
        """Test stdin TTY detection when stdin is a TTY."""
        with patch.object(sys.stdin, 'isatty', return_value=True):
            assert TerminalDetector.is_stdin_tty() is True
    
    def test_is_stdin_tty_false(self):
        """Test stdin TTY detection when stdin is not a TTY."""
        with patch.object(sys.stdin, 'isatty', return_value=False):
            assert TerminalDetector.is_stdin_tty() is False
    
    def test_is_stdout_tty_true(self):
        """Test stdout TTY detection when stdout is a TTY."""
        with patch.object(sys.stdout, 'isatty', return_value=True):
            assert TerminalDetector.is_stdout_tty() is True
    
    def test_is_stdout_tty_false(self):
        """Test stdout TTY detection when stdout is not a TTY."""
        with patch.object(sys.stdout, 'isatty', return_value=False):
            assert TerminalDetector.is_stdout_tty() is False
    
    def test_is_stderr_tty_true(self):
        """Test stderr TTY detection when stderr is a TTY."""
        with patch.object(sys.stderr, 'isatty', return_value=True):
            assert TerminalDetector.is_stderr_tty() is True
    
    def test_is_stderr_tty_false(self):
        """Test stderr TTY detection when stderr is not a TTY."""
        with patch.object(sys.stderr, 'isatty', return_value=False):
            assert TerminalDetector.is_stderr_tty() is False
    
    def test_get_terminal_size_success(self):
        """Test terminal size detection when successful."""
        mock_size = Mock()
        mock_size.columns = 80
        mock_size.lines = 24
        
        with patch('os.get_terminal_size', return_value=mock_size):
            result = TerminalDetector.get_terminal_size()
            assert result == (80, 24)
    
    def test_get_terminal_size_failure(self):
        """Test terminal size detection when it fails."""
        with patch('os.get_terminal_size', side_effect=OSError("No terminal")):
            result = TerminalDetector.get_terminal_size()
            assert result is None
    
    def test_has_color_support_no_color_env(self):
        """Test color support detection with NO_COLOR environment variable."""
        with patch.dict(os.environ, {'NO_COLOR': '1'}, clear=False):
            assert TerminalDetector.has_color_support() is False
    
    def test_has_color_support_force_color_env(self):
        """Test color support detection with FORCE_COLOR environment variable."""
        with patch.dict(os.environ, {'FORCE_COLOR': '1'}, clear=False):
            assert TerminalDetector.has_color_support() is True
    
    def test_has_color_support_term_with_color(self):
        """Test color support detection with color-supporting TERM."""
        with patch.dict(os.environ, {'TERM': 'xterm-256color'}, clear=True):
            with patch.object(TerminalDetector, 'is_stdout_tty', return_value=True):
                assert TerminalDetector.has_color_support() is True
    
    def test_has_color_support_term_without_color(self):
        """Test color support detection with non-color TERM."""
        with patch.dict(os.environ, {'TERM': 'dumb'}, clear=True):
            with patch.object(TerminalDetector, 'is_stdout_tty', return_value=True):
                assert TerminalDetector.has_color_support() is True  # Still true for TTY
    
    def test_has_color_support_no_tty(self):
        """Test color support detection when stdout is not a TTY."""
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(TerminalDetector, 'is_stdout_tty', return_value=False):
                assert TerminalDetector.has_color_support() is False
    
    def test_get_parent_process_name_with_psutil(self):
        """Test parent process detection with psutil available."""
        mock_parent = Mock()
        mock_parent.name.return_value = 'bash'
        
        mock_process = Mock()
        mock_process.parent.return_value = mock_parent
        
        mock_psutil = Mock()
        mock_psutil.Process.return_value = mock_process
        
        with patch.dict('sys.modules', {'psutil': mock_psutil}):
            result = TerminalDetector.get_parent_process_name()
            assert result == 'bash'
    
    def test_get_parent_process_name_psutil_no_parent(self):
        """Test parent process detection when no parent exists."""
        mock_process = Mock()
        mock_process.parent.return_value = None
        
        mock_psutil = Mock()
        mock_psutil.Process.return_value = mock_process
        
        with patch.dict('sys.modules', {'psutil': mock_psutil}):
            result = TerminalDetector.get_parent_process_name()
            assert result is None
    
    def test_get_parent_process_name_psutil_exception(self):
        """Test parent process detection when psutil raises exception."""
        mock_psutil = Mock()
        mock_psutil.Process.side_effect = Exception("Process error")
        
        with patch.dict('sys.modules', {'psutil': mock_psutil}):
            with patch.dict(os.environ, {'_': '/bin/bash'}, clear=False):
                result = TerminalDetector.get_parent_process_name()
                assert result == 'bash'
    
    def test_get_parent_process_name_fallback_env(self):
        """Test parent process detection using environment variable fallback."""
        # Simulate psutil not being available by not adding it to sys.modules
        with patch.dict('sys.modules', {}, clear=False):
            # Remove psutil if it exists
            if 'psutil' in sys.modules:
                del sys.modules['psutil']
            with patch.dict(os.environ, {'_': '/usr/bin/zsh'}, clear=False):
                result = TerminalDetector.get_parent_process_name()
                assert result == 'zsh'
    
    def test_get_parent_process_name_no_fallback(self):
        """Test parent process detection when no fallback is available."""
        # Simulate psutil not being available by not adding it to sys.modules
        with patch.dict('sys.modules', {}, clear=False):
            # Remove psutil if it exists
            if 'psutil' in sys.modules:
                del sys.modules['psutil']
            with patch.dict(os.environ, {}, clear=True):
                result = TerminalDetector.get_parent_process_name()
                assert result is None
    
    def test_get_terminal_info_comprehensive(self):
        """Test comprehensive terminal information gathering."""
        mock_size = Mock()
        mock_size.columns = 120
        mock_size.lines = 30
        
        with patch.object(TerminalDetector, 'is_stdin_tty', return_value=True), \
             patch.object(TerminalDetector, 'is_stdout_tty', return_value=True), \
             patch.object(TerminalDetector, 'is_stderr_tty', return_value=False), \
             patch.object(TerminalDetector, 'get_terminal_size', return_value=(120, 30)), \
             patch.object(TerminalDetector, 'has_color_support', return_value=True), \
             patch.object(TerminalDetector, 'get_parent_process_name', return_value='zsh'), \
             patch.dict(os.environ, {'TERM': 'xterm-256color', 'COLORTERM': 'truecolor'}, clear=False):
            
            info = TerminalDetector.get_terminal_info()
            
            expected = {
                'stdin_tty': True,
                'stdout_tty': True,
                'stderr_tty': False,
                'terminal_size': (120, 30),
                'color_support': True,
                'parent_process': 'zsh',
                'term_env': 'xterm-256color',
                'colorterm_env': 'truecolor',
            }
            
            assert info == expected
    
    def test_get_terminal_info_minimal(self):
        """Test terminal information gathering with minimal environment."""
        with patch.object(TerminalDetector, 'is_stdin_tty', return_value=False), \
             patch.object(TerminalDetector, 'is_stdout_tty', return_value=False), \
             patch.object(TerminalDetector, 'is_stderr_tty', return_value=False), \
             patch.object(TerminalDetector, 'get_terminal_size', return_value=None), \
             patch.object(TerminalDetector, 'has_color_support', return_value=False), \
             patch.object(TerminalDetector, 'get_parent_process_name', return_value=None), \
             patch.dict(os.environ, {}, clear=True):
            
            info = TerminalDetector.get_terminal_info()
            
            expected = {
                'stdin_tty': False,
                'stdout_tty': False,
                'stderr_tty': False,
                'terminal_size': None,
                'color_support': False,
                'parent_process': None,
                'term_env': None,
                'colorterm_env': None,
            }
            
            assert info == expected


class TestTerminalDetectorEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_color_support_term_variations(self):
        """Test color support with various TERM values."""
        color_terms = ['xterm', 'xterm-256color', 'screen', 'tmux', 'xterm-color']
        
        for term in color_terms:
            with patch.dict(os.environ, {'TERM': term}, clear=True):
                with patch.object(TerminalDetector, 'is_stdout_tty', return_value=True):
                    assert TerminalDetector.has_color_support() is True, f"Failed for TERM={term}"
    
    def test_terminal_size_different_errors(self):
        """Test terminal size detection with different error types."""
        errors = [OSError("No terminal"), IOError("Permission denied"), ValueError("Invalid")]
        
        for error in errors:
            with patch('os.get_terminal_size', side_effect=error):
                result = TerminalDetector.get_terminal_size()
                assert result is None
    
    def test_parent_process_psutil_import_variations(self):
        """Test parent process detection with different import scenarios."""
        # Test ImportError - simulate psutil not being available
        with patch.dict('sys.modules', {}, clear=False):
            # Remove psutil if it exists
            if 'psutil' in sys.modules:
                del sys.modules['psutil']
            with patch.dict(os.environ, {'_': '/bin/sh'}, clear=False):
                result = TerminalDetector.get_parent_process_name()
                assert result == 'sh'
        
        # Test with different environment variable
        with patch.dict('sys.modules', {}, clear=False):
            # Remove psutil if it exists
            if 'psutil' in sys.modules:
                del sys.modules['psutil']
            with patch.dict(os.environ, {'_': '/usr/local/bin/fish'}, clear=False):
                result = TerminalDetector.get_parent_process_name()
                assert result == 'fish'
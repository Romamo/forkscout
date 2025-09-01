"""Tests for adaptive progress reporting system."""

import sys
from io import StringIO
from unittest.mock import patch, Mock, MagicMock
import pytest

from src.forklift.display.progress_reporter import (
    ProgressReporter,
    RichProgressReporter,
    PlainTextProgressReporter,
    StderrProgressReporter,
    ProgressReporterFactory,
    get_progress_reporter,
    reset_progress_reporter
)
from src.forklift.display.interaction_mode import InteractionMode


class TestProgressReporter:
    """Test the abstract ProgressReporter interface."""
    
    def test_abstract_methods(self):
        """Test that ProgressReporter is abstract and cannot be instantiated."""
        with pytest.raises(TypeError):
            ProgressReporter()


class TestRichProgressReporter:
    """Test RichProgressReporter class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.reporter = RichProgressReporter()
    
    def test_init(self):
        """Test reporter initialization."""
        assert self.reporter.current_operation is None
        assert self.reporter.total_items is None
        assert self.reporter.current_count == 0
    
    def test_check_rich_availability_with_rich(self):
        """Test rich availability check when rich is available."""
        with patch('builtins.__import__', return_value=Mock()):
            reporter = RichProgressReporter()
            assert reporter._use_rich is True
    
    def test_check_rich_availability_without_rich(self):
        """Test rich availability check when rich is not available."""
        with patch('builtins.__import__', side_effect=ImportError("No module named 'rich'")):
            reporter = RichProgressReporter()
            assert reporter._use_rich is False
    
    def test_start_operation_with_rich(self):
        """Test starting operation with rich available."""
        mock_progress = Mock()
        mock_console = Mock()
        
        with patch.dict('sys.modules', {
            'rich': Mock(),
            'rich.console': Mock(Console=Mock(return_value=mock_console)),
            'rich.progress': Mock(
                Progress=Mock(return_value=mock_progress),
                SpinnerColumn=Mock(),
                TextColumn=Mock(),
                BarColumn=Mock(),
                TaskProgressColumn=Mock()
            )
        }):
            self.reporter._use_rich = True
            mock_progress.add_task.return_value = "task_id"
            
            self.reporter.start_operation("Test Operation", 100)
            
            assert self.reporter.current_operation == "Test Operation"
            assert self.reporter.total_items == 100
            assert self.reporter.current_count == 0
            mock_progress.start.assert_called_once()
            mock_progress.add_task.assert_called_once_with("Test Operation", total=100)
    
    def test_start_operation_fallback(self):
        """Test starting operation with fallback when rich is not available."""
        with patch('sys.stderr', new_callable=StringIO) as mock_stderr:
            self.reporter._use_rich = False
            self.reporter.start_operation("Test Operation", 50)
            
            assert self.reporter.current_operation == "Test Operation"
            assert self.reporter.total_items == 50
            output = mock_stderr.getvalue()
            assert "Starting Test Operation (0/50)" in output
    
    def test_update_progress_with_rich(self):
        """Test updating progress with rich available."""
        mock_progress = Mock()
        self.reporter._use_rich = True
        self.reporter.progress = mock_progress
        self.reporter.task_id = "task_id"
        self.reporter.current_operation = "Test Operation"
        
        self.reporter.update_progress(25, "Processing item 25")
        
        assert self.reporter.current_count == 25
        mock_progress.update.assert_called_once_with(
            "task_id",
            completed=25,
            description="Test Operation: Processing item 25"
        )
    
    def test_update_progress_fallback(self):
        """Test updating progress with fallback."""
        with patch('sys.stderr', new_callable=StringIO) as mock_stderr:
            self.reporter._use_rich = False
            self.reporter.total_items = 100
            
            self.reporter.update_progress(25, "Processing")
            
            assert self.reporter.current_count == 25
            output = mock_stderr.getvalue()
            assert "Progress: 25/100 - Processing" in output
    
    def test_complete_operation_with_rich(self):
        """Test completing operation with rich available."""
        mock_progress = Mock()
        self.reporter._use_rich = True
        self.reporter.progress = mock_progress
        self.reporter.task_id = "task_id"
        self.reporter.current_operation = "Test Operation"
        self.reporter.total_items = 100
        
        self.reporter.complete_operation("All done!")
        
        mock_progress.update.assert_called_with("task_id", description="All done!")
        mock_progress.stop.assert_called_once()
        assert self.reporter.current_operation is None
        assert self.reporter.total_items is None
        assert self.reporter.current_count == 0
    
    def test_complete_operation_fallback(self):
        """Test completing operation with fallback."""
        with patch('sys.stderr', new_callable=StringIO) as mock_stderr:
            self.reporter._use_rich = False
            self.reporter.current_operation = "Test Operation"
            
            self.reporter.complete_operation("Finished!")
            
            output = mock_stderr.getvalue()
            assert "Finished!" in output
    
    def test_log_message_with_rich(self):
        """Test logging message with rich available."""
        mock_console = Mock()
        
        with patch.dict('sys.modules', {
            'rich': Mock(),
            'rich.console': Mock(Console=Mock(return_value=mock_console))
        }):
            self.reporter._use_rich = True
            
            self.reporter.log_message("Test message", "info")
            self.reporter.log_message("Warning message", "warning")
            self.reporter.log_message("Error message", "error")
            
            assert mock_console.print.call_count == 3
    
    def test_log_message_fallback(self):
        """Test logging message with fallback."""
        with patch('sys.stderr', new_callable=StringIO) as mock_stderr:
            self.reporter._use_rich = False
            
            self.reporter.log_message("Test message", "info")
            self.reporter.log_message("Warning message", "warning")
            self.reporter.log_message("Error message", "error")
            
            output = mock_stderr.getvalue()
            assert "INFO: Test message" in output
            assert "WARNING: Warning message" in output
            assert "ERROR: Error message" in output


class TestPlainTextProgressReporter:
    """Test PlainTextProgressReporter class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.output_stream = StringIO()
        self.reporter = PlainTextProgressReporter(self.output_stream)
    
    def test_init(self):
        """Test reporter initialization."""
        assert self.reporter.output_stream is self.output_stream
        assert self.reporter.current_operation is None
        assert self.reporter.total_items is None
        assert self.reporter.current_count == 0
        assert self.reporter.last_reported_percent == -1
    
    def test_start_operation_with_total(self):
        """Test starting operation with known total."""
        self.reporter.start_operation("Test Operation", 100)
        
        assert self.reporter.current_operation == "Test Operation"
        assert self.reporter.total_items == 100
        assert self.reporter.current_count == 0
        
        output = self.output_stream.getvalue()
        assert "Starting Test Operation (100 items)" in output
    
    def test_start_operation_without_total(self):
        """Test starting operation without known total."""
        self.reporter.start_operation("Test Operation")
        
        assert self.reporter.current_operation == "Test Operation"
        assert self.reporter.total_items is None
        
        output = self.output_stream.getvalue()
        assert "Starting Test Operation" in output
        assert "(100 items)" not in output
    
    def test_update_progress_with_total_at_milestones(self):
        """Test updating progress with total at milestone percentages."""
        self.reporter.start_operation("Test", 100)
        self.output_stream.seek(0)
        self.output_stream.truncate(0)
        
        # Test milestone reporting
        milestones = [1, 5, 10, 25, 50, 75, 90, 95, 99, 100]
        for milestone in milestones:
            self.reporter.update_progress(milestone)
            output = self.output_stream.getvalue()
            assert f"Progress: {milestone}/100 ({milestone}%)" in output
            self.output_stream.seek(0)
            self.output_stream.truncate(0)
    
    def test_update_progress_with_total_skips_non_milestones(self):
        """Test that non-milestone progress updates are skipped."""
        self.reporter.start_operation("Test", 100)
        self.output_stream.seek(0)
        self.output_stream.truncate(0)
        
        # These should not generate output
        non_milestones = [2, 3, 4, 6, 7, 8, 9, 11, 12]
        for value in non_milestones:
            self.reporter.update_progress(value)
            output = self.output_stream.getvalue()
            assert f"Progress: {value}/100" not in output
    
    def test_update_progress_without_total(self):
        """Test updating progress without known total."""
        self.reporter.start_operation("Test")
        self.output_stream.seek(0)
        self.output_stream.truncate(0)
        
        # Should report every 10 items
        self.reporter.update_progress(10)
        output = self.output_stream.getvalue()
        assert "Processing: 10 items" in output
        
        self.output_stream.seek(0)
        self.output_stream.truncate(0)
        
        # Should not report non-multiples of 10
        self.reporter.update_progress(15)
        output = self.output_stream.getvalue()
        assert "Processing: 15 items" not in output
    
    def test_update_progress_with_message(self):
        """Test updating progress with message forces reporting."""
        self.reporter.start_operation("Test", 100)
        self.output_stream.seek(0)
        self.output_stream.truncate(0)
        
        # Non-milestone with message should still report
        self.reporter.update_progress(7, "Special update")
        output = self.output_stream.getvalue()
        assert "Progress: 7/100 (7%) - Special update" in output
    
    def test_complete_operation_with_total(self):
        """Test completing operation with total items."""
        self.reporter.start_operation("Test Operation", 100)
        self.reporter.complete_operation("All finished!")
        
        output = self.output_stream.getvalue()
        assert "All finished! (100 items processed)" in output
        
        # Check state reset
        assert self.reporter.current_operation is None
        assert self.reporter.total_items is None
        assert self.reporter.current_count == 0
        assert self.reporter.last_reported_percent == -1
    
    def test_complete_operation_without_total(self):
        """Test completing operation without total items."""
        self.reporter.start_operation("Test Operation")
        self.reporter.complete_operation("Done!")
        
        output = self.output_stream.getvalue()
        assert "Done!" in output
        assert "items processed" not in output
    
    def test_log_message_different_levels(self):
        """Test logging messages with different levels."""
        self.reporter.log_message("Info message", "info")
        self.reporter.log_message("Warning message", "warning")
        self.reporter.log_message("Error message", "error")
        
        output = self.output_stream.getvalue()
        assert "INFO: Info message" in output
        assert "WARNING: Warning message" in output
        assert "ERROR: Error message" in output


class TestStderrProgressReporter:
    """Test StderrProgressReporter class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.reporter = StderrProgressReporter()
    
    def test_init(self):
        """Test reporter initialization."""
        assert isinstance(self.reporter.progress_reporter, PlainTextProgressReporter)
        assert self.reporter.progress_reporter.output_stream is sys.stderr
    
    def test_delegates_to_plain_text_reporter(self):
        """Test that all methods delegate to the plain text reporter."""
        mock_reporter = Mock()
        self.reporter.progress_reporter = mock_reporter
        
        self.reporter.start_operation("Test", 100)
        mock_reporter.start_operation.assert_called_once_with("Test", 100)
        
        self.reporter.update_progress(50, "message")
        mock_reporter.update_progress.assert_called_once_with(50, "message")
        
        self.reporter.complete_operation("done")
        mock_reporter.complete_operation.assert_called_once_with("done")
        
        self.reporter.log_message("test", "info")
        mock_reporter.log_message.assert_called_once_with("test", "info")


class TestProgressReporterFactory:
    """Test ProgressReporterFactory class."""
    
    def test_create_reporter_fully_interactive(self):
        """Test creating reporter for fully interactive mode."""
        with patch('src.forklift.display.progress_reporter.get_interaction_mode_detector') as mock_detector:
            mock_detector.return_value.get_interaction_mode.return_value = InteractionMode.FULLY_INTERACTIVE
            
            reporter = ProgressReporterFactory.create_reporter()
            assert isinstance(reporter, RichProgressReporter)
    
    def test_create_reporter_output_redirected(self):
        """Test creating reporter for output redirected mode."""
        with patch('src.forklift.display.progress_reporter.get_interaction_mode_detector') as mock_detector:
            mock_detector.return_value.get_interaction_mode.return_value = InteractionMode.OUTPUT_REDIRECTED
            
            reporter = ProgressReporterFactory.create_reporter()
            assert isinstance(reporter, StderrProgressReporter)
    
    def test_create_reporter_input_redirected(self):
        """Test creating reporter for input redirected mode."""
        with patch('src.forklift.display.progress_reporter.get_interaction_mode_detector') as mock_detector:
            mock_detector.return_value.get_interaction_mode.return_value = InteractionMode.INPUT_REDIRECTED
            
            reporter = ProgressReporterFactory.create_reporter()
            assert isinstance(reporter, RichProgressReporter)
    
    def test_create_reporter_non_interactive(self):
        """Test creating reporter for non-interactive mode."""
        with patch('src.forklift.display.progress_reporter.get_interaction_mode_detector') as mock_detector:
            mock_detector.return_value.get_interaction_mode.return_value = InteractionMode.NON_INTERACTIVE
            
            reporter = ProgressReporterFactory.create_reporter()
            assert isinstance(reporter, PlainTextProgressReporter)
    
    def test_create_reporter_piped(self):
        """Test creating reporter for piped mode."""
        with patch('src.forklift.display.progress_reporter.get_interaction_mode_detector') as mock_detector:
            mock_detector.return_value.get_interaction_mode.return_value = InteractionMode.PIPED
            
            reporter = ProgressReporterFactory.create_reporter()
            assert isinstance(reporter, PlainTextProgressReporter)
    
    def test_create_reporter_for_mode_all_modes(self):
        """Test creating reporter for specific modes."""
        test_cases = [
            (InteractionMode.FULLY_INTERACTIVE, RichProgressReporter),
            (InteractionMode.OUTPUT_REDIRECTED, StderrProgressReporter),
            (InteractionMode.INPUT_REDIRECTED, RichProgressReporter),
            (InteractionMode.NON_INTERACTIVE, PlainTextProgressReporter),
            (InteractionMode.PIPED, PlainTextProgressReporter),
        ]
        
        for mode, expected_type in test_cases:
            reporter = ProgressReporterFactory.create_reporter_for_mode(mode)
            assert isinstance(reporter, expected_type), f"Failed for mode {mode}"


class TestGlobalProgressReporter:
    """Test global progress reporter functions."""
    
    def setup_method(self):
        """Reset global state before each test."""
        reset_progress_reporter()
    
    def test_get_progress_reporter_singleton(self):
        """Test that get_progress_reporter returns singleton."""
        reporter1 = get_progress_reporter()
        reporter2 = get_progress_reporter()
        
        assert reporter1 is reporter2
        assert isinstance(reporter1, ProgressReporter)
    
    def test_reset_progress_reporter(self):
        """Test resetting the global progress reporter."""
        reporter1 = get_progress_reporter()
        reset_progress_reporter()
        reporter2 = get_progress_reporter()
        
        assert reporter1 is not reporter2
        assert isinstance(reporter2, ProgressReporter)
    
    def test_get_progress_reporter_creates_appropriate_type(self):
        """Test that global reporter creates appropriate type based on mode."""
        with patch('src.forklift.display.progress_reporter.get_interaction_mode_detector') as mock_detector:
            mock_detector.return_value.get_interaction_mode.return_value = InteractionMode.FULLY_INTERACTIVE
            
            reset_progress_reporter()
            reporter = get_progress_reporter()
            assert isinstance(reporter, RichProgressReporter)


class TestProgressReporterEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_rich_progress_reporter_import_error_during_operation(self):
        """Test handling import errors during rich operations."""
        reporter = RichProgressReporter()
        reporter._use_rich = True
        
        # Simulate import error during start_operation
        def mock_import(name, *args, **kwargs):
            if name == 'rich.console' or name == 'rich.progress':
                raise ImportError("Module not found")
            return __import__(name, *args, **kwargs)
        
        with patch('builtins.__import__', side_effect=mock_import):
            with patch('sys.stderr', new_callable=StringIO) as mock_stderr:
                reporter.start_operation("Test", 100)
                
                # Should fall back to plain text
                output = mock_stderr.getvalue()
                assert "Starting Test (0/100)" in output
    
    def test_rich_progress_reporter_exception_during_update(self):
        """Test handling exceptions during rich progress updates."""
        reporter = RichProgressReporter()
        reporter._use_rich = True
        reporter.progress = Mock()
        reporter.task_id = "task_id"
        reporter.current_operation = "Test"
        reporter.total_items = 100
        
        # Simulate exception during update
        reporter.progress.update.side_effect = Exception("Update failed")
        
        with patch('sys.stderr', new_callable=StringIO) as mock_stderr:
            reporter.update_progress(50, "test")
            
            # Should fall back to plain text
            output = mock_stderr.getvalue()
            assert "Progress: 50/100 - test" in output
    
    def test_plain_text_reporter_with_zero_total(self):
        """Test plain text reporter with zero total items."""
        output_stream = StringIO()
        reporter = PlainTextProgressReporter(output_stream)
        
        reporter.start_operation("Test", 0)
        reporter.update_progress(0)
        reporter.complete_operation()
        
        output = output_stream.getvalue()
        assert "Starting Test" in output
        assert "(0 items)" not in output  # Zero items should not show count
        assert "Progress: 0/0 (0%)" not in output  # Should avoid division by zero
    
    def test_progress_reporter_state_isolation(self):
        """Test that multiple operations don't interfere with each other."""
        output_stream = StringIO()
        reporter = PlainTextProgressReporter(output_stream)
        
        # First operation
        reporter.start_operation("Operation 1", 50)
        reporter.update_progress(25)
        reporter.complete_operation()
        
        # Second operation should start fresh
        reporter.start_operation("Operation 2", 100)
        assert reporter.current_operation == "Operation 2"
        assert reporter.total_items == 100
        assert reporter.current_count == 0
        assert reporter.last_reported_percent == -1
    
    def test_rich_reporter_without_task_id(self):
        """Test rich reporter behavior when task_id is not set."""
        reporter = RichProgressReporter()
        reporter._use_rich = True
        reporter.progress = Mock()
        reporter.current_operation = "Test Operation"
        # Don't set task_id
        
        with patch('sys.stderr', new_callable=StringIO) as mock_stderr:
            reporter.complete_operation("test")
            
            # Should handle gracefully - either through rich or fallback
            # The progress.stop() should still be called
            reporter.progress.stop.assert_called_once()
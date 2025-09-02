"""CSV output management with comprehensive error handling."""

import sys
from io import StringIO
from typing import Any, TextIO

from forklift.exceptions import ForkliftOutputError, ForkliftUnicodeError, safe_unicode_output
from forklift.reporting.csv_exporter import CSVExporter, CSVExportConfig


class CSVOutputManager:
    """Manages CSV output with proper error handling and clean stdout/stderr separation."""
    
    def __init__(self, debug: bool = False):
        self.debug = debug
        self.exporter = CSVExporter()
        self._output_buffer = StringIO()
        self._has_output = False
    
    def configure_exporter(self, config: CSVExportConfig) -> None:
        """Configure the CSV exporter.
        
        Args:
            config: CSV export configuration
        """
        self.exporter = CSVExporter(config)
    
    def export_to_stdout(self, data: Any, **kwargs) -> None:
        """Export data to stdout with error handling.
        
        Args:
            data: Data to export
            **kwargs: Additional arguments for export
            
        Raises:
            ForkliftOutputError: If export fails
        """
        try:
            # Generate CSV content
            csv_content = self._generate_csv_safely(data, **kwargs)
            
            # Write to stdout
            self._write_to_stdout(csv_content)
            
            self._has_output = True
            
        except Exception as e:
            # Clean up any partial output
            self._cleanup_partial_output()
            
            if isinstance(e, (ForkliftOutputError, ForkliftUnicodeError)):
                raise
            else:
                raise ForkliftOutputError(f"Failed to export CSV data: {e}")
    
    def export_to_file(self, data: Any, file_path: str, **kwargs) -> None:
        """Export data to file with error handling.
        
        Args:
            data: Data to export
            file_path: Path to output file
            **kwargs: Additional arguments for export
            
        Raises:
            ForkliftOutputError: If export fails
        """
        try:
            # Generate CSV content
            csv_content = self._generate_csv_safely(data, **kwargs)
            
            # Write to file
            with open(file_path, 'w', encoding='utf-8', newline='') as f:
                f.write(csv_content)
            
            # Log success to stderr (not stdout to keep CSV clean)
            self._log_to_stderr(f"CSV exported to: {file_path}")
            
        except Exception as e:
            if isinstance(e, (ForkliftOutputError, ForkliftUnicodeError)):
                raise
            else:
                raise ForkliftOutputError(f"Failed to export CSV to file '{file_path}': {e}")
    
    def _generate_csv_safely(self, data: Any, **kwargs) -> str:
        """Generate CSV content with Unicode safety.
        
        Args:
            data: Data to export
            **kwargs: Additional arguments for export
            
        Returns:
            Safe CSV content
            
        Raises:
            ForkliftOutputError: If generation fails
            ForkliftUnicodeError: If Unicode handling fails
        """
        try:
            # Generate CSV using the exporter
            csv_content = self.exporter.export_to_csv(data, **kwargs)
            
            # Validate Unicode content
            safe_content = self._validate_csv_unicode(csv_content)
            
            return safe_content
            
        except UnicodeError as e:
            raise ForkliftUnicodeError(f"Unicode error in CSV generation: {e}")
        except Exception as e:
            raise ForkliftOutputError(f"CSV generation failed: {e}")
    
    def _validate_csv_unicode(self, csv_content: str) -> str:
        """Validate and clean CSV content for Unicode safety.
        
        Args:
            csv_content: Raw CSV content
            
        Returns:
            Unicode-safe CSV content
            
        Raises:
            ForkliftUnicodeError: If content cannot be made safe
        """
        try:
            # Ensure content is valid UTF-8
            csv_content.encode('utf-8').decode('utf-8')
            return csv_content
        except UnicodeError:
            # Try to clean the content
            try:
                lines = csv_content.split('\n')
                safe_lines = []
                
                for line in lines:
                    safe_line = safe_unicode_output(line, "[Unicode Error in CSV line]")
                    safe_lines.append(safe_line)
                
                return '\n'.join(safe_lines)
            except Exception as e:
                raise ForkliftUnicodeError(f"Cannot create Unicode-safe CSV content: {e}")
    
    def _write_to_stdout(self, content: str) -> None:
        """Write content to stdout with error handling.
        
        Args:
            content: Content to write
            
        Raises:
            ForkliftOutputError: If write fails
        """
        try:
            # Write to stdout
            sys.stdout.write(content)
            sys.stdout.flush()
            
        except UnicodeEncodeError as e:
            # Try with error replacement
            try:
                safe_content = content.encode('utf-8', errors='replace').decode('utf-8')
                sys.stdout.write(safe_content)
                sys.stdout.flush()
            except Exception:
                raise ForkliftOutputError(f"Cannot write CSV to stdout: Unicode encoding error")
        except Exception as e:
            raise ForkliftOutputError(f"Failed to write CSV to stdout: {e}")
    
    def _cleanup_partial_output(self) -> None:
        """Clean up any partial output that may have been written."""
        # Note: We can't actually "undo" stdout writes, but we can ensure
        # no further output is generated and log the issue
        if self._has_output:
            self._log_to_stderr("Warning: Partial CSV output may have been generated due to error")
    
    def _log_to_stderr(self, message: str) -> None:
        """Log a message to stderr.
        
        Args:
            message: Message to log
        """
        try:
            safe_message = safe_unicode_output(message)
            print(safe_message, file=sys.stderr)
        except Exception:
            # Last resort
            print("Log message could not be displayed due to encoding error", file=sys.stderr)


class CSVOutputContext:
    """Context manager for CSV output operations."""
    
    def __init__(self, manager: CSVOutputManager, suppress_progress: bool = True):
        self.manager = manager
        self.suppress_progress = suppress_progress
        self._original_stderr = None
        self._stderr_buffer = None
    
    def __enter__(self) -> CSVOutputManager:
        """Enter CSV output context."""
        if self.suppress_progress:
            # Capture stderr to suppress progress indicators
            self._original_stderr = sys.stderr
            self._stderr_buffer = StringIO()
            sys.stderr = self._stderr_buffer
        
        return self.manager
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit CSV output context."""
        if self.suppress_progress and self._original_stderr:
            # Restore stderr
            sys.stderr = self._original_stderr
            
            # If there was an error, write captured stderr to original stderr
            if exc_type is not None:
                captured_output = self._stderr_buffer.getvalue()
                if captured_output.strip():
                    print(captured_output, file=self._original_stderr, end='')


def create_csv_output_manager(debug: bool = False) -> CSVOutputManager:
    """Create a CSV output manager.
    
    Args:
        debug: Whether to enable debug mode
        
    Returns:
        CSVOutputManager instance
    """
    return CSVOutputManager(debug=debug)


def create_csv_context(
    manager: CSVOutputManager | None = None,
    suppress_progress: bool = True,
    debug: bool = False
) -> CSVOutputContext:
    """Create a CSV output context.
    
    Args:
        manager: CSV output manager (creates new one if None)
        suppress_progress: Whether to suppress progress indicators
        debug: Whether to enable debug mode
        
    Returns:
        CSVOutputContext instance
    """
    if manager is None:
        manager = create_csv_output_manager(debug=debug)
    
    return CSVOutputContext(manager, suppress_progress=suppress_progress)
"""Core exceptions for Forkscout application."""

import sys
from typing import Any, Optional


class ForkscoutError(Exception):
    """Base exception for all Forkscout errors."""
    
    def __init__(self, message: str, exit_code: int = 1):
        super().__init__(message)
        self.exit_code = exit_code


class ForkscoutConfigurationError(ForkscoutError):
    """Raised when configuration is invalid or missing."""
    
    def __init__(self, message: str):
        super().__init__(message, exit_code=2)


class ForkscoutValidationError(ForkscoutError):
    """Raised when input validation fails."""
    
    def __init__(self, message: str):
        super().__init__(message, exit_code=3)


class ForkscoutNetworkError(ForkscoutError):
    """Raised when network operations fail."""
    
    def __init__(self, message: str, operation: str = "network operation"):
        super().__init__(message, exit_code=4)
        self.operation = operation


class ForkscoutAuthenticationError(ForkscoutError):
    """Raised when authentication fails."""
    
    def __init__(self, message: str):
        super().__init__(message, exit_code=5)


class ForkscoutOutputError(ForkscoutError):
    """Raised when output operations fail."""
    
    def __init__(self, message: str):
        super().__init__(message, exit_code=6)


class CLIError(ForkscoutError):
    """Raised when CLI operations fail."""
    
    def __init__(self, message: str):
        super().__init__(message, exit_code=1)


class ForkscoutUnicodeError(ForkscoutError):
    """Raised when Unicode handling fails."""
    
    def __init__(self, message: str, text: str = ""):
        super().__init__(message, exit_code=7)
        # Truncate text if too long
        if len(text) > 100:
            self.text = text[:100] + "..."
        else:
            self.text = text


class ErrorHandler:
    """Centralized error handling for CLI operations."""
    
    def __init__(self, debug: bool = False):
        self.debug = debug
    
    def handle_error(self, error: Exception, context: str = "") -> None:
        """Handle an error by logging it to stderr and exiting with appropriate code.
        
        Args:
            error: The exception that occurred
            context: Additional context about where the error occurred
        """
        # Determine exit code
        if isinstance(error, ForkscoutError):
            exit_code = error.exit_code
        elif isinstance(error, KeyboardInterrupt):
            exit_code = 130  # Standard exit code for SIGINT
        else:
            exit_code = 1  # Generic error
        
        # Format error message
        error_message = self._format_error_message(error, context)
        
        # Write to stderr
        self._write_error_to_stderr(error_message)
        
        # Exit with appropriate code
        sys.exit(exit_code)
    
    def _format_error_message(self, error: Exception, context: str) -> str:
        """Format error message for display.
        
        Args:
            error: The exception that occurred
            context: Additional context about where the error occurred
            
        Returns:
            Formatted error message
        """
        if isinstance(error, KeyboardInterrupt):
            return "Operation interrupted by user"
        
        # Base error message
        message = str(error)
        
        # Add context if provided
        if context:
            message = f"{context}: {message}"
        
        # Add debug information if enabled
        if self.debug and not isinstance(error, ForkscoutError):
            import traceback
            tb = traceback.format_exc()
            if tb and tb.strip() != "NoneType: None":
                message = f"{message}\n\nDebug information:\n{tb}"
        
        return message
    
    def _write_error_to_stderr(self, message: str) -> None:
        """Write error message to stderr with proper Unicode handling.
        
        Args:
            message: Error message to write
        """
        try:
            # Ensure message is properly encoded for stderr
            if isinstance(message, str):
                # Try to encode as UTF-8, fall back to ASCII with replacement
                try:
                    encoded_message = message.encode('utf-8').decode('utf-8')
                except UnicodeError:
                    encoded_message = message.encode('ascii', errors='replace').decode('ascii')
            else:
                encoded_message = str(message)
            
            # Write to stderr
            print(f"Error: {encoded_message}", file=sys.stderr)
            
        except Exception as e:
            # Last resort: write a generic error message
            try:
                print(f"Error: An error occurred (details could not be displayed: {e})", file=sys.stderr)
            except Exception:
                # If even this fails, there's nothing more we can do
                pass
    
    def validate_unicode_text(self, text: str, context: str = "text") -> str:
        """Validate and clean Unicode text for safe output.
        
        Args:
            text: Text to validate
            context: Context for error reporting
            
        Returns:
            Cleaned text safe for output
            
        Raises:
            ForkscoutUnicodeError: If text cannot be processed
        """
        if not isinstance(text, str):
            text = str(text)
        
        try:
            # Try to encode/decode to ensure valid Unicode
            text.encode('utf-8').decode('utf-8')
            return text
        except UnicodeError as e:
            # Try to clean the text
            try:
                cleaned = text.encode('utf-8', errors='replace').decode('utf-8')
                return cleaned
            except Exception:
                raise ForkscoutUnicodeError(
                    f"Cannot process Unicode text in {context}",
                    text=text[:100] + "..." if len(text) > 100 else text
                )


def safe_unicode_output(text: str, fallback: str = "[Unicode Error]") -> str:
    """Safely convert text to Unicode for output.
    
    Args:
        text: Text to convert
        fallback: Fallback text if conversion fails
        
    Returns:
        Safe Unicode text
    """
    if not isinstance(text, str):
        text = str(text)
    
    try:
        # Ensure valid UTF-8
        return text.encode('utf-8').decode('utf-8')
    except UnicodeError:
        try:
            # Try with replacement characters
            return text.encode('utf-8', errors='replace').decode('utf-8')
        except Exception:
            return fallback


def create_error_handler(debug: bool = False) -> ErrorHandler:
    """Create an error handler instance.
    
    Args:
        debug: Whether to enable debug mode
        
    Returns:
        ErrorHandler instance
    """
    return ErrorHandler(debug=debug)
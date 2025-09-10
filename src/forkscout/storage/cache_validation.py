"""Cache data validation utilities."""

import logging
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class CacheValidationError(Exception):
    """Raised when cached data fails validation."""
    pass


class CacheValidator:
    """Validates cached data against Pydantic models."""

    @staticmethod
    def validate_cached_data(
        cached_data: dict[str, Any],
        model_class: type[T],
        context: str = "cached_data"
    ) -> T:
        """Validate cached data against a Pydantic model.
        
        Args:
            cached_data: The cached data dictionary
            model_class: The Pydantic model class to validate against
            context: Context string for error messages
            
        Returns:
            Validated model instance
            
        Raises:
            CacheValidationError: If validation fails
        """
        try:
            return model_class(**cached_data)
        except ValidationError as e:
            logger.warning(f"Cache validation failed for {context}: {e}")
            raise CacheValidationError(f"Invalid cached data for {context}: {e}")

    @staticmethod
    def validate_repository_reconstruction(cached_repo_data: dict[str, Any]) -> None:
        """Validate that cached repository data has all required fields.
        
        Args:
            cached_repo_data: Repository data from cache
            
        Raises:
            CacheValidationError: If required fields are missing
        """
        required_fields = [
            "name", "owner", "full_name", "url", "html_url", "clone_url"
        ]

        missing_fields = []
        for field in required_fields:
            if field not in cached_repo_data or cached_repo_data[field] is None:
                missing_fields.append(field)

        if missing_fields:
            raise CacheValidationError(
                f"Cached repository data missing required fields: {missing_fields}"
            )

    @staticmethod
    def ensure_cache_compatibility(
        cached_data: dict[str, Any],
        expected_schema_version: str = "1.0"
    ) -> bool:
        """Check if cached data is compatible with current schema.
        
        Args:
            cached_data: The cached data
            expected_schema_version: Expected schema version
            
        Returns:
            True if compatible, False otherwise
        """
        schema_version = cached_data.get("_schema_version", "unknown")

        if schema_version != expected_schema_version:
            logger.warning(
                f"Cache schema version mismatch: expected {expected_schema_version}, "
                f"got {schema_version}"
            )
            return False

        return True


def add_schema_version(data: dict[str, Any], version: str = "1.0") -> dict[str, Any]:
    """Add schema version to cached data.
    
    Args:
        data: Data to cache
        version: Schema version
        
    Returns:
        Data with schema version added
    """
    data["_schema_version"] = version
    return data


def validate_before_cache(data: dict[str, Any], model_class: type[T]) -> dict[str, Any]:
    """Validate data before caching to ensure it can be reconstructed.
    
    Args:
        data: Data to validate and cache
        model_class: Model class to validate against
        
    Returns:
        Validated data ready for caching
        
    Raises:
        CacheValidationError: If data cannot be validated
    """
    try:
        # Try to reconstruct the model to ensure all required fields are present
        model_instance = model_class(**data)

        # Convert back to dict to ensure serializable
        validated_data = model_instance.model_dump()

        # Add schema version
        return add_schema_version(validated_data)

    except ValidationError as e:
        raise CacheValidationError(f"Data validation failed before caching: {e}")

"""Tests for cache validation utilities."""

import pytest
from datetime import datetime
from forklift.storage.cache_validation import (
    CacheValidator, 
    CacheValidationError,
    add_schema_version,
    validate_before_cache
)
from forklift.models.github import Repository


class TestCacheValidator:
    """Test cache validation functionality."""
    
    def test_validate_cached_data_success(self):
        """Test successful validation of cached data."""
        valid_repo_data = {
            "id": 12345,
            "owner": "test_owner",
            "name": "test_repo",
            "full_name": "test_owner/test_repo",
            "url": "https://github.com/test_owner/test_repo",
            "html_url": "https://github.com/test_owner/test_repo", 
            "clone_url": "https://github.com/test_owner/test_repo.git",
            "default_branch": "main",
            "stars": 100,
            "forks_count": 50,
            "watchers_count": 75,
            "open_issues_count": 5,
            "size": 1024,
            "language": "Python",
            "description": "Test repository",
            "topics": ["test", "python"],
            "license_name": "MIT",
            "is_private": False,
            "is_fork": False,
            "is_archived": False,
            "is_disabled": False,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "pushed_at": datetime.now()
        }
        
        # Should not raise exception
        repo = CacheValidator.validate_cached_data(valid_repo_data, Repository)
        assert repo.name == "test_repo"
        assert repo.owner == "test_owner"
    
    def test_validate_cached_data_missing_required_field(self):
        """Test validation failure with missing required field."""
        invalid_repo_data = {
            "id": 12345,
            "owner": "test_owner",
            "name": "test_repo",
            "full_name": "test_owner/test_repo",
            # Missing: url, html_url, clone_url (required fields)
            "default_branch": "main",
            "stars": 100
        }
        
        with pytest.raises(CacheValidationError) as exc_info:
            CacheValidator.validate_cached_data(invalid_repo_data, Repository)
        
        assert "Invalid cached data" in str(exc_info.value)
    
    def test_validate_repository_reconstruction_success(self):
        """Test successful repository reconstruction validation."""
        valid_repo_data = {
            "name": "test_repo",
            "owner": "test_owner", 
            "full_name": "test_owner/test_repo",
            "url": "https://github.com/test_owner/test_repo",
            "html_url": "https://github.com/test_owner/test_repo",
            "clone_url": "https://github.com/test_owner/test_repo.git"
        }
        
        # Should not raise exception
        CacheValidator.validate_repository_reconstruction(valid_repo_data)
    
    def test_validate_repository_reconstruction_missing_fields(self):
        """Test repository reconstruction validation with missing fields."""
        invalid_repo_data = {
            "name": "test_repo",
            "owner": "test_owner",
            "full_name": "test_owner/test_repo"
            # Missing: url, html_url, clone_url
        }
        
        with pytest.raises(CacheValidationError) as exc_info:
            CacheValidator.validate_repository_reconstruction(invalid_repo_data)
        
        error_msg = str(exc_info.value)
        assert "missing required fields" in error_msg
        assert "url" in error_msg
        assert "html_url" in error_msg
        assert "clone_url" in error_msg
    
    def test_ensure_cache_compatibility_success(self):
        """Test cache compatibility check with matching version."""
        cached_data = {
            "_schema_version": "1.0",
            "data": "test"
        }
        
        assert CacheValidator.ensure_cache_compatibility(cached_data, "1.0") is True
    
    def test_ensure_cache_compatibility_version_mismatch(self):
        """Test cache compatibility check with version mismatch."""
        cached_data = {
            "_schema_version": "0.9",
            "data": "test"
        }
        
        assert CacheValidator.ensure_cache_compatibility(cached_data, "1.0") is False
    
    def test_ensure_cache_compatibility_missing_version(self):
        """Test cache compatibility check with missing version."""
        cached_data = {
            "data": "test"
            # Missing _schema_version
        }
        
        assert CacheValidator.ensure_cache_compatibility(cached_data, "1.0") is False


class TestCacheUtilities:
    """Test cache utility functions."""
    
    def test_add_schema_version(self):
        """Test adding schema version to data."""
        data = {"key": "value"}
        versioned_data = add_schema_version(data, "1.0")
        
        assert versioned_data["_schema_version"] == "1.0"
        assert versioned_data["key"] == "value"
    
    def test_validate_before_cache_success(self):
        """Test successful validation before caching."""
        repo_data = {
            "id": 12345,
            "owner": "test_owner",
            "name": "test_repo",
            "full_name": "test_owner/test_repo",
            "url": "https://github.com/test_owner/test_repo",
            "html_url": "https://github.com/test_owner/test_repo",
            "clone_url": "https://github.com/test_owner/test_repo.git"
        }
        
        validated_data = validate_before_cache(repo_data, Repository)
        
        assert validated_data["_schema_version"] == "1.0"
        assert validated_data["name"] == "test_repo"
        assert validated_data["owner"] == "test_owner"
    
    def test_validate_before_cache_failure(self):
        """Test validation failure before caching."""
        invalid_repo_data = {
            "owner": "test_owner",
            "name": "test_repo"
            # Missing required fields
        }
        
        with pytest.raises(CacheValidationError) as exc_info:
            validate_before_cache(invalid_repo_data, Repository)
        
        assert "Data validation failed before caching" in str(exc_info.value)
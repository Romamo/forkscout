#!/usr/bin/env python3
"""Script to validate that all Pydantic models can be serialized and deserialized correctly."""

import sys
import json
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from forklift.models.github import Repository
from forklift.models.analysis import AnalysisResult, Feature, ForkAnalysis
from forklift.storage.cache_validation import validate_before_cache, CacheValidationError


def test_repository_serialization():
    """Test Repository model serialization/deserialization."""
    print("Testing Repository model serialization...")
    
    # Create a complete Repository instance
    repo = Repository(
        id=12345,
        owner="test_owner",
        name="test_repo",
        full_name="test_owner/test_repo",
        url="https://github.com/test_owner/test_repo",
        html_url="https://github.com/test_owner/test_repo",
        clone_url="https://github.com/test_owner/test_repo.git",
        default_branch="main",
        stars=100,
        forks_count=50,
        watchers_count=75,
        open_issues_count=5,
        size=1024,
        language="Python",
        description="Test repository for serialization",
        topics=["test", "serialization"],
        license_name="MIT",
        is_private=False,
        is_fork=False,
        is_archived=False,
        is_disabled=False,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        pushed_at=datetime.now()
    )
    
    # Test serialization to dict
    repo_dict = repo.model_dump()
    
    # Test JSON serialization
    try:
        json_str = json.dumps(repo_dict, default=str)
        print(f"✅ Repository JSON serialization: {len(json_str)} bytes")
    except Exception as e:
        print(f"❌ Repository JSON serialization failed: {e}")
        return False
    
    # Test deserialization
    try:
        repo_reconstructed = Repository(**repo_dict)
        print("✅ Repository deserialization successful")
    except Exception as e:
        print(f"❌ Repository deserialization failed: {e}")
        return False
    
    # Test cache validation
    try:
        validate_before_cache(repo_dict, Repository)
        print("✅ Repository cache validation successful")
    except CacheValidationError as e:
        print(f"❌ Repository cache validation failed: {e}")
        return False
    
    # Verify data integrity
    if (repo.name == repo_reconstructed.name and 
        repo.owner == repo_reconstructed.owner and
        repo.url == repo_reconstructed.url):
        print("✅ Repository data integrity verified")
        return True
    else:
        print("❌ Repository data integrity check failed")
        return False


def test_feature_serialization():
    """Test Feature model serialization/deserialization."""
    print("\nTesting Feature model serialization...")
    
    # Create a Feature instance (simplified for testing)
    feature_data = {
        "id": "test_feature_1",
        "name": "Test Feature",
        "description": "A test feature for serialization testing",
        "fork_source": "test_owner/test_fork",
        "commit_sha": "abc123def456",
        "author": "test_author",
        "date": datetime.now().isoformat(),
        "github_url": "https://github.com/test_owner/test_fork/commit/abc123def456",
        "impact_score": 0.8,
        "complexity_score": 0.6,
        "value_score": 0.7
    }
    
    try:
        feature = Feature(**feature_data)
        print("✅ Feature creation successful")
    except Exception as e:
        print(f"❌ Feature creation failed: {e}")
        return False
    
    # Test serialization
    try:
        feature_dict = feature.model_dump()
        json_str = json.dumps(feature_dict, default=str)
        print(f"✅ Feature JSON serialization: {len(json_str)} bytes")
    except Exception as e:
        print(f"❌ Feature JSON serialization failed: {e}")
        return False
    
    # Test deserialization
    try:
        feature_reconstructed = Feature(**feature_dict)
        print("✅ Feature deserialization successful")
    except Exception as e:
        print(f"❌ Feature deserialization failed: {e}")
        return False
    
    return True


def check_required_fields():
    """Check that all models have properly defined required fields."""
    print("\nChecking required fields...")
    
    # Test Repository required fields
    try:
        Repository()  # Should fail due to missing required fields
        print("❌ Repository allows creation without required fields")
        return False
    except Exception:
        print("✅ Repository properly validates required fields")
    
    # Test with minimal required fields
    try:
        minimal_repo = Repository(
            owner="test",
            name="test",
            full_name="test/test",
            url="https://github.com/test/test",
            html_url="https://github.com/test/test",
            clone_url="https://github.com/test/test.git"
        )
        print("✅ Repository accepts minimal required fields")
    except Exception as e:
        print(f"❌ Repository rejects valid minimal data: {e}")
        return False
    
    return True


def main():
    """Run all serialization checks."""
    print("🔍 Running model serialization validation checks...\n")
    
    checks = [
        test_repository_serialization,
        test_feature_serialization,
        check_required_fields
    ]
    
    results = []
    for check in checks:
        try:
            result = check()
            results.append(result)
        except Exception as e:
            print(f"❌ Check {check.__name__} failed with exception: {e}")
            results.append(False)
    
    print(f"\n📊 Results: {sum(results)}/{len(results)} checks passed")
    
    if all(results):
        print("🎉 All model serialization checks passed!")
        return 0
    else:
        print("💥 Some model serialization checks failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
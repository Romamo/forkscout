#!/usr/bin/env python3
"""Script to validate that all Pydantic models can be serialized and deserialized correctly."""

import sys
import json
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from forklift.models.github import Repository
from forklift.models.analysis import Feature, ForkAnalysis
from forklift.models.fork_qualification import ForkQualificationMetrics, QualifiedForksResult, QualificationStats, CollectedForkData
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


def test_fork_qualification_serialization():
    """Test ForkQualificationMetrics model serialization/deserialization."""
    print("\nTesting ForkQualificationMetrics model serialization...")
    
    # Create a ForkQualificationMetrics instance
    metrics = ForkQualificationMetrics(
        id=12345,
        name="test-fork",
        full_name="owner/test-fork",
        owner="owner",
        html_url="https://github.com/owner/test-fork",
        stargazers_count=25,
        forks_count=5,
        watchers_count=15,
        size=2048,
        language="Python",
        topics=["test", "fork"],
        open_issues_count=3,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        pushed_at=datetime.now(),
        archived=False,
        disabled=False,
        fork=True,
        license_key="mit",
        license_name="MIT License",
        description="Test fork for serialization",
        homepage="https://example.com",
        default_branch="main"
    )
    
    try:
        print("✅ ForkQualificationMetrics creation successful")
    except Exception as e:
        print(f"❌ ForkQualificationMetrics creation failed: {e}")
        return False
    
    # Test serialization
    try:
        metrics_dict = metrics.model_dump()
        json_str = json.dumps(metrics_dict, default=str)
        print(f"✅ ForkQualificationMetrics JSON serialization: {len(json_str)} bytes")
    except Exception as e:
        print(f"❌ ForkQualificationMetrics JSON serialization failed: {e}")
        return False
    
    # Test deserialization
    try:
        metrics_reconstructed = ForkQualificationMetrics(**metrics_dict)
        print("✅ ForkQualificationMetrics deserialization successful")
    except Exception as e:
        print(f"❌ ForkQualificationMetrics deserialization failed: {e}")
        return False
    
    # Test cache validation
    try:
        validate_before_cache(metrics_dict, ForkQualificationMetrics)
        print("✅ ForkQualificationMetrics cache validation successful")
    except CacheValidationError as e:
        print(f"❌ ForkQualificationMetrics cache validation failed: {e}")
        return False
    
    return True


def test_qualified_forks_result_serialization():
    """Test QualifiedForksResult model serialization/deserialization."""
    print("\nTesting QualifiedForksResult model serialization...")
    
    # Create sample data
    metrics = ForkQualificationMetrics(
        id=12345,
        name="test-fork",
        full_name="owner/test-fork",
        owner="owner",
        html_url="https://github.com/owner/test-fork",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        pushed_at=datetime.now()
    )
    
    collected_fork = CollectedForkData(metrics=metrics)
    
    stats = QualificationStats(
        total_forks_discovered=10,
        forks_with_no_commits=3,
        forks_with_commits=7,
        api_calls_made=20,
        api_calls_saved=80,
        processing_time_seconds=15.5
    )
    
    result = QualifiedForksResult(
        repository_owner="owner",
        repository_name="repo",
        repository_url="https://github.com/owner/repo",
        collected_forks=[collected_fork],
        stats=stats
    )
    
    try:
        print("✅ QualifiedForksResult creation successful")
    except Exception as e:
        print(f"❌ QualifiedForksResult creation failed: {e}")
        return False
    
    # Test serialization
    try:
        result_dict = result.model_dump()
        json_str = json.dumps(result_dict, default=str)
        print(f"✅ QualifiedForksResult JSON serialization: {len(json_str)} bytes")
    except Exception as e:
        print(f"❌ QualifiedForksResult JSON serialization failed: {e}")
        return False
    
    # Test deserialization
    try:
        result_reconstructed = QualifiedForksResult(**result_dict)
        print("✅ QualifiedForksResult deserialization successful")
    except Exception as e:
        print(f"❌ QualifiedForksResult deserialization failed: {e}")
        return False
    
    return True


def check_required_fields():
    """Check that all models have properly defined required fields."""
    print("\nChecking required fields...")
    
    # Test ForkQualificationMetrics required fields
    try:
        ForkQualificationMetrics()  # Should fail due to missing required fields
        print("❌ ForkQualificationMetrics allows creation without required fields")
        return False
    except Exception:
        print("✅ ForkQualificationMetrics properly validates required fields")
    
    # Test with minimal required fields
    try:
        minimal_metrics = ForkQualificationMetrics(
            id=12345,
            name="test",
            full_name="test/test",
            owner="test",
            html_url="https://github.com/test/test",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            pushed_at=datetime.now()
        )
        print("✅ ForkQualificationMetrics accepts minimal required fields")
    except Exception as e:
        print(f"❌ ForkQualificationMetrics rejects valid minimal data: {e}")
        return False
    
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
        test_fork_qualification_serialization,
        test_qualified_forks_result_serialization,
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
"""Unit tests for CSV header generation for both traditional and enhanced formats."""

import pytest

from forklift.reporting.csv_exporter import CSVExporter, CSVExportConfig


class TestCSVHeaderGeneration:
    """Test cases for CSV header generation for both traditional and enhanced formats."""

    def test_enhanced_headers_basic_configuration(self):
        """Test enhanced header generation with basic configuration."""
        config = CSVExportConfig()
        exporter = CSVExporter(config)
        
        headers = exporter._generate_enhanced_fork_analysis_headers()
        
        # Check essential fork metadata columns
        expected_base_headers = [
            "fork_name",
            "owner", 
            "stars",
            "forks_count",
            "commits_ahead",
            "commits_behind",
            "is_active",
            "features_count"
        ]
        
        for header in expected_base_headers:
            assert header in headers
        
        # Check commit-specific columns (new format)
        expected_commit_headers = [
            "commit_date",
            "commit_sha",
            "commit_description"
        ]
        
        for header in expected_commit_headers:
            assert header in headers
        
        # Verify old format column is NOT present
        assert "recent_commits" not in headers
        
        # Check URL columns are included by default
        assert "fork_url" in headers
        assert "owner_url" in headers
        assert "commit_url" in headers

    def test_enhanced_headers_without_urls(self):
        """Test enhanced header generation without URLs."""
        config = CSVExportConfig(include_urls=False)
        exporter = CSVExporter(config)
        
        headers = exporter._generate_enhanced_fork_analysis_headers()
        
        # URL columns should not be present
        assert "fork_url" not in headers
        assert "owner_url" not in headers
        assert "commit_url" not in headers
        
        # But essential columns should still be present
        assert "fork_name" in headers
        assert "owner" in headers
        assert "commit_date" in headers
        assert "commit_sha" in headers
        assert "commit_description" in headers

    def test_enhanced_headers_with_detail_mode(self):
        """Test enhanced header generation with detail mode enabled."""
        config = CSVExportConfig(detail_mode=True)
        exporter = CSVExporter(config)
        
        headers = exporter._generate_enhanced_fork_analysis_headers()
        
        # Check detail mode columns are included
        expected_detail_headers = [
            "language",
            "description",
            "last_activity",
            "created_date",
            "updated_date",
            "pushed_date",
            "size_kb",
            "open_issues",
            "is_archived",
            "is_private"
        ]
        
        for header in expected_detail_headers:
            assert header in headers
        
        # Essential and commit columns should still be present
        assert "fork_name" in headers
        assert "commit_date" in headers
        assert "commit_sha" in headers
        assert "commit_description" in headers

    def test_enhanced_headers_without_detail_mode(self):
        """Test enhanced header generation without detail mode."""
        config = CSVExportConfig(detail_mode=False)
        exporter = CSVExporter(config)
        
        headers = exporter._generate_enhanced_fork_analysis_headers()
        
        # Detail mode columns should not be present
        detail_headers = [
            "language", "description", "last_activity", "created_date",
            "updated_date", "pushed_date", "size_kb", "open_issues",
            "is_archived", "is_private"
        ]
        
        for header in detail_headers:
            assert header not in headers
        
        # But essential and commit columns should be present
        assert "fork_name" in headers
        assert "commit_date" in headers
        assert "commit_sha" in headers
        assert "commit_description" in headers

    def test_enhanced_headers_with_both_urls_and_detail_mode(self):
        """Test enhanced header generation with both URLs and detail mode enabled."""
        config = CSVExportConfig(include_urls=True, detail_mode=True)
        exporter = CSVExporter(config)
        
        headers = exporter._generate_enhanced_fork_analysis_headers()
        
        # Should have all types of columns
        # Essential columns
        assert "fork_name" in headers
        assert "owner" in headers
        assert "stars" in headers
        
        # URL columns
        assert "fork_url" in headers
        assert "owner_url" in headers
        assert "commit_url" in headers
        
        # Detail mode columns
        assert "language" in headers
        assert "description" in headers
        assert "last_activity" in headers
        
        # Commit columns
        assert "commit_date" in headers
        assert "commit_sha" in headers
        assert "commit_description" in headers

    def test_enhanced_headers_with_neither_urls_nor_detail_mode(self):
        """Test enhanced header generation with both URLs and detail mode disabled."""
        config = CSVExportConfig(include_urls=False, detail_mode=False)
        exporter = CSVExporter(config)
        
        headers = exporter._generate_enhanced_fork_analysis_headers()
        
        # Should only have essential and commit columns
        expected_minimal_headers = [
            "fork_name",
            "owner",
            "stars", 
            "forks_count",
            "commits_ahead",
            "commits_behind",
            "is_active",
            "features_count",
            "commit_date",
            "commit_sha",
            "commit_description"
        ]
        
        assert set(headers) == set(expected_minimal_headers)

    def test_traditional_fork_analysis_headers_basic(self):
        """Test traditional fork analysis header generation with basic configuration."""
        config = CSVExportConfig()
        exporter = CSVExporter(config)
        
        headers = exporter._generate_fork_analysis_headers()
        
        # Check essential fork metadata columns
        expected_base_headers = [
            "fork_name",
            "owner",
            "stars",
            "forks_count", 
            "commits_ahead",
            "commits_behind",
            "is_active",
            "features_count"
        ]
        
        for header in expected_base_headers:
            assert header in headers
        
        # URL columns should be included by default
        assert "fork_url" in headers
        assert "owner_url" in headers

    def test_traditional_fork_analysis_headers_with_commits(self):
        """Test traditional fork analysis header generation with commits enabled."""
        config = CSVExportConfig(include_commits=True)
        exporter = CSVExporter(config)
        
        headers = exporter._generate_fork_analysis_headers()
        
        # Check commit-related columns are included
        expected_commit_headers = [
            "commit_sha",
            "commit_message",
            "commit_author",
            "commit_date",
            "files_changed",
            "additions",
            "deletions"
        ]
        
        for header in expected_commit_headers:
            assert header in headers
        
        # URL should include commit URL when URLs are enabled
        assert "commit_url" in headers

    def test_traditional_fork_analysis_headers_with_detail_mode(self):
        """Test traditional fork analysis header generation with detail mode."""
        config = CSVExportConfig(detail_mode=True)
        exporter = CSVExporter(config)
        
        headers = exporter._generate_fork_analysis_headers()
        
        # Check detail mode columns
        expected_detail_headers = [
            "language",
            "description",
            "last_activity",
            "created_date",
            "updated_date",
            "pushed_date",
            "size_kb",
            "open_issues",
            "is_archived",
            "is_private"
        ]
        
        for header in expected_detail_headers:
            assert header in headers

    def test_traditional_fork_analysis_headers_without_urls(self):
        """Test traditional fork analysis header generation without URLs."""
        config = CSVExportConfig(include_urls=False)
        exporter = CSVExporter(config)
        
        headers = exporter._generate_fork_analysis_headers()
        
        # URL columns should not be present
        assert "fork_url" not in headers
        assert "owner_url" not in headers

    def test_forks_preview_headers_basic(self):
        """Test forks preview header generation with basic configuration."""
        config = CSVExportConfig()
        exporter = CSVExporter(config)
        
        headers = exporter._generate_forks_preview_headers()
        
        # Check basic preview columns
        expected_basic_headers = [
            "fork_name",
            "owner",
            "stars",
            "commits_ahead",
            "activity_status"
        ]
        
        for header in expected_basic_headers:
            assert header in headers
        
        # URL should be included by default
        assert "fork_url" in headers

    def test_forks_preview_headers_with_detail_mode(self):
        """Test forks preview header generation with detail mode."""
        config = CSVExportConfig(detail_mode=True)
        exporter = CSVExporter(config)
        
        headers = exporter._generate_forks_preview_headers()
        
        # Check detail mode columns are included
        assert "last_push_date" in headers
        assert "created_date" in headers
        assert "updated_date" in headers

    def test_forks_preview_headers_with_commits(self):
        """Test forks preview header generation with commits enabled."""
        config = CSVExportConfig(include_commits=True)
        exporter = CSVExporter(config)
        
        headers = exporter._generate_forks_preview_headers()
        
        # Should include recent_commits column
        assert "recent_commits" in headers

    def test_forks_preview_headers_without_commits(self):
        """Test forks preview header generation without commits."""
        config = CSVExportConfig(include_commits=False)
        exporter = CSVExporter(config)
        
        headers = exporter._generate_forks_preview_headers()
        
        # Should not include recent_commits column
        assert "recent_commits" not in headers

    def test_forks_preview_headers_without_urls(self):
        """Test forks preview header generation without URLs."""
        config = CSVExportConfig(include_urls=False)
        exporter = CSVExporter(config)
        
        headers = exporter._generate_forks_preview_headers()
        
        # URL column should not be present
        assert "fork_url" not in headers

    def test_ranked_features_headers_basic(self):
        """Test ranked features header generation with basic configuration."""
        config = CSVExportConfig()
        exporter = CSVExporter(config)
        
        headers = exporter._generate_ranked_features_headers()
        
        # Check basic ranked features columns
        expected_basic_headers = [
            "feature_id",
            "title",
            "category",
            "score",
            "description",
            "source_fork",
            "source_owner",
            "commits_count",
            "files_affected_count"
        ]
        
        for header in expected_basic_headers:
            assert header in headers
        
        # URL columns should be included by default
        assert "source_fork_url" in headers
        assert "source_owner_url" in headers

    def test_ranked_features_headers_with_detail_mode(self):
        """Test ranked features header generation with detail mode."""
        config = CSVExportConfig(detail_mode=True)
        exporter = CSVExporter(config)
        
        headers = exporter._generate_ranked_features_headers()
        
        # Check detail mode columns
        expected_detail_headers = [
            "ranking_factors",
            "similar_implementations_count",
            "files_affected"
        ]
        
        for header in expected_detail_headers:
            assert header in headers

    def test_ranked_features_headers_without_urls(self):
        """Test ranked features header generation without URLs."""
        config = CSVExportConfig(include_urls=False)
        exporter = CSVExporter(config)
        
        headers = exporter._generate_ranked_features_headers()
        
        # URL columns should not be present
        assert "source_fork_url" not in headers
        assert "source_owner_url" not in headers

    def test_commits_explanations_headers_basic(self):
        """Test commits explanations header generation with basic configuration."""
        config = CSVExportConfig()
        exporter = CSVExporter(config)
        
        headers = exporter._generate_commits_explanations_headers()
        
        # Check basic commit explanation columns
        expected_basic_headers = [
            "commit_sha",
            "commit_message",
            "author",
            "commit_date",
            "files_changed",
            "additions",
            "deletions"
        ]
        
        for header in expected_basic_headers:
            assert header in headers
        
        # URL columns should be included by default
        assert "commit_url" in headers
        assert "github_url" in headers

    def test_commits_explanations_headers_with_explanations(self):
        """Test commits explanations header generation with explanations enabled."""
        config = CSVExportConfig(include_explanations=True)
        exporter = CSVExporter(config)
        
        headers = exporter._generate_commits_explanations_headers()
        
        # Check explanation columns
        expected_explanation_headers = [
            "category",
            "impact_level",
            "main_repo_value",
            "what_changed",
            "explanation",
            "is_complex"
        ]
        
        for header in expected_explanation_headers:
            assert header in headers

    def test_commits_explanations_headers_with_detail_mode(self):
        """Test commits explanations header generation with detail mode."""
        config = CSVExportConfig(detail_mode=True)
        exporter = CSVExporter(config)
        
        headers = exporter._generate_commits_explanations_headers()
        
        # Check detail mode columns
        expected_detail_headers = [
            "repository_name",
            "fork_name",
            "category_confidence",
            "impact_reasoning",
            "explanation_generated_at"
        ]
        
        for header in expected_detail_headers:
            assert header in headers

    def test_commits_explanations_headers_without_urls(self):
        """Test commits explanations header generation without URLs."""
        config = CSVExportConfig(include_urls=False)
        exporter = CSVExporter(config)
        
        headers = exporter._generate_commits_explanations_headers()
        
        # URL columns should not be present
        assert "commit_url" not in headers
        assert "github_url" not in headers

    def test_header_generation_consistency_across_methods(self):
        """Test that header generation is consistent across different methods."""
        config = CSVExportConfig(include_urls=True, detail_mode=True, include_commits=True, include_explanations=True)
        exporter = CSVExporter(config)
        
        # Generate headers for different export types
        enhanced_headers = exporter._generate_enhanced_fork_analysis_headers()
        traditional_headers = exporter._generate_fork_analysis_headers()
        preview_headers = exporter._generate_forks_preview_headers()
        features_headers = exporter._generate_ranked_features_headers()
        explanations_headers = exporter._generate_commits_explanations_headers()
        
        # All should be lists of strings
        assert isinstance(enhanced_headers, list)
        assert isinstance(traditional_headers, list)
        assert isinstance(preview_headers, list)
        assert isinstance(features_headers, list)
        assert isinstance(explanations_headers, list)
        
        # All headers should be non-empty strings
        for headers in [enhanced_headers, traditional_headers, preview_headers, features_headers, explanations_headers]:
            assert len(headers) > 0
            for header in headers:
                assert isinstance(header, str)
                assert len(header) > 0

    def test_header_generation_no_duplicates(self):
        """Test that header generation produces no duplicate column names."""
        config = CSVExportConfig(include_urls=True, detail_mode=True, include_commits=True, include_explanations=True)
        exporter = CSVExporter(config)
        
        # Test each header generation method
        header_methods = [
            exporter._generate_enhanced_fork_analysis_headers,
            exporter._generate_fork_analysis_headers,
            exporter._generate_forks_preview_headers,
            exporter._generate_ranked_features_headers,
            exporter._generate_commits_explanations_headers
        ]
        
        for method in header_methods:
            headers = method()
            # Check for duplicates
            assert len(headers) == len(set(headers)), f"Duplicate headers found in {method.__name__}: {headers}"

    def test_enhanced_vs_traditional_header_differences(self):
        """Test the key differences between enhanced and traditional fork analysis headers."""
        config = CSVExportConfig()
        exporter = CSVExporter(config)
        
        enhanced_headers = exporter._generate_enhanced_fork_analysis_headers()
        traditional_headers = exporter._generate_fork_analysis_headers()
        
        # Enhanced format should have commit columns
        assert "commit_date" in enhanced_headers
        assert "commit_sha" in enhanced_headers
        assert "commit_description" in enhanced_headers
        
        # Traditional format should NOT have these commit columns by default (include_commits=False)
        assert "commit_date" not in traditional_headers
        assert "commit_sha" not in traditional_headers
        assert "commit_description" not in traditional_headers
        
        # Both should have common fork metadata
        common_headers = [
            "fork_name", "owner", "stars", "forks_count",
            "commits_ahead", "commits_behind", "is_active", "features_count"
        ]
        
        for header in common_headers:
            assert header in enhanced_headers
            assert header in traditional_headers

    def test_header_ordering_consistency(self):
        """Test that header ordering is consistent and logical."""
        config = CSVExportConfig(include_urls=True, detail_mode=True)
        exporter = CSVExporter(config)
        
        headers = exporter._generate_enhanced_fork_analysis_headers()
        
        # Essential fork metadata should come first
        essential_headers = ["fork_name", "owner", "stars", "forks_count", "commits_ahead", "commits_behind", "is_active", "features_count"]
        
        for i, header in enumerate(essential_headers):
            assert header in headers[:len(essential_headers) + 5]  # Allow some flexibility for ordering
        
        # Commit columns should be towards the end
        commit_headers = ["commit_date", "commit_sha", "commit_description"]
        for header in commit_headers:
            commit_index = headers.index(header)
            # Commit headers should be in the latter half of the headers
            assert commit_index > len(headers) // 2

    def test_header_generation_with_all_options_combinations(self):
        """Test header generation with various option combinations."""
        option_combinations = [
            {"include_urls": True, "detail_mode": True},
            {"include_urls": False, "detail_mode": True},
            {"include_urls": True, "detail_mode": False},
            {"include_urls": False, "detail_mode": False},
            {"include_urls": True, "detail_mode": True, "include_commits": True},
            {"include_urls": False, "detail_mode": False, "include_commits": False},
            {"include_urls": True, "detail_mode": True, "include_explanations": True},
            {"include_urls": False, "detail_mode": False, "include_explanations": False},
        ]
        
        for options in option_combinations:
            config = CSVExportConfig(**options)
            exporter = CSVExporter(config)
            
            # Test that all header generation methods work
            enhanced_headers = exporter._generate_enhanced_fork_analysis_headers()
            traditional_headers = exporter._generate_fork_analysis_headers()
            preview_headers = exporter._generate_forks_preview_headers()
            features_headers = exporter._generate_ranked_features_headers()
            explanations_headers = exporter._generate_commits_explanations_headers()
            
            # All should produce valid headers
            for headers in [enhanced_headers, traditional_headers, preview_headers, features_headers, explanations_headers]:
                assert isinstance(headers, list)
                assert len(headers) > 0
                assert all(isinstance(h, str) and len(h) > 0 for h in headers)

    def test_header_generation_field_name_conventions(self):
        """Test that header field names follow consistent naming conventions."""
        config = CSVExportConfig(include_urls=True, detail_mode=True, include_commits=True, include_explanations=True)
        exporter = CSVExporter(config)
        
        # Test all header generation methods
        all_headers = []
        all_headers.extend(exporter._generate_enhanced_fork_analysis_headers())
        all_headers.extend(exporter._generate_fork_analysis_headers())
        all_headers.extend(exporter._generate_forks_preview_headers())
        all_headers.extend(exporter._generate_ranked_features_headers())
        all_headers.extend(exporter._generate_commits_explanations_headers())
        
        # Remove duplicates
        unique_headers = list(set(all_headers))
        
        for header in unique_headers:
            # Should be lowercase with underscores (snake_case)
            assert header.islower(), f"Header '{header}' should be lowercase"
            assert " " not in header, f"Header '{header}' should not contain spaces"
            # Should not start or end with underscore
            assert not header.startswith("_"), f"Header '{header}' should not start with underscore"
            assert not header.endswith("_"), f"Header '{header}' should not end with underscore"
            # Should not contain consecutive underscores
            assert "__" not in header, f"Header '{header}' should not contain consecutive underscores"
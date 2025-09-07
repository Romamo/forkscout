"""Unit tests for CSV export fix functionality."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from forklift.exceptions import ForkliftOutputError, ForkliftUnicodeError


class TestValidateForkDataStructure:
    """Test the _validate_fork_data_structure helper function."""

    def test_validate_fork_data_structure_with_collected_forks_key(self):
        """Test validation with collected_forks key (current structure)."""
        from src.forklift.cli import _validate_fork_data_structure
        
        fork_data = {
            "total_forks": 5,
            "collected_forks": [
                {"name": "fork1", "owner": "user1"},
                {"name": "fork2", "owner": "user2"}
            ],
            "api_calls_made": 10
        }
        
        result = _validate_fork_data_structure(fork_data)
        
        assert len(result) == 2
        assert result[0]["name"] == "fork1"
        assert result[1]["name"] == "fork2"

    def test_validate_fork_data_structure_with_forks_key(self):
        """Test validation with forks key (backward compatibility)."""
        from src.forklift.cli import _validate_fork_data_structure
        
        fork_data = {
            "total_forks": 3,
            "forks": [
                {"name": "fork1", "owner": "user1"},
                {"name": "fork2", "owner": "user2"},
                {"name": "fork3", "owner": "user3"}
            ]
        }
        
        result = _validate_fork_data_structure(fork_data)
        
        assert len(result) == 3
        assert result[0]["name"] == "fork1"
        assert result[2]["name"] == "fork3"

    def test_validate_fork_data_structure_with_empty_data(self):
        """Test validation with empty or None data."""
        from src.forklift.cli import _validate_fork_data_structure
        
        # Test with None
        result = _validate_fork_data_structure(None)
        assert result == []
        
        # Test with empty dict
        result = _validate_fork_data_structure({})
        assert result == []
        
        # Test with non-dict
        result = _validate_fork_data_structure("not a dict")
        assert result == []

    def test_validate_fork_data_structure_with_invalid_structure(self):
        """Test validation with unexpected data structure."""
        from src.forklift.cli import _validate_fork_data_structure
        
        fork_data = {
            "total_forks": 2,
            "unexpected_key": [{"name": "fork1"}],
            "another_key": "value"
        }
        
        with patch('src.forklift.cli.logger') as mock_logger:
            result = _validate_fork_data_structure(fork_data)
            
            assert result == []
            mock_logger.warning.assert_called_once()
            assert "Unexpected fork data structure" in mock_logger.warning.call_args[0][0]

    def test_validate_fork_data_structure_with_non_list_value(self):
        """Test validation when fork data value is not a list."""
        from src.forklift.cli import _validate_fork_data_structure
        
        fork_data = {
            "collected_forks": "not a list",
            "total_forks": 0
        }
        
        with patch('src.forklift.cli.logger') as mock_logger:
            result = _validate_fork_data_structure(fork_data)
            
            assert result == []
            mock_logger.warning.assert_called_once()

    def test_validate_fork_data_structure_prefers_collected_forks(self):
        """Test that collected_forks is preferred over forks when both exist."""
        from src.forklift.cli import _validate_fork_data_structure
        
        fork_data = {
            "collected_forks": [{"name": "collected_fork"}],
            "forks": [{"name": "legacy_fork"}],
            "total_forks": 2
        }
        
        result = _validate_fork_data_structure(fork_data)
        
        assert len(result) == 1
        assert result[0]["name"] == "collected_fork"


class TestExportForksCSV:
    """Test the _export_forks_csv function."""

    @pytest.fixture
    def mock_display_service(self):
        """Create a mock repository display service."""
        service = AsyncMock()
        return service

    @pytest.fixture
    def mock_csv_manager(self):
        """Create a mock CSV manager."""
        manager = MagicMock()
        return manager

    @pytest.fixture
    def sample_fork_data_collected_forks(self):
        """Sample fork data with collected_forks key."""
        return {
            "total_forks": 2,
            "displayed_forks": 2,
            "collected_forks": [
                {
                    "name": "test-fork-1",
                    "owner": {"login": "user1"},
                    "stargazers_count": 5,
                    "html_url": "https://github.com/user1/test-fork-1"
                },
                {
                    "name": "test-fork-2", 
                    "owner": {"login": "user2"},
                    "stargazers_count": 10,
                    "html_url": "https://github.com/user2/test-fork-2"
                }
            ],
            "api_calls_made": 5
        }

    @pytest.fixture
    def sample_fork_data_forks(self):
        """Sample fork data with forks key (legacy)."""
        return {
            "total_forks": 1,
            "forks": [
                {
                    "name": "legacy-fork",
                    "owner": {"login": "legacy_user"},
                    "stargazers_count": 3,
                    "html_url": "https://github.com/legacy_user/legacy-fork"
                }
            ]
        }

    @pytest.mark.asyncio
    async def test_export_forks_csv_with_collected_forks_key(
        self, mock_display_service, sample_fork_data_collected_forks
    ):
        """Test CSV export with collected_forks key."""
        from src.forklift.cli import _export_forks_csv
        
        # Setup mock - the display service handles CSV export internally
        mock_display_service.show_fork_data.return_value = sample_fork_data_collected_forks
        
        # Execute
        await _export_forks_csv(
            mock_display_service,
            "owner/repo",
            None,
            False,  # detail=False
            0,      # show_commits=0
            False,  # force_all_commits=False
            False   # ahead_only=False
        )
        
        # Verify the display service was called with csv_export=True
        mock_display_service.show_fork_data.assert_called_once_with(
            "owner/repo",
            exclude_archived=False,
            exclude_disabled=False,
            sort_by="stars",
            show_all=True,
            disable_cache=False,
            show_commits=0,
            force_all_commits=False,
            ahead_only=False,
            csv_export=True
        )

    @pytest.mark.asyncio
    async def test_export_forks_csv_with_forks_key(
        self, mock_display_service, sample_fork_data_forks
    ):
        """Test CSV export with forks key (backward compatibility)."""
        from src.forklift.cli import _export_forks_csv
        
        # Setup mock - the display service handles CSV export internally
        mock_display_service.show_fork_data.return_value = sample_fork_data_forks
        
        # Execute
        await _export_forks_csv(
            mock_display_service,
            "owner/repo",
            None,
            False,
            0,
            False,
            False
        )
        
        # Verify the display service was called with csv_export=True
        mock_display_service.show_fork_data.assert_called_once_with(
            "owner/repo",
            exclude_archived=False,
            exclude_disabled=False,
            sort_by="stars",
            show_all=True,
            disable_cache=False,
            show_commits=0,
            force_all_commits=False,
            ahead_only=False,
            csv_export=True
        )

    @pytest.mark.asyncio
    async def test_export_forks_csv_with_empty_data(self, mock_display_service):
        """Test CSV export with empty data."""
        from src.forklift.cli import _export_forks_csv
        
        with patch('src.forklift.cli.create_csv_context') as mock_context:
            mock_context.return_value.__enter__.return_value = MagicMock()
            
            # Execute
            await _export_forks_csv(
                mock_display_service,
                "owner/repo",
                None,
                False,
                0,
                False,
                False
            )
            
            # Verify display service is called with CSV export enabled
            mock_display_service.show_fork_data.assert_called_once_with(
                "owner/repo",
                exclude_archived=False,
                exclude_disabled=False,
                sort_by="stars",
                show_all=True,
                disable_cache=False,
                show_commits=0,
                force_all_commits=False,
                ahead_only=False,
                csv_export=True
            )

    @pytest.mark.asyncio
    async def test_export_forks_csv_with_invalid_data_structure(self, mock_display_service):
        """Test CSV export with invalid data structure."""
        from src.forklift.cli import _export_forks_csv
        
        with patch('src.forklift.cli.create_csv_context') as mock_context:
            mock_context.return_value.__enter__.return_value = MagicMock()
            
            # Execute - the display service handles invalid data internally
            await _export_forks_csv(
                mock_display_service,
                "owner/repo",
                None,
                False,
                0,
                False,
                False
            )
            
            # Verify display service is called with CSV export enabled
            mock_display_service.show_fork_data.assert_called_once_with(
                "owner/repo",
                exclude_archived=False,
                exclude_disabled=False,
                sort_by="stars",
                show_all=True,
                disable_cache=False,
                show_commits=0,
                force_all_commits=False,
                ahead_only=False,
                csv_export=True
            )

    @pytest.mark.asyncio
    async def test_export_forks_csv_detail_mode(
        self, mock_display_service, sample_fork_data_collected_forks
    ):
        """Test CSV export in detail mode."""
        from src.forklift.cli import _export_forks_csv
        
        # Setup mock for detailed mode
        mock_display_service.show_fork_data_detailed.return_value = sample_fork_data_collected_forks
        
        with patch('src.forklift.cli.create_csv_context') as mock_context:
            mock_context.return_value.__enter__.return_value = MagicMock()
            
            # Execute with detail=True
            await _export_forks_csv(
                mock_display_service,
                "owner/repo",
                None,
                True,   # detail=True
                2,      # show_commits=2
                False,
                True    # ahead_only=True
            )
            
            # Verify detailed method was called
            mock_display_service.show_fork_data_detailed.assert_called_once_with(
                "owner/repo",
                max_forks=None,
                disable_cache=False,
                show_commits=2,
                force_all_commits=False,
                ahead_only=True,
                csv_export=True
            )

    @pytest.mark.asyncio
    async def test_export_forks_csv_unicode_error(self, mock_display_service):
        """Test CSV export handles Unicode errors."""
        from src.forklift.cli import _export_forks_csv
        
        # Setup mock to raise UnicodeError
        mock_display_service.show_fork_data.side_effect = UnicodeError("Unicode test error")
        
        # Execute and verify exception
        with pytest.raises(ForkliftUnicodeError) as exc_info:
            await _export_forks_csv(
                mock_display_service,
                "owner/repo",
                None,
                False,
                0,
                False,
                False
            )
        
        assert "Unicode error in CSV export" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_export_forks_csv_general_error(self, mock_display_service):
        """Test CSV export handles general errors."""
        from src.forklift.cli import _export_forks_csv
        
        # Setup mock to raise general exception
        mock_display_service.show_fork_data.side_effect = Exception("General test error")
        
        # Execute and verify exception
        with pytest.raises(ForkliftOutputError) as exc_info:
            await _export_forks_csv(
                mock_display_service,
                "owner/repo",
                None,
                False,
                0,
                False,
                False
            )
        
        assert "CSV export failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_export_forks_csv_with_show_commits(
        self, mock_display_service, sample_fork_data_collected_forks
    ):
        """Test CSV export with commit details."""
        from src.forklift.cli import _export_forks_csv
        
        with patch('src.forklift.cli.create_csv_context') as mock_context:
            mock_context.return_value.__enter__.return_value = MagicMock()
            
            # Execute with show_commits
            await _export_forks_csv(
                mock_display_service,
                "owner/repo",
                10,     # max_forks=10
                False,
                5,      # show_commits=5
                True,   # force_all_commits=True
                False
            )
            
            # Verify display service is called with commit parameters
            mock_display_service.show_fork_data.assert_called_once_with(
                "owner/repo",
                exclude_archived=False,
                exclude_disabled=False,
                sort_by="stars",
                show_all=True,
                disable_cache=False,
                show_commits=5,
                force_all_commits=True,
                ahead_only=False,
                csv_export=True
            )
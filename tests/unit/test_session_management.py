"""Tests for interactive session management and completion summaries."""

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock

import pytest
from rich.console import Console

from forkscout.analysis.interactive_orchestrator import InteractiveAnalysisOrchestrator
from forkscout.analysis.interactive_step import InteractiveStep
from forkscout.github.client import GitHubClient
from forkscout.models.interactive import InteractiveConfig, StepResult


class MockStep(InteractiveStep):
    """Mock step for testing."""

    def __init__(self, name: str, should_succeed: bool = True):
        super().__init__(name, f"Mock step: {name}")
        self.should_succeed = should_succeed

    async def execute(self, context):
        if self.should_succeed:
            return StepResult(
                step_name=self.name,
                success=True,
                data={"mock": "data"},
                summary=f"{self.name} completed successfully",
                metrics={"items": 5, "duration": 1.2}
            )
        else:
            raise Exception(f"Mock failure in {self.name}")

    def display_results(self, results):
        return f"Mock display for {self.name}"

    def get_confirmation_prompt(self, results):
        return f"Continue after {self.name}?"


@pytest.fixture
def mock_github_client():
    """Create a mock GitHub client."""
    return Mock(spec=GitHubClient)


@pytest.fixture
def mock_console():
    """Create a mock console."""
    return Mock(spec=Console)


@pytest.fixture
def temp_session_file():
    """Create a temporary session file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        temp_path = f.name
    yield temp_path
    # Cleanup
    Path(temp_path).unlink(missing_ok=True)


class TestSessionManagement:
    """Test cases for session management functionality."""

    def test_get_session_metrics(self, mock_github_client, mock_console):
        """Test session metrics calculation."""
        config = InteractiveConfig(save_session_state=False)
        orchestrator = InteractiveAnalysisOrchestrator(
            github_client=mock_github_client,
            config=config,
            console=mock_console
        )

        # Add some steps and simulate completion
        orchestrator.add_step(MockStep("Step 1"))
        orchestrator.add_step(MockStep("Step 2"))
        orchestrator.add_step(MockStep("Step 3"))

        orchestrator.session_start_time = datetime.utcnow() - timedelta(minutes=5)
        orchestrator.confirmation_count = 3

        # Add completed steps
        orchestrator.completed_steps = [
            StepResult(step_name="Step 1", success=True, data={}, summary="Success", metrics={"items": 5}),
            StepResult(step_name="Step 2", success=True, data={}, summary="Success", metrics={"items": 3}),
            StepResult(step_name="Step 3", success=False, data={}, summary="Failed", error=Exception("Test error"))
        ]

        metrics = orchestrator.get_session_metrics()

        assert metrics["total_steps"] == 3
        assert metrics["completed_steps"] == 3
        assert metrics["successful_steps"] == 2
        assert metrics["failed_steps"] == 1
        assert metrics["completion_rate"] == 1.0
        assert metrics["success_rate"] == 2/3
        assert metrics["total_confirmations"] == 3
        assert isinstance(metrics["session_duration"], timedelta)
        assert isinstance(metrics["avg_time_per_step"], timedelta)

    def test_format_duration(self, mock_github_client, mock_console):
        """Test duration formatting."""
        config = InteractiveConfig()
        orchestrator = InteractiveAnalysisOrchestrator(
            github_client=mock_github_client,
            config=config,
            console=mock_console
        )

        # Test different duration formats
        assert orchestrator._format_duration(timedelta(seconds=30)) == "30 seconds"
        assert orchestrator._format_duration(timedelta(minutes=2, seconds=15)) == "2m 15s"
        assert orchestrator._format_duration(timedelta(hours=1, minutes=30)) == "1h 30m"
        assert orchestrator._format_duration(timedelta(hours=2, minutes=45, seconds=30)) == "2h 45m"

    def test_serialize_step_data(self, mock_github_client, mock_console):
        """Test step data serialization."""
        config = InteractiveConfig()
        orchestrator = InteractiveAnalysisOrchestrator(
            github_client=mock_github_client,
            config=config,
            console=mock_console
        )

        # Test different data types
        assert orchestrator._serialize_step_data("string") == "string"
        assert orchestrator._serialize_step_data(123) == 123
        assert orchestrator._serialize_step_data([1, 2, 3]) == [1, 2, 3]
        assert orchestrator._serialize_step_data({"key": "value"}) == {"key": "value"}
        assert orchestrator._serialize_step_data(None) is None

        # Test object serialization
        class MockObject:
            def __init__(self):
                self.attr1 = "value1"
                self.attr2 = 42
                self.attr3 = [1, 2, 3]

        obj = MockObject()
        serialized = orchestrator._serialize_step_data(obj)
        assert isinstance(serialized, dict)
        assert serialized["attr1"] == "value1"
        assert serialized["attr2"] == 42
        assert serialized["attr3"] == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_save_session_state(self, mock_github_client, mock_console, temp_session_file):
        """Test session state saving."""
        config = InteractiveConfig(
            save_session_state=True,
            session_state_file=temp_session_file
        )
        orchestrator = InteractiveAnalysisOrchestrator(
            github_client=mock_github_client,
            config=config,
            console=mock_console
        )

        # Set up session data
        orchestrator.session_start_time = datetime.utcnow()
        orchestrator.context = {"repo_url": "https://github.com/test/repo", "test_key": "test_value"}
        orchestrator.confirmation_count = 2
        orchestrator.add_step(MockStep("Test Step"))

        # Add completed step
        step_result = StepResult(
            step_name="Test Step",
            success=True,
            data={"result": "test"},
            summary="Test completed",
            metrics={"items": 10}
        )
        orchestrator.completed_steps.append(step_result)

        # Save session state
        await orchestrator._save_session_state()

        # Verify file was created and contains expected data
        assert Path(temp_session_file).exists()

        with open(temp_session_file) as f:
            saved_state = json.load(f)

        assert saved_state["version"] == "1.0"
        assert saved_state["repo_url"] == "https://github.com/test/repo"
        assert saved_state["total_steps"] == 1
        assert saved_state["confirmation_count"] == 2
        assert len(saved_state["completed_steps"]) == 1
        assert saved_state["completed_steps"][0]["step_name"] == "Test Step"
        assert saved_state["completed_steps"][0]["success"] is True
        assert saved_state["context"]["test_key"] == "test_value"

    @pytest.mark.asyncio
    async def test_load_session_state(self, mock_github_client, mock_console, temp_session_file):
        """Test session state loading."""
        # Create session state file
        session_data = {
            "version": "1.0",
            "created_at": datetime.utcnow().isoformat(),
            "session_start_time": (datetime.utcnow() - timedelta(minutes=10)).isoformat(),
            "repo_url": "https://github.com/test/repo",
            "total_steps": 2,
            "completed_steps": [
                {
                    "step_name": "Step 1",
                    "success": True,
                    "summary": "Step 1 completed",
                    "data": {"result": "step1"},
                    "metrics": {"items": 5}
                }
            ],
            "context": {"repo_url": "https://github.com/test/repo", "loaded_key": "loaded_value"},
            "confirmation_count": 1
        }

        with open(temp_session_file, "w") as f:
            json.dump(session_data, f)

        config = InteractiveConfig(
            save_session_state=True,
            session_state_file=temp_session_file
        )
        orchestrator = InteractiveAnalysisOrchestrator(
            github_client=mock_github_client,
            config=config,
            console=mock_console
        )

        # Load session state
        await orchestrator._load_session_state()

        # Verify state was restored
        assert orchestrator.session_start_time is not None
        assert orchestrator.confirmation_count == 1
        assert len(orchestrator.completed_steps) == 1
        assert orchestrator.completed_steps[0].step_name == "Step 1"
        assert orchestrator.completed_steps[0].success is True
        assert orchestrator.context["loaded_key"] == "loaded_value"
        assert orchestrator.context["repo_url"] == "https://github.com/test/repo"

    @pytest.mark.asyncio
    async def test_load_old_session_state(self, mock_github_client, mock_console, temp_session_file):
        """Test loading old session state (should be skipped)."""
        # Create old session state file (25 hours old)
        old_time = datetime.utcnow() - timedelta(hours=25)
        session_data = {
            "version": "1.0",
            "created_at": old_time.isoformat(),
            "session_start_time": old_time.isoformat(),
            "repo_url": "https://github.com/test/repo",
            "completed_steps": [],
            "context": {},
            "confirmation_count": 0
        }

        with open(temp_session_file, "w") as f:
            json.dump(session_data, f)

        config = InteractiveConfig(
            save_session_state=True,
            session_state_file=temp_session_file
        )
        orchestrator = InteractiveAnalysisOrchestrator(
            github_client=mock_github_client,
            config=config,
            console=mock_console
        )

        # Load session state
        await orchestrator._load_session_state()

        # Verify old state was not restored
        assert orchestrator.session_start_time is None
        assert orchestrator.confirmation_count == 0
        assert len(orchestrator.completed_steps) == 0

    @pytest.mark.asyncio
    async def test_backup_and_restore(self, mock_github_client, mock_console, temp_session_file):
        """Test backup creation and restoration."""
        config = InteractiveConfig(
            save_session_state=True,
            session_state_file=temp_session_file
        )
        orchestrator = InteractiveAnalysisOrchestrator(
            github_client=mock_github_client,
            config=config,
            console=mock_console
        )

        # Create initial session file
        initial_data = {"version": "1.0", "test": "initial"}
        with open(temp_session_file, "w") as f:
            json.dump(initial_data, f)

        # Set up new session data
        orchestrator.session_start_time = datetime.utcnow()
        orchestrator.context = {"repo_url": "https://github.com/test/repo"}

        # Save session state (should create backup)
        await orchestrator._save_session_state()

        # Verify backup was created
        backup_file = Path(temp_session_file).with_suffix(".json.backup")
        assert backup_file.exists()

        # Verify backup contains original data
        with open(backup_file) as f:
            backup_data = json.load(f)
        assert backup_data["test"] == "initial"

        # Cleanup backup
        backup_file.unlink()

    def test_display_success_summary(self, mock_github_client, mock_console):
        """Test success summary display."""
        config = InteractiveConfig()
        orchestrator = InteractiveAnalysisOrchestrator(
            github_client=mock_github_client,
            config=config,
            console=mock_console
        )

        # Set up session data
        orchestrator.session_start_time = datetime.utcnow() - timedelta(minutes=5)
        orchestrator.confirmation_count = 3
        orchestrator.add_step(MockStep("Step 1"))
        orchestrator.add_step(MockStep("Step 2"))

        # Add completed steps
        orchestrator.completed_steps = [
            StepResult(step_name="Step 1", success=True, data={}, summary="Step 1 completed successfully"),
            StepResult(step_name="Step 2", success=True, data={}, summary="Step 2 completed successfully")
        ]

        # Create mock final result
        final_result = {
            "fork_analyses": [Mock(), Mock()],
            "ranked_features": [Mock(score=95), Mock(score=85), Mock(score=75)],
            "total_features": 3
        }

        # Test success summary
        orchestrator._display_success_summary(final_result, timedelta(minutes=5))

        # Verify console.print was called
        assert mock_console.print.called

    def test_display_abort_summary(self, mock_github_client, mock_console):
        """Test abort summary display."""
        config = InteractiveConfig()
        orchestrator = InteractiveAnalysisOrchestrator(
            github_client=mock_github_client,
            config=config,
            console=mock_console
        )

        # Set up session data
        orchestrator.session_start_time = datetime.utcnow() - timedelta(minutes=3)
        orchestrator.confirmation_count = 2
        orchestrator.add_step(MockStep("Step 1"))
        orchestrator.add_step(MockStep("Step 2"))

        # Add one completed step
        orchestrator.completed_steps = [
            StepResult(step_name="Step 1", success=True, data={}, summary="Step 1 completed successfully")
        ]

        # Test abort summary
        orchestrator._display_abort_summary(timedelta(minutes=3))

        # Verify console.print was called
        assert mock_console.print.called

    def test_display_error_summary(self, mock_github_client, mock_console):
        """Test error summary display."""
        config = InteractiveConfig()
        orchestrator = InteractiveAnalysisOrchestrator(
            github_client=mock_github_client,
            config=config,
            console=mock_console
        )

        # Set up session data
        orchestrator.session_start_time = datetime.utcnow() - timedelta(minutes=2)
        orchestrator.confirmation_count = 1
        orchestrator.add_step(MockStep("Step 1"))

        # Add completed step
        orchestrator.completed_steps = [
            StepResult(step_name="Step 1", success=True, data={}, summary="Step 1 completed successfully")
        ]

        # Test error summary
        error = Exception("Test error message")
        orchestrator._display_error_summary(error, timedelta(minutes=2))

        # Verify console.print was called
        assert mock_console.print.called

    def test_create_result_with_summary(self, mock_github_client, mock_console):
        """Test result creation with completion summary."""
        config = InteractiveConfig()
        orchestrator = InteractiveAnalysisOrchestrator(
            github_client=mock_github_client,
            config=config,
            console=mock_console
        )

        # Set up session data
        orchestrator.session_start_time = datetime.utcnow() - timedelta(minutes=10)
        orchestrator.confirmation_count = 5

        # Add completed steps
        orchestrator.completed_steps = [
            StepResult(step_name="Step 1", success=True, data={}, summary="Success"),
            StepResult(step_name="Step 2", success=True, data={}, summary="Success")
        ]

        final_result = {"test": "data"}

        # Create result (should display summary)
        result = orchestrator._create_result(final_result=final_result)

        # Verify result properties
        assert result.final_result == final_result
        assert not result.user_aborted
        assert len(result.completed_steps) == 2
        assert result.total_confirmations == 5
        assert isinstance(result.session_duration, timedelta)

        # Verify summary was displayed
        assert mock_console.print.called

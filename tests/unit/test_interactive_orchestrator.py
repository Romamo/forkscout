"""Tests for InteractiveAnalysisOrchestrator."""

import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from rich.console import Console

from forklift.analysis.interactive_orchestrator import InteractiveAnalysisOrchestrator
from forklift.analysis.interactive_step import InteractiveStep
from forklift.github.client import GitHubClient
from forklift.models.interactive import InteractiveConfig, StepResult, UserChoice


class MockInteractiveStep(InteractiveStep):
    """Mock interactive step for testing."""

    def __init__(self, name: str, description: str, should_fail: bool = False):
        super().__init__(name, description)
        self.should_fail = should_fail
        self.execute_called = False
        self.display_called = False
        self.confirmation_called = False

    async def execute(self, context):
        self.execute_called = True
        if self.should_fail:
            raise Exception(f"Mock failure in {self.name}")

        return StepResult(
            step_name=self.name,
            success=True,
            data={"mock_data": f"result_from_{self.name.lower().replace(' ', '_')}"},
            summary=f"Successfully completed {self.name}",
            metrics={"items_processed": 10, "duration_seconds": 1.5}
        )

    def display_results(self, results: StepResult) -> str:
        self.display_called = True
        return f"Mock display for {self.name}: {results.summary}"

    def get_confirmation_prompt(self, results: StepResult) -> str:
        self.confirmation_called = True
        return f"Continue after {self.name}?"


@pytest.fixture
def mock_github_client():
    """Create a mock GitHub client."""
    client = Mock(spec=GitHubClient)
    return client


@pytest.fixture
def interactive_config():
    """Create interactive configuration for testing."""
    return InteractiveConfig(
        enabled=True,
        confirmation_timeout_seconds=1,
        default_choice="continue",
        show_detailed_results=True,
        save_session_state=False  # Disable for most tests
    )


@pytest.fixture
def mock_console():
    """Create a mock console."""
    console = Mock(spec=Console)
    return console


@pytest.fixture
def orchestrator(mock_github_client, interactive_config, mock_console):
    """Create an orchestrator instance for testing."""
    return InteractiveAnalysisOrchestrator(
        github_client=mock_github_client,
        config=interactive_config,
        console=mock_console
    )


class TestInteractiveAnalysisOrchestrator:
    """Test cases for InteractiveAnalysisOrchestrator."""

    def test_init(self, mock_github_client, interactive_config, mock_console):
        """Test orchestrator initialization."""
        orchestrator = InteractiveAnalysisOrchestrator(
            github_client=mock_github_client,
            config=interactive_config,
            console=mock_console
        )

        assert orchestrator.github_client == mock_github_client
        assert orchestrator.config == interactive_config
        assert orchestrator.console == mock_console
        assert orchestrator.steps == []
        assert orchestrator.context == {}
        assert orchestrator.session_start_time is None
        assert orchestrator.completed_steps == []
        assert orchestrator.confirmation_count == 0

    def test_add_step(self, orchestrator):
        """Test adding steps to the orchestrator."""
        step1 = MockInteractiveStep("Step 1", "First step")
        step2 = MockInteractiveStep("Step 2", "Second step")

        orchestrator.add_step(step1)
        orchestrator.add_step(step2)

        assert len(orchestrator.steps) == 2
        assert orchestrator.steps[0] == step1
        assert orchestrator.steps[1] == step2

    @pytest.mark.asyncio
    async def test_execute_step_success(self, orchestrator):
        """Test successful step execution."""
        step = MockInteractiveStep("Test Step", "Test description")

        result = await orchestrator.execute_step(step)

        assert step.execute_called
        assert result.success
        assert result.step_name == "Test Step"
        assert result.summary == "Successfully completed Test Step"
        assert "step_test_step_result" in orchestrator.context

    @pytest.mark.asyncio
    async def test_execute_step_failure(self, orchestrator):
        """Test step execution failure."""
        step = MockInteractiveStep("Failing Step", "This will fail", should_fail=True)

        result = await orchestrator.execute_step(step)

        assert step.execute_called
        assert not result.success
        assert result.step_name == "Failing Step"
        assert "Step failed" in result.summary
        assert result.error is not None

    def test_display_step_results(self, orchestrator):
        """Test displaying step results."""
        step = MockInteractiveStep("Display Step", "Test display")
        orchestrator.add_step(step)

        result = StepResult(
            step_name="Display Step",
            success=True,
            data={"test": "data"},
            summary="Test summary",
            metrics={"count": 5}
        )

        orchestrator.display_step_results("Display Step", result)

        assert step.display_called
        assert orchestrator.console.print.called

    @pytest.mark.asyncio
    async def test_get_user_confirmation_continue(self, orchestrator):
        """Test user confirmation with continue choice."""
        step = MockInteractiveStep("Confirm Step", "Test confirmation")
        orchestrator.add_step(step)

        result = StepResult(
            step_name="Confirm Step",
            success=True,
            data={},
            summary="Test"
        )

        with patch("forklift.analysis.interactive_orchestrator.Confirm.ask", return_value=True):
            choice = await orchestrator.get_user_confirmation("Confirm Step", result)

        assert choice == UserChoice.CONTINUE
        assert orchestrator.confirmation_count == 1
        assert step.confirmation_called

    @pytest.mark.asyncio
    async def test_get_user_confirmation_abort(self, orchestrator):
        """Test user confirmation with abort choice."""
        step = MockInteractiveStep("Abort Step", "Test abort")
        orchestrator.add_step(step)

        result = StepResult(
            step_name="Abort Step",
            success=True,
            data={},
            summary="Test"
        )

        with patch("forklift.analysis.interactive_orchestrator.Confirm.ask", return_value=False):
            choice = await orchestrator.get_user_confirmation("Abort Step", result)

        assert choice == UserChoice.ABORT
        assert orchestrator.confirmation_count == 1

    @pytest.mark.asyncio
    async def test_get_user_confirmation_keyboard_interrupt(self, orchestrator):
        """Test user confirmation with keyboard interrupt."""
        step = MockInteractiveStep("Interrupt Step", "Test interrupt")
        orchestrator.add_step(step)

        result = StepResult(
            step_name="Interrupt Step",
            success=True,
            data={},
            summary="Test"
        )

        with patch("forklift.analysis.interactive_orchestrator.Confirm.ask", side_effect=KeyboardInterrupt):
            choice = await orchestrator.get_user_confirmation("Interrupt Step", result)

        assert choice == UserChoice.ABORT

    @pytest.mark.asyncio
    async def test_handle_step_error_continue(self, orchestrator):
        """Test handling step error with continue choice."""
        error = Exception("Test error")

        with patch("forklift.analysis.interactive_orchestrator.Confirm.ask", return_value=True):
            choice = await orchestrator._handle_step_error("Error Step", error)

        assert choice == UserChoice.CONTINUE

    @pytest.mark.asyncio
    async def test_handle_step_error_abort(self, orchestrator):
        """Test handling step error with abort choice."""
        error = Exception("Test error")

        with patch("forklift.analysis.interactive_orchestrator.Confirm.ask", return_value=False):
            choice = await orchestrator._handle_step_error("Error Step", error)

        assert choice == UserChoice.ABORT

    @pytest.mark.asyncio
    async def test_run_interactive_analysis_success(self, orchestrator):
        """Test successful interactive analysis run."""
        step1 = MockInteractiveStep("Step 1", "First step")
        step2 = MockInteractiveStep("Step 2", "Second step")

        orchestrator.add_step(step1)
        orchestrator.add_step(step2)

        with patch("forklift.analysis.interactive_orchestrator.Confirm.ask", return_value=True):
            result = await orchestrator.run_interactive_analysis("https://github.com/test/repo")

        assert not result.user_aborted
        assert len(result.completed_steps) == 2
        assert result.session_duration > timedelta(0)
        assert result.total_confirmations == 1  # Only one confirmation between steps
        assert step1.execute_called
        assert step2.execute_called

    @pytest.mark.asyncio
    async def test_run_interactive_analysis_user_abort(self, orchestrator):
        """Test interactive analysis with user abort."""
        step1 = MockInteractiveStep("Step 1", "First step")
        step2 = MockInteractiveStep("Step 2", "Second step")

        orchestrator.add_step(step1)
        orchestrator.add_step(step2)

        with patch("forklift.analysis.interactive_orchestrator.Confirm.ask", return_value=False):
            result = await orchestrator.run_interactive_analysis("https://github.com/test/repo")

        assert result.user_aborted
        assert len(result.completed_steps) == 1  # Only first step completed
        assert step1.execute_called
        assert not step2.execute_called

    @pytest.mark.asyncio
    async def test_run_interactive_analysis_step_failure_continue(self, orchestrator):
        """Test interactive analysis with step failure and continue."""
        step1 = MockInteractiveStep("Step 1", "First step", should_fail=True)
        step2 = MockInteractiveStep("Step 2", "Second step")

        orchestrator.add_step(step1)
        orchestrator.add_step(step2)

        with patch("forklift.analysis.interactive_orchestrator.Confirm.ask", return_value=True):
            result = await orchestrator.run_interactive_analysis("https://github.com/test/repo")

        assert not result.user_aborted
        assert len(result.completed_steps) == 2
        assert not result.completed_steps[0].success  # First step failed
        assert result.completed_steps[1].success  # Second step succeeded

    @pytest.mark.asyncio
    async def test_run_interactive_analysis_step_failure_abort(self, orchestrator):
        """Test interactive analysis with step failure and abort."""
        step1 = MockInteractiveStep("Step 1", "First step", should_fail=True)
        step2 = MockInteractiveStep("Step 2", "Second step")

        orchestrator.add_step(step1)
        orchestrator.add_step(step2)

        # First call for error handling (abort), no second call needed
        with patch("forklift.analysis.interactive_orchestrator.Confirm.ask", return_value=False):
            result = await orchestrator.run_interactive_analysis("https://github.com/test/repo")

        assert result.user_aborted
        assert len(result.completed_steps) == 1
        assert not result.completed_steps[0].success

    def test_is_step_completed(self, orchestrator):
        """Test checking if step is completed."""
        completed_step = StepResult(
            step_name="Completed Step",
            success=True,
            data={},
            summary="Done"
        )
        orchestrator.completed_steps.append(completed_step)

        assert orchestrator._is_step_completed("Completed Step")
        assert not orchestrator._is_step_completed("Not Completed Step")

    @pytest.mark.asyncio
    async def test_session_state_management(self, mock_github_client, mock_console):
        """Test session state save and load functionality."""
        with tempfile.TemporaryDirectory() as temp_dir:
            session_file = Path(temp_dir) / "test_session.json"

            config = InteractiveConfig(
                enabled=True,
                save_session_state=True,
                session_state_file=str(session_file)
            )

            orchestrator = InteractiveAnalysisOrchestrator(
                github_client=mock_github_client,
                config=config,
                console=mock_console
            )

            # Set up some state
            orchestrator.session_start_time = datetime.utcnow()
            orchestrator.context = {"test_key": "test_value"}
            orchestrator.confirmation_count = 2

            completed_step = StepResult(
                step_name="Test Step",
                success=True,
                data={"result": "test"},
                summary="Test completed"
            )
            orchestrator.completed_steps.append(completed_step)

            # Save state
            await orchestrator._save_session_state()

            # Verify file was created
            assert session_file.exists()

            # Create new orchestrator and load state
            new_orchestrator = InteractiveAnalysisOrchestrator(
                github_client=mock_github_client,
                config=config,
                console=mock_console
            )

            await new_orchestrator._load_session_state()

            # Verify state was restored
            assert new_orchestrator.session_start_time is not None
            assert new_orchestrator.context["test_key"] == "test_value"
            assert new_orchestrator.confirmation_count == 2
            assert len(new_orchestrator.completed_steps) == 1
            assert new_orchestrator.completed_steps[0].step_name == "Test Step"

    @pytest.mark.asyncio
    async def test_cleanup_session_state(self, mock_github_client, mock_console):
        """Test session state cleanup."""
        with tempfile.TemporaryDirectory() as temp_dir:
            session_file = Path(temp_dir) / "cleanup_test.json"

            config = InteractiveConfig(
                enabled=True,
                save_session_state=True,
                session_state_file=str(session_file)
            )

            orchestrator = InteractiveAnalysisOrchestrator(
                github_client=mock_github_client,
                config=config,
                console=mock_console
            )

            # Create session file
            session_file.write_text('{"test": "data"}')
            assert session_file.exists()

            # Cleanup
            await orchestrator._cleanup_session_state()

            # Verify file was deleted
            assert not session_file.exists()

    def test_create_result(self, orchestrator):
        """Test creating analysis result."""
        orchestrator.session_start_time = datetime.utcnow() - timedelta(minutes=5)
        orchestrator.confirmation_count = 3

        completed_step = StepResult(
            step_name="Test Step",
            success=True,
            data={},
            summary="Test"
        )
        orchestrator.completed_steps.append(completed_step)

        result = orchestrator._create_result(
            final_result={"analysis": "complete"},
            user_aborted=False
        )

        assert not result.user_aborted
        assert result.final_result == {"analysis": "complete"}
        assert len(result.completed_steps) == 1
        assert result.session_duration > timedelta(minutes=4)
        assert result.total_confirmations == 3

    def test_display_welcome_message(self, orchestrator):
        """Test welcome message display."""
        orchestrator.add_step(MockInteractiveStep("Step 1", "Test"))
        orchestrator.add_step(MockInteractiveStep("Step 2", "Test"))

        orchestrator._display_welcome_message("https://github.com/test/repo")

        # Verify console.print was called
        assert orchestrator.console.print.called

        # Check that the call included repository URL and step count
        call_args = orchestrator.console.print.call_args[0][0]
        # The Panel object contains the text, so we need to check its renderable content
        panel_content = str(call_args.renderable)
        assert "https://github.com/test/repo" in panel_content
        assert "2 analysis phases" in panel_content

    def test_display_metrics(self, orchestrator):
        """Test metrics display."""
        metrics = {
            "items_processed": 100,
            "duration_seconds": 45.2,
            "success_rate": 0.95
        }

        orchestrator._display_metrics(metrics)

        # Verify console.print was called for the table
        assert orchestrator.console.print.called

    def test_display_metrics_empty(self, orchestrator):
        """Test metrics display with empty metrics."""
        orchestrator._display_metrics({})

        # Should not call print for empty metrics
        assert not orchestrator.console.print.called

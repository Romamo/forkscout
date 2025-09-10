"""Environment detection utilities for CI/automation detection."""

import os
from typing import ClassVar


class EnvironmentDetector:
    """Detect execution environment characteristics."""

    # Common CI environment variables
    CI_ENVIRONMENT_VARS: ClassVar[list[str]] = [
        "CI",
        "CONTINUOUS_INTEGRATION",
        "BUILD_NUMBER",
        "JENKINS_URL",
        "TRAVIS",
        "CIRCLECI",
        "APPVEYOR",
        "GITLAB_CI",
        "GITHUB_ACTIONS",
        "BUILDKITE",
        "DRONE",
        "TEAMCITY_VERSION",
        "TF_BUILD",  # Azure DevOps
        "CODEBUILD_BUILD_ID",  # AWS CodeBuild
        "BAMBOO_BUILD_NUMBER",
        "GO_PIPELINE_NAME",  # GoCD
    ]

    # Automation/scripting indicators
    AUTOMATION_INDICATORS: ClassVar[list[str]] = [
        "AUTOMATED",
        "BATCH_MODE",
        "NON_INTERACTIVE",
        "SCRIPT_MODE",
        "HEADLESS",
    ]

    # Container environment indicators
    CONTAINER_INDICATORS: ClassVar[list[str]] = [
        "DOCKER_CONTAINER",
        "KUBERNETES_SERVICE_HOST",
        "CONTAINER",
    ]

    @classmethod
    def is_ci_environment(cls) -> bool:
        """Check if running in a CI/CD environment.

        Returns:
            True if CI environment is detected, False otherwise.
        """
        return any(os.getenv(var) for var in cls.CI_ENVIRONMENT_VARS)

    @classmethod
    def is_automation_environment(cls) -> bool:
        """Check if running in an automated/scripted environment.

        Returns:
            True if automation environment is detected, False otherwise.
        """
        return any(os.getenv(var) for var in cls.AUTOMATION_INDICATORS)

    @classmethod
    def is_container_environment(cls) -> bool:
        """Check if running in a container environment.

        Returns:
            True if container environment is detected, False otherwise.
        """
        # Check environment variables
        for var in cls.CONTAINER_INDICATORS:
            if os.getenv(var):
                return True

        # Check for container-specific files
        container_files = [
            "/.dockerenv",
            "/proc/1/cgroup",
        ]

        for file_path in container_files:
            try:
                if os.path.exists(file_path):
                    if file_path == "/proc/1/cgroup":
                        # Check if cgroup contains docker or containerd
                        with open(file_path) as f:
                            content = f.read().lower()
                            if "docker" in content or "containerd" in content:
                                return True
                    else:
                        return True
            except (OSError, UnicodeDecodeError):
                continue

        return False

    @classmethod
    def get_detected_ci_system(cls) -> str | None:
        """Get the name of the detected CI system.

        Returns:
            Name of CI system if detected, None otherwise.
        """
        ci_systems = {
            "JENKINS_URL": "Jenkins",
            "TRAVIS": "Travis CI",
            "CIRCLECI": "CircleCI",
            "APPVEYOR": "AppVeyor",
            "GITLAB_CI": "GitLab CI",
            "GITHUB_ACTIONS": "GitHub Actions",
            "BUILDKITE": "Buildkite",
            "DRONE": "Drone",
            "TEAMCITY_VERSION": "TeamCity",
            "TF_BUILD": "Azure DevOps",
            "CODEBUILD_BUILD_ID": "AWS CodeBuild",
            "BAMBOO_BUILD_NUMBER": "Bamboo",
            "GO_PIPELINE_NAME": "GoCD",
        }

        for var, name in ci_systems.items():
            if os.getenv(var):
                return name

        # Generic CI detection
        if os.getenv("CI") or os.getenv("CONTINUOUS_INTEGRATION"):
            return "Generic CI"

        return None

    @classmethod
    def is_output_redirected(cls) -> bool:
        """Check if output is being redirected to a file or pipe.

        This is a heuristic based on TTY status and environment.

        Returns:
            True if output appears to be redirected, False otherwise.
        """
        from .terminal_detector import TerminalDetector

        # If stdout is not a TTY, it's likely redirected
        if not TerminalDetector.is_stdout_tty():
            return True

        # Check for explicit redirection indicators
        return bool(os.getenv("FORKSCOUT_OUTPUT_REDIRECTED"))

    @classmethod
    def is_input_redirected(cls) -> bool:
        """Check if input is being redirected from a file or pipe.

        Returns:
            True if input appears to be redirected, False otherwise.
        """
        from .terminal_detector import TerminalDetector

        # If stdin is not a TTY, it's likely redirected
        return not TerminalDetector.is_stdin_tty()

    @classmethod
    def get_shell_info(cls) -> dict[str, str | None]:
        """Get information about the current shell environment.

        Returns:
            Dictionary with shell information.
        """
        return {
            "shell": os.getenv("SHELL"),
            "shlvl": os.getenv("SHLVL"),
            "term": os.getenv("TERM"),
            "term_program": os.getenv("TERM_PROGRAM"),
            "ssh_connection": os.getenv("SSH_CONNECTION"),
            "display": os.getenv("DISPLAY"),
        }

    @classmethod
    def get_environment_info(cls) -> dict:
        """Get comprehensive environment information.

        Returns:
            Dictionary containing all environment detection results.
        """
        return {
            "is_ci": cls.is_ci_environment(),
            "is_automation": cls.is_automation_environment(),
            "is_container": cls.is_container_environment(),
            "ci_system": cls.get_detected_ci_system(),
            "output_redirected": cls.is_output_redirected(),
            "input_redirected": cls.is_input_redirected(),
            "shell_info": cls.get_shell_info(),
            "detected_vars": {
                var: os.getenv(var) for var in cls.CI_ENVIRONMENT_VARS
                if os.getenv(var)
            }
        }

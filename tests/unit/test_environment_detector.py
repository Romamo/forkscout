"""Tests for environment detection functionality."""

import os
from unittest.mock import patch, mock_open, Mock
import pytest

from src.forklift.display.environment_detector import EnvironmentDetector


class TestEnvironmentDetector:
    """Test environment detection methods."""
    
    def test_is_ci_environment_true_ci_var(self):
        """Test CI environment detection with CI variable."""
        with patch.dict(os.environ, {'CI': 'true'}, clear=True):
            assert EnvironmentDetector.is_ci_environment() is True
    
    def test_is_ci_environment_true_continuous_integration(self):
        """Test CI environment detection with CONTINUOUS_INTEGRATION variable."""
        with patch.dict(os.environ, {'CONTINUOUS_INTEGRATION': 'true'}, clear=True):
            assert EnvironmentDetector.is_ci_environment() is True
    
    def test_is_ci_environment_true_jenkins(self):
        """Test CI environment detection with Jenkins variables."""
        with patch.dict(os.environ, {'JENKINS_URL': 'http://jenkins.example.com'}, clear=True):
            assert EnvironmentDetector.is_ci_environment() is True
    
    def test_is_ci_environment_true_github_actions(self):
        """Test CI environment detection with GitHub Actions."""
        with patch.dict(os.environ, {'GITHUB_ACTIONS': 'true'}, clear=True):
            assert EnvironmentDetector.is_ci_environment() is True
    
    def test_is_ci_environment_false(self):
        """Test CI environment detection when not in CI."""
        with patch.dict(os.environ, {}, clear=True):
            assert EnvironmentDetector.is_ci_environment() is False
    
    def test_is_automation_environment_true(self):
        """Test automation environment detection when automated."""
        with patch.dict(os.environ, {'AUTOMATED': '1'}, clear=True):
            assert EnvironmentDetector.is_automation_environment() is True
    
    def test_is_automation_environment_batch_mode(self):
        """Test automation environment detection with batch mode."""
        with patch.dict(os.environ, {'BATCH_MODE': 'true'}, clear=True):
            assert EnvironmentDetector.is_automation_environment() is True
    
    def test_is_automation_environment_false(self):
        """Test automation environment detection when not automated."""
        with patch.dict(os.environ, {}, clear=True):
            assert EnvironmentDetector.is_automation_environment() is False
    
    def test_is_container_environment_docker_env(self):
        """Test container environment detection with Docker environment variable."""
        with patch.dict(os.environ, {'DOCKER_CONTAINER': '1'}, clear=True):
            assert EnvironmentDetector.is_container_environment() is True
    
    def test_is_container_environment_kubernetes(self):
        """Test container environment detection with Kubernetes."""
        with patch.dict(os.environ, {'KUBERNETES_SERVICE_HOST': '10.0.0.1'}, clear=True):
            assert EnvironmentDetector.is_container_environment() is True
    
    def test_is_container_environment_dockerenv_file(self):
        """Test container environment detection with .dockerenv file."""
        with patch.dict(os.environ, {}, clear=True):
            with patch('os.path.exists') as mock_exists:
                mock_exists.side_effect = lambda path: path == '/.dockerenv'
                assert EnvironmentDetector.is_container_environment() is True
    
    def test_is_container_environment_cgroup_docker(self):
        """Test container environment detection with Docker in cgroup."""
        with patch.dict(os.environ, {}, clear=True):
            with patch('os.path.exists') as mock_exists:
                mock_exists.side_effect = lambda path: path == '/proc/1/cgroup'
                with patch('builtins.open', mock_open(read_data='1:name=systemd:/docker/abc123')):
                    assert EnvironmentDetector.is_container_environment() is True
    
    def test_is_container_environment_cgroup_containerd(self):
        """Test container environment detection with containerd in cgroup."""
        with patch.dict(os.environ, {}, clear=True):
            with patch('os.path.exists') as mock_exists:
                mock_exists.side_effect = lambda path: path == '/proc/1/cgroup'
                with patch('builtins.open', mock_open(read_data='1:name=systemd:/containerd/xyz789')):
                    assert EnvironmentDetector.is_container_environment() is True
    
    def test_is_container_environment_cgroup_no_container(self):
        """Test container environment detection with non-container cgroup."""
        with patch.dict(os.environ, {}, clear=True):
            with patch('os.path.exists') as mock_exists:
                mock_exists.side_effect = lambda path: path == '/proc/1/cgroup'
                with patch('builtins.open', mock_open(read_data='1:name=systemd:/init.scope')):
                    assert EnvironmentDetector.is_container_environment() is False
    
    def test_is_container_environment_file_error(self):
        """Test container environment detection with file read error."""
        with patch.dict(os.environ, {}, clear=True):
            with patch('os.path.exists') as mock_exists:
                mock_exists.side_effect = lambda path: path == '/proc/1/cgroup'
                with patch('builtins.open', side_effect=IOError("Permission denied")):
                    assert EnvironmentDetector.is_container_environment() is False
    
    def test_is_container_environment_false(self):
        """Test container environment detection when not in container."""
        with patch.dict(os.environ, {}, clear=True):
            with patch('os.path.exists', return_value=False):
                assert EnvironmentDetector.is_container_environment() is False
    
    def test_get_detected_ci_system_jenkins(self):
        """Test CI system detection for Jenkins."""
        with patch.dict(os.environ, {'JENKINS_URL': 'http://jenkins.example.com'}, clear=True):
            assert EnvironmentDetector.get_detected_ci_system() == 'Jenkins'
    
    def test_get_detected_ci_system_github_actions(self):
        """Test CI system detection for GitHub Actions."""
        with patch.dict(os.environ, {'GITHUB_ACTIONS': 'true'}, clear=True):
            assert EnvironmentDetector.get_detected_ci_system() == 'GitHub Actions'
    
    def test_get_detected_ci_system_travis(self):
        """Test CI system detection for Travis CI."""
        with patch.dict(os.environ, {'TRAVIS': 'true'}, clear=True):
            assert EnvironmentDetector.get_detected_ci_system() == 'Travis CI'
    
    def test_get_detected_ci_system_generic(self):
        """Test CI system detection for generic CI."""
        with patch.dict(os.environ, {'CI': 'true'}, clear=True):
            assert EnvironmentDetector.get_detected_ci_system() == 'Generic CI'
    
    def test_get_detected_ci_system_none(self):
        """Test CI system detection when not in CI."""
        with patch.dict(os.environ, {}, clear=True):
            assert EnvironmentDetector.get_detected_ci_system() is None
    
    def test_is_output_redirected_not_tty(self):
        """Test output redirection detection when stdout is not TTY."""
        with patch('src.forklift.display.terminal_detector.TerminalDetector.is_stdout_tty', return_value=False):
            assert EnvironmentDetector.is_output_redirected() is True
    
    def test_is_output_redirected_env_var(self):
        """Test output redirection detection with environment variable."""
        with patch.dict(os.environ, {'FORKLIFT_OUTPUT_REDIRECTED': '1'}, clear=False):
            with patch('src.forklift.display.terminal_detector.TerminalDetector.is_stdout_tty', return_value=True):
                assert EnvironmentDetector.is_output_redirected() is True
    
    def test_is_output_redirected_false(self):
        """Test output redirection detection when not redirected."""
        with patch.dict(os.environ, {}, clear=True):
            with patch('src.forklift.display.terminal_detector.TerminalDetector.is_stdout_tty', return_value=True):
                assert EnvironmentDetector.is_output_redirected() is False
    
    def test_is_input_redirected_not_tty(self):
        """Test input redirection detection when stdin is not TTY."""
        with patch('src.forklift.display.terminal_detector.TerminalDetector.is_stdin_tty', return_value=False):
            assert EnvironmentDetector.is_input_redirected() is True
    
    def test_is_input_redirected_false(self):
        """Test input redirection detection when not redirected."""
        with patch('src.forklift.display.terminal_detector.TerminalDetector.is_stdin_tty', return_value=True):
            assert EnvironmentDetector.is_input_redirected() is False
    
    def test_get_shell_info(self):
        """Test shell information gathering."""
        env_vars = {
            'SHELL': '/bin/bash',
            'SHLVL': '2',
            'TERM': 'xterm-256color',
            'TERM_PROGRAM': 'iTerm.app',
            'SSH_CONNECTION': '192.168.1.100 22 192.168.1.1 54321',
            'DISPLAY': ':0',
        }
        
        with patch.dict(os.environ, env_vars, clear=False):
            info = EnvironmentDetector.get_shell_info()
            
            expected = {
                'shell': '/bin/bash',
                'shlvl': '2',
                'term': 'xterm-256color',
                'term_program': 'iTerm.app',
                'ssh_connection': '192.168.1.100 22 192.168.1.1 54321',
                'display': ':0',
            }
            
            assert info == expected
    
    def test_get_shell_info_minimal(self):
        """Test shell information gathering with minimal environment."""
        with patch.dict(os.environ, {}, clear=True):
            info = EnvironmentDetector.get_shell_info()
            
            expected = {
                'shell': None,
                'shlvl': None,
                'term': None,
                'term_program': None,
                'ssh_connection': None,
                'display': None,
            }
            
            assert info == expected
    
    def test_get_environment_info_comprehensive(self):
        """Test comprehensive environment information gathering."""
        env_vars = {
            'CI': 'true',
            'GITHUB_ACTIONS': 'true',
            'AUTOMATED': '1',
            'DOCKER_CONTAINER': '1',
            'SHELL': '/bin/zsh',
            'TERM': 'xterm-256color',
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            with patch.object(EnvironmentDetector, 'is_output_redirected', return_value=False), \
                 patch.object(EnvironmentDetector, 'is_input_redirected', return_value=False):
                
                info = EnvironmentDetector.get_environment_info()
                
                assert info['is_ci'] is True
                assert info['is_automation'] is True
                assert info['is_container'] is True
                assert info['ci_system'] == 'GitHub Actions'
                assert info['output_redirected'] is False
                assert info['input_redirected'] is False
                assert info['shell_info']['shell'] == '/bin/zsh'
                assert 'CI' in info['detected_vars']
                assert 'GITHUB_ACTIONS' in info['detected_vars']
    
    def test_get_environment_info_minimal(self):
        """Test environment information gathering with minimal environment."""
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(EnvironmentDetector, 'is_output_redirected', return_value=False), \
                 patch.object(EnvironmentDetector, 'is_input_redirected', return_value=False):
                
                info = EnvironmentDetector.get_environment_info()
                
                assert info['is_ci'] is False
                assert info['is_automation'] is False
                assert info['is_container'] is False
                assert info['ci_system'] is None
                assert info['output_redirected'] is False
                assert info['input_redirected'] is False
                assert info['shell_info']['shell'] is None
                assert info['detected_vars'] == {}


class TestEnvironmentDetectorEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_all_ci_systems_detected(self):
        """Test that all defined CI systems can be detected."""
        ci_systems = {
            'JENKINS_URL': 'Jenkins',
            'TRAVIS': 'Travis CI',
            'CIRCLECI': 'CircleCI',
            'APPVEYOR': 'AppVeyor',
            'GITLAB_CI': 'GitLab CI',
            'GITHUB_ACTIONS': 'GitHub Actions',
            'BUILDKITE': 'Buildkite',
            'DRONE': 'Drone',
            'TEAMCITY_VERSION': 'TeamCity',
            'TF_BUILD': 'Azure DevOps',
            'CODEBUILD_BUILD_ID': 'AWS CodeBuild',
            'BAMBOO_BUILD_NUMBER': 'Bamboo',
            'GO_PIPELINE_NAME': 'GoCD',
        }
        
        for env_var, expected_name in ci_systems.items():
            with patch.dict(os.environ, {env_var: 'test_value'}, clear=True):
                assert EnvironmentDetector.get_detected_ci_system() == expected_name
    
    def test_multiple_ci_vars_first_wins(self):
        """Test that when multiple CI variables are set, the first one wins."""
        with patch.dict(os.environ, {'JENKINS_URL': 'jenkins', 'TRAVIS': 'true'}, clear=True):
            # Jenkins should win because it's checked first in the implementation
            result = EnvironmentDetector.get_detected_ci_system()
            assert result == 'Jenkins'
    
    def test_container_detection_priority(self):
        """Test container detection priority (env vars before files)."""
        with patch.dict(os.environ, {'DOCKER_CONTAINER': '1'}, clear=True):
            with patch('os.path.exists', return_value=False):  # No files exist
                assert EnvironmentDetector.is_container_environment() is True
    
    def test_cgroup_file_read_exceptions(self):
        """Test various exceptions when reading cgroup file."""
        exceptions = [OSError("No such file"), IOError("Permission denied"), 
                     UnicodeDecodeError('utf-8', b'', 0, 1, 'invalid')]
        
        for exception in exceptions:
            with patch.dict(os.environ, {}, clear=True):
                with patch('os.path.exists') as mock_exists:
                    mock_exists.side_effect = lambda path: path == '/proc/1/cgroup'
                    with patch('builtins.open', side_effect=exception):
                        assert EnvironmentDetector.is_container_environment() is False
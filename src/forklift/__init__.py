"""
Forklift - GitHub repository fork analysis tool.

A tool that scans all forks of a repository, identifies valuable features,
ranks them by impact, and can automatically create pull requests.
"""

__version__ = "0.1.0"
__author__ = "Forklift Team"
__email__ = "team@forklift.dev"

from .config import ForkliftConfig, ScoringConfig, load_config
from .models import Commit, Feature, Fork, RankedFeature, Repository, User

__all__ = [
    "Commit",
    "Feature",
    "Fork",
    "ForkliftConfig",
    "RankedFeature",
    "Repository",
    "ScoringConfig",
    "User",
    "load_config",
]

"""
Forkscout - GitHub repository fork analysis tool.

A tool that scans all forks of a repository, identifies valuable features,
ranks them by impact, and can automatically create pull requests.
"""

__version__ = "1.0.5"
__author__ = "Roman Medvedev"
__email__ = "pypi@romavm.dev"

from .config import ForkscoutConfig, ScoringConfig, load_config
from .models import Commit, Feature, Fork, RankedFeature, Repository, User

__all__ = [
    "Commit",
    "Feature",
    "Fork",
    "ForkscoutConfig",
    "RankedFeature",
    "Repository",
    "ScoringConfig",
    "User",
    "load_config",
]

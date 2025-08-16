"""Concrete interactive step implementations for repository analysis."""

import logging
from typing import Any, Dict, List

from rich.table import Table
from rich.text import Text

from forklift.analysis.fork_discovery import ForkDiscoveryService
from forklift.analysis.interactive_step import InteractiveStep
from forklift.analysis.repository_analyzer import RepositoryAnalyzer
from forklift.github.client import GitHubClient
from forklift.models.analysis import ForkAnalysis
from forklift.models.github import Fork, Repository
from forklift.models.interactive import StepResult
from forklift.ranking.feature_ranking_engine import FeatureRankingEngine

logger = logging.getLogger(__name__)


class RepositoryDiscoveryStep(InteractiveStep):
    """Step for discovering and validating the target repository."""
    
    def __init__(self, github_client: GitHubClient):
        super().__init__(
            name="Repository Discovery",
            description="Fetch repository information and validate access"
        )
        self.github_client = github_client
    
    async def execute(self, context: Dict[str, Any]) -> StepResult:
        """Execute repository discovery."""
        try:
            repo_url = context.get("repo_url")
            if not repo_url:
                raise ValueError("Repository URL not provided in context")
            
            # Extract owner and repo name from URL
            if repo_url.startswith("https://github.com/"):
                parts = repo_url.replace("https://github.com/", "").split("/")
            elif "/" in repo_url:
                parts = repo_url.split("/")
            else:
                raise ValueError(f"Invalid repository URL format: {repo_url}")
            
            if len(parts) < 2:
                raise ValueError(f"Invalid repository URL format: {repo_url}")
            
            owner, repo_name = parts[0], parts[1]
            
            # Fetch repository data
            repository = await self.github_client.get_repository(f"{owner}/{repo_name}")
            
            # Store in context
            context["repository"] = repository
            context["owner"] = owner
            context["repo_name"] = repo_name
            
            metrics = {
                "repository_name": repository.full_name,
                "stars": repository.stars,
                "forks_count": repository.forks_count,
                "is_private": repository.is_private,
                "primary_language": repository.language or "Unknown"
            }
            
            return StepResult(
                step_name=self.name,
                success=True,
                data=repository,
                summary=f"Successfully discovered repository: {repository.full_name}",
                metrics=metrics
            )
            
        except Exception as e:
            logger.error(f"Repository discovery failed: {e}")
            return StepResult(
                step_name=self.name,
                success=False,
                data=None,
                summary=f"Failed to discover repository: {str(e)}",
                error=e
            )
    
    def display_results(self, results: StepResult) -> str:
        """Display repository discovery results."""
        if not results.success:
            return f"❌ Repository discovery failed: {results.summary}"
        
        repository = results.data
        if not repository:
            return "❌ No repository data available"
        
        display_text = f"""✅ **Repository Found**

**Name:** {repository.full_name}
**Description:** {repository.description or 'No description'}
**Language:** {repository.language or 'Unknown'}
**Stars:** {repository.stars:,}
**Forks:** {repository.forks_count:,}
**Private:** {'Yes' if repository.is_private else 'No'}
**Created:** {repository.created_at.strftime('%Y-%m-%d') if repository.created_at else 'Unknown'}
**Last Updated:** {repository.updated_at.strftime('%Y-%m-%d') if repository.updated_at else 'Unknown'}"""
        
        return display_text
    
    def get_confirmation_prompt(self, results: StepResult) -> str:
        """Get confirmation prompt for repository discovery."""
        if results.success:
            return f"Repository '{results.data.full_name}' discovered successfully. Proceed with fork discovery?"
        else:
            return "Repository discovery failed. Skip to next step anyway?"


class ForkDiscoveryStep(InteractiveStep):
    """Step for discovering all forks of the repository."""
    
    def __init__(self, github_client: GitHubClient, max_forks: int = 100):
        super().__init__(
            name="Fork Discovery",
            description="Discover all public forks of the repository"
        )
        self.github_client = github_client
        self.max_forks = max_forks
    
    async def execute(self, context: Dict[str, Any]) -> StepResult:
        """Execute fork discovery."""
        try:
            repository = context.get("repository")
            if not repository:
                raise ValueError("Repository not found in context")
            
            # Initialize fork discovery service
            fork_discovery = ForkDiscoveryService(
                github_client=self.github_client,
                max_forks_to_analyze=self.max_forks
            )
            
            # Discover forks
            forks = await fork_discovery.discover_forks(repository.url)
            
            # Store in context
            context["all_forks"] = forks
            context["total_forks"] = len(forks)
            
            # Calculate metrics
            active_forks = [f for f in forks if f.is_active]
            forks_with_commits = [f for f in forks if f.commits_ahead > 0]
            
            metrics = {
                "total_forks": len(forks),
                "active_forks": len(active_forks),
                "forks_with_commits_ahead": len(forks_with_commits),
                "max_commits_ahead": max((f.commits_ahead for f in forks), default=0),
                "avg_commits_ahead": sum(f.commits_ahead for f in forks) / len(forks) if forks else 0
            }
            
            return StepResult(
                step_name=self.name,
                success=True,
                data=forks,
                summary=f"Discovered {len(forks)} forks ({len(active_forks)} active, {len(forks_with_commits)} with commits ahead)",
                metrics=metrics
            )
            
        except Exception as e:
            logger.error(f"Fork discovery failed: {e}")
            return StepResult(
                step_name=self.name,
                success=False,
                data=None,
                summary=f"Failed to discover forks: {str(e)}",
                error=e
            )
    
    def display_results(self, results: StepResult) -> str:
        """Display fork discovery results."""
        if not results.success:
            return f"❌ Fork discovery failed: {results.summary}"
        
        forks = results.data or []
        metrics = results.metrics or {}
        
        if not forks:
            return "📭 **No Forks Found**\n\nThis repository has no public forks to analyze."
        
        # Create summary table
        table_text = f"""✅ **Fork Discovery Complete**

**Summary:**
- Total Forks: {metrics.get('total_forks', 0):,}
- Active Forks: {metrics.get('active_forks', 0):,}
- Forks with Commits Ahead: {metrics.get('forks_with_commits_ahead', 0):,}
- Max Commits Ahead: {metrics.get('max_commits_ahead', 0):,}
- Average Commits Ahead: {metrics.get('avg_commits_ahead', 0):.1f}

**Top 5 Most Active Forks:**"""
        
        # Sort forks by commits ahead and show top 5
        sorted_forks = sorted(forks, key=lambda f: f.commits_ahead, reverse=True)[:5]
        for i, fork in enumerate(sorted_forks, 1):
            table_text += f"\n{i}. {fork.repository.full_name} ({fork.commits_ahead} commits ahead, {fork.repository.stars} stars)"
        
        return table_text
    
    def get_confirmation_prompt(self, results: StepResult) -> str:
        """Get confirmation prompt for fork discovery."""
        if results.success:
            forks = results.data or []
            if forks:
                return f"Found {len(forks)} forks. Proceed with fork filtering and analysis?"
            else:
                return "No forks found. Skip to final report generation?"
        else:
            return "Fork discovery failed. Skip to next step anyway?"


class ForkFilteringStep(InteractiveStep):
    """Step for filtering forks to identify promising candidates."""
    
    def __init__(self, min_commits_ahead: int = 1, min_stars: int = 0):
        super().__init__(
            name="Fork Filtering",
            description="Filter forks to identify promising candidates for analysis"
        )
        self.min_commits_ahead = min_commits_ahead
        self.min_stars = min_stars
    
    async def execute(self, context: Dict[str, Any]) -> StepResult:
        """Execute fork filtering."""
        try:
            all_forks = context.get("all_forks", [])
            if not all_forks:
                return StepResult(
                    step_name=self.name,
                    success=True,
                    data=[],
                    summary="No forks to filter",
                    metrics={"filtered_forks": 0, "total_forks": 0}
                )
            
            # Apply filters
            filtered_forks = []
            for fork in all_forks:
                if (fork.commits_ahead >= self.min_commits_ahead and 
                    fork.repository.stars >= self.min_stars and
                    fork.is_active):
                    filtered_forks.append(fork)
            
            # Store in context
            context["filtered_forks"] = filtered_forks
            
            # Calculate metrics
            metrics = {
                "total_forks": len(all_forks),
                "filtered_forks": len(filtered_forks),
                "filter_ratio": len(filtered_forks) / len(all_forks) if all_forks else 0,
                "avg_stars_filtered": sum(f.repository.stars for f in filtered_forks) / len(filtered_forks) if filtered_forks else 0,
                "avg_commits_ahead_filtered": sum(f.commits_ahead for f in filtered_forks) / len(filtered_forks) if filtered_forks else 0
            }
            
            return StepResult(
                step_name=self.name,
                success=True,
                data=filtered_forks,
                summary=f"Filtered {len(all_forks)} forks down to {len(filtered_forks)} promising candidates",
                metrics=metrics
            )
            
        except Exception as e:
            logger.error(f"Fork filtering failed: {e}")
            return StepResult(
                step_name=self.name,
                success=False,
                data=None,
                summary=f"Failed to filter forks: {str(e)}",
                error=e
            )
    
    def display_results(self, results: StepResult) -> str:
        """Display fork filtering results."""
        if not results.success:
            return f"❌ Fork filtering failed: {results.summary}"
        
        filtered_forks = results.data or []
        metrics = results.metrics or {}
        
        display_text = f"""🔍 **Fork Filtering Complete**

**Filtering Criteria:**
- Minimum commits ahead: {self.min_commits_ahead}
- Minimum stars: {self.min_stars}
- Must be active

**Results:**
- Original forks: {metrics.get('total_forks', 0):,}
- Filtered forks: {metrics.get('filtered_forks', 0):,}
- Filter ratio: {metrics.get('filter_ratio', 0):.1%}"""
        
        if filtered_forks:
            display_text += f"""
- Average stars (filtered): {metrics.get('avg_stars_filtered', 0):.1f}
- Average commits ahead (filtered): {metrics.get('avg_commits_ahead_filtered', 0):.1f}

**Selected Forks for Analysis:**"""
            
            for i, fork in enumerate(filtered_forks[:10], 1):  # Show top 10
                display_text += f"\n{i}. {fork.repository.full_name} ({fork.commits_ahead} commits, {fork.repository.stars} stars)"
            
            if len(filtered_forks) > 10:
                display_text += f"\n... and {len(filtered_forks) - 10} more"
        else:
            display_text += "\n\n⚠️ No forks passed the filtering criteria."
        
        return display_text
    
    def get_confirmation_prompt(self, results: StepResult) -> str:
        """Get confirmation prompt for fork filtering."""
        if results.success:
            filtered_forks = results.data or []
            if filtered_forks:
                return f"Selected {len(filtered_forks)} forks for detailed analysis. Proceed with fork analysis?"
            else:
                return "No forks passed filtering. Skip to final report generation?"
        else:
            return "Fork filtering failed. Skip to next step anyway?"


class ForkAnalysisStep(InteractiveStep):
    """Step for analyzing individual forks to extract features."""
    
    def __init__(self, github_client: GitHubClient, explanation_engine=None):
        super().__init__(
            name="Fork Analysis",
            description="Analyze individual forks to extract features and changes"
        )
        self.github_client = github_client
        self.explanation_engine = explanation_engine
    
    async def execute(self, context: Dict[str, Any]) -> StepResult:
        """Execute fork analysis."""
        try:
            filtered_forks = context.get("filtered_forks", [])
            repository = context.get("repository")
            
            if not repository:
                raise ValueError("Repository not found in context")
            
            if not filtered_forks:
                return StepResult(
                    step_name=self.name,
                    success=True,
                    data=[],
                    summary="No forks to analyze",
                    metrics={"analyzed_forks": 0, "total_features": 0}
                )
            
            # Initialize repository analyzer
            analyzer = RepositoryAnalyzer(
                github_client=self.github_client,
                explanation_engine=self.explanation_engine
            )
            
            # Analyze each fork
            fork_analyses = []
            total_features = 0
            successful_analyses = 0
            
            for fork in filtered_forks:
                try:
                    analysis = await analyzer.analyze_fork(
                        fork, 
                        repository, 
                        explain=self.explanation_engine is not None
                    )
                    fork_analyses.append(analysis)
                    total_features += len(analysis.features)
                    successful_analyses += 1
                    
                except Exception as e:
                    logger.warning(f"Failed to analyze fork {fork.repository.full_name}: {e}")
                    # Continue with other forks
                    continue
            
            # Store in context
            context["fork_analyses"] = fork_analyses
            context["total_features"] = total_features
            
            # Calculate metrics
            metrics = {
                "total_forks_to_analyze": len(filtered_forks),
                "successfully_analyzed": successful_analyses,
                "failed_analyses": len(filtered_forks) - successful_analyses,
                "total_features": total_features,
                "avg_features_per_fork": total_features / successful_analyses if successful_analyses > 0 else 0,
                "analysis_success_rate": successful_analyses / len(filtered_forks) if filtered_forks else 0
            }
            
            return StepResult(
                step_name=self.name,
                success=True,
                data=fork_analyses,
                summary=f"Analyzed {successful_analyses}/{len(filtered_forks)} forks, found {total_features} features",
                metrics=metrics
            )
            
        except Exception as e:
            logger.error(f"Fork analysis failed: {e}")
            return StepResult(
                step_name=self.name,
                success=False,
                data=None,
                summary=f"Failed to analyze forks: {str(e)}",
                error=e
            )
    
    def display_results(self, results: StepResult) -> str:
        """Display fork analysis results."""
        if not results.success:
            return f"❌ Fork analysis failed: {results.summary}"
        
        fork_analyses = results.data or []
        metrics = results.metrics or {}
        
        display_text = f"""🔬 **Fork Analysis Complete**

**Analysis Summary:**
- Forks to analyze: {metrics.get('total_forks_to_analyze', 0)}
- Successfully analyzed: {metrics.get('successfully_analyzed', 0)}
- Failed analyses: {metrics.get('failed_analyses', 0)}
- Success rate: {metrics.get('analysis_success_rate', 0):.1%}
- Total features found: {metrics.get('total_features', 0)}
- Average features per fork: {metrics.get('avg_features_per_fork', 0):.1f}"""
        
        if fork_analyses:
            display_text += "\n\n**Top Analyzed Forks:**"
            
            # Sort by number of features found
            sorted_analyses = sorted(fork_analyses, key=lambda a: len(a.features), reverse=True)
            
            for i, analysis in enumerate(sorted_analyses[:5], 1):
                fork_name = analysis.fork.repository.full_name
                feature_count = len(analysis.features)
                display_text += f"\n{i}. {fork_name} ({feature_count} features)"
        
        return display_text
    
    def get_confirmation_prompt(self, results: StepResult) -> str:
        """Get confirmation prompt for fork analysis."""
        if results.success:
            metrics = results.metrics or {}
            total_features = metrics.get('total_features', 0)
            if total_features > 0:
                return f"Analysis complete! Found {total_features} features across all forks. Proceed with feature ranking?"
            else:
                return "Analysis complete but no features found. Skip to final report generation?"
        else:
            return "Fork analysis failed. Skip to next step anyway?"


class FeatureRankingStep(InteractiveStep):
    """Step for ranking discovered features by value and impact."""
    
    def __init__(self):
        super().__init__(
            name="Feature Ranking",
            description="Rank discovered features by value and impact"
        )
    
    async def execute(self, context: Dict[str, Any]) -> StepResult:
        """Execute feature ranking."""
        try:
            fork_analyses = context.get("fork_analyses", [])
            
            if not fork_analyses:
                return StepResult(
                    step_name=self.name,
                    success=True,
                    data=[],
                    summary="No features to rank",
                    metrics={"ranked_features": 0}
                )
            
            # Collect all features from all analyses
            all_features = []
            for analysis in fork_analyses:
                all_features.extend(analysis.features)
            
            if not all_features:
                return StepResult(
                    step_name=self.name,
                    success=True,
                    data=[],
                    summary="No features found to rank",
                    metrics={"ranked_features": 0}
                )
            
            # Initialize ranking engine
            ranking_engine = FeatureRankingEngine()
            
            # Rank features
            ranked_features = ranking_engine.rank_features(all_features)
            
            # Store in context
            context["ranked_features"] = ranked_features
            context["final_result"] = {
                "fork_analyses": fork_analyses,
                "ranked_features": ranked_features,
                "total_features": len(all_features)
            }
            
            # Calculate metrics
            high_value_features = [f for f in ranked_features if f.score >= 80]
            medium_value_features = [f for f in ranked_features if 60 <= f.score < 80]
            
            metrics = {
                "total_features": len(all_features),
                "ranked_features": len(ranked_features),
                "high_value_features": len(high_value_features),
                "medium_value_features": len(medium_value_features),
                "avg_score": sum(f.score for f in ranked_features) / len(ranked_features) if ranked_features else 0,
                "top_score": max((f.score for f in ranked_features), default=0)
            }
            
            return StepResult(
                step_name=self.name,
                success=True,
                data=ranked_features,
                summary=f"Ranked {len(ranked_features)} features ({len(high_value_features)} high-value)",
                metrics=metrics
            )
            
        except Exception as e:
            logger.error(f"Feature ranking failed: {e}")
            return StepResult(
                step_name=self.name,
                success=False,
                data=None,
                summary=f"Failed to rank features: {str(e)}",
                error=e
            )
    
    def display_results(self, results: StepResult) -> str:
        """Display feature ranking results."""
        if not results.success:
            return f"❌ Feature ranking failed: {results.summary}"
        
        ranked_features = results.data or []
        metrics = results.metrics or {}
        
        if not ranked_features:
            return "📊 **Feature Ranking Complete**\n\nNo features were found to rank."
        
        display_text = f"""📊 **Feature Ranking Complete**

**Ranking Summary:**
- Total features: {metrics.get('total_features', 0)}
- High-value features (≥80): {metrics.get('high_value_features', 0)}
- Medium-value features (60-79): {metrics.get('medium_value_features', 0)}
- Average score: {metrics.get('avg_score', 0):.1f}
- Top score: {metrics.get('top_score', 0):.1f}

**Top 5 Features:**"""
        
        for i, feature in enumerate(ranked_features[:5], 1):
            display_text += f"\n{i}. {feature.feature.title} (Score: {feature.score:.1f})"
            display_text += f"\n   From: {feature.feature.source_fork.repository.full_name}"
            display_text += f"\n   Category: {feature.feature.category.value}"
        
        return display_text
    
    def get_confirmation_prompt(self, results: StepResult) -> str:
        """Get confirmation prompt for feature ranking."""
        if results.success:
            ranked_features = results.data or []
            if ranked_features:
                high_value = sum(1 for f in ranked_features if f.score >= 80)
                return f"Ranking complete! Found {high_value} high-value features. Generate final report?"
            else:
                return "Ranking complete but no features found. Generate final report anyway?"
        else:
            return "Feature ranking failed. Generate final report anyway?"
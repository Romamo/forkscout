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
            repository = await self.github_client.get_repository(owner, repo_name)
            
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
            forks = await fork_discovery.discover_forks(repository.html_url)
            
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
        
        # Create detailed summary with filtering criteria preview
        table_text = f"""✅ **Fork Discovery Complete**

**Discovery Summary:**
- Total Forks Found: {metrics.get('total_forks', 0):,}
- Active Forks: {metrics.get('active_forks', 0):,}
- Forks with Commits Ahead: {metrics.get('forks_with_commits_ahead', 0):,}
- Max Commits Ahead: {metrics.get('max_commits_ahead', 0):,}
- Average Commits Ahead: {metrics.get('avg_commits_ahead', 0):.1f}

**Fork Activity Breakdown:**"""
        
        # Categorize forks by activity level
        high_activity = [f for f in forks if f.commits_ahead >= 10]
        medium_activity = [f for f in forks if 3 <= f.commits_ahead < 10]
        low_activity = [f for f in forks if 1 <= f.commits_ahead < 3]
        no_activity = [f for f in forks if f.commits_ahead == 0]
        
        table_text += f"""
- High Activity (≥10 commits): {len(high_activity)} forks
- Medium Activity (3-9 commits): {len(medium_activity)} forks  
- Low Activity (1-2 commits): {len(low_activity)} forks
- No New Commits: {len(no_activity)} forks

**Top 5 Most Active Forks:**"""
        
        # Sort forks by commits ahead and show top 5
        sorted_forks = sorted(forks, key=lambda f: f.commits_ahead, reverse=True)[:5]
        for i, fork in enumerate(sorted_forks, 1):
            activity_level = "🔥" if fork.commits_ahead >= 10 else "⚡" if fork.commits_ahead >= 3 else "💫"
            table_text += f"\n{i}. {activity_level} {fork.repository.full_name}"
            table_text += f"\n   📊 {fork.commits_ahead} commits ahead, ⭐ {fork.repository.stars} stars"
            if fork.last_activity:
                table_text += f", 🕒 Last active: {fork.last_activity.strftime('%Y-%m-%d')}"
        
        return table_text
    
    def get_confirmation_prompt(self, results: StepResult) -> str:
        """Get confirmation prompt for fork discovery."""
        if results.success:
            forks = results.data or []
            metrics = results.metrics or {}
            if forks:
                active_forks = metrics.get('active_forks', 0)
                forks_with_commits = metrics.get('forks_with_commits_ahead', 0)
                return f"Found {len(forks)} forks ({active_forks} active, {forks_with_commits} with new commits). Continue to filtering stage?"
            else:
                return "No forks found for this repository. Skip to final report generation?"
        else:
            return "Fork discovery encountered errors. Continue with available data or abort analysis?"


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

**Applied Filtering Criteria:**
- ✅ Minimum commits ahead: {self.min_commits_ahead}
- ✅ Minimum stars: {self.min_stars}
- ✅ Must be active (not archived/disabled)

**Filtering Results:**
- 📊 Original forks discovered: {metrics.get('total_forks', 0):,}
- 🎯 Forks passing filters: {metrics.get('filtered_forks', 0):,}
- 📈 Selection ratio: {metrics.get('filter_ratio', 0):.1%}"""
        
        if filtered_forks:
            display_text += f"""
- ⭐ Average stars (selected): {metrics.get('avg_stars_filtered', 0):.1f}
- Average commits ahead (selected): {metrics.get('avg_commits_ahead_filtered', 0):.1f}

**🎯 Selected Forks for Detailed Analysis:**"""
            
            # Group forks by activity level for better display
            high_value = [f for f in filtered_forks if f.repository.stars >= 10 or f.commits_ahead >= 10]
            medium_value = [f for f in filtered_forks if f not in high_value and (f.repository.stars >= 5 or f.commits_ahead >= 5)]
            other_forks = [f for f in filtered_forks if f not in high_value and f not in medium_value]
            
            if high_value:
                display_text += f"\n\n🔥 **High-Value Forks ({len(high_value)}):**"
                for i, fork in enumerate(high_value[:5], 1):
                    display_text += f"\n{i}. {fork.repository.full_name}"
                    display_text += f"\n   📊 {fork.commits_ahead} commits ahead, ⭐ {fork.repository.stars} stars"
                if len(high_value) > 5:
                    display_text += f"\n   ... and {len(high_value) - 5} more high-value forks"
            
            if medium_value:
                display_text += f"\n\n⚡ **Medium-Value Forks ({len(medium_value)}):**"
                for i, fork in enumerate(medium_value[:3], 1):
                    display_text += f"\n{i}. {fork.repository.full_name} ({fork.commits_ahead} commits, {fork.repository.stars} stars)"
                if len(medium_value) > 3:
                    display_text += f"\n   ... and {len(medium_value) - 3} more medium-value forks"
            
            if other_forks:
                display_text += f"\n\n💫 **Other Selected Forks:** {len(other_forks)} additional forks"
                
        else:
            display_text += f"""

⚠️  **No Forks Passed Filtering**

**Suggestions:**
- Consider lowering the minimum commits ahead (currently {self.min_commits_ahead})
- Consider lowering the minimum stars requirement (currently {self.min_stars})
- Check if the repository has any active forks with meaningful contributions"""
        
        return display_text
    
    def get_confirmation_prompt(self, results: StepResult) -> str:
        """Get confirmation prompt for fork filtering."""
        if results.success:
            filtered_forks = results.data or []
            metrics = results.metrics or {}
            if filtered_forks:
                high_value = len([f for f in filtered_forks if f.repository.stars >= 10 or f.commits_ahead >= 10])
                if high_value > 0:
                    return f"Selected {len(filtered_forks)} forks for analysis ({high_value} high-value). This may take several minutes. Continue?"
                else:
                    return f"Selected {len(filtered_forks)} forks for analysis. Proceed with detailed feature extraction?"
            else:
                return "No forks passed the filtering criteria. Would you like to generate a summary report anyway?"
        else:
            return "Fork filtering encountered issues. Continue with partial results or abort the analysis?"


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

**Analysis Performance:**
- 🎯 Forks targeted for analysis: {metrics.get('total_forks_to_analyze', 0)}
- ✅ Successfully analyzed: {metrics.get('successfully_analyzed', 0)}
- ❌ Failed analyses: {metrics.get('failed_analyses', 0)}
- 📊 Success rate: {metrics.get('analysis_success_rate', 0):.1%}

**Feature Discovery Results:**
- 🔍 Total features discovered: {metrics.get('total_features', 0)}
- 📈 Average features per fork: {metrics.get('avg_features_per_fork', 0):.1f}"""
        
        if fork_analyses:
            # Categorize analyses by feature count
            rich_forks = [a for a in fork_analyses if len(a.features) >= 5]
            moderate_forks = [a for a in fork_analyses if 2 <= len(a.features) < 5]
            sparse_forks = [a for a in fork_analyses if 1 <= len(a.features) < 2]
            empty_forks = [a for a in fork_analyses if len(a.features) == 0]
            
            display_text += f"""

**Feature Distribution:**
- 🔥 Feature-rich forks (≥5 features): {len(rich_forks)}
- ⚡ Moderate forks (2-4 features): {len(moderate_forks)}
- 💫 Sparse forks (1 feature): {len(sparse_forks)}
- 📭 Empty forks (0 features): {len(empty_forks)}"""
            
            if rich_forks:
                display_text += f"\n\n🔥 **Top Feature-Rich Forks:**"
                sorted_rich = sorted(rich_forks, key=lambda a: len(a.features), reverse=True)
                for i, analysis in enumerate(sorted_rich[:5], 1):
                    fork_name = analysis.fork.repository.full_name
                    feature_count = len(analysis.features)
                    stars = analysis.fork.repository.stars
                    display_text += f"\n{i}. {fork_name}"
                    display_text += f"\n   🎯 {feature_count} features discovered, ⭐ {stars} stars"
                    
                    # Show feature categories if available
                    if analysis.features:
                        categories = {}
                        for feature in analysis.features:
                            cat = feature.category.value
                            categories[cat] = categories.get(cat, 0) + 1
                        
                        cat_summary = ", ".join([f"{count} {cat}" for cat, count in categories.items()])
                        display_text += f"\n   📋 Categories: {cat_summary}"
            
            if moderate_forks and not rich_forks:
                display_text += f"\n\n⚡ **Moderate Forks with Features:**"
                for i, analysis in enumerate(moderate_forks[:3], 1):
                    fork_name = analysis.fork.repository.full_name
                    feature_count = len(analysis.features)
                    display_text += f"\n{i}. {fork_name} ({feature_count} features)"
        else:
            display_text += "\n\n📭 No fork analyses were completed successfully."
        
        return display_text
    
    def get_confirmation_prompt(self, results: StepResult) -> str:
        """Get confirmation prompt for fork analysis."""
        if results.success:
            metrics = results.metrics or {}
            total_features = metrics.get('total_features', 0)
            successful_analyses = metrics.get('successfully_analyzed', 0)
            
            if total_features > 0:
                if total_features >= 20:
                    return f"Excellent! Discovered {total_features} features from {successful_analyses} forks. Ready to rank and prioritize these features?"
                elif total_features >= 10:
                    return f"Good results! Found {total_features} features from {successful_analyses} forks. Continue to feature ranking and scoring?"
                else:
                    return f"Found {total_features} features from {successful_analyses} forks. Proceed with ranking to identify the most valuable ones?"
            else:
                if successful_analyses > 0:
                    return f"Analysis completed for {successful_analyses} forks but no distinct features were identified. Generate summary report anyway?"
                else:
                    return "No forks were successfully analyzed. Would you like to see a diagnostic report of what went wrong?"
        else:
            return "Fork analysis encountered significant errors. Continue with partial results or abort to investigate issues?"


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
            
            # Initialize ranking engine with default scoring config
            from forklift.config.settings import ScoringConfig
            scoring_config = ScoringConfig()
            ranking_engine = FeatureRankingEngine(scoring_config)
            
            # Create fork metrics map from fork analyses
            fork_metrics_map = {}
            for analysis in fork_analyses:
                fork_url = analysis.fork.repository.url
                # Create basic fork metrics from available data
                from forklift.models.analysis import ForkMetrics
                fork_metrics = ForkMetrics(
                    stars=analysis.fork.repository.stars,
                    forks=analysis.fork.repository.forks_count,
                    contributors=1,  # Default value, could be enhanced later
                    last_activity=analysis.fork.last_activity,
                    commit_frequency=len(analysis.features) / max(1, analysis.fork.commits_ahead)  # Rough estimate
                )
                fork_metrics_map[fork_url] = fork_metrics
            
            # Rank features
            ranked_features = ranking_engine.rank_features(all_features, fork_metrics_map)
            
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
        
        # Categorize features by score ranges
        excellent_features = [f for f in ranked_features if f.score >= 90]
        high_value_features = [f for f in ranked_features if 80 <= f.score < 90]
        good_features = [f for f in ranked_features if 70 <= f.score < 80]
        medium_features = [f for f in ranked_features if 60 <= f.score < 70]
        low_features = [f for f in ranked_features if f.score < 60]
        
        display_text = f"""📊 **Feature Ranking Complete**

**Quality Distribution:**
- 🏆 Excellent features (≥90): {len(excellent_features)}
- 🔥 High-value features (80-89): {len(high_value_features)}
- ✅ Good features (70-79): {len(good_features)}
- ⚡ Medium features (60-69): {len(medium_features)}
- 💫 Lower-scored features (<60): {len(low_features)}

**Overall Statistics:**
- 📊 Total features ranked: {metrics.get('total_features', 0)}
- 📈 Average score: {metrics.get('avg_score', 0):.1f}/100
- 🎯 Highest score achieved: {metrics.get('top_score', 0):.1f}/100"""
        
        # Show top features with detailed information
        if excellent_features or high_value_features:
            top_features = excellent_features + high_value_features
            display_text += f"\n\n🏆 **Top-Tier Features (Score ≥80):**"
            
            for i, feature in enumerate(top_features[:5], 1):
                score_emoji = "🏆" if feature.score >= 90 else "🔥"
                display_text += f"\n{i}. {score_emoji} **{feature.feature.title}**"
                display_text += f"\n   📊 Score: {feature.score:.1f}/100"
                display_text += f"\n   🏠 Source: {feature.feature.source_fork.repository.full_name}"
                display_text += f"\n   🏷️  Category: {feature.feature.category.value.replace('_', ' ').title()}"
                
                # Show key ranking factors if available
                if hasattr(feature, 'ranking_factors') and feature.ranking_factors:
                    top_factors = sorted(feature.ranking_factors.items(), key=lambda x: x[1], reverse=True)[:2]
                    factors_text = ", ".join([f"{factor}: {value:.1f}" for factor, value in top_factors])
                    display_text += f"\n   ⚖️  Key factors: {factors_text}"
                
                display_text += ""  # Empty line for spacing
            
            if len(top_features) > 5:
                display_text += f"\n   ... and {len(top_features) - 5} more top-tier features"
        
        elif good_features:
            display_text += f"\n\n✅ **Best Available Features (Score 70-79):**"
            for i, feature in enumerate(good_features[:3], 1):
                display_text += f"\n{i}. {feature.feature.title} (Score: {feature.score:.1f})"
                display_text += f"\n   From: {feature.feature.source_fork.repository.full_name}"
                display_text += f"\n   Category: {feature.feature.category.value.replace('_', ' ').title()}"
        
        elif medium_features:
            display_text += f"\n\n⚡ **Available Features (Score 60-69):**"
            for i, feature in enumerate(medium_features[:3], 1):
                display_text += f"\n{i}. {feature.feature.title} (Score: {feature.score:.1f})"
                display_text += f"\n   From: {feature.feature.source_fork.repository.full_name}"
        
        # Add recommendation based on results
        if excellent_features:
            display_text += f"\n\n💡 **Recommendation:** You have {len(excellent_features)} excellent features that are highly recommended for integration!"
        elif high_value_features:
            display_text += f"\n\n💡 **Recommendation:** {len(high_value_features)} high-value features identified - these are strong candidates for your project."
        elif good_features:
            display_text += f"\n\n💡 **Recommendation:** {len(good_features)} good features found - consider reviewing these for potential value."
        else:
            display_text += f"\n\n💡 **Recommendation:** Consider reviewing the analysis criteria or exploring different forks for higher-value features."
        
        return display_text
    
    def get_confirmation_prompt(self, results: StepResult) -> str:
        """Get confirmation prompt for feature ranking."""
        if results.success:
            ranked_features = results.data or []
            if ranked_features:
                excellent_features = sum(1 for f in ranked_features if f.score >= 90)
                high_value_features = sum(1 for f in ranked_features if 80 <= f.score < 90)
                
                if excellent_features > 0:
                    return f"🎉 Outstanding results! Found {excellent_features} excellent features (≥90 score) and {high_value_features} high-value features. Ready to generate your comprehensive analysis report?"
                elif high_value_features > 0:
                    return f"Great results! Identified {high_value_features} high-value features (≥80 score). Generate detailed report with recommendations?"
                else:
                    good_features = sum(1 for f in ranked_features if f.score >= 70)
                    if good_features > 0:
                        return f"Found {good_features} good features (≥70 score) from the analysis. Create summary report with findings?"
                    else:
                        return f"Ranking completed for {len(ranked_features)} features. Generate report to review all findings and recommendations?"
            else:
                return "Feature ranking completed but no features were identified. Would you like a diagnostic report explaining the analysis results?"
        else:
            return "Feature ranking encountered errors. Generate a partial report with available data, or abort to investigate the issues?"
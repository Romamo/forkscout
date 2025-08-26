"""Report generation for fork analysis results."""

import logging
from datetime import datetime

from forklift.models.analysis import (
    Feature,
    FeatureCategory,
    ForkAnalysis,
    RankedFeature,
)
from forklift.models.github import Repository

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Generates human-readable markdown reports from fork analysis results."""

    def __init__(self, include_code_snippets: bool = True, max_features: int = 20):
        """Initialize the report generator.

        Args:
            include_code_snippets: Whether to include code snippets in reports
            max_features: Maximum number of features to include in the report
        """
        self.include_code_snippets = include_code_snippets
        self.max_features = max_features

    def generate_analysis_report(
        self,
        repository: Repository,
        fork_analyses: list[ForkAnalysis],
        ranked_features: list[RankedFeature],
        analysis_metadata: dict[str, str] | None = None,
    ) -> str:
        """Generate a comprehensive analysis report.

        Args:
            repository: The main repository that was analyzed
            fork_analyses: List of fork analysis results
            ranked_features: List of ranked features found across forks
            analysis_metadata: Optional metadata about the analysis process

        Returns:
            Markdown-formatted report string
        """
        logger.info(f"Generating analysis report for {repository.full_name}")

        report_sections = []

        # Header and overview
        report_sections.append(self._generate_header(repository))
        report_sections.append(
            self._generate_overview(repository, fork_analyses, ranked_features)
        )

        # Executive summary
        report_sections.append(self._generate_executive_summary(ranked_features))

        # Top features by category
        report_sections.append(self._generate_features_by_category(ranked_features))

        # Detailed feature analysis
        report_sections.append(
            self._generate_detailed_features(ranked_features[: self.max_features])
        )

        # Fork statistics and metadata
        report_sections.append(self._generate_fork_statistics(fork_analyses))

        # Analysis metadata
        if analysis_metadata:
            report_sections.append(self._generate_analysis_metadata(analysis_metadata))

        # Footer
        report_sections.append(self._generate_footer())

        return "\n\n".join(report_sections)

    def _generate_header(self, repository: Repository) -> str:
        """Generate the report header."""
        return f"""# Fork Analysis Report: {repository.full_name}

**Repository:** [{repository.full_name}]({repository.html_url})
**Analysis Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}
**Primary Language:** {repository.language or 'Not specified'}
**Stars:** {repository.stars:,} | **Forks:** {repository.forks_count:,}"""

    def _generate_overview(
        self,
        repository: Repository,
        fork_analyses: list[ForkAnalysis],
        ranked_features: list[RankedFeature],
    ) -> str:
        """Generate the overview section."""
        total_forks = len(fork_analyses)
        forks_with_features = len([fa for fa in fork_analyses if fa.features])
        total_features = len(ranked_features)
        high_value_features = len([rf for rf in ranked_features if rf.score >= 80])

        return f"""## Overview

This report analyzes **{total_forks}** forks of [{repository.full_name}]({repository.html_url}) to identify valuable features and improvements that could benefit the main repository.

### Key Findings

- **{total_features}** unique features discovered across all forks
- **{forks_with_features}** forks contain potentially valuable contributions
- **{high_value_features}** features scored 80+ points (high value)
- **{len([rf for rf in ranked_features if rf.score >= 90])}** features scored 90+ points (excellent)"""

    def _generate_executive_summary(self, ranked_features: list[RankedFeature]) -> str:
        """Generate executive summary of top features."""
        if not ranked_features:
            return """## Executive Summary

No significant features were identified in the analyzed forks."""

        top_5 = ranked_features[:5]

        summary = """## Executive Summary

The following are the most valuable features identified across all forks:

"""

        for i, feature in enumerate(top_5, 1):
            category_emoji = self._get_category_emoji(feature.feature.category)
            summary += f"{i}. **{feature.feature.title}** {category_emoji} (Score: {feature.score:.1f})\n"
            summary += f"   - {feature.feature.description}\n"
            summary += f"   - Source: [{feature.feature.source_fork.repository.full_name}]({feature.feature.source_fork.repository.html_url})\n\n"

        return summary.rstrip()

    def _generate_features_by_category(
        self, ranked_features: list[RankedFeature]
    ) -> str:
        """Generate features organized by category."""
        if not ranked_features:
            return ""

        # Group features by category
        categories: dict[FeatureCategory, list[RankedFeature]] = {}
        for feature in ranked_features:
            category = feature.feature.category
            if category not in categories:
                categories[category] = []
            categories[category].append(feature)

        section = "## Features by Category\n\n"

        # Sort categories by total score
        sorted_categories = sorted(
            categories.items(), key=lambda x: sum(f.score for f in x[1]), reverse=True
        )

        for category, features in sorted_categories:
            category_emoji = self._get_category_emoji(category)
            avg_score = sum(f.score for f in features) / len(features)

            section += f"### {category_emoji} {category.value.replace('_', ' ').title()} ({len(features)} features, avg score: {avg_score:.1f})\n\n"

            # Show top 3 features in each category
            for feature in features[:3]:
                section += (
                    f"- **{feature.feature.title}** (Score: {feature.score:.1f})\n"
                )
                section += f"  - {feature.feature.description}\n"
                section += f"  - Fork: [{feature.feature.source_fork.repository.full_name}]({feature.feature.source_fork.repository.html_url})\n\n"

            if len(features) > 3:
                section += (
                    f"  *...and {len(features) - 3} more features in this category*\n\n"
                )

        return section

    def _generate_detailed_features(self, top_features: list[RankedFeature]) -> str:
        """Generate detailed analysis of top features."""
        if not top_features:
            return ""

        section = f"## Top {len(top_features)} Features (Detailed Analysis)\n\n"

        for i, ranked_feature in enumerate(top_features, 1):
            feature = ranked_feature.feature
            section += f"### {i}. {feature.title}\n\n"

            # Basic info
            category_emoji = self._get_category_emoji(feature.category)
            section += f"**Category:** {category_emoji} {feature.category.value.replace('_', ' ').title()}  \n"
            section += f"**Score:** {ranked_feature.score:.1f}/100  \n"
            section += f"**Source Fork:** [{feature.source_fork.repository.full_name}]({feature.source_fork.repository.html_url})  \n"
            section += f"**Fork Author:** [{feature.source_fork.owner.login}]({feature.source_fork.owner.html_url})  \n"
            section += f"**Fork Stars:** {feature.source_fork.repository.stars}  \n"
            section += f"**Last Activity:** {feature.source_fork.last_activity.strftime('%Y-%m-%d') if feature.source_fork.last_activity else 'Unknown'}  \n\n"

            # Description
            section += f"**Description:** {feature.description}\n\n"

            # Scoring breakdown
            if ranked_feature.ranking_factors:
                section += "**Scoring Breakdown:**\n"
                for factor, score in ranked_feature.ranking_factors.items():
                    section += f"- {factor.replace('_', ' ').title()}: {score:.1f}\n"
                section += "\n"

            # Related commits
            if feature.commits:
                section += f"**Related Commits ({len(feature.commits)}):**\n"
                for commit in feature.commits[:3]:  # Show top 3 commits
                    commit_url = (
                        f"{feature.source_fork.repository.html_url}/commit/{commit.sha}"
                    )
                    section += f"- [`{commit.sha[:8]}`]({commit_url}) {commit.message.split(chr(10))[0]}\n"

                if len(feature.commits) > 3:
                    section += f"- *...and {len(feature.commits) - 3} more commits*\n"
                section += "\n"

            # Files affected
            if feature.files_affected:
                section += f"**Files Affected ({len(feature.files_affected)}):**\n"
                for file_path in feature.files_affected[:5]:  # Show top 5 files
                    section += f"- `{file_path}`\n"

                if len(feature.files_affected) > 5:
                    section += (
                        f"- *...and {len(feature.files_affected) - 5} more files*\n"
                    )
                section += "\n"

            # Code snippets (if enabled and available)
            if self.include_code_snippets and feature.commits:
                section += self._generate_code_snippet(feature)

            # Similar implementations
            if ranked_feature.similar_implementations:
                section += "**Similar Implementations Found:**\n"
                for similar in ranked_feature.similar_implementations[:2]:
                    section += f"- [{similar.source_fork.repository.full_name}]({similar.source_fork.repository.html_url}): {similar.title}\n"
                section += "\n"

            section += "---\n\n"

        return section

    def _generate_fork_statistics(self, fork_analyses: list[ForkAnalysis]) -> str:
        """Generate fork statistics section."""
        if not fork_analyses:
            return ""

        section = "## Fork Analysis Statistics\n\n"

        # Overall stats
        total_forks = len(fork_analyses)
        active_forks = len([fa for fa in fork_analyses if fa.fork.is_active])
        forks_with_features = len([fa for fa in fork_analyses if fa.features])

        section += f"**Total Forks Analyzed:** {total_forks}  \n"
        section += f"**Active Forks:** {active_forks} ({active_forks/total_forks*100:.1f}%)  \n"
        section += f"**Forks with Features:** {forks_with_features} ({forks_with_features/total_forks*100:.1f}%)  \n\n"

        # Top contributing forks
        forks_by_features = sorted(
            fork_analyses, key=lambda fa: len(fa.features), reverse=True
        )[:10]

        section += "### Top Contributing Forks\n\n"
        section += "| Fork | Author | Stars | Features | Last Activity |\n"
        section += "|------|--------|-------|----------|---------------|\n"

        for fork_analysis in forks_by_features:
            if not fork_analysis.features:
                continue

            fork = fork_analysis.fork
            last_activity = (
                fork.last_activity.strftime("%Y-%m-%d")
                if fork.last_activity
                else "Unknown"
            )

            section += f"| [{fork.repository.full_name}]({fork.repository.html_url}) | "
            section += f"[{fork.owner.login}]({fork.owner.html_url}) | "
            section += f"{fork.repository.stars} | "
            section += f"{len(fork_analysis.features)} | "
            section += f"{last_activity} |\n"

        section += "\n"

        return section

    def _generate_analysis_metadata(self, metadata: dict[str, str]) -> str:
        """Generate analysis metadata section."""
        section = "## Analysis Configuration\n\n"

        for key, value in metadata.items():
            formatted_key = key.replace("_", " ").title()
            section += f"**{formatted_key}:** {value}  \n"

        return section

    def _generate_footer(self) -> str:
        """Generate report footer."""
        return f"""---

*Report generated by Forklift v1.0 on {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}*

**Next Steps:**
1. Review the top-ranked features for potential integration
2. Contact fork authors for collaboration opportunities
3. Create pull requests for high-value features
4. Consider reaching out to active contributors

For questions about this analysis, please refer to the [Forklift documentation](https://github.com/forklift/forklift)."""

    def _generate_code_snippet(self, feature: Feature) -> str:
        """Generate a code snippet section for a feature."""
        if not feature.commits:
            return ""

        # For now, just show commit info - actual code extraction would require diff parsing
        section = "**Code Changes Preview:**\n"
        section += "```\n"

        main_commit = feature.commits[0]
        section += f"Commit: {main_commit.sha[:8]}\n"
        section += f"Message: {main_commit.message.split(chr(10))[0]}\n"
        section += f"Files changed: {len(main_commit.files_changed)}\n"
        section += f"Lines added: +{main_commit.additions}\n"
        section += f"Lines removed: -{main_commit.deletions}\n"

        section += "```\n\n"

        # Link to view full diff
        commit_url = (
            f"{feature.source_fork.repository.html_url}/commit/{main_commit.sha}"
        )
        section += f"[View full diff on GitHub]({commit_url})\n\n"

        return section

    def _get_category_emoji(self, category: FeatureCategory) -> str:
        """Get emoji for feature category."""
        text_map = {
            FeatureCategory.NEW_FEATURE: "[FEAT]",
            FeatureCategory.BUG_FIX: "[FIX]",
            FeatureCategory.PERFORMANCE: "[PERF]",
            FeatureCategory.DOCUMENTATION: "[DOCS]",
            FeatureCategory.REFACTOR: "[REF]",
            FeatureCategory.TEST: "[TEST]",
            FeatureCategory.OTHER: "[OTHER]",
        }
        return text_map.get(category, "[OTHER]")

    def generate_summary_report(
        self,
        repository: Repository,
        total_forks: int,
        features_found: int,
        analysis_duration: float | None = None,
    ) -> str:
        """Generate a brief summary report.

        Args:
            repository: The analyzed repository
            total_forks: Total number of forks analyzed
            features_found: Number of features discovered
            analysis_duration: Analysis duration in seconds

        Returns:
            Brief markdown summary
        """
        duration_text = ""
        if analysis_duration:
            duration_text = f" (completed in {analysis_duration:.1f}s)"

        return f"""# Fork Analysis Summary: {repository.full_name}

**Analysis completed{duration_text}**

- **Repository:** [{repository.full_name}]({repository.html_url})
- **Forks analyzed:** {total_forks}
- **Features discovered:** {features_found}
- **Analysis date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}

{f"**{features_found} valuable features** were identified across the fork ecosystem." if features_found > 0 else "No significant features were found in the analyzed forks."}

*Run a full analysis with `forklift analyze {repository.html_url}` for detailed results.*"""

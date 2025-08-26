"""Commit explanation engine that orchestrates the explanation system."""

import logging
from datetime import datetime

from forklift.models import (
    AnalysisContext,
    Commit,
    CommitExplanation,
    CommitWithExplanation,
    FileChange,
)

from .commit_categorizer import CommitCategorizer
from .explanation_generator import ExplanationGenerator
from .impact_assessor import ImpactAssessor

logger = logging.getLogger(__name__)


class CommitExplanationEngine:
    """Orchestrates commit analysis and explanation generation."""

    def __init__(
        self,
        categorizer: CommitCategorizer | None = None,
        assessor: ImpactAssessor | None = None,
        generator: ExplanationGenerator | None = None
    ):
        """Initialize the commit explanation engine.
        
        Args:
            categorizer: Commit categorizer. If None, creates default instance.
            assessor: Impact assessor. If None, creates default instance.
            generator: Explanation generator. If None, creates default instance.
        """
        self.categorizer = categorizer or CommitCategorizer()
        self.assessor = assessor or ImpactAssessor()
        self.generator = generator or ExplanationGenerator()

    def explain_commit(
        self,
        commit: Commit,
        context: AnalysisContext,
        file_changes: list[FileChange] | None = None
    ) -> CommitExplanation:
        """Generate explanation for a single commit.
        
        Args:
            commit: The commit to explain
            context: Analysis context for the commit
            file_changes: Optional list of file changes. If None, inferred from commit.
            
        Returns:
            CommitExplanation with generated explanation
            
        Raises:
            Exception: If explanation generation fails
        """
        try:
            logger.debug(f"Explaining commit {commit.sha[:8]}: {commit.message[:50]}...")

            # Prepare file changes if not provided
            if file_changes is None:
                file_changes = [
                    FileChange(filename=filename, status="modified")
                    for filename in commit.files_changed
                ]

            # Step 1: Categorize the commit
            category = self.categorizer.categorize_commit(commit, file_changes)
            logger.debug(f"Categorized as {category.category_type.value} with confidence {category.confidence:.2f}")

            # Step 2: Assess impact
            impact_assessment = self.assessor.assess_impact(commit, file_changes, context)
            logger.debug(f"Impact assessed as {impact_assessment.impact_level.value}")

            # Step 3: Generate explanation
            what_changed, explanation, main_repo_value, is_complex, github_url = self.generator.generate_explanation(
                commit, category.category_type, impact_assessment.impact_level, file_changes, context.repository
            )
            logger.debug(f"Generated explanation: {explanation[:100]}...")

            # Create the complete explanation
            commit_explanation = CommitExplanation(
                commit_sha=commit.sha,
                category=category,
                impact_assessment=impact_assessment,
                what_changed=what_changed,
                main_repo_value=main_repo_value,
                explanation=explanation,
                is_complex=is_complex,
                github_url=github_url,
                generated_at=datetime.utcnow()
            )

            logger.debug(f"Successfully explained commit {commit.sha[:8]}")
            return commit_explanation

        except Exception as e:
            logger.error(f"Failed to explain commit {commit.sha[:8]}: {e}")
            raise

    def explain_commits_batch(
        self,
        commits: list[Commit],
        context: AnalysisContext,
        file_changes_map: dict[str, list[FileChange]] | None = None
    ) -> list[CommitWithExplanation]:
        """Generate explanations for multiple commits.
        
        Args:
            commits: List of commits to explain
            context: Analysis context for the commits
            file_changes_map: Optional mapping of commit SHA to file changes
            
        Returns:
            List of CommitWithExplanation objects
        """
        logger.info(f"Explaining {len(commits)} commits in batch")
        results = []

        for commit in commits:
            try:
                # Get file changes for this commit
                file_changes = None
                if file_changes_map:
                    file_changes = file_changes_map.get(commit.sha)

                # Generate explanation
                explanation = self.explain_commit(commit, context, file_changes)

                # Create result with explanation
                result = CommitWithExplanation(
                    commit=commit,
                    explanation=explanation
                )

            except Exception as e:
                logger.warning(f"Failed to explain commit {commit.sha[:8]}: {e}")

                # Create result with error
                result = CommitWithExplanation(
                    commit=commit,
                    explanation_error=str(e)
                )

            results.append(result)

        successful_explanations = sum(1 for r in results if r.explanation is not None)
        logger.info(f"Successfully explained {successful_explanations}/{len(commits)} commits")

        return results

    def is_explanation_enabled(self) -> bool:
        """Check if explanation generation is enabled.
        
        Returns:
            True if explanation generation is enabled
        """
        # For now, always return True since the engine exists
        # In the future, this could check configuration settings
        return True

    def get_explanation_summary(self, explanations: list[CommitExplanation]) -> str:
        """Generate a summary of commit explanations.
        
        Args:
            explanations: List of commit explanations
            
        Returns:
            Summary string describing the explanations
        """
        if not explanations:
            return "No commit explanations generated."

        # Count by category
        category_counts = {}
        impact_counts = {}
        value_counts = {}
        complex_count = 0

        for explanation in explanations:
            # Count categories
            category = explanation.category.category_type.value
            category_counts[category] = category_counts.get(category, 0) + 1

            # Count impact levels
            impact = explanation.impact_assessment.impact_level.value
            impact_counts[impact] = impact_counts.get(impact, 0) + 1

            # Count main repo values
            value = explanation.main_repo_value.value
            value_counts[value] = value_counts.get(value, 0) + 1

            # Count complex commits
            if explanation.is_complex:
                complex_count += 1

        # Build summary
        total = len(explanations)
        summary_parts = [f"Analyzed {total} commits:"]

        # Category breakdown
        if category_counts:
            category_summary = ", ".join([
                f"{count} {category}" for category, count in
                sorted(category_counts.items(), key=lambda x: x[1], reverse=True)
            ])
            summary_parts.append(f"Categories: {category_summary}")

        # Impact breakdown
        if impact_counts:
            impact_summary = ", ".join([
                f"{count} {impact}" for impact, count in
                sorted(impact_counts.items(), key=lambda x: x[1], reverse=True)
            ])
            summary_parts.append(f"Impact levels: {impact_summary}")

        # Value assessment
        valuable_commits = value_counts.get("yes", 0)
        if valuable_commits > 0:
            summary_parts.append(f"{valuable_commits} commits could benefit the main repository")

        # Complex commits
        if complex_count > 0:
            summary_parts.append(f"{complex_count} commits are complex (do multiple things)")

        return ". ".join(summary_parts) + "."

    def validate_explanation(self, explanation: CommitExplanation) -> list[str]:
        """Validate a commit explanation for completeness and quality.
        
        Args:
            explanation: The explanation to validate
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        # Check required fields
        if not explanation.commit_sha:
            errors.append("Missing commit SHA")

        if not explanation.what_changed:
            errors.append("Missing 'what changed' description")

        if not explanation.explanation:
            errors.append("Missing explanation text")

        if not explanation.github_url:
            errors.append("Missing GitHub URL")

        # Check explanation quality
        if explanation.explanation and len(explanation.explanation) < 10:
            errors.append("Explanation is too short")

        if explanation.what_changed and len(explanation.what_changed) < 5:
            errors.append("'What changed' description is too short")

        # Check category confidence
        if explanation.category.confidence < 0.1:
            errors.append("Category confidence is too low")

        # Check impact assessment
        if explanation.impact_assessment.change_magnitude < 0:
            errors.append("Invalid change magnitude")

        if not (0 <= explanation.impact_assessment.file_criticality <= 1):
            errors.append("File criticality must be between 0 and 1")

        return errors

    def get_engine_stats(self) -> dict:
        """Get statistics about the explanation engine.
        
        Returns:
            Dictionary with engine statistics
        """
        return {
            "categorizer_patterns": len(self.categorizer.patterns.message_patterns),
            "assessor_rules": len(self.assessor.criticality_rules.core_patterns),
            "generator_templates": len(self.generator.templates.category_templates),
            "explanation_enabled": self.is_explanation_enabled(),
        }

"""Impact assessment for commits in explanation system."""

import re
from typing import Dict, List, Set

from forklift.models import (
    ImpactLevel,
    ImpactAssessment,
    FileChange,
    Commit,
    AnalysisContext,
)


class FileCriticalityRules:
    """Rules for determining file criticality in different project types."""

    def __init__(self):
        """Initialize file criticality patterns."""
        # Core system files (highest criticality)
        self.core_patterns = [
            re.compile(r'^(main|index|app|server|client)\.py$', re.IGNORECASE),
            re.compile(r'^(main|index|app)\.js$', re.IGNORECASE),
            re.compile(r'^(main|index|app)\.ts$', re.IGNORECASE),
            re.compile(r'^__init__\.py$', re.IGNORECASE),
            re.compile(r'^setup\.py$', re.IGNORECASE),
            re.compile(r'^pyproject\.toml$', re.IGNORECASE),
            re.compile(r'^package\.json$', re.IGNORECASE),
        ]

        # Configuration files (high criticality)
        self.config_patterns = [
            re.compile(r'config.*\.(py|js|ts|json|yaml|yml|toml)$', re.IGNORECASE),
            re.compile(r'settings.*\.(py|js|ts|json|yaml|yml)$', re.IGNORECASE),
            re.compile(r'.*\.env.*$', re.IGNORECASE),
            re.compile(r'Dockerfile$', re.IGNORECASE),
            re.compile(r'docker-compose.*\.ya?ml$', re.IGNORECASE),
        ]

        # Security-related files (high criticality)
        self.security_patterns = [
            re.compile(r'.*auth.*\.(py|js|ts)$', re.IGNORECASE),
            re.compile(r'.*security.*\.(py|js|ts)$', re.IGNORECASE),
            re.compile(r'.*crypto.*\.(py|js|ts)$', re.IGNORECASE),
            re.compile(r'.*permission.*\.(py|js|ts)$', re.IGNORECASE),
        ]

        # Database/model files (medium-high criticality)
        self.data_patterns = [
            re.compile(r'.*model.*\.(py|js|ts)$', re.IGNORECASE),
            re.compile(r'.*schema.*\.(py|js|ts|sql)$', re.IGNORECASE),
            re.compile(r'.*migration.*\.(py|js|ts|sql)$', re.IGNORECASE),
            re.compile(r'.*database.*\.(py|js|ts)$', re.IGNORECASE),
        ]

        # API/interface files (medium criticality)
        self.api_patterns = [
            re.compile(r'.*api.*\.(py|js|ts)$', re.IGNORECASE),
            re.compile(r'.*endpoint.*\.(py|js|ts)$', re.IGNORECASE),
            re.compile(r'.*route.*\.(py|js|ts)$', re.IGNORECASE),
            re.compile(r'.*controller.*\.(py|js|ts)$', re.IGNORECASE),
        ]

        # Test files (low criticality for production impact)
        self.test_patterns = [
            re.compile(r'test_.*\.py$', re.IGNORECASE),
            re.compile(r'.*_test\.(py|js|ts)$', re.IGNORECASE),
            re.compile(r'.*\.test\.(js|ts)$', re.IGNORECASE),
            re.compile(r'.*\.spec\.(js|ts)$', re.IGNORECASE),
            re.compile(r'tests?/.*', re.IGNORECASE),
        ]

        # Documentation files (low criticality for production impact)
        self.doc_patterns = [
            re.compile(r'README.*', re.IGNORECASE),
            re.compile(r'.*\.md$', re.IGNORECASE),
            re.compile(r'.*\.rst$', re.IGNORECASE),
            re.compile(r'docs?/.*', re.IGNORECASE),
        ]


class ImpactAssessor:
    """Assesses the impact of commits based on various factors."""

    def __init__(self, criticality_rules: FileCriticalityRules = None):
        """Initialize the impact assessor.
        
        Args:
            criticality_rules: Rules for determining file criticality.
                              If None, uses default rules.
        """
        self.criticality_rules = criticality_rules or FileCriticalityRules()

    def assess_impact(
        self,
        commit: Commit,
        file_changes: List[FileChange],
        context: AnalysisContext
    ) -> ImpactAssessment:
        """Assess the impact of a commit.
        
        Args:
            commit: The commit to assess
            file_changes: List of file changes in the commit
            context: Analysis context for additional information
            
        Returns:
            ImpactAssessment with impact level and detailed analysis
        """
        # Handle None file_changes by creating from commit.files_changed
        if file_changes is None:
            file_changes = [
                FileChange(filename=filename, status="modified")
                for filename in commit.files_changed
            ]
        
        # Calculate change magnitude
        change_magnitude = self._calculate_change_magnitude(commit, file_changes)
        
        # Assess file criticality
        file_criticality = self._assess_file_criticality(file_changes, context)
        
        # Evaluate quality factors
        quality_factors = self._evaluate_quality_factors(commit, file_changes, context)
        
        # Determine overall impact level
        impact_level = self._determine_impact_level(
            change_magnitude, file_criticality, quality_factors
        )
        
        # Generate reasoning
        reasoning = self._generate_reasoning(
            impact_level, change_magnitude, file_criticality, quality_factors
        )
        
        return ImpactAssessment(
            impact_level=impact_level,
            change_magnitude=change_magnitude,
            file_criticality=file_criticality,
            quality_factors=quality_factors,
            reasoning=reasoning
        )

    def _calculate_change_magnitude(
        self, commit: Commit, file_changes: List[FileChange]
    ) -> float:
        """Calculate the magnitude of changes in a commit.
        
        Args:
            commit: The commit to analyze
            file_changes: List of file changes
            
        Returns:
            Change magnitude score (higher = more changes)
        """
        # Base score from commit stats
        lines_changed = commit.additions + commit.deletions
        files_changed = len(file_changes) if file_changes else len(commit.files_changed)
        
        # Weight factors
        line_weight = 0.7
        file_weight = 0.3
        
        # Calculate weighted score
        line_score = min(lines_changed / 100.0, 10.0)  # Normalize to reasonable range
        file_score = min(files_changed / 10.0, 5.0)    # Normalize file count
        
        magnitude = (line_score * line_weight) + (file_score * file_weight)
        
        # Bonus for large changes
        if lines_changed > 500:
            magnitude *= 1.5
        elif lines_changed > 200:
            magnitude *= 1.2
        
        return round(magnitude, 2)

    def _assess_file_criticality(
        self, file_changes: List[FileChange], context: AnalysisContext
    ) -> float:
        """Assess the criticality of files being changed.
        
        Args:
            file_changes: List of file changes
            context: Analysis context
            
        Returns:
            File criticality score (0.0 to 1.0)
        """
        if not file_changes:
            return 0.0
        
        criticality_scores = []
        
        for file_change in file_changes:
            filename = file_change.filename
            score = self._get_file_criticality_score(filename, context)
            criticality_scores.append(score)
        
        # Return average criticality, weighted by change size
        if not criticality_scores:
            return 0.0
        
        # Weight by change size (additions + deletions)
        weighted_scores = []
        total_weight = 0
        
        for i, file_change in enumerate(file_changes):
            weight = max(file_change.additions + file_change.deletions, 1)
            weighted_scores.append(criticality_scores[i] * weight)
            total_weight += weight
        
        if total_weight == 0:
            return sum(criticality_scores) / len(criticality_scores)
        
        return sum(weighted_scores) / total_weight

    def _get_file_criticality_score(self, filename: str, context: AnalysisContext) -> float:
        """Get criticality score for a single file.
        
        Args:
            filename: Name of the file
            context: Analysis context
            
        Returns:
            Criticality score (0.0 to 1.0)
        """
        # Check against known critical files from context
        if filename in context.critical_files:
            return 1.0
        
        # Check pattern-based criticality
        for pattern in self.criticality_rules.core_patterns:
            if pattern.search(filename):
                return 1.0
        
        for pattern in self.criticality_rules.security_patterns:
            if pattern.search(filename):
                return 0.9
        
        for pattern in self.criticality_rules.config_patterns:
            if pattern.search(filename):
                return 0.8
        
        for pattern in self.criticality_rules.data_patterns:
            if pattern.search(filename):
                return 0.7
        
        for pattern in self.criticality_rules.api_patterns:
            if pattern.search(filename):
                return 0.6
        
        # Test and doc files have lower criticality for production impact
        for pattern in self.criticality_rules.test_patterns:
            if pattern.search(filename):
                return 0.2
        
        for pattern in self.criticality_rules.doc_patterns:
            if pattern.search(filename):
                return 0.1
        
        # Default for unknown files
        return 0.4

    def _evaluate_quality_factors(
        self, commit: Commit, file_changes: List[FileChange], context: AnalysisContext
    ) -> Dict[str, float]:
        """Evaluate quality-related factors of the commit.
        
        Args:
            commit: The commit to evaluate
            file_changes: List of file changes
            context: Analysis context
            
        Returns:
            Dictionary of quality factor scores
        """
        factors = {}
        
        # Test coverage factor
        factors["test_coverage"] = self._assess_test_coverage(file_changes)
        
        # Documentation factor
        factors["documentation"] = self._assess_documentation_impact(file_changes)
        
        # Code organization factor
        factors["code_organization"] = self._assess_code_organization(commit, file_changes)
        
        # Commit quality factor
        factors["commit_quality"] = self._assess_commit_quality(commit)
        
        return factors

    def _assess_test_coverage(self, file_changes: List[FileChange]) -> float:
        """Assess test coverage impact of the changes.
        
        Args:
            file_changes: List of file changes
            
        Returns:
            Test coverage score (0.0 to 1.0)
        """
        if not file_changes:
            return 0.0
        
        test_files = 0
        total_files = len(file_changes)
        
        for file_change in file_changes:
            for pattern in self.criticality_rules.test_patterns:
                if pattern.search(file_change.filename):
                    test_files += 1
                    break
        
        # Score based on proportion of test files
        test_ratio = test_files / total_files
        
        # Bonus for having any tests
        if test_files > 0:
            return min(test_ratio + 0.3, 1.0)
        else:
            return 0.0

    def _assess_documentation_impact(self, file_changes: List[FileChange]) -> float:
        """Assess documentation impact of the changes.
        
        Args:
            file_changes: List of file changes
            
        Returns:
            Documentation score (0.0 to 1.0)
        """
        if not file_changes:
            return 0.0
        
        doc_files = 0
        total_files = len(file_changes)
        
        for file_change in file_changes:
            for pattern in self.criticality_rules.doc_patterns:
                if pattern.search(file_change.filename):
                    doc_files += 1
                    break
        
        # Score based on proportion of doc files
        doc_ratio = doc_files / total_files
        
        # Bonus for having any documentation
        if doc_files > 0:
            return min(doc_ratio + 0.2, 1.0)
        else:
            return 0.0

    def _assess_code_organization(
        self, commit: Commit, file_changes: List[FileChange]
    ) -> float:
        """Assess code organization impact.
        
        Args:
            commit: The commit to assess
            file_changes: List of file changes
            
        Returns:
            Code organization score (0.0 to 1.0)
        """
        # Simple heuristics for code organization
        score = 0.5  # Default neutral score
        
        # Handle None file_changes
        if file_changes is None:
            file_changes = []
        
        # Bonus for focused changes (few files)
        if len(file_changes) <= 3:
            score += 0.2
        elif len(file_changes) > 10:
            score -= 0.3  # Stronger penalty for scattered changes
        
        # Bonus for reasonable change size per file
        if file_changes:
            avg_changes_per_file = sum(
                fc.additions + fc.deletions for fc in file_changes
            ) / len(file_changes)
            
            if avg_changes_per_file <= 50:  # Small, focused changes
                score += 0.2
            elif avg_changes_per_file > 200:  # Very large changes
                score -= 0.2
        
        return max(0.0, min(score, 1.0))

    def _assess_commit_quality(self, commit: Commit) -> float:
        """Assess the quality of the commit itself.
        
        Args:
            commit: The commit to assess
            
        Returns:
            Commit quality score (0.0 to 1.0)
        """
        score = 0.5  # Default neutral score
        
        # Message quality
        message = commit.message.strip()
        
        # Bonus for descriptive messages
        if len(message) >= 20:
            score += 0.2
        elif len(message) < 10:
            score -= 0.2
        
        # Bonus for conventional commit format
        if re.match(r'^(feat|fix|docs|style|refactor|test|chore|perf|security)(\([^)]+\))?:', message, re.IGNORECASE):
            score += 0.3
        
        # Penalty for merge commits (usually less meaningful)
        if commit.is_merge:
            score -= 0.2
        
        return max(0.0, min(score, 1.0))

    def _determine_impact_level(
        self,
        change_magnitude: float,
        file_criticality: float,
        quality_factors: Dict[str, float]
    ) -> ImpactLevel:
        """Determine the overall impact level.
        
        Args:
            change_magnitude: Magnitude of changes
            file_criticality: Criticality of affected files
            quality_factors: Quality factor scores
            
        Returns:
            Overall impact level
        """
        # Calculate weighted impact score
        magnitude_weight = 0.4
        criticality_weight = 0.4
        quality_weight = 0.2
        
        avg_quality = sum(quality_factors.values()) / len(quality_factors) if quality_factors else 0.5
        
        # Normalize change magnitude to 0-1 scale
        normalized_magnitude = min(change_magnitude / 5.0, 1.0)
        
        impact_score = (
            normalized_magnitude * magnitude_weight +
            file_criticality * criticality_weight +
            avg_quality * quality_weight
        )
        
        # Determine level based on score
        if impact_score >= 0.8:
            return ImpactLevel.CRITICAL
        elif impact_score >= 0.6:
            return ImpactLevel.HIGH
        elif impact_score >= 0.3:
            return ImpactLevel.MEDIUM
        else:
            return ImpactLevel.LOW

    def _generate_reasoning(
        self,
        impact_level: ImpactLevel,
        change_magnitude: float,
        file_criticality: float,
        quality_factors: Dict[str, float]
    ) -> str:
        """Generate human-readable reasoning for the impact assessment.
        
        Args:
            impact_level: Determined impact level
            change_magnitude: Change magnitude score
            file_criticality: File criticality score
            quality_factors: Quality factor scores
            
        Returns:
            Human-readable reasoning string
        """
        reasons = []
        
        # Change magnitude reasoning
        if change_magnitude > 3.0:
            reasons.append("large number of changes")
        elif change_magnitude > 1.0:
            reasons.append("moderate changes")
        else:
            reasons.append("small changes")
        
        # File criticality reasoning
        if file_criticality > 0.8:
            reasons.append("affects critical system files")
        elif file_criticality > 0.6:
            reasons.append("affects important files")
        elif file_criticality > 0.3:
            reasons.append("affects standard files")
        else:
            reasons.append("affects low-impact files")
        
        # Quality factors reasoning
        test_coverage = quality_factors.get("test_coverage", 0.0)
        documentation = quality_factors.get("documentation", 0.0)
        
        if test_coverage > 0.5:
            reasons.append("includes test coverage")
        if documentation > 0.5:
            reasons.append("includes documentation")
        
        reasoning = f"Impact level {impact_level.value} due to {', '.join(reasons)}"
        return reasoning
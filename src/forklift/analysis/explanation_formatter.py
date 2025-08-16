"""Explanation formatting utilities for rich terminal output."""

from typing import List, Tuple

from rich.console import Console
from rich.table import Table
from rich.text import Text

from ..models.analysis import (
    CategoryType,
    CommitExplanation,
    CommitWithExplanation,
    FormattedExplanation,
    ImpactLevel,
    MainRepoValue,
)
from ..models.github import Commit
from .github_link_generator import GitHubLinkGenerator


class ExplanationFormatter:
    """Formats commit explanations for rich terminal output."""

    # Category icons and colors
    CATEGORY_ICONS = {
        CategoryType.FEATURE: "🚀",
        CategoryType.BUGFIX: "🐛",
        CategoryType.REFACTOR: "♻️",
        CategoryType.DOCS: "📝",
        CategoryType.TEST: "🧪",
        CategoryType.CHORE: "🔧",
        CategoryType.PERFORMANCE: "⚡",
        CategoryType.SECURITY: "🔒",
        CategoryType.OTHER: "❓",
    }

    CATEGORY_COLORS = {
        CategoryType.FEATURE: "bright_green",
        CategoryType.BUGFIX: "bright_red",
        CategoryType.REFACTOR: "bright_blue",
        CategoryType.DOCS: "bright_cyan",
        CategoryType.TEST: "bright_yellow",
        CategoryType.CHORE: "bright_magenta",
        CategoryType.PERFORMANCE: "bright_green",
        CategoryType.SECURITY: "red",
        CategoryType.OTHER: "white",
    }

    # Impact level indicators
    IMPACT_INDICATORS = {
        ImpactLevel.LOW: "🟢",
        ImpactLevel.MEDIUM: "🟡",
        ImpactLevel.HIGH: "🟠",
        ImpactLevel.CRITICAL: "🔴",
    }

    IMPACT_COLORS = {
        ImpactLevel.LOW: "green",
        ImpactLevel.MEDIUM: "yellow",
        ImpactLevel.HIGH: "orange3",
        ImpactLevel.CRITICAL: "red",
    }

    # Main repo value indicators
    VALUE_INDICATORS = {
        MainRepoValue.YES: "✅",
        MainRepoValue.NO: "❌",
        MainRepoValue.UNCLEAR: "❔",
    }

    VALUE_COLORS = {
        MainRepoValue.YES: "bright_green",
        MainRepoValue.NO: "bright_red",
        MainRepoValue.UNCLEAR: "yellow",
    }

    def __init__(self, use_colors: bool = True, use_icons: bool = True):
        """
        Initialize the formatter.
        
        Args:
            use_colors: Whether to use color coding
            use_icons: Whether to use icons for visual identification
        """
        self.use_colors = use_colors
        self.use_icons = use_icons
        self.console = Console()

    def format_commit_explanation(
        self, commit: Commit, explanation: CommitExplanation, github_url: str
    ) -> str:
        """
        Format a single commit explanation for display.
        
        Args:
            commit: The commit object
            explanation: The explanation object
            github_url: GitHub URL for the commit
            
        Returns:
            Formatted explanation string
        """
        # Create formatted explanation
        formatted = self.create_formatted_explanation(explanation, github_url)
        
        # Build the display string
        lines = []
        
        # Header with commit info
        lines.append(f"┌─ Commit: {commit.sha[:8]} {'─' * 50}")
        
        # GitHub link
        if self.use_colors:
            link_text = GitHubLinkGenerator.format_clickable_link(github_url, github_url)
            lines.append(f"│ 🔗 {link_text}")
        else:
            lines.append(f"│ Link: {github_url}")
        
        lines.append("│")
        
        # Description section
        lines.append(f"│ 📝 Description: {formatted.description}")
        lines.append("│")
        
        # Evaluation section
        lines.append(f"│ ⚖️  Assessment: {formatted.evaluation}")
        lines.append(f"│    Category: {formatted.category_display}")
        lines.append(f"│    Impact: {formatted.impact_indicator}")
        
        if formatted.is_complex:
            lines.append("│    ⚠️  Complex: Does multiple things")
        
        lines.append("└" + "─" * 60)
        
        return "\n".join(lines)

    def format_explanation_table(
        self, explanations: List[CommitWithExplanation]
    ) -> Table:
        """
        Format multiple commit explanations as a table.
        
        Args:
            explanations: List of commits with explanations
            
        Returns:
            Rich Table object for display
        """
        table = Table(title="Commit Explanations", show_header=True, header_style="bold magenta")
        
        # Add columns
        table.add_column("SHA", style="cyan", width=8)
        table.add_column("Category", width=12)
        table.add_column("Impact", width=8)
        table.add_column("Value", width=8)
        table.add_column("Description", style="white")
        table.add_column("GitHub", width=10)
        
        for commit_with_explanation in explanations:
            commit = commit_with_explanation.commit
            explanation = commit_with_explanation.explanation
            
            if explanation is None:
                # Handle missing explanation
                table.add_row(
                    commit.sha[:8],
                    "❓ Unknown",
                    "❓",
                    "❓",
                    "No explanation available",
                    "N/A"
                )
                continue
            
            # Create formatted explanation
            formatted = self.create_formatted_explanation(explanation, explanation.github_url)
            
            # Create clickable link
            if self.use_colors:
                link_display = GitHubLinkGenerator.format_clickable_link(
                    explanation.github_url, "View"
                )
            else:
                link_display = "Link"
            
            # Add row to table
            table.add_row(
                commit.sha[:8],
                formatted.category_display,
                formatted.impact_indicator,
                self._format_value_indicator(explanation.main_repo_value),
                formatted.description[:80] + ("..." if len(formatted.description) > 80 else ""),
                link_display
            )
        
        return table

    def create_formatted_explanation(
        self, explanation: CommitExplanation, github_url: str
    ) -> FormattedExplanation:
        """
        Create a FormattedExplanation from a CommitExplanation.
        
        Args:
            explanation: The explanation to format
            github_url: GitHub URL for the commit
            
        Returns:
            FormattedExplanation object
        """
        # Format category with icon and color
        category_display = self.format_category_with_icon(explanation.category.category_type)
        
        # Format impact indicator
        impact_indicator = self.format_impact_indicator(explanation.impact_assessment.impact_level)
        
        # Separate description from evaluation
        description, evaluation = self.separate_description_from_evaluation(explanation)
        
        return FormattedExplanation(
            commit_sha=explanation.commit_sha,
            github_url=github_url,
            category_display=category_display,
            description=description,
            evaluation=evaluation,
            impact_indicator=impact_indicator,
            is_complex=explanation.is_complex
        )

    def format_category_with_icon(self, category: CategoryType) -> str:
        """
        Format a category with icon and color.
        
        Args:
            category: Category type to format
            
        Returns:
            Formatted category string
        """
        icon = self.CATEGORY_ICONS.get(category, "❓") if self.use_icons else ""
        color = self.CATEGORY_COLORS.get(category, "white") if self.use_colors else None
        
        category_text = category.value.title()
        
        if icon:
            display_text = f"{icon} {category_text}"
        else:
            display_text = category_text
        
        if color and self.use_colors:
            # Create colored text using Rich
            text = Text(display_text, style=color)
            return str(text)
        
        return display_text

    def format_impact_indicator(self, impact: ImpactLevel) -> str:
        """
        Format an impact level with visual indicator.
        
        Args:
            impact: Impact level to format
            
        Returns:
            Formatted impact string
        """
        indicator = self.IMPACT_INDICATORS.get(impact, "❓") if self.use_icons else ""
        color = self.IMPACT_COLORS.get(impact, "white") if self.use_colors else None
        
        impact_text = impact.value.title()
        
        if indicator:
            display_text = f"{indicator} {impact_text}"
        else:
            display_text = impact_text
        
        if color and self.use_colors:
            # Create colored text using Rich
            text = Text(display_text, style=color)
            return str(text)
        
        return display_text

    def _format_value_indicator(self, value: MainRepoValue) -> str:
        """Format main repo value with indicator."""
        indicator = self.VALUE_INDICATORS.get(value, "❓") if self.use_icons else ""
        color = self.VALUE_COLORS.get(value, "white") if self.use_colors else None
        
        if indicator:
            display_text = f"{indicator} {value.value.upper()}"
        else:
            display_text = value.value.upper()
        
        if color and self.use_colors:
            text = Text(display_text, style=color)
            return str(text)
        
        return display_text

    def separate_description_from_evaluation(
        self, explanation: CommitExplanation
    ) -> Tuple[str, str]:
        """
        Separate factual description from evaluative assessment.
        
        Args:
            explanation: The explanation to separate
            
        Returns:
            Tuple of (description, evaluation)
        """
        # Description is the factual "what changed"
        description = explanation.what_changed
        
        # Evaluation includes the assessment and value determination
        value_text = f"Value for main repo: {explanation.main_repo_value.value.upper()}"
        
        if explanation.is_complex:
            evaluation = f"{value_text} (Complex: does multiple things)"
        else:
            evaluation = value_text
        
        return description, evaluation

    def print_formatted_explanation(
        self, commit: Commit, explanation: CommitExplanation, github_url: str
    ) -> None:
        """
        Print a formatted explanation to the console.
        
        Args:
            commit: The commit object
            explanation: The explanation object
            github_url: GitHub URL for the commit
        """
        formatted_text = self.format_commit_explanation(commit, explanation, github_url)
        self.console.print(formatted_text)

    def print_explanation_table(
        self, explanations: List[CommitWithExplanation]
    ) -> None:
        """
        Print a table of explanations to the console.
        
        Args:
            explanations: List of commits with explanations
        """
        table = self.format_explanation_table(explanations)
        self.console.print(table)
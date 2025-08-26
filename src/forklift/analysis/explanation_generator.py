"""Explanation generation for commits in explanation system."""

import re

from forklift.models import (
    CategoryType,
    Commit,
    FileChange,
    ImpactLevel,
    MainRepoValue,
    Repository,
)

from .github_link_generator import GitHubLinkGenerator


class ExplanationTemplates:
    """Templates for generating commit explanations."""

    def __init__(self):
        """Initialize explanation templates."""
        # Templates for different category types
        self.category_templates: dict[CategoryType, list[str]] = {
            CategoryType.FEATURE: [
                "This commit adds {description}",
                "This commit implements {description}",
                "This commit introduces {description}",
            ],
            CategoryType.BUGFIX: [
                "This commit fixes {description}",
                "This commit resolves {description}",
                "This commit corrects {description}",
            ],
            CategoryType.REFACTOR: [
                "This commit refactors {description}",
                "This commit improves {description}",
                "This commit restructures {description}",
            ],
            CategoryType.DOCS: [
                "This commit updates {description}",
                "This commit adds documentation for {description}",
                "This commit improves documentation of {description}",
            ],
            CategoryType.TEST: [
                "This commit adds tests for {description}",
                "This commit improves test coverage of {description}",
                "This commit updates tests for {description}",
            ],
            CategoryType.CHORE: [
                "This commit updates {description}",
                "This commit maintains {description}",
                "This commit upgrades {description}",
            ],
            CategoryType.PERFORMANCE: [
                "This commit optimizes {description}",
                "This commit improves performance of {description}",
                "This commit speeds up {description}",
            ],
            CategoryType.SECURITY: [
                "This commit secures {description}",
                "This commit fixes security issue in {description}",
                "This commit improves security of {description}",
            ],
            CategoryType.OTHER: [
                "This commit modifies {description}",
                "This commit changes {description}",
                "This commit updates {description}",
            ],
        }

        # Value assessment templates
        self.value_templates: dict[MainRepoValue, list[str]] = {
            MainRepoValue.YES: [
                "This could be useful for the main repository.",
                "This change would benefit the main repository.",
                "This improvement could help the main repository.",
            ],
            MainRepoValue.NO: [
                "This is specific to this fork and not relevant for the main repository.",
                "This change is not applicable to the main repository.",
                "This is a fork-specific modification.",
            ],
            MainRepoValue.UNCLEAR: [
                "It's unclear if this would be useful for the main repository.",
                "The value for the main repository is uncertain.",
                "This needs further review to determine main repository value.",
            ],
        }

        # Complexity indicators
        self.complexity_indicators = [
            "This commit does multiple things at once",
            "This is a complex change that combines several modifications",
            "This commit mixes different types of changes",
        ]


class ExplanationGenerator:
    """Generates human-readable explanations for commits."""

    def __init__(self, templates: ExplanationTemplates = None):
        """Initialize the explanation generator.
        
        Args:
            templates: Explanation templates to use. If None, uses default templates.
        """
        self.templates = templates or ExplanationTemplates()

    def generate_explanation(
        self,
        commit: Commit,
        category: CategoryType,
        impact_level: ImpactLevel,
        file_changes: list[FileChange],
        repository: Repository
    ) -> tuple[str, str, MainRepoValue, bool, str]:
        """Generate a complete explanation for a commit.
        
        Args:
            commit: The commit to explain
            category: Determined category of the commit
            impact_level: Assessed impact level
            file_changes: List of file changes
            repository: Repository information for generating GitHub URL
            
        Returns:
            Tuple of (what_changed, explanation, main_repo_value, is_complex, github_url)
        """
        # Extract what changed
        what_changed = self._describe_what_changed(commit, file_changes)

        # Assess main repository value
        main_repo_value = self._assess_main_repo_value(commit, category, file_changes)

        # Check if commit is complex
        is_complex = self._is_complex_commit(commit, file_changes)

        # Generate GitHub commit URL
        github_url = self._generate_github_commit_url(commit, repository)

        # Generate full explanation
        explanation = self._generate_full_explanation(
            commit, category, what_changed, main_repo_value, is_complex
        )

        # Ensure brevity
        explanation = self._ensure_brevity(explanation)

        return what_changed, explanation, main_repo_value, is_complex, github_url

    def _describe_what_changed(self, commit: Commit, file_changes: list[FileChange]) -> str:
        """Describe what changed in the commit.
        
        Args:
            commit: The commit to describe
            file_changes: List of file changes
            
        Returns:
            Description of what changed
        """
        # Extract key information from commit message
        message = commit.message.strip()

        # Remove conventional commit prefix if present
        clean_message = re.sub(r"^(feat|fix|docs|style|refactor|test|chore|perf|security)(\([^)]+\))?:\s*", "", message, flags=re.IGNORECASE)

        # If message is still descriptive, use it
        if len(clean_message) > 10 and not self._is_generic_message(clean_message):
            return clean_message.split("\n")[0]  # Use first line only

        # Otherwise, infer from file changes
        return self._infer_changes_from_files(file_changes)

    def _infer_changes_from_files(self, file_changes: list[FileChange]) -> str:
        """Infer what changed from file changes.
        
        Args:
            file_changes: List of file changes
            
        Returns:
            Inferred description of changes
        """
        if not file_changes:
            return "code changes"

        # Categorize files
        categories = {
            "test": [],
            "doc": [],
            "config": [],
            "core": [],
            "other": []
        }

        for file_change in file_changes:
            filename = file_change.filename.lower()

            if "test" in filename or filename.endswith(".test.js") or filename.endswith(".spec.js"):
                categories["test"].append(file_change)
            elif filename.endswith(".md") or filename.endswith(".rst") or "readme" in filename or "doc" in filename:
                categories["doc"].append(file_change)
            elif "config" in filename or filename.endswith(".json") or filename.endswith(".yaml") or filename.endswith(".toml"):
                categories["config"].append(file_change)
            elif any(core in filename for core in ["main", "index", "app", "server", "client"]):
                categories["core"].append(file_change)
            else:
                categories["other"].append(file_change)

        # Generate description based on predominant category
        if categories["test"] and len(categories["test"]) >= len(file_changes) / 2:
            return "test coverage and testing functionality"
        elif categories["doc"] and len(categories["doc"]) >= len(file_changes) / 2:
            return "documentation and project information"
        elif categories["config"]:
            return "configuration and project setup"
        elif categories["core"]:
            return "core application functionality"
        elif len(file_changes) == 1:
            return f"the {file_changes[0].filename} file"
        else:
            return f"{len(file_changes)} files across the project"

    def _is_generic_message(self, message: str) -> bool:
        """Check if a commit message is too generic to be useful.
        
        Args:
            message: Commit message to check
            
        Returns:
            True if message is generic
        """
        generic_patterns = [
            r"^(update|fix|change|modify|improve)s?$",
            r"^(update|fix|change|modify|improve)\s+(stuff|things|code)$",
            r"^(wip|work in progress)$",
            r"^(misc|miscellaneous)$",
            r"^(stuff|things)$",
            r"^(code|changes)$",
        ]

        message_lower = message.lower().strip()

        for pattern in generic_patterns:
            if re.match(pattern, message_lower):
                return True

        return False

    def _assess_main_repo_value(
        self,
        commit: Commit,
        category: CategoryType,
        file_changes: list[FileChange]
    ) -> MainRepoValue:
        """Assess whether the commit would be valuable for the main repository.
        
        Args:
            commit: The commit to assess
            category: Commit category
            file_changes: List of file changes
            
        Returns:
            Assessment of main repository value
        """
        # High-value categories
        if category in [CategoryType.BUGFIX, CategoryType.SECURITY, CategoryType.PERFORMANCE]:
            return MainRepoValue.YES

        # Medium-value categories that depend on content
        if category in [CategoryType.FEATURE, CategoryType.REFACTOR]:
            # Check if it's a substantial change
            total_changes = sum(fc.additions + fc.deletions for fc in file_changes)
            if total_changes > 50:
                return MainRepoValue.YES
            else:
                return MainRepoValue.UNCLEAR

        # Documentation and tests are usually valuable
        if category in [CategoryType.DOCS, CategoryType.TEST]:
            return MainRepoValue.YES

        # Chore changes depend on what they are
        if category == CategoryType.CHORE:
            # Check if it's dependency updates or important maintenance
            message_lower = commit.message.lower()
            if any(keyword in message_lower for keyword in ["dependency", "dependencies", "security", "vulnerability"]):
                return MainRepoValue.YES
            else:
                return MainRepoValue.NO

        # Default for unclear cases
        return MainRepoValue.UNCLEAR

    def _is_complex_commit(self, commit: Commit, file_changes: list[FileChange]) -> bool:
        """Determine if a commit is complex (does multiple things).
        
        Args:
            commit: The commit to assess
            file_changes: List of file changes
            
        Returns:
            True if commit is complex
        """
        # Check for multiple categories in file changes
        categories = set()

        for file_change in file_changes:
            filename = file_change.filename.lower()

            if "test" in filename:
                categories.add("test")
            elif filename.endswith(".md") or "doc" in filename:
                categories.add("doc")
            elif "config" in filename:
                categories.add("config")
            else:
                categories.add("code")

        # Complex if touches multiple categories
        if len(categories) > 2:
            return True

        # Complex if changes many files
        if len(file_changes) > 10:
            return True

        # Complex if commit message suggests multiple actions
        message = commit.message.lower()
        action_words = ["add", "fix", "update", "remove", "refactor", "improve"]
        action_count = sum(1 for word in action_words if word in message)

        if action_count > 2:
            return True

        # Check for "and" in commit message (often indicates multiple things)
        if " and " in message and len(message.split(" and ")) > 2:
            return True

        return False

    def _generate_full_explanation(
        self,
        commit: Commit,
        category: CategoryType,
        what_changed: str,
        main_repo_value: MainRepoValue,
        is_complex: bool
    ) -> str:
        """Generate the full explanation text.
        
        Args:
            commit: The commit
            category: Commit category
            what_changed: Description of what changed
            main_repo_value: Main repository value assessment
            is_complex: Whether commit is complex
            
        Returns:
            Full explanation text
        """
        # Get category template
        category_templates = self.templates.category_templates.get(category, self.templates.category_templates[CategoryType.OTHER])
        category_template = category_templates[0]  # Use first template for consistency

        # Format the main description
        main_description = category_template.format(description=what_changed)

        # Add value assessment
        value_templates = self.templates.value_templates[main_repo_value]
        value_description = value_templates[0]  # Use first template for consistency

        # Combine descriptions
        if is_complex:
            complexity_note = self.templates.complexity_indicators[0]
            explanation = f"{complexity_note}. {value_description}"
        else:
            explanation = f"{main_description}. {value_description}"

        return explanation

    def _ensure_brevity(self, explanation: str, max_sentences: int = 2) -> str:
        """Ensure explanation is brief and concise.
        
        Args:
            explanation: Original explanation
            max_sentences: Maximum number of sentences
            
        Returns:
            Shortened explanation if necessary
        """
        # Split into sentences
        sentences = re.split(r"[.!?]+", explanation)
        sentences = [s.strip() for s in sentences if s.strip()]

        # Keep only the first max_sentences
        if len(sentences) > max_sentences:
            sentences = sentences[:max_sentences]

        # Rejoin and ensure proper punctuation
        result = ". ".join(sentences)
        if result and not result.endswith("."):
            result += "."

        return result

    def _generate_github_commit_url(self, commit: Commit, repository: Repository) -> str:
        """Generate GitHub commit URL for the commit.
        
        Args:
            commit: The commit to generate URL for
            repository: Repository information
            
        Returns:
            GitHub commit URL
        """
        try:
            return GitHubLinkGenerator.generate_commit_url(
                repository.owner,
                repository.name,
                commit.sha
            )
        except ValueError as e:
            # If URL generation fails, return a fallback URL
            return f"https://github.com/{repository.owner}/{repository.name}/commit/{commit.sha}"

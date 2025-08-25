#!/usr/bin/env python3
"""
Expert Commit Analyzer - Provides intelligent analysis of commits to help evaluate their value.

This tool goes beyond basic file changes to provide expert insights about:
- Code quality impact
- Feature significance  
- Risk assessment
- Business value
- Technical debt implications
"""

import asyncio
import sys
import re
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

from forklift.github.client import GitHubClient
from forklift.config.settings import load_config
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


class CommitValue(Enum):
    """Commit value assessment levels."""
    CRITICAL = "[CRIT] Critical"
    HIGH = "[HIGH] High Value" 
    MEDIUM = "[MED] Medium Value"
    LOW = "[LOW] Low Value"
    NOISE = "[NOISE] Noise"


class RiskLevel(Enum):
    """Risk assessment levels."""
    HIGH = "[HIGH RISK] High Risk"
    MEDIUM = "[MED RISK] Medium Risk"
    LOW = "[LOW RISK] Low Risk"


@dataclass
class CommitAnalysis:
    """Expert analysis of a single commit."""
    sha: str
    message: str
    author: str
    date: datetime
    
    # File analysis
    files_changed: List[str]
    additions: int
    deletions: int
    
    # Expert assessments
    value_level: CommitValue
    risk_level: RiskLevel
    significance_score: float  # 0-100
    
    # Insights
    summary: str
    key_changes: List[str]
    potential_impact: str
    concerns: List[str]
    recommendations: List[str]
    
    # Technical analysis
    affects_core: bool
    affects_api: bool
    affects_security: bool
    affects_performance: bool
    introduces_dependencies: bool
    
    # Business analysis
    user_facing: bool
    feature_complete: bool
    bug_fix_quality: str  # "comprehensive", "partial", "band-aid"


class CommitExpertAnalyzer:
    """Expert system for analyzing commit value and significance."""
    
    def __init__(self):
        self.core_patterns = [
            r'src/.*/(core|engine|kernel|main)/',
            r'.*/(api|service|controller)/',
            r'.*/models?/',
            r'.*/database/',
        ]
        
        self.security_patterns = [
            r'auth', r'security', r'crypto', r'password', r'token',
            r'permission', r'access', r'login', r'session'
        ]
        
        self.performance_patterns = [
            r'cache', r'optimize', r'performance', r'speed', r'memory',
            r'async', r'parallel', r'concurrent', r'index'
        ]
        
        self.api_patterns = [
            r'api/', r'endpoint', r'route', r'handler', r'controller',
            r'swagger', r'openapi', r'graphql'
        ]

    async def analyze_commit(self, commit, detailed_commit=None) -> CommitAnalysis:
        """Perform expert analysis of a commit."""
        
        # Use detailed commit if available, otherwise basic commit
        analysis_commit = detailed_commit if detailed_commit else commit
        
        # Extract basic information
        files = getattr(analysis_commit, 'files_changed', [])
        additions = getattr(analysis_commit, 'additions', 0)
        deletions = getattr(analysis_commit, 'deletions', 0)
        
        # Perform technical analysis
        tech_analysis = self._analyze_technical_impact(
            analysis_commit.message, files, additions, deletions
        )
        
        # Perform business analysis  
        business_analysis = self._analyze_business_impact(
            analysis_commit.message, files, additions, deletions
        )
        
        # Calculate significance score
        significance = self._calculate_significance_score(
            analysis_commit.message, files, additions, deletions, tech_analysis, business_analysis
        )
        
        # Determine value and risk levels
        value_level = self._assess_value_level(significance, tech_analysis, business_analysis)
        risk_level = self._assess_risk_level(tech_analysis, files, additions, deletions)
        
        # Generate expert insights
        insights = self._generate_insights(
            analysis_commit.message, files, additions, deletions, 
            tech_analysis, business_analysis, significance
        )
        
        return CommitAnalysis(
            sha=analysis_commit.sha,
            message=analysis_commit.message,
            author=analysis_commit.author.login,
            date=analysis_commit.date,
            files_changed=files,
            additions=additions,
            deletions=deletions,
            value_level=value_level,
            risk_level=risk_level,
            significance_score=significance,
            summary=insights['summary'],
            key_changes=insights['key_changes'],
            potential_impact=insights['impact'],
            concerns=insights['concerns'],
            recommendations=insights['recommendations'],
            affects_core=tech_analysis['affects_core'],
            affects_api=tech_analysis['affects_api'],
            affects_security=tech_analysis['affects_security'],
            affects_performance=tech_analysis['affects_performance'],
            introduces_dependencies=tech_analysis['introduces_dependencies'],
            user_facing=business_analysis['user_facing'],
            feature_complete=business_analysis['feature_complete'],
            bug_fix_quality=business_analysis['bug_fix_quality']
        )

    def _analyze_technical_impact(self, message: str, files: List[str], additions: int, deletions: int) -> Dict:
        """Analyze technical impact of the commit."""
        message_lower = message.lower()
        files_str = ' '.join(files).lower()
        
        return {
            'affects_core': any(re.search(pattern, files_str) for pattern in self.core_patterns),
            'affects_api': any(re.search(pattern, files_str) for pattern in self.api_patterns) or 
                          any(keyword in message_lower for keyword in ['api', 'endpoint', 'route']),
            'affects_security': any(re.search(pattern, message_lower) for pattern in self.security_patterns) or
                               any(re.search(pattern, files_str) for pattern in self.security_patterns),
            'affects_performance': any(re.search(pattern, message_lower) for pattern in self.performance_patterns) or
                                  any(re.search(pattern, files_str) for pattern in self.performance_patterns),
            'introduces_dependencies': any(file.endswith(('requirements.txt', 'package.json', 'Cargo.toml', 'go.mod', 'pom.xml')) for file in files),
            'large_change': additions + deletions > 500,
            'complex_change': len(files) > 20,
            'refactoring': any(keyword in message_lower for keyword in ['refactor', 'restructure', 'reorganize', 'cleanup']),
            'breaking_change': any(keyword in message_lower for keyword in ['breaking', 'break', 'incompatible']) or 'BREAKING' in message
        }

    def _analyze_business_impact(self, message: str, files: List[str], additions: int, deletions: int) -> Dict:
        """Analyze business impact of the commit."""
        message_lower = message.lower()
        
        # Detect user-facing changes
        user_facing_indicators = [
            'ui', 'frontend', 'interface', 'user', 'client', 'web', 'mobile',
            'dashboard', 'form', 'button', 'page', 'screen', 'view'
        ]
        
        # Detect feature completeness
        feature_indicators = [
            'implement', 'add', 'create', 'new', 'feature', 'functionality'
        ]
        
        # Detect bug fix quality
        bug_fix_quality = "none"
        if any(keyword in message_lower for keyword in ['fix', 'bug', 'issue', 'problem']):
            if any(keyword in message_lower for keyword in ['comprehensive', 'complete', 'thorough']):
                bug_fix_quality = "comprehensive"
            elif any(keyword in message_lower for keyword in ['partial', 'temp', 'temporary', 'quick']):
                bug_fix_quality = "partial"
            elif any(keyword in message_lower for keyword in ['hotfix', 'patch', 'band-aid', 'workaround']):
                bug_fix_quality = "band-aid"
            else:
                bug_fix_quality = "standard"
        
        return {
            'user_facing': any(indicator in message_lower for indicator in user_facing_indicators) or
                          any(indicator in ' '.join(files).lower() for indicator in user_facing_indicators),
            'feature_complete': any(indicator in message_lower for indicator in feature_indicators) and
                               additions > deletions and len(files) > 1,
            'bug_fix_quality': bug_fix_quality,
            'documentation_change': any(file.endswith(('.md', '.rst', '.txt', '.doc')) for file in files),
            'test_change': any('test' in file.lower() for file in files),
            'config_change': any(file.endswith(('.json', '.yaml', '.yml', '.toml', '.ini', '.conf')) for file in files)
        }

    def _calculate_significance_score(self, message: str, files: List[str], additions: int, deletions: int, 
                                    tech_analysis: Dict, business_analysis: Dict) -> float:
        """Calculate overall significance score (0-100)."""
        score = 0.0
        
        # Base score from change size
        change_size = additions + deletions
        if change_size > 1000:
            score += 30
        elif change_size > 500:
            score += 25
        elif change_size > 100:
            score += 20
        elif change_size > 50:
            score += 15
        elif change_size > 10:
            score += 10
        else:
            score += 5
        
        # Technical impact bonuses
        if tech_analysis['affects_core']:
            score += 20
        if tech_analysis['affects_api']:
            score += 15
        if tech_analysis['affects_security']:
            score += 25
        if tech_analysis['affects_performance']:
            score += 15
        if tech_analysis['breaking_change']:
            score += 30
        if tech_analysis['introduces_dependencies']:
            score += 10
        
        # Business impact bonuses
        if business_analysis['user_facing']:
            score += 15
        if business_analysis['feature_complete']:
            score += 20
        if business_analysis['bug_fix_quality'] == 'comprehensive':
            score += 15
        elif business_analysis['bug_fix_quality'] == 'standard':
            score += 10
        
        # File diversity bonus
        file_types = set(file.split('.')[-1] for file in files if '.' in file)
        if len(file_types) > 3:
            score += 10
        
        # Penalties
        if business_analysis['documentation_change'] and len(files) == 1:
            score -= 10  # Pure documentation changes are less significant
        if change_size < 5 and len(files) == 1:
            score -= 5   # Very small changes
        
        return min(100.0, max(0.0, score))

    def _assess_value_level(self, significance: float, tech_analysis: Dict, business_analysis: Dict) -> CommitValue:
        """Assess the overall value level of the commit."""
        
        # Critical value indicators
        if (tech_analysis['affects_security'] or 
            tech_analysis['breaking_change'] or
            significance >= 80):
            return CommitValue.CRITICAL
        
        # High value indicators
        if (significance >= 60 or
            (tech_analysis['affects_core'] and business_analysis['user_facing']) or
            business_analysis['feature_complete'] or
            business_analysis['bug_fix_quality'] == 'comprehensive'):
            return CommitValue.HIGH
        
        # Medium value indicators
        if (significance >= 30 or
            tech_analysis['affects_api'] or
            tech_analysis['affects_performance'] or
            business_analysis['user_facing']):
            return CommitValue.MEDIUM
        
        # Low value indicators
        if (significance >= 15 or
            business_analysis['bug_fix_quality'] in ['standard', 'partial']):
            return CommitValue.LOW
        
        # Everything else is noise
        return CommitValue.NOISE

    def _assess_risk_level(self, tech_analysis: Dict, files: List[str], additions: int, deletions: int) -> RiskLevel:
        """Assess the risk level of the commit."""
        
        risk_factors = 0
        
        # High risk factors
        if tech_analysis['affects_core']:
            risk_factors += 3
        if tech_analysis['affects_security']:
            risk_factors += 3
        if tech_analysis['breaking_change']:
            risk_factors += 4
        if tech_analysis['large_change']:
            risk_factors += 2
        if tech_analysis['complex_change']:
            risk_factors += 2
        
        # Medium risk factors
        if tech_analysis['affects_api']:
            risk_factors += 1
        if tech_analysis['introduces_dependencies']:
            risk_factors += 1
        if deletions > additions * 2:  # Lots of deletions
            risk_factors += 1
        
        if risk_factors >= 5:
            return RiskLevel.HIGH
        elif risk_factors >= 2:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW

    def _generate_insights(self, message: str, files: List[str], additions: int, deletions: int,
                          tech_analysis: Dict, business_analysis: Dict, significance: float) -> Dict:
        """Generate expert insights and recommendations."""
        
        # Generate summary
        summary_parts = []
        if tech_analysis['affects_core']:
            summary_parts.append("modifies core system components")
        if tech_analysis['affects_api']:
            summary_parts.append("changes API interfaces")
        if business_analysis['user_facing']:
            summary_parts.append("impacts user experience")
        if business_analysis['feature_complete']:
            summary_parts.append("implements new functionality")
        
        if not summary_parts:
            if business_analysis['documentation_change']:
                summary_parts.append("updates documentation")
            elif business_analysis['test_change']:
                summary_parts.append("modifies tests")
            else:
                summary_parts.append("makes code changes")
        
        summary = f"This commit {', '.join(summary_parts)}."
        
        # Identify key changes
        key_changes = []
        if len(files) <= 5:
            key_changes = [f"Modified {file}" for file in files]
        else:
            file_types = {}
            for file in files:
                ext = file.split('.')[-1] if '.' in file else 'other'
                file_types[ext] = file_types.get(ext, 0) + 1
            
            for ext, count in sorted(file_types.items(), key=lambda x: x[1], reverse=True)[:3]:
                key_changes.append(f"Modified {count} {ext} files")
        
        # Assess potential impact
        impact_parts = []
        if tech_analysis['affects_security']:
            impact_parts.append("security posture")
        if tech_analysis['affects_performance']:
            impact_parts.append("system performance")
        if business_analysis['user_facing']:
            impact_parts.append("user workflows")
        if tech_analysis['affects_api']:
            impact_parts.append("API compatibility")
        
        if impact_parts:
            potential_impact = f"May affect {', '.join(impact_parts)}"
        else:
            potential_impact = "Limited system impact expected"
        
        # Identify concerns
        concerns = []
        if tech_analysis['breaking_change']:
            concerns.append("Breaking change may affect existing integrations")
        if tech_analysis['large_change']:
            concerns.append("Large change increases risk of introducing bugs")
        if tech_analysis['affects_security'] and not business_analysis['test_change']:
            concerns.append("Security changes should include comprehensive tests")
        if tech_analysis['introduces_dependencies']:
            concerns.append("New dependencies may introduce vulnerabilities or conflicts")
        if business_analysis['bug_fix_quality'] == 'band-aid':
            concerns.append("Quick fix may not address root cause")
        
        # Generate recommendations
        recommendations = []
        if tech_analysis['affects_core'] or tech_analysis['affects_security']:
            recommendations.append("Conduct thorough code review and testing")
        if tech_analysis['affects_api']:
            recommendations.append("Update API documentation and notify consumers")
        if tech_analysis['breaking_change']:
            recommendations.append("Plan migration strategy and communicate changes")
        if significance >= 70:
            recommendations.append("Consider feature flagging for gradual rollout")
        if not business_analysis['test_change'] and significance >= 50:
            recommendations.append("Ensure adequate test coverage for changes")
        
        return {
            'summary': summary,
            'key_changes': key_changes,
            'impact': potential_impact,
            'concerns': concerns if concerns else ["No major concerns identified"],
            'recommendations': recommendations if recommendations else ["Standard review process recommended"]
        }


async def analyze_commits_expert(repo_url: str, limit: int = 10):
    """Perform expert analysis of repository commits."""
    
    # Parse repository URL
    if repo_url.startswith('https://github.com/'):
        repo_path = repo_url.replace('https://github.com/', '')
    else:
        repo_path = repo_url
    
    owner, repo_name = repo_path.split('/')
    
    config = load_config()
    analyzer = CommitExpertAnalyzer()
    
    async with GitHubClient(config.github) as client:
        console.print(f"[blue]ANALYZING - Performing expert analysis of {owner}/{repo_name}...[/blue]")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            
            # Get basic commits
            task1 = progress.add_task("Fetching commits...", total=None)
            basic_commits = await client.get_repository_commits(owner, repo_name, per_page=limit)
            progress.update(task1, completed=True)
            
            # Get detailed information and analyze
            task2 = progress.add_task("Analyzing commits...", total=len(basic_commits))
            analyses = []
            
            for i, commit in enumerate(basic_commits):
                try:
                    # Get detailed commit info
                    detailed_commit = await client.get_commit(owner, repo_name, commit.sha)
                    
                    # Perform expert analysis
                    analysis = await analyzer.analyze_commit(commit, detailed_commit)
                    analyses.append(analysis)
                    
                    progress.update(task2, advance=1, description=f"Analyzing commit {i+1}/{len(basic_commits)}")
                    
                except Exception as e:
                    console.print(f"[yellow]Warning: Could not analyze commit {commit.sha[:8]}: {e}[/yellow]")
                    progress.update(task2, advance=1)
        
        # Display expert analysis
        _display_expert_analysis(analyses, owner, repo_name)


def _display_expert_analysis(analyses: List[CommitAnalysis], owner: str, repo_name: str):
    """Display expert analysis results."""
    
    if not analyses:
        console.print("[yellow]No commits analyzed.[/yellow]")
        return
    
    console.print(f"\n[bold blue]ANALYSIS - Expert Commit Analysis: {owner}/{repo_name}[/bold blue]")
    console.print("=" * 80)
    
    # Summary table
    summary_table = Table(title="Commit Value Assessment")
    summary_table.add_column("SHA", style="cyan", width=10)
    summary_table.add_column("Message", style="white", min_width=25, max_width=40)
    summary_table.add_column("Value", style="green", width=15)
    summary_table.add_column("Risk", style="yellow", width=15)
    summary_table.add_column("Score", style="blue", justify="right", width=8)
    
    # Sort by significance score
    sorted_analyses = sorted(analyses, key=lambda x: x.significance_score, reverse=True)
    
    for analysis in sorted_analyses:
        message = analysis.message.split('\n')[0]
        if len(message) > 35:
            message = message[:32] + "..."
        
        # Color code by value level
        if analysis.value_level == CommitValue.CRITICAL:
            value_style = "bold red"
        elif analysis.value_level == CommitValue.HIGH:
            value_style = "bold green"
        elif analysis.value_level == CommitValue.MEDIUM:
            value_style = "yellow"
        elif analysis.value_level == CommitValue.LOW:
            value_style = "blue"
        else:
            value_style = "dim"
        
        summary_table.add_row(
            analysis.sha[:8],
            message,
            f"[{value_style}]{analysis.value_level.value}[/{value_style}]",
            analysis.risk_level.value,
            f"{analysis.significance_score:.0f}"
        )
    
    console.print(summary_table)
    
    # Detailed analysis for top commits
    console.print(f"\n[bold blue]DETAILS - Detailed Analysis (Top {min(3, len(sorted_analyses))} commits)[/bold blue]")
    
    for i, analysis in enumerate(sorted_analyses[:3], 1):
        _display_commit_expert_details(analysis, i)
    
    # Overall insights
    _display_overall_insights(analyses)


def _display_commit_expert_details(analysis: CommitAnalysis, rank: int):
    """Display detailed expert analysis for a single commit."""
    
    # Create detailed panel
    details = []
    
    # Basic info
    details.append(f"[bold]Author:[/bold] {analysis.author}")
    details.append(f"[bold]Date:[/bold] {analysis.date.strftime('%Y-%m-%d %H:%M')}")
    details.append(f"[bold]Changes:[/bold] {len(analysis.files_changed)} files, +{analysis.additions}/-{analysis.deletions} lines")
    details.append("")
    
    # Expert summary
    details.append(f"[bold]Expert Summary:[/bold]")
    details.append(f"  {analysis.summary}")
    details.append("")
    
    # Key changes
    if analysis.key_changes:
        details.append(f"[bold]Key Changes:[/bold]")
        for change in analysis.key_changes[:3]:
            details.append(f"  • {change}")
        details.append("")
    
    # Impact assessment
    details.append(f"[bold]Potential Impact:[/bold] {analysis.potential_impact}")
    details.append("")
    
    # Technical flags
    tech_flags = []
    if analysis.affects_core:
        tech_flags.append("Core System")
    if analysis.affects_api:
        tech_flags.append("API Changes")
    if analysis.affects_security:
        tech_flags.append("Security")
    if analysis.affects_performance:
        tech_flags.append("Performance")
    
    if tech_flags:
        details.append(f"[bold]Technical Impact:[/bold] {', '.join(tech_flags)}")
        details.append("")
    
    # Concerns
    if analysis.concerns and analysis.concerns != ["No major concerns identified"]:
        details.append(f"[bold]⚠️  Concerns:[/bold]")
        for concern in analysis.concerns[:2]:
            details.append(f"  • {concern}")
        details.append("")
    
    # Recommendations
    if analysis.recommendations:
        details.append(f"[bold]RECOMMENDATIONS:[/bold]")
        for rec in analysis.recommendations[:2]:
            details.append(f"  • {rec}")
    
    # Panel styling based on value level
    if analysis.value_level == CommitValue.CRITICAL:
        border_style = "red"
        title_style = "bold red"
    elif analysis.value_level == CommitValue.HIGH:
        border_style = "green"
        title_style = "bold green"
    elif analysis.value_level == CommitValue.MEDIUM:
        border_style = "yellow"
        title_style = "yellow"
    else:
        border_style = "blue"
        title_style = "blue"
    
    # Truncate message for title
    title_message = analysis.message.split('\n')[0]
    if len(title_message) > 50:
        title_message = title_message[:47] + "..."
    
    panel = Panel(
        "\n".join(details),
        title=f"#{rank} [{title_style}]{analysis.value_level.value}[/{title_style}] - {title_message}",
        border_style=border_style,
        padding=(1, 2)
    )
    
    console.print(panel)
    console.print()


def _display_overall_insights(analyses: List[CommitAnalysis]):
    """Display overall repository insights."""
    
    # Calculate statistics
    value_counts = {}
    risk_counts = {}
    avg_score = sum(a.significance_score for a in analyses) / len(analyses)
    
    for analysis in analyses:
        value_counts[analysis.value_level] = value_counts.get(analysis.value_level, 0) + 1
        risk_counts[analysis.risk_level] = risk_counts.get(analysis.risk_level, 0) + 1
    
    # Technical impact summary
    core_changes = sum(1 for a in analyses if a.affects_core)
    api_changes = sum(1 for a in analyses if a.affects_api)
    security_changes = sum(1 for a in analyses if a.affects_security)
    user_facing = sum(1 for a in analyses if a.user_facing)
    
    insights_table = Table(title="Repository Insights")
    insights_table.add_column("Metric", style="cyan")
    insights_table.add_column("Value", style="green")
    insights_table.add_column("Assessment", style="yellow")
    
    insights_table.add_row("Average Significance", f"{avg_score:.1f}/100", 
                          "High" if avg_score >= 60 else "Medium" if avg_score >= 30 else "Low")
    insights_table.add_row("High-Value Commits", 
                          str(value_counts.get(CommitValue.HIGH, 0) + value_counts.get(CommitValue.CRITICAL, 0)),
                          "Active development" if value_counts.get(CommitValue.HIGH, 0) > 2 else "Maintenance mode")
    insights_table.add_row("Core System Changes", str(core_changes),
                          "Significant refactoring" if core_changes > 3 else "Stable core")
    insights_table.add_row("User-Facing Changes", str(user_facing),
                          "User-focused" if user_facing > len(analyses) // 2 else "Internal focus")
    insights_table.add_row("Security-Related", str(security_changes),
                          "Security-conscious" if security_changes > 0 else "Standard development")
    
    console.print(insights_table)
    
    # Recommendations
    recommendations = []
    
    if avg_score >= 70:
        recommendations.append("[HIGH IMPACT] High-impact repository with significant ongoing development")
    elif avg_score >= 40:
        recommendations.append("[MODERATE] Moderate development activity with some valuable changes")
    else:
        recommendations.append("[MAINTENANCE] Maintenance-focused with incremental improvements")
    
    if core_changes > len(analyses) // 3:
        recommendations.append("⚠️  Frequent core changes suggest architectural evolution")
    
    if security_changes > 0:
        recommendations.append("[SECURITY] Security-conscious development practices observed")
    
    if user_facing > len(analyses) // 2:
        recommendations.append("[UX] Strong focus on user experience improvements")
    
    high_risk = sum(1 for a in analyses if a.risk_level == RiskLevel.HIGH)
    if high_risk > len(analyses) // 4:
        recommendations.append("[WARNING] Consider additional review processes for high-risk changes")
    
    if recommendations:
        console.print(f"\n[bold blue]RECOMMENDATIONS - Expert Recommendations:[/bold blue]")
        for rec in recommendations:
            console.print(f"  {rec}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        console.print("[red]Usage: python commit_expert_analyzer.py <repository_url> [limit][/red]")
        console.print("[dim]Example: python commit_expert_analyzer.py https://github.com/owner/repo 10[/dim]")
        sys.exit(1)
    
    repo_url = sys.argv[1]
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    
    asyncio.run(analyze_commits_expert(repo_url, limit))
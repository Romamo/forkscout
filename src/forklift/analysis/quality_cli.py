"""
CLI interface for code quality analysis
"""

import logging
from pathlib import Path

import click

from .code_quality_analyzer import CodeQualityAnalyzer
from .quality_report_generator import QualityReportGenerator

logger = logging.getLogger(__name__)


@click.command()
@click.option(
    "--source-path",
    default="src",
    help="Path to source code directory to analyze"
)
@click.option(
    "--output-dir",
    default=".",
    help="Directory to save analysis reports"
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["markdown", "json", "both", "summary"]),
    default="both",
    help="Output format for the report"
)
@click.option(
    "--verbose",
    is_flag=True,
    help="Enable verbose logging"
)
def analyze_code_quality(source_path: str, output_dir: str, output_format: str, verbose: bool):
    """Analyze code quality and generate technical debt report"""

    # Configure logging
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    try:
        # Initialize analyzer
        click.echo(f"🔍 Analyzing code quality in: {source_path}")
        analyzer = CodeQualityAnalyzer(source_path)

        # Run analysis
        with click.progressbar(length=100, label="Analyzing codebase") as bar:
            metrics = analyzer.analyze_codebase()
            bar.update(100)

        # Generate reports
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        report_generator = QualityReportGenerator(analyzer)

        if output_format in ["markdown", "both"]:
            markdown_path = output_path / "code_quality_report.md"
            report_generator.generate_comprehensive_report(str(markdown_path))
            click.echo(f"📄 Markdown report saved: {markdown_path}")

        if output_format in ["json", "both"]:
            json_path = output_path / "code_quality_report.json"
            report_generator.generate_json_report(str(json_path))
            click.echo(f"📊 JSON report saved: {json_path}")

        if output_format == "summary":
            summary = report_generator.generate_summary_report()
            click.echo("\n" + summary)

        # Display summary
        total_issues = sum(metrics.issue_count_by_priority.values())
        click.echo("\n✅ Analysis complete!")
        click.echo(f"   Files analyzed: {metrics.total_files}")
        click.echo(f"   Total issues: {total_issues}")
        click.echo(f"   Technical debt items: {len(analyzer.technical_debt_items)}")
        click.echo(f"   Maintainability score: {metrics.average_maintainability:.1f}/100")

        # Health assessment
        if metrics.average_maintainability >= 80 and metrics.technical_debt_score <= 1.5:
            click.echo("   Overall health: 🟢 GOOD")
        elif metrics.average_maintainability >= 60 and metrics.technical_debt_score <= 2.5:
            click.echo("   Overall health: 🟡 FAIR")
        else:
            click.echo("   Overall health: 🔴 NEEDS ATTENTION")

    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        click.echo(f"❌ Analysis failed: {e}", err=True)
        raise click.Abort() from e


if __name__ == "__main__":
    analyze_code_quality()

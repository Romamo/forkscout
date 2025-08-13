"""Command-line interface for Forklift."""

import click


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """Forklift - GitHub repository fork analysis tool."""
    pass


@cli.command()
@click.argument("repository_url")
@click.option("--config", "-c", help="Configuration file path")
@click.option("--output", "-o", help="Output file path")
@click.option("--auto-pr", is_flag=True, help="Automatically create pull requests")
@click.option("--min-score", type=int, default=70, help="Minimum score for auto PR")
def analyze(repository_url, config, output, auto_pr, min_score):
    """Analyze a repository and its forks."""
    click.echo(f"Analyzing repository: {repository_url}")
    # Implementation will be added in later tasks


if __name__ == "__main__":
    cli()

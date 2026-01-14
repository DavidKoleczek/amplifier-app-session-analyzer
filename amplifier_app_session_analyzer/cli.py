"""CLI entry point for the Amplifier Session Analyzer."""

from pathlib import Path

import click
from rich.console import Console

from . import __version__
from .constants import SEMANTIC_CONTEXT_WINDOW
from .metrics import calculate_metrics, calculate_overlap_metrics
from .parser import collect_autonomy_periods
from .report import generate_report
from .report_html import generate_html_report
from .report_markdown import generate_markdown_report
from .time_scope import parse_time_scope

console = Console()

# Available features that can be enabled
AVAILABLE_FEATURES = ["semantic_categories"]


def validate_features(
    ctx: click.Context, param: click.Parameter, value: tuple[str, ...]
) -> list[str]:
    """Validate that requested features are available."""
    features = list(value)
    for feature in features:
        if feature not in AVAILABLE_FEATURES:
            raise click.BadParameter(
                f"Unknown feature '{feature}'. Available: {', '.join(AVAILABLE_FEATURES)}"
            )
    return features


@click.command()
@click.option(
    "--time-scope",
    "-t",
    default="default",
    help=(
        "Time period to analyze. Options: "
        "'default' (last full week), "
        "'2026/01/12' (single day), "
        "'2026/01/10 - 2026/01/12' (date range)"
    ),
)
@click.option(
    "--timezone",
    "-z",
    default="America/New_York",
    help="IANA timezone for interpreting dates (default: America/New_York)",
)
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["md", "html", "pdf"], case_sensitive=False),
    default="md",
    help="Output format: 'md' (Markdown, default), 'html', or 'pdf'",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    default=None,
    help="Output file path (default: autonomy-report.<format> based on format)",
)
@click.option(
    "--sessions-path",
    "-p",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Path to Amplifier projects directory (default: ~/.amplifier/projects)",
)
@click.option(
    "--features",
    "-F",
    multiple=True,
    callback=validate_features,
    help=(
        "Enable optional features. Can be specified multiple times. "
        f"Available: {', '.join(AVAILABLE_FEATURES)}"
    ),
)
@click.option(
    "--exclude-project",
    "-x",
    "exclude_projects",
    multiple=True,
    help=(
        "Exclude sessions from projects matching this pattern. "
        "Can be specified multiple times. Matches against project directory names. "
        "Example: -x 'session-analyzer' excludes all projects containing 'session-analyzer'"
    ),
)
@click.version_option(version=__version__, prog_name="amplifier-session-analyzer")
def main(
    time_scope: str,
    timezone: str,
    output_format: str,
    output: Path | None,
    sessions_path: Path | None,
    features: list[str],
    exclude_projects: tuple[str, ...],
) -> None:
    """Analyze Amplifier session logs and generate autonomy reports.

    Measures how long the AI agent works autonomously after receiving
    a user message, until it returns control to the user.

    Use --features semantic_categories to enable LLM-based prompt classification.
    """
    console.print(f"[bold]Amplifier Session Analyzer[/bold] v{__version__}")
    console.print()

    # Check if semantic analysis is requested
    enable_semantic = "semantic_categories" in features

    if enable_semantic:
        # Check if amplifier_foundation is available
        try:
            from amplifier_foundation import load_bundle  # noqa: F401
        except ImportError:
            console.print(
                "[red]Error:[/red] amplifier-foundation is required but not installed."
            )
            console.print(
                "[dim]Reinstall with: uv tool install git+https://github.com/DavidKoleczek/amplifier-app-session-analyzer@main[/dim]"
            )
            raise SystemExit(1)

    # Determine output path based on format if not specified
    if output is None:
        output = Path(f"autonomy-report.{output_format}")

    # Parse time scope
    try:
        scope = parse_time_scope(time_scope, timezone)
    except ValueError as e:
        console.print(f"[red]Error parsing time scope:[/red] {e}")
        raise SystemExit(1)

    console.print(f"[dim]Time period:[/dim] {scope.display_range()}")
    if sessions_path:
        console.print(f"[dim]Sessions path:[/dim] {sessions_path}")
    if exclude_projects:
        console.print(f"[dim]Excluding projects:[/dim] {', '.join(exclude_projects)}")
    if enable_semantic:
        console.print("[dim]Features:[/dim] semantic_categories")
    console.print()

    # Convert exclude_projects tuple to list
    exclude_list = list(exclude_projects) if exclude_projects else None

    # Collect autonomy periods
    with console.status("[bold blue]Scanning session logs..."):
        autonomy_data = collect_autonomy_periods(
            scope, projects_dir=sessions_path, exclude_projects=exclude_list
        )

    console.print(
        f"[dim]Found {autonomy_data.total_prompts_sent} prompts, "
        f"{len(autonomy_data.periods)} completed periods[/dim]"
    )

    # Calculate metrics
    metrics = calculate_metrics(autonomy_data.periods, autonomy_data.total_prompts_sent)
    overlap_metrics = calculate_overlap_metrics(autonomy_data.periods)

    # Semantic analysis (if enabled)
    semantic_metrics = None
    if enable_semantic:
        semantic_metrics = _run_semantic_analysis(
            scope, sessions_path, exclude_list, console
        )

    if metrics is None:
        console.print(
            "[yellow]No session data found for the specified time period.[/yellow]"
        )
    else:
        console.print()
        console.print("[bold]Summary:[/bold]")
        console.print(
            f"  Average autonomy: [cyan]{metrics.mean_minutes:.1f} minutes[/cyan]"
        )
        console.print(
            f"  Median autonomy:  [cyan]{metrics.median_minutes:.1f} minutes[/cyan]"
        )
        console.print(f"  Total prompts:    {metrics.total_prompts_sent}")
        console.print(f"  Completed periods: {metrics.completed_periods}")
        console.print(f"  Unique sessions:  {metrics.unique_sessions}")
        console.print()
        console.print("[bold]Session Overlaps:[/bold]")
        console.print(f"  Overlapping starts:    {overlap_metrics.overlap_count}")
        console.print(
            f"  Max parallel sessions: {overlap_metrics.max_parallel_sessions}"
        )

        # Print semantic summary if available
        if semantic_metrics:
            _print_semantic_summary(semantic_metrics, console)

    # Generate report
    console.print()
    if output_format == "pdf":
        with console.status("[bold blue]Generating PDF report..."):
            generate_report(metrics, overlap_metrics, scope, output, semantic_metrics)
    elif output_format == "html":
        with console.status("[bold blue]Generating HTML report..."):
            generate_html_report(
                metrics, overlap_metrics, scope, output, semantic_metrics
            )
    else:
        with console.status("[bold blue]Generating Markdown report..."):
            generate_markdown_report(
                metrics, overlap_metrics, scope, output, semantic_metrics
            )

    console.print(f"[green]Report saved to:[/green] {output}")


def _run_semantic_analysis(
    scope,
    sessions_path: Path | None,
    exclude_projects: list[str] | None,
    console: Console,
):
    """Run semantic analysis on prompts."""
    from .classifier import ClassifierConfig, classify_prompts_sync
    from .semantic import collect_prompts_with_context
    from .semantic_metrics import calculate_semantic_metrics

    # Collect prompts with context
    with console.status("[bold blue]Extracting prompts with context..."):
        prompts_with_context = collect_prompts_with_context(
            scope,
            projects_dir=sessions_path,
            context_window=SEMANTIC_CONTEXT_WINDOW,
            exclude_projects=exclude_projects,
        )

    if not prompts_with_context:
        console.print("[yellow]No prompts found for semantic analysis.[/yellow]")
        return None

    console.print(f"[dim]Found {len(prompts_with_context)} prompts to classify[/dim]")

    # Classify prompts
    config = ClassifierConfig()

    def progress_callback(current: int, total: int) -> None:
        console.print(
            f"[dim]Classified {current}/{total} prompts...[/dim]",
            end="\r",
        )

    console.print("[bold blue]Classifying prompts using Amplifier...[/bold blue]")
    classified = classify_prompts_sync(prompts_with_context, config, progress_callback)
    console.print()  # Clear the progress line

    # Calculate semantic metrics
    return calculate_semantic_metrics(classified)


def _print_semantic_summary(semantic_metrics, console: Console) -> None:
    """Print semantic analysis summary to console."""
    console.print()
    console.print("[bold]Semantic Analysis:[/bold]")
    console.print(f"  Total prompts classified: {semantic_metrics.total_prompts}")
    console.print(
        f"  Multi-category prompts: {semantic_metrics.multi_category_percentage:.1f}%"
    )
    console.print()
    console.print("[bold]Top Categories:[/bold]")
    for stat in semantic_metrics.category_stats[:5]:
        console.print(
            f"  {stat.category}: [cyan]{stat.count}[/cyan] ({stat.percentage:.1f}%)"
        )

    if semantic_metrics.wildcard_categories:
        console.print()
        console.print("[bold]Custom Categories Discovered:[/bold]")
        for cat, count in sorted(
            semantic_metrics.wildcard_categories.items(), key=lambda x: -x[1]
        )[:5]:
            console.print(f"  {cat}: [cyan]{count}[/cyan]")


if __name__ == "__main__":
    main()

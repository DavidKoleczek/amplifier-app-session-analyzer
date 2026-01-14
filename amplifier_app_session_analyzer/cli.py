"""CLI entry point for the Amplifier Session Analyzer."""

from pathlib import Path

import click
from rich.console import Console

from . import __version__
from .metrics import calculate_metrics, calculate_overlap_metrics
from .parser import collect_autonomy_periods
from .report import generate_report
from .report_markdown import generate_markdown_report
from .time_scope import parse_time_scope

console = Console()


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
    type=click.Choice(["md", "pdf"], case_sensitive=False),
    default="md",
    help="Output format: 'md' (Markdown, default) or 'pdf'",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    default=None,
    help="Output file path (default: autonomy-report.md or .pdf based on format)",
)
@click.option(
    "--sessions-path",
    "-p",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Path to Amplifier projects directory (default: ~/.amplifier/projects)",
)
@click.version_option(version=__version__, prog_name="amplifier-session-analyzer")
def main(
    time_scope: str,
    timezone: str,
    output_format: str,
    output: Path | None,
    sessions_path: Path | None,
) -> None:
    """Analyze Amplifier session logs and generate autonomy reports.

    Measures how long the AI agent works autonomously after receiving
    a user message, until it returns control to the user.
    """
    console.print(f"[bold]Amplifier Session Analyzer[/bold] v{__version__}")
    console.print()

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
    console.print()

    # Collect autonomy periods
    with console.status("[bold blue]Scanning session logs..."):
        periods = collect_autonomy_periods(scope, projects_dir=sessions_path)

    console.print(f"[dim]Found {len(periods)} autonomy periods[/dim]")

    # Calculate metrics
    metrics = calculate_metrics(periods)
    overlap_metrics = calculate_overlap_metrics(periods)

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
        console.print(f"  Total periods:    {metrics.count}")
        console.print(f"  Unique sessions:  {metrics.unique_sessions}")
        console.print()
        console.print("[bold]Session Overlaps:[/bold]")
        console.print(f"  Overlapping starts:    {overlap_metrics.overlap_count}")
        console.print(
            f"  Max parallel sessions: {overlap_metrics.max_parallel_sessions}"
        )

    # Generate report
    console.print()
    if output_format == "pdf":
        with console.status("[bold blue]Generating PDF report..."):
            generate_report(metrics, overlap_metrics, scope, output)
    else:
        with console.status("[bold blue]Generating Markdown report..."):
            generate_markdown_report(metrics, overlap_metrics, scope, output)

    console.print(f"[green]Report saved to:[/green] {output}")


if __name__ == "__main__":
    main()

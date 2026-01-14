"""Markdown report generation.

Generates clean Markdown reports for autonomy metrics.
"""

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from typing import TYPE_CHECKING

from . import constants as C
from .metrics import AutonomyMetrics, OverlapMetrics
from .time_scope import TimeScope

if TYPE_CHECKING:
    from .semantic_metrics import SemanticMetrics


def format_duration(seconds: float) -> str:
    """Format a duration in seconds to a human-readable string."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        return f"{seconds / 60:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"


def generate_markdown_report(
    metrics: AutonomyMetrics | None,
    overlap_metrics: OverlapMetrics | None,
    time_scope: TimeScope,
    output_path: Path,
    semantic_metrics: "SemanticMetrics | None" = None,
) -> None:
    """Generate a Markdown report for autonomy and overlap metrics.

    Args:
        metrics: Calculated autonomy metrics (or None if no data)
        overlap_metrics: Calculated overlap metrics (or None if no data)
        time_scope: The time scope that was analyzed
        output_path: Path to write the Markdown file
        semantic_metrics: Optional semantic analysis metrics
    """
    lines: list[str] = []

    # Title
    lines.append(f"# {C.REPORT_TITLE}")
    lines.append("")

    # Report metadata
    tz = ZoneInfo(time_scope.timezone)
    generated_at = datetime.now(tz).strftime("%Y-%m-%d %H:%M %Z")
    lines.append(f"**{C.LABEL_GENERATED}** {generated_at}")
    lines.append("")
    lines.append(f"**{C.LABEL_TIME_PERIOD}** {time_scope.display_range()}")
    lines.append("")

    # Disclaimer section
    lines.append(f"> **Note:** {C.DISCLAIMER_TEXT}")
    lines.append("")

    if metrics is None:
        lines.append(C.NO_DATA_MESSAGE)
    else:
        # Main metric highlight
        lines.append(f"## {C.HEADING_AVERAGE_AUTONOMY}")
        lines.append("")
        lines.append(C.DESC_AVERAGE_AUTONOMY)
        lines.append("")
        lines.append(f"### {metrics.mean_minutes:.1f} minutes")
        lines.append("")

        # Summary statistics table
        lines.append(f"## {C.HEADING_SUMMARY_STATS}")
        lines.append("")
        lines.append(C.DESC_SUMMARY_STATS)
        lines.append("")

        lines.append(f"| {C.LABEL_METRIC} | {C.LABEL_VALUE} |")
        lines.append("|---|---|")
        lines.append(f"| {C.LABEL_TOTAL_PROMPTS} | {metrics.total_prompts_sent} |")
        lines.append(f"| Completed Periods | {metrics.completed_periods} |")
        lines.append(f"| {C.LABEL_UNIQUE_SESSIONS} | {metrics.unique_sessions} |")
        lines.append(
            f"| {C.LABEL_MEAN_DURATION} | {format_duration(metrics.mean_seconds)} |"
        )
        lines.append(
            f"| {C.LABEL_MEDIAN_DURATION} | {format_duration(metrics.median_seconds)} |"
        )
        lines.append(
            f"| {C.LABEL_MAX_DURATION} | {format_duration(metrics.max_seconds)} |"
        )
        lines.append(
            f"| {C.LABEL_TOTAL_TIME} | {format_duration(metrics.total_seconds)} |"
        )
        if metrics.stdev_seconds is not None:
            lines.append(
                f"| {C.LABEL_STD_DEVIATION} | {format_duration(metrics.stdev_seconds)} |"
            )
        lines.append("")

        # Distribution table
        lines.append(f"## {C.HEADING_DISTRIBUTION}")
        lines.append("")
        lines.append(C.DESC_DISTRIBUTION)
        lines.append("")

        total = metrics.completed_periods
        lines.append(
            f"| {C.LABEL_DURATION_RANGE} | {C.LABEL_COUNT} | {C.LABEL_PERCENTAGE} |"
        )
        lines.append("|---|---|---|")
        lines.append(
            f"| {C.LABEL_UNDER_1MIN} | {metrics.under_1min} | {100 * metrics.under_1min / total:.0f}% |"
        )
        lines.append(
            f"| {C.LABEL_1_5MIN} | {metrics.between_1_5min} | {100 * metrics.between_1_5min / total:.0f}% |"
        )
        lines.append(
            f"| {C.LABEL_5_15MIN} | {metrics.between_5_15min} | {100 * metrics.between_5_15min / total:.0f}% |"
        )
        lines.append(
            f"| {C.LABEL_OVER_15MIN} | {metrics.over_15min} | {100 * metrics.over_15min / total:.0f}% |"
        )
        lines.append("")

        # Overlap metrics section
        if overlap_metrics is not None:
            lines.append(f"## {C.HEADING_OVERLAP}")
            lines.append("")
            lines.append(C.DESC_OVERLAP)
            lines.append("")

            lines.append(f"| {C.LABEL_METRIC} | {C.LABEL_VALUE} |")
            lines.append("|---|---|")
            lines.append(
                f"| {C.LABEL_OVERLAPPING_STARTS} | {overlap_metrics.overlap_count} |"
            )
            lines.append(
                f"| {C.LABEL_MAX_PARALLEL} | {overlap_metrics.max_parallel_sessions} |"
            )
            lines.append("")

    # Semantic analysis section (if available)
    if semantic_metrics is not None:
        lines.append("## Semantic Analysis")
        lines.append("")
        lines.append(
            "Classification of user prompts into semantic categories using LLM-based analysis. "
            "Each prompt is assigned 1-3 categories based on its intent and surrounding context."
        )
        lines.append("")

        # Summary stats
        lines.append("### Classification Summary")
        lines.append("")
        lines.append("| Metric | Value |")
        lines.append("|---|---|")
        lines.append(f"| Total Prompts Classified | {semantic_metrics.total_prompts} |")
        lines.append(
            f"| Multi-Category Prompts | {semantic_metrics.multi_category_count} "
            f"({semantic_metrics.multi_category_percentage:.1f}%) |"
        )
        lines.append("")

        # Category distribution
        lines.append("### Category Distribution")
        lines.append("")
        lines.append("| Category | Count | Percentage |")
        lines.append("|---|---|---|")
        for stat in semantic_metrics.category_stats:
            lines.append(f"| {stat.category} | {stat.count} | {stat.percentage:.1f}% |")
        lines.append("")

        # Custom categories discovered
        if semantic_metrics.wildcard_categories:
            lines.append("### Custom Categories Discovered")
            lines.append("")
            lines.append(
                "These are categories that didn't fit the predefined taxonomy "
                "and were assigned by the classifier:"
            )
            lines.append("")
            lines.append("| Custom Category | Count |")
            lines.append("|---|---|")
            for cat, count in sorted(
                semantic_metrics.wildcard_categories.items(), key=lambda x: -x[1]
            ):
                lines.append(f"| {cat} | {count} |")
            lines.append("")

        # Common combinations
        if semantic_metrics.common_combinations:
            lines.append("### Common Category Combinations")
            lines.append("")
            lines.append(
                "Most frequently occurring combinations of categories assigned to prompts:"
            )
            lines.append("")
            lines.append("| Categories | Count |")
            lines.append("|---|---|")
            for combo, count in semantic_metrics.common_combinations[:10]:
                combo_str = ", ".join(combo)
                lines.append(f"| {combo_str} | {count} |")
            lines.append("")

    # Methodology section
    lines.append(f"## {C.HEADING_METHODOLOGY}")
    lines.append("")
    lines.append(C.METHODOLOGY_DATA_SOURCE)

    # Write the file
    output_path.write_text("\n".join(lines))

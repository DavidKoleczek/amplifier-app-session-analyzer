"""PDF report generation.

Generates clean, simple PDF reports for autonomy metrics.
"""

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from . import constants as C
from .metrics import AutonomyMetrics, OverlapMetrics
from .time_scope import TimeScope


def format_duration(seconds: float) -> str:
    """Format a duration in seconds to a human-readable string."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        return f"{seconds / 60:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"


def generate_report(
    metrics: AutonomyMetrics | None,
    overlap_metrics: OverlapMetrics | None,
    time_scope: TimeScope,
    output_path: Path,
    semantic_metrics: object | None = None,
) -> None:
    """Generate a PDF report for autonomy and overlap metrics.

    Args:
        metrics: Calculated autonomy metrics (or None if no data)
        overlap_metrics: Calculated overlap metrics (or None if no data)
        time_scope: The time scope that was analyzed
        output_path: Path to write the PDF
        semantic_metrics: Optional semantic analysis metrics (not yet supported in PDF)
    """
    # Note: semantic_metrics is accepted but not yet rendered in PDF format
    # Use markdown format (--format md) for full semantic analysis output
    _ = semantic_metrics  # Silence unused parameter warning
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        rightMargin=0.5 * inch,
        leftMargin=0.5 * inch,
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch,
    )

    styles = getSampleStyleSheet()
    title_style = styles["Heading1"]
    heading_style = styles["Heading2"]
    normal_style = styles["Normal"]

    # Custom styles
    metric_value_style = ParagraphStyle(
        "MetricValue",
        parent=normal_style,
        fontSize=24,
        leading=28,
        textColor=colors.HexColor("#2563eb"),
        alignment=1,  # Center
    )

    elements: list = []

    # Title
    elements.append(Paragraph(C.REPORT_TITLE, title_style))
    elements.append(Spacer(1, 0.1 * inch))

    # Report metadata
    tz = ZoneInfo(time_scope.timezone)
    generated_at = datetime.now(tz).strftime("%Y-%m-%d %H:%M %Z")
    elements.append(
        Paragraph(f"<b>{C.LABEL_GENERATED}</b> {generated_at}", normal_style)
    )
    elements.append(
        Paragraph(
            f"<b>{C.LABEL_TIME_PERIOD}</b> {time_scope.display_range()}", normal_style
        )
    )
    elements.append(Spacer(1, 0.15 * inch))

    # Disclaimer section
    disclaimer_html = f"<b>Important:</b> {C.DISCLAIMER_TEXT}"
    elements.append(Paragraph(disclaimer_html, normal_style))
    elements.append(Spacer(1, 0.15 * inch))

    if metrics is None:
        elements.append(Paragraph(C.NO_DATA_MESSAGE, normal_style))
    else:
        # Main metric highlight
        elements.append(Paragraph(C.HEADING_AVERAGE_AUTONOMY, heading_style))
        elements.append(Paragraph(C.DESC_AVERAGE_AUTONOMY, normal_style))
        elements.append(
            Paragraph(
                f"{metrics.mean_minutes:.1f} minutes",
                metric_value_style,
            )
        )
        elements.append(Spacer(1, 0.15 * inch))

        # Summary statistics table
        elements.append(Paragraph(C.HEADING_SUMMARY_STATS, heading_style))
        elements.append(Paragraph(C.DESC_SUMMARY_STATS, normal_style))

        stats_data = [
            [C.LABEL_METRIC, C.LABEL_VALUE],
            [C.LABEL_TOTAL_PROMPTS, str(metrics.total_prompts_sent)],
            ["Completed Periods", str(metrics.completed_periods)],
            [C.LABEL_UNIQUE_SESSIONS, str(metrics.unique_sessions)],
            [C.LABEL_MEAN_DURATION, format_duration(metrics.mean_seconds)],
            [C.LABEL_MEDIAN_DURATION, format_duration(metrics.median_seconds)],
            [C.LABEL_MAX_DURATION, format_duration(metrics.max_seconds)],
            [C.LABEL_TOTAL_TIME, format_duration(metrics.total_seconds)],
        ]

        if metrics.stdev_seconds is not None:
            stats_data.append(
                [C.LABEL_STD_DEVIATION, format_duration(metrics.stdev_seconds)]
            )

        stats_table = Table(stats_data, colWidths=[4 * inch, 2.5 * inch])
        stats_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f3f4f6")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#374151")),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 1), (-1, -1), 8),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )
        )
        elements.append(stats_table)
        elements.append(Spacer(1, 0.2 * inch))

        # Distribution table
        elements.append(Paragraph(C.HEADING_DISTRIBUTION, heading_style))
        elements.append(Paragraph(C.DESC_DISTRIBUTION, normal_style))

        total = metrics.completed_periods
        dist_data = [
            [C.LABEL_DURATION_RANGE, C.LABEL_COUNT, C.LABEL_PERCENTAGE],
            [
                C.LABEL_UNDER_1MIN,
                str(metrics.under_1min),
                f"{100 * metrics.under_1min / total:.0f}%",
            ],
            [
                C.LABEL_1_5MIN,
                str(metrics.between_1_5min),
                f"{100 * metrics.between_1_5min / total:.0f}%",
            ],
            [
                C.LABEL_5_15MIN,
                str(metrics.between_5_15min),
                f"{100 * metrics.between_5_15min / total:.0f}%",
            ],
            [
                C.LABEL_OVER_15MIN,
                str(metrics.over_15min),
                f"{100 * metrics.over_15min / total:.0f}%",
            ],
        ]

        dist_table = Table(dist_data, colWidths=[3.5 * inch, 1.5 * inch, 1.5 * inch])
        dist_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f3f4f6")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#374151")),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 1), (-1, -1), 8),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
                    ("ALIGN", (1, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )
        )
        elements.append(dist_table)
        elements.append(Spacer(1, 0.2 * inch))

        # Overlap metrics section
        if overlap_metrics is not None:
            elements.append(Paragraph(C.HEADING_OVERLAP, heading_style))
            elements.append(Paragraph(C.DESC_OVERLAP, normal_style))

            overlap_data = [
                [C.LABEL_METRIC, C.LABEL_VALUE],
                [C.LABEL_OVERLAPPING_STARTS, str(overlap_metrics.overlap_count)],
                [C.LABEL_MAX_PARALLEL, str(overlap_metrics.max_parallel_sessions)],
            ]

            overlap_table = Table(overlap_data, colWidths=[4 * inch, 2.5 * inch])
            overlap_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f3f4f6")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#374151")),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, -1), 10),
                        ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                        ("TOPPADDING", (0, 0), (-1, -1), 8),
                        ("BOTTOMPADDING", (0, 1), (-1, -1), 8),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ]
                )
            )
            elements.append(overlap_table)
            elements.append(Spacer(1, 0.2 * inch))

    # Methodology section
    elements.append(Paragraph(C.HEADING_METHODOLOGY, heading_style))
    elements.append(Paragraph(C.METHODOLOGY_DATA_SOURCE, normal_style))

    # Build the PDF
    doc.build(elements)

"""HTML report generation.

Generates styled HTML reports for session analysis with embedded CSS.
"""

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from . import constants as C
from .metrics import AutonomyMetrics, OverlapMetrics
from .time_scope import TimeScope

if TYPE_CHECKING:
    from .semantic_metrics import SemanticMetrics


def format_duration(seconds: float) -> str:
    """Format seconds into a readable duration string."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        return f"{seconds / 60:.1f}m"
    else:
        return f"{seconds / 3600:.1f}h"


# CSS styles using custom properties and modern CSS
HTML_STYLES = """
:root {
    --primary: #2563eb;
    --primary-light: #3b82f6;
    --success: #10b981;
    --warning: #f59e0b;
    --danger: #ef4444;
    --background: #ffffff;
    --surface: #f3f4f6;
    --surface-hover: #e5e7eb;
    --text: #1f2937;
    --text-muted: #6b7280;
    --border: #e5e7eb;
    --shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
    --radius: 8px;
    --radius-lg: 12px;
}

* {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
    background: var(--surface);
    color: var(--text);
    line-height: 1.6;
    padding: 2rem;
}

.container {
    max-width: 1200px;
    margin: 0 auto;
}

header {
    background: var(--background);
    border-radius: var(--radius-lg);
    padding: 2rem;
    margin-bottom: 2rem;
    box-shadow: var(--shadow);
}

header h1 {
    font-size: 1.75rem;
    font-weight: 700;
    color: var(--text);
    margin-bottom: 0.5rem;
}

header .meta {
    color: var(--text-muted);
    font-size: 0.875rem;
}

header .meta span {
    margin-right: 1.5rem;
}

.note {
    background: #fef3c7;
    border-left: 4px solid var(--warning);
    padding: 1rem;
    margin: 1.5rem 0;
    border-radius: 0 var(--radius) var(--radius) 0;
    font-size: 0.875rem;
    color: #92400e;
}

.hero-stat {
    background: linear-gradient(135deg, var(--primary) 0%, var(--primary-light) 100%);
    color: white;
    border-radius: var(--radius-lg);
    padding: 2rem;
    margin-bottom: 2rem;
    text-align: center;
    box-shadow: var(--shadow-lg);
}

.hero-stat .value {
    font-size: 3.5rem;
    font-weight: 700;
    line-height: 1;
    margin-bottom: 0.5rem;
}

.hero-stat .label {
    font-size: 1rem;
    opacity: 0.9;
}

.grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 1.5rem;
    margin-bottom: 2rem;
}

.card {
    background: var(--background);
    border-radius: var(--radius-lg);
    padding: 1.5rem;
    box-shadow: var(--shadow);
    transition: box-shadow 0.2s ease, transform 0.2s ease;
}

.card:hover {
    box-shadow: var(--shadow-lg);
    transform: translateY(-2px);
}

.card h2 {
    font-size: 1.125rem;
    font-weight: 600;
    color: var(--text);
    margin-bottom: 1rem;
    padding-bottom: 0.75rem;
    border-bottom: 2px solid var(--surface);
}

.card h3 {
    font-size: 1rem;
    font-weight: 600;
    color: var(--text);
    margin: 1.5rem 0 0.75rem 0;
}

.card p {
    color: var(--text-muted);
    font-size: 0.875rem;
    margin-bottom: 1rem;
}

table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.875rem;
}

th, td {
    padding: 0.75rem;
    text-align: left;
    border-bottom: 1px solid var(--border);
}

th {
    font-weight: 600;
    color: var(--text-muted);
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

tr:hover {
    background: var(--surface);
}

tr:last-child td {
    border-bottom: none;
}

.stat-row {
    display: flex;
    justify-content: space-between;
    padding: 0.75rem 0;
    border-bottom: 1px solid var(--border);
}

.stat-row:last-child {
    border-bottom: none;
}

.stat-row .label {
    color: var(--text-muted);
}

.stat-row .value {
    font-weight: 600;
    color: var(--text);
}

.badge {
    display: inline-block;
    padding: 0.25rem 0.75rem;
    border-radius: 9999px;
    font-size: 0.75rem;
    font-weight: 500;
}

.badge-primary {
    background: #dbeafe;
    color: #1e40af;
}

.badge-success {
    background: #d1fae5;
    color: #065f46;
}

.badge-warning {
    background: #fef3c7;
    color: #92400e;
}

.progress-bar {
    height: 8px;
    background: var(--surface);
    border-radius: 4px;
    overflow: hidden;
    margin-top: 0.5rem;
}

.progress-bar .fill {
    height: 100%;
    background: var(--primary);
    border-radius: 4px;
    transition: width 0.3s ease;
}

.category-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.75rem 0;
    border-bottom: 1px solid var(--border);
}

.category-item:last-child {
    border-bottom: none;
}

.category-name {
    font-weight: 500;
}

.category-stats {
    display: flex;
    gap: 1rem;
    font-size: 0.875rem;
    color: var(--text-muted);
}

.category-count {
    font-weight: 600;
    color: var(--primary);
}

footer {
    background: var(--background);
    border-radius: var(--radius-lg);
    padding: 1.5rem;
    margin-top: 2rem;
    box-shadow: var(--shadow);
}

footer h2 {
    font-size: 1rem;
    font-weight: 600;
    margin-bottom: 0.75rem;
}

footer p {
    color: var(--text-muted);
    font-size: 0.875rem;
    line-height: 1.7;
}

@media (max-width: 640px) {
    body {
        padding: 1rem;
    }
    
    .hero-stat .value {
        font-size: 2.5rem;
    }
    
    .grid {
        grid-template-columns: 1fr;
    }
}
"""


def generate_html_report(
    metrics: AutonomyMetrics | None,
    overlap_metrics: OverlapMetrics | None,
    time_scope: TimeScope,
    output_path: Path,
    semantic_metrics: "SemanticMetrics | None" = None,
) -> None:
    """Generate an HTML report for autonomy and overlap metrics.

    Args:
        metrics: Calculated autonomy metrics (or None if no data)
        overlap_metrics: Calculated overlap metrics (or None if no data)
        time_scope: The time scope that was analyzed
        output_path: Path to write the HTML file
        semantic_metrics: Optional semantic analysis metrics
    """
    generated_time = datetime.now().strftime("%Y-%m-%d %H:%M %Z").strip()
    time_range = time_scope.display_range()

    html_parts = [
        "<!DOCTYPE html>",
        '<html lang="en">',
        "<head>",
        '    <meta charset="UTF-8">',
        '    <meta name="viewport" content="width=device-width, initial-scale=1.0">',
        "    <title>Amplifier Session Analysis Report</title>",
        f"    <style>{HTML_STYLES}</style>",
        "</head>",
        "<body>",
        '    <div class="container">',
        # Header
        "        <header>",
        "            <h1>Amplifier Session Analysis Report</h1>",
        '            <div class="meta">',
        f"                <span><strong>Generated:</strong> {generated_time}</span>",
        f"                <span><strong>Period:</strong> {time_range}</span>",
        "            </div>",
        '            <div class="note">',
        "                <strong>Note:</strong> This report provides descriptive statistics only. "
        "The data may not reflect all Amplifier usage over the time period.",
        "            </div>",
        "        </header>",
    ]

    if metrics is None:
        html_parts.extend(
            [
                '        <div class="card">',
                "            <h2>No Data Available</h2>",
                "            <p>No session data was found for the specified time period.</p>",
                "        </div>",
            ]
        )
    else:
        # Hero stat - Average Autonomy
        html_parts.extend(
            [
                '        <div class="hero-stat">',
                f'            <div class="value">{metrics.mean_minutes:.1f} min</div>',
                '            <div class="label">Average Autonomy Duration</div>',
                "        </div>",
                "",
                '        <div class="grid">',
            ]
        )

        # Summary Statistics Card
        html_parts.extend(
            [
                '            <div class="card">',
                "                <h2>Summary Statistics</h2>",
                "                <p>Key statistics about autonomous work periods.</p>",
                '                <div class="stat-row">',
                '                    <span class="label">Total Prompts Sent</span>',
                f'                    <span class="value">{metrics.total_prompts_sent}</span>',
                "                </div>",
                '                <div class="stat-row">',
                '                    <span class="label">Completed Periods</span>',
                f'                    <span class="value">{metrics.completed_periods}</span>',
                "                </div>",
                '                <div class="stat-row">',
                '                    <span class="label">Unique Sessions</span>',
                f'                    <span class="value">{metrics.unique_sessions}</span>',
                "                </div>",
                '                <div class="stat-row">',
                '                    <span class="label">Mean Duration</span>',
                f'                    <span class="value">{format_duration(metrics.mean_seconds)}</span>',
                "                </div>",
                '                <div class="stat-row">',
                '                    <span class="label">Median Duration</span>',
                f'                    <span class="value">{format_duration(metrics.median_seconds)}</span>',
                "                </div>",
                '                <div class="stat-row">',
                '                    <span class="label">Max Duration</span>',
                f'                    <span class="value">{format_duration(metrics.max_seconds)}</span>',
                "                </div>",
                '                <div class="stat-row">',
                '                    <span class="label">Total Autonomous Time</span>',
                f'                    <span class="value">{format_duration(metrics.total_seconds)}</span>',
                "                </div>",
                '                <div class="stat-row">',
                '                    <span class="label">Std Deviation</span>',
                f'                    <span class="value">{format_duration(metrics.stdev_seconds) if metrics.stdev_seconds else "N/A"}</span>',
                "                </div>",
                "            </div>",
            ]
        )

        # Duration Distribution Card
        html_parts.extend(
            [
                '            <div class="card">',
                "                <h2>Duration Distribution</h2>",
                "                <p>Breakdown of autonomy periods by duration.</p>",
                "                <table>",
                "                    <thead>",
                "                        <tr>",
                "                            <th>Duration Range</th>",
                "                            <th>Count</th>",
                "                            <th>Percentage</th>",
                "                        </tr>",
                "                    </thead>",
                "                    <tbody>",
            ]
        )

        # Duration distribution buckets
        buckets = [
            ("Under 1 minute", metrics.under_1min),
            ("1-5 minutes", metrics.between_1_5min),
            ("5-15 minutes", metrics.between_5_15min),
            ("Over 15 minutes", metrics.over_15min),
        ]
        for bucket_name, count in buckets:
            pct = (
                (count / metrics.completed_periods * 100)
                if metrics.completed_periods > 0
                else 0
            )
            html_parts.extend(
                [
                    "                        <tr>",
                    f"                            <td>{bucket_name}</td>",
                    f"                            <td>{count}</td>",
                    f"                            <td>{pct:.0f}%</td>",
                    "                        </tr>",
                ]
            )

        html_parts.extend(
            [
                "                    </tbody>",
                "                </table>",
                "            </div>",
            ]
        )

        # Session Overlap Card
        if overlap_metrics:
            html_parts.extend(
                [
                    '            <div class="card">',
                    "                <h2>Session Overlap Analysis</h2>",
                    "                <p>Concurrent session usage metrics.</p>",
                    '                <div class="stat-row">',
                    '                    <span class="label">Overlapping Session Starts</span>',
                    f'                    <span class="value">{overlap_metrics.overlap_count}</span>',
                    "                </div>",
                    '                <div class="stat-row">',
                    '                    <span class="label">Max Parallel Sessions</span>',
                    f'                    <span class="value">{overlap_metrics.max_parallel_sessions}</span>',
                    "                </div>",
                    "            </div>",
                ]
            )

        html_parts.append("        </div>")  # Close grid

        # Semantic Analysis Section
        if semantic_metrics:
            html_parts.extend(
                [
                    "",
                    '        <div class="grid">',
                    '            <div class="card">',
                    "                <h2>Semantic Analysis</h2>",
                    "                <p>LLM-based classification of user prompts into semantic categories.</p>",
                    "",
                    "                <h3>Classification Summary</h3>",
                    '                <div class="stat-row">',
                    '                    <span class="label">Total Prompts Classified</span>',
                    f'                    <span class="value">{semantic_metrics.total_prompts}</span>',
                    "                </div>",
                    '                <div class="stat-row">',
                    '                    <span class="label">Multi-Category Prompts</span>',
                    f'                    <span class="value">{semantic_metrics.multi_category_count} ({semantic_metrics.multi_category_percentage:.1f}%)</span>',
                    "                </div>",
                    "            </div>",
                    "",
                    '            <div class="card">',
                    "                <h2>Category Distribution</h2>",
                    "                <p>Frequency of each semantic category.</p>",
                ]
            )

            for stat in semantic_metrics.category_stats:
                pct = stat.percentage
                html_parts.extend(
                    [
                        '                <div class="category-item">',
                        f'                    <span class="category-name">{stat.category}</span>',
                        '                    <div class="category-stats">',
                        f'                        <span class="category-count">{stat.count}</span>',
                        f"                        <span>{pct:.1f}%</span>",
                        "                    </div>",
                        "                </div>",
                        '                <div class="progress-bar">',
                        f'                    <div class="fill" style="width: {min(pct, 100):.1f}%"></div>',
                        "                </div>",
                    ]
                )

            html_parts.append("            </div>")

            # Custom categories if any
            if semantic_metrics.wildcard_categories:
                html_parts.extend(
                    [
                        "",
                        '            <div class="card">',
                        "                <h2>Custom Categories Discovered</h2>",
                        "                <p>Categories that didn't fit the predefined taxonomy.</p>",
                        "                <table>",
                        "                    <thead>",
                        "                        <tr>",
                        "                            <th>Custom Category</th>",
                        "                            <th>Count</th>",
                        "                        </tr>",
                        "                    </thead>",
                        "                    <tbody>",
                    ]
                )

                for cat, count in sorted(
                    semantic_metrics.wildcard_categories.items(), key=lambda x: -x[1]
                ):
                    html_parts.extend(
                        [
                            "                        <tr>",
                            f"                            <td>{cat}</td>",
                            f"                            <td>{count}</td>",
                            "                        </tr>",
                        ]
                    )

                html_parts.extend(
                    [
                        "                    </tbody>",
                        "                </table>",
                        "            </div>",
                    ]
                )

            # Common combinations
            if semantic_metrics.common_combinations:
                html_parts.extend(
                    [
                        "",
                        '            <div class="card">',
                        "                <h2>Common Category Combinations</h2>",
                        "                <p>Most frequently occurring combinations.</p>",
                        "                <table>",
                        "                    <thead>",
                        "                        <tr>",
                        "                            <th>Categories</th>",
                        "                            <th>Count</th>",
                        "                        </tr>",
                        "                    </thead>",
                        "                    <tbody>",
                    ]
                )

                for combo, count in semantic_metrics.common_combinations[:10]:
                    combo_str = ", ".join(combo)
                    html_parts.extend(
                        [
                            "                        <tr>",
                            f"                            <td>{combo_str}</td>",
                            f"                            <td>{count}</td>",
                            "                        </tr>",
                        ]
                    )

                html_parts.extend(
                    [
                        "                    </tbody>",
                        "                </table>",
                        "            </div>",
                    ]
                )

            html_parts.append("        </div>")  # Close semantic grid

    # Footer with methodology
    html_parts.extend(
        [
            "",
            "        <footer>",
            "            <h2>Methodology</h2>",
            f"            <p>{C.METHODOLOGY_DATA_SOURCE}</p>",
            "        </footer>",
            "",
            "    </div>",
            "</body>",
            "</html>",
        ]
    )

    # Write the HTML file
    output_path.write_text("\n".join(html_parts))

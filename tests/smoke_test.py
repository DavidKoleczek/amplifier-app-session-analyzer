#!/usr/bin/env python3
"""Smoke test for amplifier-session-analyzer.

Generates sample reports using fixture data to verify the app works end-to-end.

Usage:
    python tests/smoke_test.py

    # Or with uv
    uv run python tests/smoke_test.py
"""

import sys
from pathlib import Path

# Add parent to path for local development
sys.path.insert(0, str(Path(__file__).parent.parent))

from amplifier_app_session_analyzer.metrics import (
    calculate_metrics,
    calculate_overlap_metrics,
)
from amplifier_app_session_analyzer.parser import collect_autonomy_periods
from amplifier_app_session_analyzer.report import generate_report
from amplifier_app_session_analyzer.report_markdown import generate_markdown_report
from amplifier_app_session_analyzer.time_scope import parse_time_scope


def main() -> int:
    """Run smoke test and generate sample reports."""
    print("=" * 60)
    print("Amplifier Session Analyzer - Smoke Test")
    print("=" * 60)
    print()

    # Paths - fixtures/projects/ mimics ~/.amplifier/projects/ structure
    fixtures_dir = Path(__file__).parent / "fixtures" / "projects"

    if not fixtures_dir.exists():
        print(f"ERROR: Fixtures directory not found: {fixtures_dir}")
        return 1

    # Parse time scope for the sample data (2026-01-10)
    time_scope = parse_time_scope("2026/01/10", "UTC")
    print(f"Time scope: {time_scope.display_range()}")
    print(f"Fixtures path: {fixtures_dir}")
    print()

    # Collect autonomy periods from fixtures
    print("Collecting autonomy periods...")
    periods = collect_autonomy_periods(time_scope, projects_dir=fixtures_dir)
    print(f"  Found {len(periods)} autonomy periods")
    print()

    if not periods:
        print("ERROR: No periods found in fixtures")
        return 1

    # Calculate metrics
    print("Calculating metrics...")
    metrics = calculate_metrics(periods)
    overlap_metrics = calculate_overlap_metrics(periods)

    if metrics is None:
        print("ERROR: Failed to calculate metrics")
        return 1

    print(f"  Mean autonomy: {metrics.mean_minutes:.1f} minutes")
    print(f"  Median autonomy: {metrics.median_minutes:.1f} minutes")
    print(f"  Total prompts: {metrics.count}")
    print(f"  Unique sessions: {metrics.unique_sessions}")
    print(f"  Overlapping starts: {overlap_metrics.overlap_count}")
    print(f"  Max parallel sessions: {overlap_metrics.max_parallel_sessions}")
    print()

    # Generate reports to .output directory (gitignored)
    output_dir = Path(__file__).parent / ".output"
    output_dir.mkdir(exist_ok=True)

    # Generate Markdown report (default format)
    md_path = output_dir / "smoke-test-report.md"
    print(f"Generating Markdown report: {md_path}")
    generate_markdown_report(metrics, overlap_metrics, time_scope, md_path)

    if not md_path.exists():
        print("ERROR: Markdown report file was not created")
        return 1

    md_size = md_path.stat().st_size
    print(f"  Report size: {md_size} bytes")

    # Generate PDF report
    pdf_path = output_dir / "smoke-test-report.pdf"
    print(f"Generating PDF report: {pdf_path}")
    generate_report(metrics, overlap_metrics, time_scope, pdf_path)

    if not pdf_path.exists():
        print("ERROR: PDF report file was not created")
        return 1

    pdf_size = pdf_path.stat().st_size
    print(f"  Report size: {pdf_size} bytes")
    print()

    # Validate expected values based on fixture data
    print("Validating expected values...")

    # Session-001: 3 prompts (30s, 2m, 45s)
    # Session-002: 2 prompts (2m, 10m) - first overlaps with session-001's second prompt
    # Session-003: 1 prompt (15s)
    # Total: 6 prompts, 3 sessions

    errors = []

    if metrics.count != 6:
        errors.append(f"Expected 6 prompts, got {metrics.count}")

    if metrics.unique_sessions != 3:
        errors.append(f"Expected 3 unique sessions, got {metrics.unique_sessions}")

    # Session-002 started at 14:06 while session-001 was still running (14:05 - 14:07)
    if overlap_metrics.overlap_count != 1:
        errors.append(f"Expected 1 overlap, got {overlap_metrics.overlap_count}")

    if overlap_metrics.max_parallel_sessions != 2:
        errors.append(
            f"Expected max 2 parallel sessions, got {overlap_metrics.max_parallel_sessions}"
        )

    if errors:
        print("VALIDATION ERRORS:")
        for error in errors:
            print(f"  - {error}")
        return 1

    print("  All validations passed!")
    print()
    print("=" * 60)
    print("SMOKE TEST PASSED")
    print("=" * 60)
    print(f"\nReports saved to:")
    print(f"  - {md_path}")
    print(f"  - {pdf_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())

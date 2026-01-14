"""Autonomy metrics calculation.

Computes statistics about agent autonomy periods and session overlaps.
"""

from dataclasses import dataclass
from statistics import mean, median, stdev

from .parser import AutonomyPeriod


@dataclass
class OverlapMetrics:
    """Metrics about overlapping sessions.

    Overlapping sessions occur when a user starts a new prompt in one session
    while another session is still working.
    """

    # Number of times a session started while another was running
    overlap_count: int

    # Maximum number of sessions running in parallel at any point
    max_parallel_sessions: int


@dataclass
class AutonomyMetrics:
    """Aggregated metrics about agent autonomy."""

    # Core statistics (in seconds)
    count: int  # Number of autonomy periods
    total_seconds: float  # Sum of all autonomy durations
    mean_seconds: float
    median_seconds: float
    max_seconds: float
    stdev_seconds: float | None  # None if < 2 samples

    # Distribution buckets
    under_1min: int
    between_1_5min: int
    between_5_15min: int
    over_15min: int

    # Session-level stats
    unique_sessions: int

    @property
    def mean_minutes(self) -> float:
        """Mean autonomy duration in minutes."""
        return self.mean_seconds / 60

    @property
    def median_minutes(self) -> float:
        """Median autonomy duration in minutes."""
        return self.median_seconds / 60

    @property
    def total_minutes(self) -> float:
        """Total autonomous work time in minutes."""
        return self.total_seconds / 60


def calculate_metrics(periods: list[AutonomyPeriod]) -> AutonomyMetrics | None:
    """Calculate aggregated metrics from autonomy periods.

    Args:
        periods: List of autonomy periods to analyze

    Returns:
        AutonomyMetrics with computed statistics, or None if no periods
    """
    if not periods:
        return None

    durations = [p.duration_seconds for p in periods]
    unique_sessions = len(set(p.session_id for p in periods))

    # Distribution buckets
    under_1min = sum(1 for d in durations if d < 60)
    between_1_5min = sum(1 for d in durations if 60 <= d < 300)
    between_5_15min = sum(1 for d in durations if 300 <= d < 900)
    over_15min = sum(1 for d in durations if d >= 900)

    # Standard deviation requires at least 2 samples
    stdev_val = stdev(durations) if len(durations) >= 2 else None

    return AutonomyMetrics(
        count=len(durations),
        total_seconds=sum(durations),
        mean_seconds=mean(durations),
        median_seconds=median(durations),
        max_seconds=max(durations),
        stdev_seconds=stdev_val,
        under_1min=under_1min,
        between_1_5min=between_1_5min,
        between_5_15min=between_5_15min,
        over_15min=over_15min,
        unique_sessions=unique_sessions,
    )


def calculate_overlap_metrics(periods: list[AutonomyPeriod]) -> OverlapMetrics:
    """Calculate metrics about overlapping sessions.

    An overlap occurs when a user starts a new prompt (prompt:submit) in one session
    while another session is still working (before its prompt:complete).

    Args:
        periods: List of autonomy periods to analyze (should be sorted by start time)

    Returns:
        OverlapMetrics with overlap count and max parallel sessions
    """
    if not periods:
        return OverlapMetrics(overlap_count=0, max_parallel_sessions=0)

    # Create events: (timestamp, event_type, session_id)
    # event_type: 'start' = +1 to active count, 'end' = -1 to active count
    events: list[tuple[float, str, str]] = []
    for p in periods:
        events.append((p.start.timestamp(), "start", p.session_id))
        events.append((p.end.timestamp(), "end", p.session_id))

    # Sort by timestamp, with 'end' events before 'start' events at same timestamp
    # This ensures we process session endings before new starts at the same moment
    events.sort(key=lambda e: (e[0], 0 if e[1] == "end" else 1))

    # Track active sessions and count overlaps
    active_sessions: set[str] = set()
    overlap_count = 0
    max_parallel = 0

    for ts, event_type, session_id in events:
        if event_type == "start":
            # Check if any OTHER session is currently active
            # (don't count same session as overlapping with itself)
            other_active = active_sessions - {session_id}
            if other_active:
                overlap_count += 1

            active_sessions.add(session_id)
            max_parallel = max(max_parallel, len(active_sessions))
        else:  # end
            active_sessions.discard(session_id)

    return OverlapMetrics(
        overlap_count=overlap_count,
        max_parallel_sessions=max_parallel,
    )

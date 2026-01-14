"""Session discovery and log parsing.

Finds Amplifier sessions and extracts autonomy-relevant events from logs.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .time_scope import TimeScope, parse_iso_timestamp


@dataclass
class AutonomyPeriod:
    """A single period of autonomous agent work.

    Measured from when user sends a message (prompt:submit)
    to when the agent finishes and returns control (prompt:complete).
    """

    start: datetime  # prompt:submit timestamp
    end: datetime  # prompt:complete timestamp
    session_id: str

    @property
    def duration_seconds(self) -> float:
        """Duration of autonomous work in seconds."""
        return (self.end - self.start).total_seconds()


@dataclass
class SessionInfo:
    """Information about a single session."""

    session_id: str
    session_path: Path
    autonomy_periods: list[AutonomyPeriod] = field(default_factory=list)
    total_prompts_in_scope: int = 0  # All prompt:submit events in time scope


def get_amplifier_projects_dir() -> Path:
    """Get the Amplifier projects directory."""
    return Path.home() / ".amplifier" / "projects"


def is_sub_session(session_id: str) -> bool:
    """Check if a session ID represents a sub-session (agent delegation).

    Sub-sessions have IDs in the format: {parent-span}-{child-span}_{agent-name}
    Example: 0000000000000000-f091bedbecda4679_foundation-modular-builder

    Root sessions are UUIDs like: ab17f0cb-975f-4e71-87c0-fcdaeaff39fc
    """
    # Sub-sessions contain an underscore followed by the agent name
    return "_" in session_id


def _matches_exclude_pattern(project_name: str, exclude_patterns: list[str]) -> bool:
    """Check if a project name matches any exclude pattern.

    Patterns are matched as substrings (case-insensitive).
    """
    project_lower = project_name.lower()
    return any(pattern.lower() in project_lower for pattern in exclude_patterns)


def discover_sessions(
    projects_dir: Path | None = None,
    exclude_projects: list[str] | None = None,
) -> list[Path]:
    """Discover all session directories.

    Args:
        projects_dir: Override the default projects directory
        exclude_projects: List of patterns to exclude (matched against project names)

    Returns:
        Paths to session directories (containing events.jsonl).
    """
    if projects_dir is None:
        projects_dir = get_amplifier_projects_dir()

    if not projects_dir.exists():
        return []

    sessions = []
    for project_dir in projects_dir.iterdir():
        if not project_dir.is_dir():
            continue

        # Check if this project should be excluded
        if exclude_projects and _matches_exclude_pattern(
            project_dir.name, exclude_projects
        ):
            continue

        sessions_dir = project_dir / "sessions"
        if not sessions_dir.exists():
            continue
        for session_dir in sessions_dir.iterdir():
            if session_dir.is_dir() and (session_dir / "events.jsonl").exists():
                sessions.append(session_dir)

    return sessions


def parse_session_events(session_path: Path, time_scope: TimeScope) -> SessionInfo:
    """Parse a session's events.jsonl and extract autonomy periods.

    Only includes autonomy periods where the prompt:submit falls within the time scope.

    Args:
        session_path: Path to session directory
        time_scope: Time range to filter by

    Returns:
        SessionInfo with autonomy periods that fall within scope
    """
    session_id = session_path.name
    events_file = session_path / "events.jsonl"

    if not events_file.exists():
        return SessionInfo(session_id=session_id, session_path=session_path)

    # Collect submit and complete timestamps
    submits: list[datetime] = []
    completes: list[datetime] = []

    with open(events_file) as f:
        for line in f:
            try:
                rec = json.loads(line)
                event = rec.get("event")
                ts_str = rec.get("ts")

                if not ts_str:
                    continue

                ts = parse_iso_timestamp(ts_str)

                if event == "prompt:submit":
                    submits.append(ts)
                elif event == "prompt:complete":
                    completes.append(ts)
            except (json.JSONDecodeError, ValueError):
                # Skip malformed lines
                continue

    # Count total prompts in scope (all prompt:submit events)
    total_prompts_in_scope = sum(1 for ts in submits if time_scope.contains(ts))

    # Pair submits with completes to create autonomy periods
    # They should be in order: submit1, complete1, submit2, complete2, ...
    autonomy_periods = []
    for i in range(min(len(submits), len(completes))):
        submit_ts = submits[i]
        complete_ts = completes[i]

        # Only include if the submit falls within the time scope
        if time_scope.contains(submit_ts):
            autonomy_periods.append(
                AutonomyPeriod(
                    start=submit_ts,
                    end=complete_ts,
                    session_id=session_id,
                )
            )

    return SessionInfo(
        session_id=session_id,
        session_path=session_path,
        autonomy_periods=autonomy_periods,
        total_prompts_in_scope=total_prompts_in_scope,
    )


@dataclass
class CollectedAutonomyData:
    """Data collected from all sessions."""

    periods: list[AutonomyPeriod]
    total_prompts_sent: int  # All prompt:submit events across all sessions


def collect_autonomy_periods(
    time_scope: TimeScope,
    projects_dir: Path | None = None,
    include_sub_sessions: bool = False,
    exclude_projects: list[str] | None = None,
) -> CollectedAutonomyData:
    """Collect all autonomy periods from all sessions within the time scope.

    Args:
        time_scope: Time range to filter by
        projects_dir: Override the default projects directory
        include_sub_sessions: If False (default), exclude agent delegation sub-sessions
        exclude_projects: List of patterns to exclude (matched against project names)

    Returns:
        CollectedAutonomyData with periods and total prompt count
    """
    session_paths = discover_sessions(projects_dir, exclude_projects)
    all_periods: list[AutonomyPeriod] = []
    total_prompts = 0

    for session_path in session_paths:
        session_id = session_path.name

        # Skip sub-sessions unless explicitly included
        if not include_sub_sessions and is_sub_session(session_id):
            continue

        session_info = parse_session_events(session_path, time_scope)
        all_periods.extend(session_info.autonomy_periods)
        total_prompts += session_info.total_prompts_in_scope

    # Sort by start time
    all_periods.sort(key=lambda p: p.start)
    return CollectedAutonomyData(periods=all_periods, total_prompts_sent=total_prompts)

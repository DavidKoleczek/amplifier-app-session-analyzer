"""Semantic analysis of user prompts.

Extracts user prompts from session logs and classifies them into categories
using Amplifier for LLM-based classification.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path

from .time_scope import TimeScope, parse_iso_timestamp


class PromptCategory(Enum):
    """Categories for classifying user prompts."""

    QUESTION = "question"
    IMPLEMENTATION = "implementation"
    DEBUGGING = "debugging"
    CLARIFICATION = "clarification"
    REVIEW = "review"
    REFACTORING = "refactoring"
    EXPLORATION = "exploration"
    TESTING = "testing"
    DIRECTIVE = "directive"
    FEEDBACK = "feedback"
    # Wildcard for categories that don't fit the predefined ones
    OTHER = "other"

    @classmethod
    def from_string(cls, value: str) -> "PromptCategory":
        """Convert a string to a PromptCategory, defaulting to OTHER if not found."""
        try:
            return cls(value.lower())
        except ValueError:
            return cls.OTHER


# Human-readable descriptions for each category
CATEGORY_DESCRIPTIONS: dict[PromptCategory, str] = {
    PromptCategory.QUESTION: "Asking for information or explanation",
    PromptCategory.IMPLEMENTATION: "Requesting code to be written or features added",
    PromptCategory.DEBUGGING: "Fixing errors, bugs, or issues",
    PromptCategory.CLARIFICATION: "Asking for more detail on a prior response",
    PromptCategory.REVIEW: "Code review or verification request",
    PromptCategory.REFACTORING: "Restructuring or improving existing code",
    PromptCategory.EXPLORATION: "Understanding codebase structure or concepts",
    PromptCategory.TESTING: "Writing or running tests",
    PromptCategory.DIRECTIVE: "Direct instruction or command to proceed",
    PromptCategory.FEEDBACK: "Correcting or guiding the assistant's approach",
    PromptCategory.OTHER: "Custom category that doesn't fit predefined ones",
}


@dataclass
class ClassifiedPrompt:
    """A user prompt with its semantic classification."""

    prompt_text: str
    timestamp: datetime
    session_id: str
    categories: list[str]  # 1-3 category names (strings to allow wildcards)
    context_before: list[str] = field(default_factory=list)
    context_after: list[str] = field(default_factory=list)
    wildcard_category: str | None = None  # Custom category if OTHER is assigned


@dataclass
class ExtractedPrompt:
    """A user prompt extracted from session logs, before classification."""

    prompt_text: str
    timestamp: datetime
    session_id: str
    index_in_session: int  # Position within the session (0-indexed)


def extract_prompts_from_session(
    session_path: Path, time_scope: TimeScope
) -> list[ExtractedPrompt]:
    """Extract all user prompts from a session's events.jsonl.

    Args:
        session_path: Path to the session directory
        time_scope: Time range to filter by

    Returns:
        List of extracted prompts within the time scope, ordered by timestamp
    """
    session_id = session_path.name
    events_file = session_path / "events.jsonl"

    if not events_file.exists():
        return []

    prompts: list[ExtractedPrompt] = []

    with open(events_file) as f:
        for line in f:
            try:
                rec = json.loads(line)
                event = rec.get("event")
                ts_str = rec.get("ts")

                if event != "prompt:submit" or not ts_str:
                    continue

                timestamp = parse_iso_timestamp(ts_str)

                # Only include if within time scope
                if not time_scope.contains(timestamp):
                    continue

                # Extract prompt text from data
                data = rec.get("data", {})
                prompt_text = data.get("prompt", "")

                if prompt_text:
                    prompts.append(
                        ExtractedPrompt(
                            prompt_text=prompt_text,
                            timestamp=timestamp,
                            session_id=session_id,
                            index_in_session=len(prompts),
                        )
                    )
            except (json.JSONDecodeError, ValueError):
                # Skip malformed lines
                continue

    return prompts


def add_context_to_prompts(
    prompts: list[ExtractedPrompt], context_window: int = 2
) -> list[tuple[ExtractedPrompt, list[str], list[str]]]:
    """Add surrounding context to each prompt.

    Groups prompts by session and adds context from neighboring prompts.

    Args:
        prompts: List of extracted prompts (should be sorted by timestamp)
        context_window: Number of prompts before and after to include as context

    Returns:
        List of tuples: (prompt, context_before, context_after)
    """
    # Group prompts by session
    by_session: dict[str, list[ExtractedPrompt]] = {}
    for prompt in prompts:
        if prompt.session_id not in by_session:
            by_session[prompt.session_id] = []
        by_session[prompt.session_id].append(prompt)

    # Sort each session's prompts by timestamp
    for session_prompts in by_session.values():
        session_prompts.sort(key=lambda p: p.timestamp)

    # Add context to each prompt
    result: list[tuple[ExtractedPrompt, list[str], list[str]]] = []

    for prompt in prompts:
        session_prompts = by_session[prompt.session_id]
        idx = next(
            i for i, p in enumerate(session_prompts) if p.timestamp == prompt.timestamp
        )

        # Get context before (up to context_window prompts)
        start_idx = max(0, idx - context_window)
        context_before = [p.prompt_text for p in session_prompts[start_idx:idx]]

        # Get context after (up to context_window prompts)
        end_idx = min(len(session_prompts), idx + context_window + 1)
        context_after = [p.prompt_text for p in session_prompts[idx + 1 : end_idx]]

        result.append((prompt, context_before, context_after))

    return result


def collect_prompts_with_context(
    time_scope: TimeScope,
    projects_dir: Path | None = None,
    include_sub_sessions: bool = False,
    context_window: int = 2,
    exclude_projects: list[str] | None = None,
) -> list[tuple[ExtractedPrompt, list[str], list[str]]]:
    """Collect all prompts with context from all sessions within the time scope.

    Args:
        time_scope: Time range to filter by
        projects_dir: Override the default projects directory
        include_sub_sessions: If False (default), exclude agent delegation sub-sessions
        context_window: Number of prompts before and after to include as context
        exclude_projects: List of patterns to exclude (matched against project names)

    Returns:
        List of tuples: (prompt, context_before, context_after), sorted by timestamp
    """
    # Import here to avoid circular import
    from .parser import discover_sessions, is_sub_session

    session_paths = discover_sessions(projects_dir, exclude_projects)
    all_prompts: list[ExtractedPrompt] = []

    for session_path in session_paths:
        session_id = session_path.name

        # Skip sub-sessions unless explicitly included
        if not include_sub_sessions and is_sub_session(session_id):
            continue

        prompts = extract_prompts_from_session(session_path, time_scope)
        all_prompts.extend(prompts)

    # Sort by timestamp
    all_prompts.sort(key=lambda p: p.timestamp)

    # Add context
    return add_context_to_prompts(all_prompts, context_window)

"""Semantic metrics calculation.

Computes statistics about prompt categories and usage patterns.
"""

from collections import Counter
from dataclasses import dataclass

from .semantic import ClassifiedPrompt, PromptCategory


@dataclass
class CategoryStats:
    """Statistics for a single category."""

    category: str
    count: int
    percentage: float


@dataclass
class SemanticMetrics:
    """Aggregated metrics about prompt semantics."""

    # Total prompts analyzed
    total_prompts: int

    # Category distribution
    category_counts: dict[str, int]
    category_stats: list[CategoryStats]

    # Wildcard/custom categories discovered
    wildcard_categories: dict[str, int]

    # Multi-category prompts (prompts with more than one category)
    multi_category_count: int
    multi_category_percentage: float

    # Most common category combinations
    common_combinations: list[tuple[tuple[str, ...], int]]

    # Session-level stats
    unique_sessions: int
    categories_per_session: dict[str, dict[str, int]]  # session_id -> category -> count


@dataclass
class CategorySequence:
    """A sequence of categories representing conversation flow."""

    sequence: tuple[str, ...]
    count: int


def calculate_semantic_metrics(
    classified_prompts: list[ClassifiedPrompt],
) -> SemanticMetrics | None:
    """Calculate aggregated metrics from classified prompts.

    Args:
        classified_prompts: List of classified prompts to analyze

    Returns:
        SemanticMetrics with computed statistics, or None if no prompts
    """
    if not classified_prompts:
        return None

    total = len(classified_prompts)

    # Count categories (each prompt can have 1-3 categories)
    category_counter: Counter[str] = Counter()
    for prompt in classified_prompts:
        for cat in prompt.categories:
            category_counter[cat] += 1

    # Count wildcard categories
    wildcard_counter: Counter[str] = Counter()
    for prompt in classified_prompts:
        if prompt.wildcard_category:
            wildcard_counter[prompt.wildcard_category] += 1

    # Count multi-category prompts
    multi_cat_count = sum(1 for p in classified_prompts if len(p.categories) > 1)

    # Find common category combinations
    combination_counter: Counter[tuple[str, ...]] = Counter()
    for prompt in classified_prompts:
        combo = tuple(sorted(prompt.categories))
        combination_counter[combo] += 1

    # Get top 10 combinations
    common_combos = combination_counter.most_common(10)

    # Session-level analysis
    sessions: set[str] = set()
    categories_per_session: dict[str, dict[str, int]] = {}

    for prompt in classified_prompts:
        sessions.add(prompt.session_id)
        if prompt.session_id not in categories_per_session:
            categories_per_session[prompt.session_id] = {}

        for cat in prompt.categories:
            if cat not in categories_per_session[prompt.session_id]:
                categories_per_session[prompt.session_id][cat] = 0
            categories_per_session[prompt.session_id][cat] += 1

    # Build category stats sorted by count (descending)
    category_stats = []
    for cat, count in category_counter.most_common():
        category_stats.append(
            CategoryStats(
                category=cat,
                count=count,
                percentage=100 * count / total,
            )
        )

    return SemanticMetrics(
        total_prompts=total,
        category_counts=dict(category_counter),
        category_stats=category_stats,
        wildcard_categories=dict(wildcard_counter),
        multi_category_count=multi_cat_count,
        multi_category_percentage=100 * multi_cat_count / total,
        common_combinations=common_combos,
        unique_sessions=len(sessions),
        categories_per_session=categories_per_session,
    )


def get_category_description(category: str) -> str:
    """Get a human-readable description for a category."""
    from .semantic import CATEGORY_DESCRIPTIONS

    try:
        cat_enum = PromptCategory(category)
        return CATEGORY_DESCRIPTIONS.get(cat_enum, "")
    except ValueError:
        # Custom/wildcard category
        return f"Custom category: {category}"

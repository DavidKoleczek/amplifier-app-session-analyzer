"""LLM-based prompt classification using Amplifier.

Uses Amplifier to classify user prompts into semantic categories.
Batches multiple prompts per LLM request for efficiency.
"""

import asyncio
import json
import re
from dataclasses import dataclass
from typing import Callable

from amplifier_foundation import load_bundle

from . import constants as C
from .semantic import (
    CATEGORY_DESCRIPTIONS,
    ClassifiedPrompt,
    ExtractedPrompt,
    PromptCategory,
)

# Batched classification prompt template
BATCH_CLASSIFICATION_PROMPT = """\
You are classifying user prompts from AI coding assistant sessions.

## Categories (assign 1-3 per prompt that best describe the prompt)

{category_list}

## Prompts to Classify

{prompts_section}

## Instructions

For each prompt:
1. Analyze the prompt considering its conversation context
2. Assign 1-3 categories that best describe the prompt's intent
3. If a prompt doesn't fit any predefined category well, use "other" and provide a custom_category name

## Response Format (JSON array only)

Return ONLY a valid JSON array with one object per prompt, in the same order as listed above.
Each object must have: "index", "categories", "custom_category"

Example:
[
  {{"index": 1, "categories": ["debugging", "question"], "custom_category": null}},
  {{"index": 2, "categories": ["implementation"], "custom_category": null}},
  {{"index": 3, "categories": ["other"], "custom_category": "planning"}}
]
"""


def _build_category_list() -> str:
    """Build a formatted list of categories for the prompt."""
    lines = []
    for cat in PromptCategory:
        if cat != PromptCategory.OTHER:
            desc = CATEGORY_DESCRIPTIONS.get(cat, "")
            lines.append(f"- **{cat.value}**: {desc}")
    # Add OTHER last with special instructions
    lines.append(
        f"- **{PromptCategory.OTHER.value}**: Use when prompt doesn't fit above categories. "
        "Provide a custom_category name."
    )
    return "\n".join(lines)


# Maximum characters per prompt entry (user message + context combined)
MAX_PROMPT_CHARS = 3000


def _truncate_with_budget(
    prompt_text: str,
    ctx_before: list[str],
    ctx_after: list[str],
    total_budget: int = MAX_PROMPT_CHARS,
) -> tuple[str, str, str]:
    """Truncate prompt and context to fit within budget.

    Prioritizes the user's message over surrounding context.
    Allocates: 70% to prompt, 15% each to before/after context.
    """
    # Reserve most budget for the actual prompt
    prompt_budget = int(total_budget * 0.70)
    context_budget_each = int(total_budget * 0.15)

    # Truncate prompt text (priority)
    if len(prompt_text) > prompt_budget:
        prompt_text = prompt_text[:prompt_budget] + "..."

    # Format context with remaining budget
    def format_context(messages: list[str], budget: int) -> str:
        if not messages:
            return "(none)"
        result = []
        remaining = budget
        for msg in messages[:2]:  # Max 2 context messages per direction
            # Reserve space for quotes and ellipsis
            max_len = remaining - 10
            if max_len <= 0:
                break
            if len(msg) > max_len:
                result.append(f'"{msg[:max_len]}..."')
                remaining = 0
            else:
                result.append(f'"{msg}"')
                remaining -= len(msg) + 4  # quotes and comma
        return ", ".join(result) if result else "(none)"

    ctx_before_str = format_context(ctx_before, context_budget_each)
    ctx_after_str = format_context(ctx_after, context_budget_each)

    return prompt_text, ctx_before_str, ctx_after_str


def _build_prompts_section(
    prompts_with_context: list[tuple[ExtractedPrompt, list[str], list[str]]],
) -> str:
    """Build the prompts section for batched classification."""
    sections = []
    for i, (prompt, ctx_before, ctx_after) in enumerate(prompts_with_context, 1):
        prompt_text, ctx_before_str, ctx_after_str = _truncate_with_budget(
            prompt.prompt_text, ctx_before, ctx_after
        )

        section = f"""### Prompt {i}
Context before: {ctx_before_str}
Text: "{prompt_text}"
Context after: {ctx_after_str}"""
        sections.append(section)

    return "\n\n".join(sections)


def _parse_batch_response(response: str, expected_count: int) -> list[dict]:
    """Parse the JSON array response from the LLM.

    Args:
        response: Raw LLM response text
        expected_count: Number of prompts we expect results for

    Returns:
        List of classification dicts, one per prompt
    """
    text = response.strip()

    # Try to extract JSON array from markdown code blocks
    json_match = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", text, re.DOTALL)
    if json_match:
        text = json_match.group(1)
    else:
        # Find raw JSON array
        start = text.find("[")
        end = text.rfind("]") + 1
        if start >= 0 and end > start:
            text = text[start:end]

    try:
        results = json.loads(text)
        if isinstance(results, list):
            return results
    except json.JSONDecodeError:
        pass

    # Return defaults on parse failure
    return [
        {
            "index": i + 1,
            "categories": ["other"],
            "custom_category": "parse_error",
        }
        for i in range(expected_count)
    ]


def _validate_categories(
    categories: list[str], custom_category: str | None
) -> tuple[list[str], str | None]:
    """Validate and normalize categories from LLM response."""
    validated = []
    wildcard = custom_category

    for cat in categories[:3]:
        cat_lower = cat.lower().strip()
        try:
            PromptCategory(cat_lower)
            validated.append(cat_lower)
        except ValueError:
            # Not a predefined category - treat as "other" with custom
            if "other" not in validated:
                validated.append("other")
            if not wildcard:
                wildcard = cat_lower

    if not validated:
        validated = ["other"]

    return validated, wildcard if "other" in validated else None


@dataclass
class ClassifierConfig:
    """Configuration for the prompt classifier."""

    foundation_source: str = (
        "git+https://github.com/microsoft/amplifier-foundation@main"
    )
    provider_name: str = "anthropic-sonnet"  # Default provider
    max_concurrency: int = 3  # Number of parallel batch requests


class PromptClassifier:
    """Classifies user prompts using Amplifier with batching."""

    def __init__(self, config: ClassifierConfig | None = None):
        self.config = config or ClassifierConfig()
        self._prepared = None
        self._category_list = _build_category_list()

    async def _get_prepared_bundle(self):
        """Lazy-load and cache the prepared bundle."""
        if self._prepared is None:
            foundation = await load_bundle(self.config.foundation_source)
            provider_path = (
                foundation.base_path / "providers" / f"{self.config.provider_name}.yaml"
            )
            provider = await load_bundle(str(provider_path))
            composed = foundation.compose(provider)
            self._prepared = await composed.prepare()
        return self._prepared

    async def _classify_batch_group(
        self,
        prompts_with_context: list[tuple[ExtractedPrompt, list[str], list[str]]],
    ) -> list[ClassifiedPrompt]:
        """Classify a batch of prompts in a single LLM request.

        Args:
            prompts_with_context: List of (prompt, context_before, context_after) tuples

        Returns:
            List of ClassifiedPrompt objects in the same order as input
        """
        if not prompts_with_context:
            return []

        prepared = await self._get_prepared_bundle()
        session = await prepared.create_session()

        # Build the batched prompt
        prompts_section = _build_prompts_section(prompts_with_context)
        batch_prompt = BATCH_CLASSIFICATION_PROMPT.format(
            category_list=self._category_list,
            prompts_section=prompts_section,
        )

        async with session:
            response = await session.execute(batch_prompt)

        # Parse the batch response
        parsed_results = _parse_batch_response(response, len(prompts_with_context))

        # Build ClassifiedPrompt objects
        results = []
        for i, (prompt, ctx_before, ctx_after) in enumerate(prompts_with_context):
            # Find matching result by index (1-based in response)
            result_data = None
            for r in parsed_results:
                if r.get("index") == i + 1:
                    result_data = r
                    break

            if result_data is None:
                # Fallback if index not found - use position
                if i < len(parsed_results):
                    result_data = parsed_results[i]
                else:
                    result_data = {
                        "categories": ["other"],
                        "custom_category": "missing_result",
                    }

            categories = result_data.get("categories", ["other"])
            custom_category = result_data.get("custom_category")

            validated_categories, wildcard = _validate_categories(
                categories, custom_category
            )

            results.append(
                ClassifiedPrompt(
                    prompt_text=prompt.prompt_text,
                    timestamp=prompt.timestamp,
                    session_id=prompt.session_id,
                    categories=validated_categories,
                    context_before=ctx_before,
                    context_after=ctx_after,
                    wildcard_category=wildcard,
                )
            )

        return results

    async def classify_batch(
        self,
        prompts_with_context: list[tuple[ExtractedPrompt, list[str], list[str]]],
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> list[ClassifiedPrompt]:
        """Classify multiple prompts using batched LLM requests.

        Prompts are grouped into batches of SEMANTIC_BATCH_SIZE and processed
        with limited concurrency for efficiency.

        Args:
            prompts_with_context: List of (prompt, context_before, context_after) tuples
            progress_callback: Optional callback(current, total) for progress updates

        Returns:
            List of ClassifiedPrompt objects in the same order as input
        """
        total = len(prompts_with_context)
        if total == 0:
            return []

        batch_size = C.SEMANTIC_BATCH_SIZE

        # Split into batches
        batches = [
            prompts_with_context[i : i + batch_size]
            for i in range(0, total, batch_size)
        ]

        # Use semaphore to limit concurrent batch requests
        semaphore = asyncio.Semaphore(self.config.max_concurrency)
        completed_count = 0
        lock = asyncio.Lock()

        async def process_batch(
            batch_index: int,
            batch: list[tuple[ExtractedPrompt, list[str], list[str]]],
        ) -> tuple[int, list[ClassifiedPrompt]]:
            """Process a single batch with concurrency limiting."""
            nonlocal completed_count

            async with semaphore:
                results = await self._classify_batch_group(batch)

                # Update progress
                async with lock:
                    completed_count += len(batch)
                    if progress_callback:
                        progress_callback(completed_count, total)

                return (batch_index, results)

        # Create tasks for all batches
        tasks = [process_batch(i, batch) for i, batch in enumerate(batches)]

        # Run all batch tasks concurrently (semaphore limits actual parallelism)
        indexed_results = await asyncio.gather(*tasks)

        # Sort by batch index and flatten results
        indexed_results.sort(key=lambda x: x[0])
        all_results = []
        for _, batch_results in indexed_results:
            all_results.extend(batch_results)

        return all_results


def classify_prompts_sync(
    prompts_with_context: list[tuple[ExtractedPrompt, list[str], list[str]]],
    config: ClassifierConfig | None = None,
    progress_callback: Callable[[int, int], None] | None = None,
) -> list[ClassifiedPrompt]:
    """Synchronous wrapper for prompt classification.

    Args:
        prompts_with_context: List of (prompt, context_before, context_after) tuples
        config: Optional classifier configuration
        progress_callback: Optional callback(current, total) for progress updates

    Returns:
        List of ClassifiedPrompt objects
    """
    classifier = PromptClassifier(config)
    return asyncio.run(
        classifier.classify_batch(prompts_with_context, progress_callback)
    )

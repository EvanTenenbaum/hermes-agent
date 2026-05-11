#!/usr/bin/env python3
"""Fix skill_fitness_metric to support GEPA's 5-argument signature.

GEPA requires: metric(gold, pred, trace=None, pred_name=None, pred_trace=None)
The current fitness.py only accepts (gold, pred).

Usage:
    python fix_gepa_metric.py
    # Then rebuild the skill_fitness_metric in evolution/core/fitness.py

This script is a reference for the exact signature GEPA expects.
"""

from typing import Optional


def skill_fitness_metric_gepa(
    gold: dict,
    pred: dict,
    trace: Optional[list] = None,
    pred_name: Optional[str] = None,
    pred_trace: Optional[list] = None,
) -> float:
    """Skill fitness metric compatible with GEPA's 5-argument signature.

    Same scoring logic as the original, but accepts the extra args GEPA passes
    for reflective failure analysis.

    Args:
        gold: Ground truth example with expected output fields
        pred: Predicted output from the module
        trace: Full execution trace (tool calls, reasoning)
        pred_name: Name of the predictor that produced this output
        pred_trace: Trace specific to this predictor

    Returns:
        Score between 0.0 and 1.0
    """
    # Extract expected and actual outputs
    expected = gold.get("output", gold.get("expected_output", "")).strip()
    actual = pred.get("output", "").strip()

    if not expected or not actual:
        return 0.0

    # Semantic similarity: does the output mention the key steps/concepts
    expected_keywords = set(expected.lower().split())
    actual_keywords = set(actual.lower().split())

    if not expected_keywords:
        return 0.0

    overlap = len(expected_keywords & actual_keywords)
    semantic_score = overlap / len(expected_keywords)

    # Format fidelity: does it look like a skill output (structured, not rambling)
    format_score = 0.0
    if any(marker in actual for marker in ["```", "---", "##", "1."]):
        format_score = 0.3  # Has structure markers
    elif "tool" in actual.lower() or "command" in actual.lower():
        format_score = 0.2  # Mentions tools/commands
    else:
        format_score = 0.1  # Plain text

    # Trace bonus: if GEPA provides trace, check for tool call presence
    trace_bonus = 0.0
    if trace and any("tool" in str(t).lower() for t in trace):
        trace_bonus = 0.1

    total = min(1.0, semantic_score * 0.6 + format_score + trace_bonus)
    return total


if __name__ == "__main__":
    # Quick self-test
    gold = {"output": "Use gh pr review to leave inline comments on the diff"}
    pred = {"output": "Run: gh pr review --comments 'Looks good'"}
    score = skill_fitness_metric_gepa(gold, pred)
    print(f"Self-test score: {score:.3f}")
    assert 0.0 <= score <= 1.0
    print("Signature OK — ready to replace in evolution/core/fitness.py")

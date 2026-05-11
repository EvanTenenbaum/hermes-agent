#!/usr/bin/env python3
"""Mine Hermes session DB for real execution traces of a skill.

Builds evaluation datasets from actual session history instead of synthetic data.
This is the key differentiator for high-quality skill evolution.

Usage:
    python mine_traces.py --skill github-code-review --output datasets/skills/github-code-review/
"""

import argparse
import json
import sqlite3
import sys
from pathlib import Path


def get_session_db() -> Path:
    """Find the Hermes session database."""
    candidates = [
        Path.home() / ".hermes" / "sessions.db",
        Path.home() / ".hermes" / "hermes-agent" / "sessions.db",
    ]
    for c in candidates:
        if c.exists():
            return c
    raise FileNotFoundError("No sessions.db found in ~/.hermes/")


def find_sessions_with_skill(skill_name: str, db: Path, min_score: float = 0.3) -> list[dict]:
    """Query session DB for conversations mentioning the skill.

    Uses FTS5 full-text search on session content. Returns sessions
    with (user_message, tool_calls, assistant_response) tuples.
    """
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # FTS5 search for skill name in session content
    cur.execute(
        """
        SELECT id, title, content, created_at, platform
        FROM sessions
        WHERE content MATCH ?
        ORDER BY created_at DESC
        LIMIT 50
        """,
        (skill_name,),
    )

    sessions = []
    for row in cur.fetchall():
        sessions.append(
            {
                "id": row["id"],
                "title": row["title"],
                "created_at": row["created_at"],
                "platform": row["platform"],
                "content": row["content"],
            }
        )

    conn.close()
    return sessions


def extract_eval_examples(sessions: list[dict], skill_name: str) -> list[dict]:
    """Extract structured eval examples from raw session content.

    Naive approach: split by assistant/user turns, look for tool call blocks.
    A production version should parse the exact message format.
    """
    examples = []
    for sess in sessions:
        content = sess["content"]

        # Look for user → assistant tool call patterns
        # Heuristic: find user message followed by tool calls and result
        chunks = content.split("user:")
        for chunk in chunks[1:]:  # Skip first (before any user message)
            lines = chunk.strip().split("\n")
            if len(lines) < 5:
                continue

            user_request = lines[0][:500]  # First line is the request

            # Check if this chunk mentions our skill
            if skill_name not in chunk.lower():
                continue

            # Look for tool call blocks
            has_tool_calls = "tool:" in chunk or "function:" in chunk
            has_output = len([l for l in lines if l.strip()]) > 3

            if has_tool_calls and has_output:
                examples.append(
                    {
                        "task_input": user_request.strip(),
                        "session_id": sess["id"],
                        "created_at": sess["created_at"],
                        "raw_snippet": chunk[:2000],
                    }
                )

    return examples


def save_dataset(examples: list[dict], output_dir: Path, skill_name: str) -> None:
    """Save mined examples in the format expected by evolution.skills.evolve_skill."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # Shuffle deterministically
    import random

    random.seed(42)
    random.shuffle(examples)

    # Split 70/15/15
    n = len(examples)
    train = examples[: int(n * 0.7)]
    val = examples[int(n * 0.7) : int(n * 0.85)]
    holdout = examples[int(n * 0.85) :]

    def save_split(split: list[dict], name: str):
        path = output_dir / f"{name}.jsonl"
        with open(path, "w") as f:
            for ex in split:
                f.write(json.dumps(ex) + "\n")

    save_split(train, "train")
    save_split(val, "val")
    save_split(holdout, "holdout")

    print(f"Saved {len(train)} train / {len(val)} val / {len(holdout)} holdout to {output_dir}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--skill", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--min-examples", type=int, default=5)
    args = parser.parse_args()

    db = get_session_db()
    print(f"Using session DB: {db}")

    sessions = find_sessions_with_skill(args.skill, db)
    print(f"Found {len(sessions)} sessions mentioning '{args.skill}'")

    if len(sessions) < args.min_examples:
        print(f"ERROR: Need ≥{args.min_examples} sessions. Found {len(sessions)}.")
        print("Suggestion: use --eval-source synthetic for first run, or wait for more sessions.")
        sys.exit(1)

    examples = extract_eval_examples(sessions, args.skill)
    print(f"Extracted {len(examples)} eval examples")

    if len(examples) < args.min_examples:
        print(f"WARNING: Only {len(examples)} examples mined. May need manual curation.")

    save_dataset(examples, Path(args.output), args.skill)
    print("Done. Pass --eval-source sessiondb to evolve_skill.py to use these traces.")


if __name__ == "__main__":
    main()

---
name: hermes-self-evolution
description: Evolve Hermes skills via DSPy+GEPA using real session traces. Wraps EvanTenenbaum/hermes-self-evolution. Produces diffs for human review — never auto-applies.
tags: [hermes, self-improvement, evolution, dspy, skill-optimization]
category: autonomous-ai-agents
---

# Hermes Self-Evolution

Evolve any Hermes skill using DSPy + GEPA (Genetic-Pareto Prompt Evolution) with real session execution traces as evaluation data.

**Repo:** `EvanTenenbaum/hermes-self-evolution` (forked from NousResearch, patched)
**Path:** `~/hermes-self-evolution` or `/tmp/hermes-agent-self-evolution`
**Blast radius:** Phase 1 only (SKILL.md files). No runtime, no auto-merge.

## When to Use

- A skill underperforms or feels stale
- After accumulating 5+ sessions with a skill to build real trace data
- To compare synthetic vs trace-based evolution quality
- Quarterly skill hygiene review

## Never Do

- Auto-merge evolved skills without review
- Run on system-critical skills (approval gates, safety policies) without backup
- Schedule unattended cron until Phase 1 proves stable over 3+ manual runs

## One-Shot Invocation

```bash
cd ~/hermes-self-evolution && \
HERMES_AGENT_REPO=~/.hermes/hermes-agent \
OPENAI_API_KEY=$(grep OPENAI_API_KEY ~/.hermes/.env | cut -d= -f2) \
python -m evolution.skills.evolve_skill \
  --skill <skill_name> \
  --iterations 5 \
  --eval-source sessiondb \
  --optimizer-model openai/gpt-4.1-mini \
  --eval-model openai/gpt-4.1-mini
```

Output lands in `output/<skill_name>/<timestamp>/evolved.md` for diff review.

## Eval Data Sources

| Source | Quality | Setup | When |
|--------|---------|-------|------|
| `synthetic` | Low | Zero | First-time smoke test only |
| `sessiondb` | High | Requires trace mining | Preferred — real usage patterns |
| `golden` | Highest | Manual curation | Reserved for mission-critical skills |

## Trace Mining (sessiondb)

The tool extracts from `session_search`:
1. Identify sessions where the target skill was loaded
2. Extract user requests + tool call sequences + outcomes
3. Build eval examples: `{task_input, expected_behavior}`
4. Feed to GEPA as training data

This is the key differentiator vs synthetic data — it captures *why* things fail, not just *that* they fail.

## Constraint Gates

Every evolved skill must pass:
- Size ≤ 15KB
- Growth ≤ +20%
- Valid YAML frontmatter (name + description)
- Non-empty body
- (Optional) `pytest tests/ -q` in hermes-agent repo

Failed constraints = variant discarded, no deploy.

## Known Issues / Patches Applied

Upstream had 3 bugs fixed in our fork:
1. `GEPA.__init__` param `max_steps` → `max_full_evals` (DSPy 3.2 API change)
2. Missing `optuna` dependency (required for MIPROv2 fallback)
3. Constraint validator checked evolved body instead of reassembled skill (frontmatter stripped)

## Phase Roadmap

| Phase | Target | Status | Risk |
|-------|--------|--------|------|
| 1 | Skills (SKILL.md) | ✅ Working | Low |
| 2 | Tool descriptions | 🔲 Planned | Medium |
| 3 | System prompt sections | 🔲 Planned | High |
| 4 | Tool implementation code | 🔲 Deferred | Highest |

Phase 2+ gated behind Phase 1 proving value over 3+ manual runs.

## Related Skills

- `dspy` — the optimizer engine this tool uses
- `deep-research` — good candidate for evolution (large, well-defined)
- `github-code-review` — proven trial skill

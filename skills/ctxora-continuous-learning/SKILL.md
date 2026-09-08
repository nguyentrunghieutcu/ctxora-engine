---
name: ctxora-continuous-learning
description: Capture evidence-backed project lessons in CTXORA memory and promote repeated lessons into reusable guidance. Use after a correction, verified bug fix, architectural decision, or repeatable workflow is established.
---

# CTXORA Continuous Learning

CTXORA learning is deliberate and memory-based; it does not require background hooks.

Skill-routing learning is separate from durable memory. Keep the `route_id` returned by `route_skills` or `prepare_context` in task state. After validation passes, automatically call `skill_feedback` with `success` and the skills actually used; use `failure` only when the failed result is attributable to the guidance, and `corrected` when the user replaces the routed skill. Do not ask the user to submit routine feedback manually. CTXORA stores only a task fingerprint, matched catalog terms, bounded counters, and decayed associations; it never stores raw tasks or transcripts.

Inspect connected tool schemas and resolve the registered workspace ID before using `memory_search` or `memory_save`. If tools are unavailable, present a proposed lesson and explicitly report that it was not saved. Do not write directly into memory databases or ECC vaults. Do not capture raw session transcripts or install observers as part of this skill.

Before saving, search existing memory for the same rule. Save only knowledge supported by repository evidence, a passing validation, an explicit user decision, or a reproduced incident.

Choose one memory tier:

- `semantic`: stable project facts, terminology, conventions, and decisions.
- `procedural`: repeatable workflows, diagnostics, and repair sequences.
- `episodic`: a specific incident, handoff, experiment, or one-time decision context.

Use workspace scope by default. Use a broader scope only when the same lesson has been independently verified across projects. Store one atomic lesson per key, include the evidence or validation in the value, set `source` accurately, and lower `confidence` when evidence is incomplete.

Do not learn secrets, transient command output, guesses, generated summaries with no source, or preferences inferred from a single uncorrected example. Update a conflicting memory instead of averaging incompatible rules.

Promote repeated lessons into `AGENTS.md`, a skill, or a command only when the behavior is stable, broadly useful in its scope, and the user has requested or approved that durable project change.

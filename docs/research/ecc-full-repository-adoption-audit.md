# ECC full-repository adoption audit for CTXORA

Date: 2026-09-09
ECC revision: `5064474d4d762dc9640234a41617cccb79185cec` (ECC 2.2.1)

## Decision summary

CTXORA should not become a smaller ECC distribution. It should remain a local-first context engine and adopt only the ECC patterns that strengthen context retrieval, portable host installation, provenance, validation, and safe workflow guidance.

Recommended disposition:

| ECC surface | Decision | CTXORA action |
|---|---|---|
| Install manifests and state | Adapt now | Add target capabilities, pure planning, receipts, validation, rollback |
| Harness capability registry | Adapt now | Make target support declarative and shared by installer/doctor |
| Agents | Curate and adapt | Keep a small CTXORA-native role set; never bulk-copy all agents |
| Commands | Curate and adapt | Package only commands backed by CTXORA tools or deterministic CLI actions |
| Skills | Continue curated vendoring | Add compatibility, provenance, quality, and duplication gates |
| CI validators | Adapt now | Validate agents, commands, skills, references, paths, and manifests |
| Rules | Reference selectively | Generate host/project instructions; do not ship all language rules |
| Hooks | Do not copy by default | Prefer watcher/CLI; offer only explicit, target-specific opt-in hooks |
| Memory/handoff schemas | Adapt selectively | Keep CTXORA model; preserve ECC read compatibility and provenance concepts |
| Context presets | Adapt | Represent dev/research/review as retrieval policies, not static prompt dumps |
| ECC2 session control plane | Do not copy now | Separate product scope; revisit only if CTXORA becomes a session orchestrator |
| Dashboards/control pane | Do not copy | Not required for the context-engine objective |
| Third-party plugin recommendations | Do not bundle | Keep integrations explicit and independently audited |

## Repository inventory

At the reviewed revision, the major authored surfaces include:

- 68 top-level agent definitions.
- 94 command definitions.
- 122 rule files.
- 464 files under the skills tree.
- 272 files under scripts, including 142 shared library files and 53 hook scripts.
- Install manifests and schemas, memory/provenance schemas, plugin packaging, harness adapters, and the separate Rust `ecc2` alpha control plane.

Primary source: [ECC repository](https://github.com/affaan-m/ECC/tree/5064474d4d762dc9640234a41617cccb79185cec).

## Should CTXORA copy ECC agents?

### Answer

**Copy the architectural idea and a few role boundaries; do not copy the complete agent catalog.**

The top-level ECC agents are primarily Claude-oriented prompt packages. Many definitions:

- hard-code Claude model names such as `haiku`, `sonnet`, or `opus`;
- hard-code Claude-style tool names and broad write/shell permissions;
- contain imperative routing such as “use proactively” or “must be used”;
- overlap with skills, commands, and each other;
- encode general software-development opinions unrelated to CTXORA's context-engine responsibility.

Installing these definitions into Codex, Gemini, Cursor, and other hosts without adaptation would recreate the same blind fan-out problem identified in the skill installer.

ECC itself demonstrates the better cross-host pattern in `.codex/agents`: three small read-only roles—explorer, reviewer, and documentation researcher—with concise responsibility boundaries. These are more useful as design references than the large Claude-specific prompts. See [Codex agent definitions](https://github.com/affaan-m/ECC/tree/5064474d4d762dc9640234a41617cccb79185cec/.codex/agents) and [top-level agents](https://github.com/affaan-m/ECC/tree/5064474d4d762dc9640234a41617cccb79185cec/agents).

### Existing CTXORA agents

CTXORA already has an appropriate minimal base:

- `ctxora-context-engineer`: retrieves and validates repository evidence.
- `ctxora-reviewer`: performs evidence-grounded review without autonomous edits.
- `ctxora-maintainer`: manages setup, indexing, diagnostics, memory, and handoffs.

These are portable role prompts rather than separate model configurations. That design should remain.

### Recommended additions

Add only two default roles:

1. `ctxora-planner`
   - Uses `plan_context`, `retrieve_context`, and repository evidence.
   - Produces an implementation plan with files, dependencies, risks, success criteria, and tests.
   - Does not edit code.

2. `ctxora-researcher`
   - Uses local retrieval first and primary external sources when requested.
   - Separates repository facts, external facts, and inferences.
   - Writes cited findings; read-only by default.

Optional internal role, not installed by default:

3. `ctxora-evaluator`
   - Evaluates retrieval coverage, source quality, route selection, and handoff completeness.
   - Feeds measurable outcomes into `skill_feedback`/evaluation datasets.

Do not add separate language reviewers, build resolvers, TDD agents, security agents, or architecture agents to the default CTXORA package. Those are better represented by on-demand skills and the host's own agent ecosystem.

### Agent portability contract

Create a CTXORA-owned agent manifest with:

- stable role ID and description;
- required CTXORA tools/capabilities;
- read/write risk level;
- supported targets;
- target adapter;
- provenance and source revision;
- optional install status, never a fixed model name.

Each target adapter should render the native host format. The canonical role must remain host-neutral.

## Commands

ECC's command library is broad and tightly coupled to its agents, skills, hooks, and orchestration scripts. CTXORA should not import generic build/review/framework commands.

Keep commands that expose CTXORA-native capabilities:

- context/retrieve;
- plan;
- review;
- route;
- handoff;
- learn/feedback;
- health/doctor;
- refresh/index.

Add a command only when it maps to a real MCP tool or deterministic CLI operation. For hosts without slash-command support, render the same workflow as a normal prompt template. Validate every command-to-tool, command-to-skill, and command-to-agent reference, following ECC's [command-agent map](https://github.com/affaan-m/ECC/blob/5064474d4d762dc9640234a41617cccb79185cec/docs/COMMAND-AGENT-MAP.md) and validator approach.

## Rules and project instructions

Do not vendor ECC's full language/framework rule tree. CTXORA already generates `AGENTS.md`, Copilot instructions, and Cursor rules from repository evidence. That is more aligned with its product boundary than shipping static global rules.

Adopt these ideas:

- deterministic invariants belong in generated project instructions or path-scoped host rules;
- expensive workflows belong in skills;
- structured repeated operations belong in MCP;
- one-shot deterministic actions belong in the CLI.

This boundary is documented in ECC's [capability surface selection guide](https://github.com/affaan-m/ECC/blob/5064474d4d762dc9640234a41617cccb79185cec/docs/capability-surface-selection.md).

## Hooks

Do not copy ECC's hook runtime or 53 hook scripts into CTXORA's default installation.

Reasons:

- hooks are host/event-schema specific;
- they execute automatically and increase security and support burden;
- many duplicate CTXORA's watcher, refresh, diagnostics, or host behavior;
- cross-target installation requires substantial adaptation and verification.

Potential future opt-in hooks:

- notify CTXORA of changed files after successful edits;
- check index freshness before context-heavy work;
- save a handoff before compaction/session termination.

Each must be explicit, target-specific, idempotent, timeout-bounded, and removable from ownership state. Prefer the current watcher or direct CLI when an automatic hook is not necessary.

## Skills

CTXORA's pinned ECC skill catalog is the correct integration form, but catalog growth should not be automatic.

Add gates before importing more skills:

- unique capability versus existing CTXORA/ECC skills;
- portable instructions without hidden Claude-only assumptions;
- no undeclared external package/service requirement;
- valid frontmatter and bounded routing text;
- supported target/capability metadata;
- provenance, source commit, license, and content hash;
- tests for routing and installation;
- removal/deprecation strategy.

Prefer adapting a skill to CTXORA-native tools rather than preserving instructions that call unavailable ECC scripts, agents, hooks, or Claude tools. Follow the intent of ECC's [skill adaptation policy](https://github.com/affaan-m/ECC/blob/5064474d4d762dc9640234a41617cccb79185cec/docs/skill-adaptation-policy.md).

## Schemas, manifests, and validators

This is the highest-value area to adopt after the installer work.

Recommended CTXORA schemas:

- `install-targets.v1`;
- `install-request.v1`;
- `install-plan.v1`;
- `install-receipt.v1`;
- `agent-manifest.v1`;
- `command-manifest.v1`;
- extended skill catalog compatibility/provenance fields.

Recommended validation gates:

- agent frontmatter and target compatibility;
- command references to existing tools, agents, and skills;
- skill frontmatter, IDs, routing size, and referenced files;
- manifest schema/dependency/cycle validation;
- no personal absolute paths in packaged artifacts;
- Unicode/invisible-character safety for executable prompt/config surfaces;
- package contents match declared installable artifacts;
- third-party provenance and license files remain synchronized.

ECC references: [CI validators](https://github.com/affaan-m/ECC/tree/5064474d4d762dc9640234a41617cccb79185cec/scripts/ci) and [schemas](https://github.com/affaan-m/ECC/tree/5064474d4d762dc9640234a41617cccb79185cec/schemas).

## Harness capability and compliance audit

Adapt ECC's harness-capability concept into one CTXORA registry used by:

- MCP client installer;
- skill/agent/command installers;
- `profile` output;
- `doctor` and topology diagnostics;
- packaging tests;
- generated user instructions.

Capabilities should include custom skills, custom agents, slash commands, MCP config format, hooks, project/global scope, and required adaptation. This prevents separate hard-coded target lists from drifting.

Reference: [harness capabilities](https://github.com/affaan-m/ECC/blob/5064474d4d762dc9640234a41617cccb79185cec/scripts/lib/harness-capabilities.js) and [adapter compliance](https://github.com/affaan-m/ECC/blob/5064474d4d762dc9640234a41617cccb79185cec/scripts/lib/harness-adapter-compliance.js).

## Memory, handoff, and provenance

CTXORA already owns its memory and handoff model and has a read-only ECC vault adapter. Do not replace it with ECC's memory implementation.

Useful concepts to retain or strengthen:

- explicit source/target harness identifiers;
- immutable provenance for imported evidence;
- schema-versioned handoff envelopes;
- bounded payloads and path validation;
- conflict-safe writes and append-only audit evidence where appropriate.

Avoid importing ECC orchestration, automatic learning, or observer loops until there is a concrete CTXORA requirement and an evaluation proving value.

## ECC2, orchestration, and worktrees

The Rust `ecc2` tree is an alpha session control plane for multi-session lifecycle, SQLite state, worktrees, dashboards, and promotion/evaluation gates. Its own README says it is incomplete. CTXORA should not copy this subsystem.

Potential ideas to reference later:

- immutable evaluation records;
- deterministic candidate/baseline comparison;
- atomic active-pointer updates and rollback evidence;
- explicit distinction between orchestration state and harness runtime state.

Reference: [ECC2 README](https://github.com/affaan-m/ECC/blob/5064474d4d762dc9640234a41617cccb79185cec/ecc2/README.md).

## Recommended execution order

### P0 — Target-aware artifact installer

- Complete the installer plan from the earlier audit.
- Model skills, agents, and commands as separate artifact kinds.
- Do not allow a profile to imply all targets.

### P1 — Unified capability registry and validators

- Add typed target/capability definitions.
- Add manifests and cross-reference validation.
- Wire the same registry into install, profile, doctor, and packaging tests.

### P2 — Portable agent package

- Keep the existing three roles.
- Add `ctxora-planner` and `ctxora-researcher`.
- Add target adapters and explicit `--artifact agents` or separate `agents install` workflow.
- Default to read-only roles and avoid fixed model selection.

### P3 — Command synchronization

- Generate/install only CTXORA-native commands supported by each target.
- Validate command-to-tool/agent/skill references.

### P4 — Skill catalog hardening

- Add compatibility and provenance fields.
- Detect duplicates, unavailable dependencies, and host-specific assumptions.
- Introduce catalog import/update validation before vendoring new ECC revisions.

### P5 — Optional automation

- Evaluate watcher-backed refresh and handoff behavior first.
- Add hooks only when a measured workflow gap remains.

## Licensing and provenance

ECC is MIT-licensed and requires preservation of its copyright and permission notice in copies or substantial portions. CTXORA already packages `THIRD_PARTY_NOTICES.md`, `docs/third-party/ECC-LICENSE`, and per-skill `LICENSE.ecc` files. Any copied or materially adapted agent, command, rule, script, schema, or documentation must be added to the same provenance process rather than being copied without attribution.

Source: [ECC LICENSE](https://github.com/affaan-m/ECC/blob/5064474d4d762dc9640234a41617cccb79185cec/LICENSE).

## Final recommendation

The next implementation should not import more ECC content first. It should build the shared capability registry, target-aware artifact planner, and validators. After that foundation exists, add exactly two portable CTXORA agents—planner and researcher—and install them only into explicitly selected, verified targets.

The CTXORA MCP tools were still not exposed in this session, so the audit used the current workspace source and pinned upstream source. After MCP connection, retrieve only installer, agent templates, packaging declarations, command templates, generated-instruction code, and related tests before implementation.

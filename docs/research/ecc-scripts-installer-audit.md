# ECC scripts audit and CTXORA target-aware installer plan

Date: 2026-09-09  
ECC revision reviewed: `5064474d4d762dc9640234a41617cccb79185cec` (ECC 2.2.1, 2026-09-07)

## Scope and conclusion

The review covered the complete `scripts/` tree at the pinned revision: 272 files across root commands, `lib/`, hooks, CI validators, Codex helpers, Discord automation, codemaps, and git hooks. The install architecture was then compared with CTXORA's current client and skill installers.

The main architectural lesson is to keep **content selection** separate from **deployment target selection**:

- A profile selects modules.
- Modules resolve dependencies and declare compatible targets.
- A target registry owns destination paths and capabilities.
- A resolver produces an immutable, target-specific plan.
- An executor applies only that plan and records ownership for repair/uninstall.

CTXORA already separates profile selection from output selection, but it currently copies the same skill selection to every requested target without target capability filtering or adaptation. The correct update is a small target-aware planning layer, not a port of ECC's full lifecycle implementation.

## ECC script structure

| Area | Files | Responsibility |
|---|---:|---|
| `scripts/lib/` | 142 | Shared domain logic, installers, lifecycle, state, adapters, safety |
| `scripts/hooks/` | 53 | Runtime hook entry points and dispatchers |
| `scripts/` root | 51 | User-facing commands and orchestration |
| `scripts/ci/` | 13 | Manifest, command, hook, rule, skill, and security validation |
| `scripts/codex/` | 6 | Codex config/plugin migration and verification |
| Other subdirectories | 7 | Discord, codemaps, and git-hook support |

This is a command-oriented repository with a large shared library. For CTXORA, only the installer boundary and validation patterns are directly relevant.

## ECC install flow

1. **Entry point** parses profile, target, component/module overrides, compatibility flags, and dry-run options.
2. **Manifest loading** validates the profile, module, and component catalogs.
3. **Resolution** expands profile → modules → dependencies, applies additions/removals, checks dependency conflicts/cycles, and filters modules by target compatibility.
4. **Planning** converts the resolved selection into destination operations without mutating the target.
5. **Preflight** checks target root, path containment, existing state, conflicts, platform requirements, and adapter-specific prerequisites.
6. **Apply** stages/copies operations, backs up managed paths, updates host configuration where needed, and rolls back failed mutations.
7. **State** records request, resolution, source revision, target, operations, ownership, and hashes under the `ecc.install.v1` schema.
8. **Validation/repair/uninstall** operate from recorded state rather than guessing from directory contents.

Primary references:

- [Profiles manifest](https://github.com/affaan-m/ECC/blob/5064474d4d762dc9640234a41617cccb79185cec/manifests/install-profiles.json)
- [Modules manifest](https://github.com/affaan-m/ECC/blob/5064474d4d762dc9640234a41617cccb79185cec/manifests/install-modules.json)
- [Components manifest](https://github.com/affaan-m/ECC/blob/5064474d4d762dc9640234a41617cccb79185cec/manifests/install-components.json)
- [Manifest resolver](https://github.com/affaan-m/ECC/blob/5064474d4d762dc9640234a41617cccb79185cec/scripts/lib/install-manifests.js)
- [Plan command](https://github.com/affaan-m/ECC/blob/5064474d4d762dc9640234a41617cccb79185cec/scripts/install-plan.js)
- [Apply command](https://github.com/affaan-m/ECC/blob/5064474d4d762dc9640234a41617cccb79185cec/scripts/install-apply.js)
- [Guided command](https://github.com/affaan-m/ECC/blob/5064474d4d762dc9640234a41617cccb79185cec/scripts/install-guided.js)
- [Executor](https://github.com/affaan-m/ECC/blob/5064474d4d762dc9640234a41617cccb79185cec/scripts/lib/install-executor.js)
- [Lifecycle](https://github.com/affaan-m/ECC/blob/5064474d4d762dc9640234a41617cccb79185cec/scripts/lib/install-lifecycle.js)
- [Install state](https://github.com/affaan-m/ECC/blob/5064474d4d762dc9640234a41617cccb79185cec/scripts/lib/install-state.js)
- [Manifest validator](https://github.com/affaan-m/ECC/blob/5064474d4d762dc9640234a41617cccb79185cec/scripts/ci/validate-install-manifests.js)

## Current CTXORA behavior

CTXORA has two separate installers:

- `ClientInstaller` safely installs the CTXORA MCP server into one client config and tracks the previous owned value.
- `SkillCatalog` resolves an ECC skill profile and copies skills into one or more host directories.

For skill installation:

- `--profile developer` only chooses modules/skills; it does not inherently select hosts.
- No `--target` defaults to `codex`, mapped to `.agents/skills`.
- Repeated `--target` installs the same selection independently into each requested host.
- `--target all` expands to Codex, Claude, Cursor, Gemini, and OpenCode.
- The literal form `-developer` is not the current CLI syntax; the supported form is `--profile developer`.

Therefore, an observed “developer installs every agent” behavior should first be reproduced with the exact command and installed CTXORA version. In the current source, fan-out requires `--target all`, repeated targets, a wrapper/alias that injects targets, or an older/stale package.

Relevant CTXORA source:

- `src/harness_context/skills/catalog.py`: target registry, selection, plan, staging, ownership hashes, rollback.
- `src/harness_context/cli/app.py`: CLI parser and loop over selected targets.
- `src/harness_context/installer/service.py`: MCP client config mutation and ownership restoration.
- `tests/test_skill_catalog.py`: default target, all-target mapping, conflict, prune, and independent-output tests.

## Gaps to fix

1. **Static target map**: target metadata is only a name → directory mapping.
2. **No compatibility model**: skills/modules have no target allowlist, required capabilities, or adapter metadata.
3. **Blind fan-out**: every requested target receives the same files even if its skill format or discovery rules differ.
4. **Plan is executor-shaped**: `install()` both computes operations and applies them; there is no serializable first-class plan boundary.
5. **State is output-centric**: manifests are keyed by destination hash, but do not model a normalized target identity and resolved compatibility decisions.
6. **Two installer concepts**: MCP client installation and skill deployment use different models and terminology; they should share request/plan/result vocabulary without being merged into one executor.

## Proposed architecture

```text
InstallRequest
  profile + module/skill overrides + explicit targets + flags
        |
        v
CatalogResolver
  profile -> modules -> skills
        |
        v
TargetResolver
  registry + capabilities + compatibility/adapters
        |
        v
InstallPlan[]                 (one plan per target)
  operations + conflicts + skipped reasons + state path
        |
        v
TargetExecutor
  preflight -> stage -> atomic replace -> state write -> verify/rollback
```

Suggested types:

- `InstallTarget`: `id`, `skill_root`, `scope`, `capabilities`, `adapter`, `enabled`.
- `InstallRequest`: profile, overrides, explicit target IDs, force/prune/dry-run.
- `ResolvedSelection`: selected modules/skills plus dependency and compatibility decisions.
- `TargetInstallPlan`: target, destination, operations, conflicts, skipped items, provenance.
- `InstallReceipt`: plan digest, installed hashes, previous ownership, verification result.

Rules:

- Require explicit `--target` for mutating installs, or retain `codex` as a documented compatibility default; never infer `all` from the profile.
- `developer` remains a content profile only.
- `all` is an explicit convenience alias expanded by the request parser.
- Resolve and preview every target before applying any target.
- Default multi-target behavior should fail before mutation if any target plan conflicts.
- Keep per-target receipts and never prune files not proven to be CTXORA-owned.
- Adapters transform only when a host actually requires a different layout/metadata format.

## Implementation plan

### Phase 0 — Reproduce and freeze behavior

- Capture exact failing command, `ctxora --version`, workspace tree before/after, and generated installer manifests.
- Add regression tests proving `--profile developer` does not imply `all`.
- Decide whether no target remains a Codex compatibility default or becomes a required argument.

### Phase 1 — Introduce target domain model

- Replace `SKILL_INSTALL_TARGETS` with typed target definitions.
- Add target capabilities and optional adapter ID.
- Move target parsing/validation out of the CLI handler.
- Preserve existing names and paths for backward compatibility.

### Phase 2 — Split planning from execution

- Extract the operation computation from `SkillCatalog.install()` into `plan_install()`.
- Return one immutable plan per target with explicit skipped/incompatible reasons.
- Add a deterministic plan digest and JSON representation for preview and stale-plan detection.

### Phase 3 — Add compatibility resolution

- Extend the pinned catalog schema with module/skill target metadata only where needed.
- Filter incompatible content before operation planning.
- Fail loud for explicitly requested incompatible skills; skip only profile-derived optional content with a reported reason.

### Phase 4 — Transactional multi-target apply

- Preflight all plans first.
- Acquire locks in stable target order.
- Stage all changed skills before replacing any destination.
- Apply per-target operations and write receipts atomically.
- Roll back targets already changed if a later target fails.

### Phase 5 — CLI, migration, and diagnostics

- Make `skills preview` display profile separately from targets.
- Deprecate ambiguous aliases such as `-developer`; print the canonical command.
- Add `skills doctor --target ...` to compare receipts, hashes, and discovery paths.
- Migrate current destination-hash manifests to target-aware receipts lazily on the next successful install.

### Phase 6 — Verification gates

- Unit tests: request parsing, dependency resolution, target filtering, plan stability, ownership, and conflict rules.
- Integration tests: each supported target path, repeated targets, `all`, custom output, prune, force, stale preview, interrupted install, and rollback.
- Packaging test: installed CLI and `npx` launcher produce identical plans.
- Security tests: symlink/path traversal, malicious catalog IDs, lock races, and preservation of user-modified files.

## What CTXORA should copy from ECC

- Declarative profiles/modules with target compatibility.
- Pure resolver before mutation.
- First-class dry-run plan.
- Validated install-state schema and ownership hashes.
- Preflight-all-before-apply and fail-closed path safety.
- Validator tests that keep manifests and target identifiers consistent.

## What CTXORA should not copy

- ECC's large legacy compatibility surface.
- A monolithic lifecycle module with host-specific branches.
- Hook/plugin/config installation in the skill-copy executor.
- Implicit target inference from content profiles.
- Adapters for hosts CTXORA does not support or cannot verify.

## CTXORA MCP note

The session exposed no CTXORA MCP server/resources, so `prepare_context`, `retrieve_context`, `memory_search`, `refresh_workspace`, and `skill_feedback` could not be called. This audit used the local CTXORA source and the pinned upstream ECC source directly. Once the MCP is connected, the first useful query is: “retrieve the skill installer request parsing, target registry, operation planning, ownership manifests, and their tests; exclude skill content.”

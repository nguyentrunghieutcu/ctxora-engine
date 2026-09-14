# CTXORA Domain Language

## Harness

An external coding-agent host that consumes CTXORA capabilities, such as Codex, Claude Code, Cursor, Gemini CLI, or OpenCode.

## Target

A concrete installation destination for one harness and scope. A target owns paths, supported artifact kinds, configuration format, and capabilities.

## Canonical Artifact

A host-neutral CTXORA definition stored once and rendered for one or more targets. Agents, commands, skills, and generated instructions are artifact kinds.

## Harness Adapter

The implementation that converts canonical artifacts and CTXORA configuration into a target's native format. It must not own product workflow logic.

## Artifact Profile

A named selection of canonical artifacts. A profile selects content and never implies installation into all targets.

## Install Plan

An immutable preview of target-specific operations, conflicts, skipped artifacts, provenance, and expected ownership state.

## Install Receipt

The durable record of an applied install plan, including hashes and previous owned values needed for verification, repair, and uninstall.

## CTXORA Console

A local-first operator interface over existing CTXORA application modules. It observes system state and exposes only explicitly approved safe actions; it is not an agent-session control plane.

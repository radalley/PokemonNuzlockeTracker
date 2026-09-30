# ADR-0004: Local Cross-Agent Memory

- Status: Accepted
- Scope: Codex and Claude Code development sessions

## Decision

Use a gitignored `.agent-memory/` directory as the shared local corpus. Keep the
hook implementation and agent instructions tracked. Capture user prompts and
final assistant responses, but not tool output or provider transcript files.

Session hooks inject curated context and bounded relevant excerpts. Durable
architecture remains in intentionally maintained Markdown files. Automatic
logs provide an audit trail and retrieval source without becoming the source of
truth.

The system is local to Lockley sessions and does not depend on either provider's
private memory implementation.

## Evidence

- Shared hook program: `scripts/agent-memory.cjs`
- Codex integration: `.codex/hooks.json`, `AGENTS.md`
- Claude Code integration: `.claude/settings.json`, `CLAUDE.md`
- Verification: capture, paired-turn retrieval, redaction, opt-out, JSON parsing,
  and nested Windows hook launch tests passed on 2026-08-07.

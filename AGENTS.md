# Lockley Agent Instructions

## Shared Local Memory

Lockley uses `.agent-memory/` as a local, gitignored knowledge base shared by
Codex and Claude Code. Project hooks load curated context and relevant excerpts
at the start of a session and record user prompts and final assistant responses.

- Treat memory as fallible recall. Current user instructions and verified code
  or database state take precedence.
- Never place credentials, access tokens, private keys, or personal data in
  memory. Likely secrets are redacted automatically, but that is a safety net,
  not a guarantee.
- A prompt containing `[no-memory]` is private for that turn. Do not reproduce
  its sensitive details in a later memory entry.
- Do not manually copy raw transcripts. Hooks own conversation capture.
- For substantial architecture or feature work, update the curated memory
  before the final response:
  - `CONTEXT.md` when the current system shape changes.
  - `architecture-decisions/ADR-*.md` when a durable choice is made or replaced.
  - `features/*.md` when a feature's behavior or ownership changes.
  - `known-issues.md` for verified operational risks or unresolved defects.
- Keep curated entries concise and include evidence such as relevant file paths,
  schema names, routes, and verification results.
- If hook context is unavailable, run `node scripts/agent-memory.cjs context`.
  Use `node scripts/agent-memory.cjs search "topic"` for older relevant history.

The memory store is supporting context, not a source for current external facts.

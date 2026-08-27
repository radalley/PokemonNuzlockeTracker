# Lockley Agent Memory

Lockley keeps a project-specific memory corpus in `.agent-memory/`. The corpus
is local and gitignored, while the hook program and agent instructions are
tracked so Codex and Claude Code use the same conventions.

## What Is Captured

- User prompts submitted from a Lockley Codex or Claude Code session.
- The final assistant message for each turn.
- Session start, resume, compaction, and end metadata.
- Curated architecture decisions, feature notes, project principles, known
  issues, and glossary entries written intentionally by an agent.

Tool inputs, tool outputs, environment variables, and full provider transcript
files are not copied into the memory store. Likely credentials are redacted,
but secrets should never be intentionally placed in memory.

Add `[no-memory]` anywhere in a prompt to skip both that prompt and its matching
assistant response.

## How Recall Works

At session start, the hook injects the curated project context, recent durable
decisions, feature notes, and a small number of recent conversation excerpts.
Before each later prompt, a bounded lexical search retrieves matching entries
from the local corpus. All history remains on disk, but only relevant excerpts
are added to the model context.

Durable decisions belong in curated Markdown files. Conversation logs are an
audit trail and retrieval source, not the canonical architecture description.

## Layout

```text
.agent-memory/
  CONTEXT.md
  project-principles.md
  known-issues.md
  glossary.md
  architecture-decisions/
  features/
  session-logs/
    codex/
    claude/
  state/
    events.jsonl
    sessions.json
  config.json
```

## Commands

```powershell
node scripts/agent-memory.cjs init
node scripts/agent-memory.cjs status
node scripts/agent-memory.cjs context
node scripts/agent-memory.cjs search "badge architecture"
node --test scripts/agent-memory.test.cjs
```

`init` is idempotent and never overwrites existing curated files.

## Agent Integration

Codex reads `AGENTS.md` and `.codex/hooks.json`. Project hooks require trust;
review them when Codex prompts, or use `/hooks` in the Codex CLI. Start a new
Lockley task after changing hook configuration.

Claude Code reads `CLAUDE.md` and `.claude/settings.json`. Its project hook uses
the same Node program and memory directory. Claude may ask for approval after a
hook configuration change.

Codex's built-in local memories may be enabled separately, but they are not the
shared source of truth because Claude Code cannot read that private Codex store.

## Retention And Maintenance

Conversation entries are append-only and are not automatically deleted. The
retriever reads a bounded number of recent events, while curated files preserve
long-lived decisions. Review or remove local logs manually when needed, and
never publish `.agent-memory/` without inspecting it first.

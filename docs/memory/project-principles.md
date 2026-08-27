# Project Principles

- Prefer normalized, event-driven domain data over page-level identity maps.
- Preserve authenticated and guest-mode behavior when a workflow supports both.
- Treat `game_id`, `version_group_id`, run, attempt, and user ownership as
  explicit context rather than inferring them from presentation state.
- Investigate backend and local database health before diagnosing empty frontend
  data as an authentication failure.
- Make large architecture changes deliberately and verify the migration path,
  API behavior, frontend behavior, and existing data.
- Memory is context, not authority. Current code, database state, tests, and the
  user's latest instruction win when they disagree with a stored note.

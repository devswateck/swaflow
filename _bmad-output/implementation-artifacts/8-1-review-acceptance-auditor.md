# Acceptance Auditor Prompt

Review target:
- Story: `_bmad-output/implementation-artifacts/8-1-blindaje-de-inbox-contra-estado-obsoleto.md`
- Diff scope: `frontend/src/App.tsx`, `_bmad-output/implementation-artifacts/8-1-blindaje-de-inbox-contra-estado-obsoleto.md`, `_bmad-output/implementation-artifacts/sprint-status.yaml`

Context:
- `baseline_commit: 595b380d6111b59e727b01d978cf27ebc2b6a335`
- Story acceptance criteria cover stale inbox refreshes, selection races, realtime bounce-back, cross-thread message send behavior, deterministic clearing on disappearing conversations, and stale error suppression.

Constraints:
- Review against the story spec and project context only.
- Output findings as a Markdown list.
- Each finding must include the violated AC or constraint and evidence from the diff.

Current diff summary:
- 3 files changed
- 111 insertions
- 65 deletions

Review the current diff adversarially and output only findings with evidence.

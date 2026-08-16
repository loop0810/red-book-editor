## 1. Suggestion history contract and persistence

- [x] 1.1 Add server-side `SuggestionStatus` and extend `FieldSuggestionDto` with persisted status metadata while preserving old response parsing.
- [x] 1.2 Add `FieldSuggestionModel`, indexes, and Alembic migration with note/account foreign keys and cascade behavior.
- [x] 1.3 Implement repository operations to create, list, derive stale status from current note digests, and idempotently resolve suggestions.

## 2. Suggestion history API

- [x] 2.1 Persist successful field regeneration results for saved notes without changing the current NoteModel draft.
- [x] 2.2 Add note-scoped list and status-update endpoints with validation for accepted/rejected/stale transitions and digest conflicts.
- [x] 2.3 Add server unit and PostgreSQL integration tests for persistence, cross-session listing, stale detection, account/note scope, and non-mutating resolution.

## 3. Flutter models and API integration

- [x] 3.1 Parse and serialize suggestion status and expose list/status API methods in `app_core`.
- [x] 3.2 Extend `EditorSessionState` to retain multiple candidates per field, distinguish pending/history entries, and preserve conflict semantics.
- [x] 3.3 Add optional note editor callbacks for loading suggestion history and synchronizing candidate status, with graceful local fallback.

## 4. Precise client Diff

- [x] 4.1 Extend `DiffSegment` with before/after text ranges and update tokenization to produce stable UTF-16 code-unit spans.
- [x] 4.2 Preserve field-specific behavior: body semantic boundaries, short-text character spans, and hashtag set differences without fake offsets.
- [x] 4.3 Add app_core Diff tests for changed ranges, Unicode text, unchanged spans, and set-based hashtags.

## 5. Editor history and recovery UX

- [x] 5.1 Load persisted suggestions when opening a saved note and seed session conflict baselines from the current draft.
- [x] 5.2 Add a candidate history panel showing pending, accepted, rejected, and stale candidates; keep only pending candidates actionable.
- [x] 5.3 Sync explicit accept/reject decisions, handle stale/conflict responses, and ensure saving the draft remains the only content mutation path.
- [x] 5.4 Add widget tests for reopening candidates, multiple candidates, status display, conflict handling, and precise Diff ranges.

## 6. Contract, documentation, and verification

- [x] 6.1 Update `docs/contracts/CONTENT_WORKFLOW_CONTRACT.md` and related OpenSpec main specs after implementation semantics are confirmed.
- [x] 6.2 Run server format, typecheck, unit, migration, and integration checks; restore PostgreSQL to Alembic head.
- [x] 6.3 Run Flutter format, analyze, root/package tests, OpenSpec strict validation, and `git diff --check`.

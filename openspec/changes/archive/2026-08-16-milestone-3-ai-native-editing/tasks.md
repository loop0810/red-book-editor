## 1. Domain and contract foundations

- [x] 1.1 Define normalized editable field names and a typed `FieldSuggestion` contract for title, body, hashtags, and cover copy, including suggestion ID, base digests, candidate value, review metadata, and source evidence.
- [x] 1.2 Add bounded field metadata to review findings and preserve backward-compatible parsing for legacy findings without a field.
- [x] 1.3 Add server and Dart tests for field suggestion JSON round-tripping, digest stability, legacy review parsing, and candidate value shapes.

## 2. Server-side target-only field suggestions

- [x] 2.1 Refactor content workflow field regeneration to merge the candidate into a temporary full draft for validation while returning only the requested field suggestion.
- [x] 2.2 Update the field regeneration HTTP response contract and error mapping, including missing style form and invalid field cases; keep the existing save and export contracts unchanged.
- [x] 2.3 Make deterministic and claim audit findings associate new results with normalized fields and expose target-field evidence in suggestion responses.
- [x] 2.4 Update unit, API, and integration tests to verify target-only responses, preservation of other fields, full-draft review, and no database migration requirement.

## 3. Flutter app-core interaction models

- [x] 3.1 Add `FieldSuggestion` and editor-session models with pending status, base snapshots, conflict detection, and candidate review/evidence accessors.
- [x] 3.2 Add client-side field Diff utilities for paragraph/sentence body diffs, short-text diffs, and hashtag set diffs without returning HTML from the server.
- [x] 3.3 Migrate the API Client and note-creation callbacks from full-draft field regeneration responses to target-only suggestions.
- [x] 3.4 Add SSE reconnect support using the last event sequence, terminal-event deduplication, and resume/retry API wiring.
- [x] 3.5 Add app-core tests for target-only requests/responses, digest conflicts, Diff output, SSE reconnect cursors, and resume failure handling.

## 4. Flutter editor experience

- [x] 4.1 Track AI baseline, current controller values, pending suggestions, and dirty/conflict state independently inside `NoteEditorPage`.
- [x] 4.2 Capture a baseline from newly generated drafts and use the earliest available saved version when reopening a draft; hide the edit Diff when no reliable baseline exists.
- [x] 4.3 Add per-field candidate panels with current-versus-suggestion Diff, explicit accept/reject actions, and a conflict choice that never silently overwrites user text.
- [x] 4.4 Ensure accepting a suggestion changes only the target field, preserves other fields and style form, and sends the resulting full draft through the existing explicit save/review flow.
- [x] 4.5 Add field-level source evidence and review finding navigation, showing matched text without pretending to know an exact character range.
- [x] 4.6 Add widget tests for pending suggestions, manual edits during generation, accept/reject, stale-base conflicts, Diff visibility, and field review navigation.

## 5. Generation recovery and documentation

- [x] 5.1 Add retry and continue-running actions to the generation page, preserving the failed/interrupted run ID and SourceExperience until the user finishes or discards the attempt.
- [x] 5.2 Verify cancellation, retry, resume, and SSE reconnect never open a cancelled or failed run as a successful editable result.
- [x] 5.3 Update `docs/contracts/CONTENT_WORKFLOW_CONTRACT.md` with the breaking field suggestion response, session-only lifecycle, Diff semantics, field evidence, and recovery behavior.
- [x] 5.4 Update the main OpenSpec specifications and roadmap only after implementation behavior and verification match this change.

## 6. Verification

- [x] 6.1 Run server lock-check, format-check, typecheck, unit tests, integration tests, and evaluation validation.
- [x] 6.2 Run Flutter format, analyze, root tests, and all package tests, including the new editor interaction coverage.
- [x] 6.3 Run `openspec validate milestone-3-ai-native-editing --strict`, inspect the final diff, and confirm no database migration or sensitive artifact was added.

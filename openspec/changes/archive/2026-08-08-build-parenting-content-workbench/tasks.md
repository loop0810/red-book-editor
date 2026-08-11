## 1. Monorepo foundation

- [x] 1.1 Create the root monorepo layout for `client`, `server`, `docs`, and existing `openspec` planning
- [x] 1.2 Add root README and AGENTS guidance for Flutter, Python server, shared contracts, documentation routing, and validation commands
- [x] 1.3 Add documentation index directories for product, contracts, client, server, decisions, and learning

## 2. Flutter client foundation

- [x] 2.1 Initialize the Flutter iOS/Android app under `client/`
- [x] 2.2 Configure the Dart workspace and create only the initial core, design-system, account, note, asset, and publish-record packages
- [x] 2.3 Add client routing, dependency injection, API client boundary, error state model, and Riverpod-based application state
- [x] 2.4 Add client-side draft preservation for unsent source experiences and failed generation requests
- [x] 2.5 Add Flutter formatting, analysis, unit/widget test, and iOS/Android verification commands

## 3. Python server foundation

- [x] 3.1 Initialize the Python server under `server/` using the reference modular-monolith layout with `src/`, `tests/`, and `migrations/`
- [x] 3.2 Configure the Python version, FastAPI runtime, SQLAlchemy, Alembic, PostgreSQL connection, Ruff, mypy, pytest, and locked dependencies
- [x] 3.3 Add application factory, health endpoints, request IDs, structured logging, dependency injection, and safe error responses
- [x] 3.4 Add server Makefile commands for lock check, formatting, type checking, tests, migrations, and local run
- [x] 3.5 Add model, storage, and external-provider configuration with environment validation and no secret logging

## 4. Cross-platform contracts

- [x] 4.1 Define account, content-column, source-experience, note-draft, asset, review-result, publish-record, and metric DTOs
- [x] 4.2 Define API endpoints, request/response examples, identifiers, status values, errors, retry behavior, and blocking-review semantics in `docs/contracts/`
- [x] 4.3 Implement matching Python DTOs and Flutter models from the shared contract
- [x] 4.4 Add contract tests covering successful responses, validation failures, generation failures, and blocking review results

## 5. Server persistence and domain modules

- [x] 5.1 Create domain ports and entities for accounts, columns, source experiences, notes, versions, assets, publication records, and metrics
- [x] 5.2 Implement PostgreSQL repositories and Alembic migrations for the V1 data model
- [x] 5.3 Implement account profile and content-column APIs with account-scoped context loading
- [x] 5.4 Implement note draft, version, and publication-record APIs
- [x] 5.5 Implement account-scoped asset upload, metadata, ordering, download, and deletion APIs

## 6. Agent content workflow

- [x] 6.1 Define the provider-agnostic content-generation and content-review interfaces in the server domain layer
- [x] 6.2 Implement structured source-experience normalization without inventing key facts
- [x] 6.3 Implement topic, title, body, hashtag, cover-copy, and image-suggestion generation with validated structured output
- [x] 6.4 Implement selective field regeneration without overwriting untouched draft fields
- [x] 6.5 Implement provider timeout, malformed-output, retry, and source-preservation behavior
- [x] 6.6 Add model adapter configuration and test doubles for deterministic server tests

## 7. Safety review

- [x] 7.1 Define review result, risk level, matched text, reason, and recommended-action models
- [x] 7.2 Implement deterministic checks for diagnosis, medication, dosage, treatment claims, fabricated facts, and exaggerated guarantees
- [x] 7.3 Implement model-assisted checks for account scope, unsupported claims, and anxiety-inducing language
- [x] 7.4 Block export of drafts with blocking risks while allowing warning-level drafts after user review
- [x] 7.5 Add tests for common-care experiences that may be recorded without diagnosis or medication advice

## 8. Flutter account and note workflow

- [x] 8.1 Build account profile settings for positioning, age range, current baby month, tone, boundaries, and common expressions
- [x] 8.2 Build content-column management and the initial 0–2 year parenting column presets
- [x] 8.3 Build the source-experience form for month, scenario, actual actions, observations, notes, and optional images
- [x] 8.4 Build the note generation screen with loading, failure, retry, and blocking-review states
- [x] 8.5 Build the note editor with field-level editing, version history, selective regeneration, and manual review display
- [x] 8.6 Add copy actions for title, body, and hashtags with mobile clipboard feedback

## 9. Flutter assets and publication workflow

- [x] 9.1 Build image selection, upload progress, preview, deletion, and ordering
- [x] 9.2 Build cover-copy and image-suggestion display
- [x] 9.3 Build asset download/export for manual Xiaohongshu publishing
- [x] 9.4 Build draft list, saved-state recovery, and version history views
- [x] 9.5 Build manual publication status, publication time, link, and notes
- [x] 9.6 Build optional performance metric entry for views, likes, saves, and comments

## 10. Verification and documentation

- [x] 10.1 Add client tests for account isolation, source-fact preservation, selective regeneration, and manual-publishing boundaries
- [x] 10.2 Add server tests for medical-risk blocking, unsupported claims, asset access, persistence, and draft recovery
- [x] 10.3 Run Flutter format, analyze, unit/widget tests, and package tests on the client
- [x] 10.4 Run Python lock check, format check, type check, unit tests, migrations, and PostgreSQL integration tests on the server
- [x] 10.5 Verify the complete iOS/Android workflow from experience entry through copy/export and publication recording
- [x] 10.6 Record the implemented architecture and learning notes in the repository documentation structure

## 1. Regression and repository safety

- [x] 1.1 Update the PostgreSQL field-regeneration integration test to assert the target-only `FieldSuggestion` response and reject legacy full-draft fields.
- [x] 1.2 Expand the `ai-editing-interactions` Purpose text so strict OpenSpec validation passes.
- [x] 1.3 Add root `key.json` to `.gitignore` and verify the existing local key remains untracked and unstaged.

## 2. Baseline runner and automatic hard-failure checks

- [x] 2.1 Change the `make eval-baseline` command to invoke the runner with a module-safe import path from `server/`.
- [x] 2.2 Unwrap nested `FinalizeArgs` results in automatic hard-failure text extraction while preserving compatibility with flat legacy drafts.
- [x] 2.3 Add unit coverage for nested results, failed runtime classification, and non-false-positive fact coverage.

## 3. Fact coverage and Agent convergence

- [x] 3.1 Make source fact validation match independently identifiable Chinese fact clauses with limited safe normalization while retaining exact action and safety boundaries.
- [x] 3.2 Require `critique_draft` to return `passed=false` whenever unresolved fact, forbidden-expression, tag-count, or rich-text issues remain; add regression tests.
- [x] 3.3 Restrict precise and trending tag suggestions to topic-matching entries, keeping generic tags available as fallback.
- [x] 3.4 Replace unsafe or overly concrete style-profile examples with neutral templates that do not invent medical backing, efficacy, platform outcomes, brands, or event details.

## 4. Verification and evaluation records

- [x] 4.1 Run server lock, format, type, unit, integration, and evaluation validation checks with PostgreSQL restored to Alembic head afterward.
- [x] 4.2 Run Flutter format, analyze, root tests, package tests, OpenSpec strict validation, and `git diff --check`.
- [x] 4.3 Run the same five-case DeepSeek baseline with local `key.json` loaded only into the environment, summarize status/failure codes/hard failures without recording the key, and preserve a new independent run record.
- [x] 4.4 Update the baseline report now with actual verification results and remaining limitations.
- [x] 4.5 After this change is archived, update `docs/error/change-fix-history.md` so the record points to the final archive path.

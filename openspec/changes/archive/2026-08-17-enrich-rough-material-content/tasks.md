## 1. Freeze the rough-material contract

- [x] 1.1 Update the content workflow contract and note-creation documentation to define raw material as rough, user-authored input rather than a publishable draft.
- [x] 1.2 Define the internal distinction between confirmed facts, observations, constraints, user opinions, and unsupported inferences without adding new client input fields.
- [x] 1.3 Update the new-content page labels and hints so users know keywords,流水账 and incomplete descriptions are valid input.

## 2. Build the enrichment-oriented generation flow

- [x] 2.1 Update the Content Agent instructions so it plans from extracted facts and focus before composing the body, and explicitly treats raw material as notes to rewrite rather than text to quote.
- [x] 2.2 Define and enforce the allowed enrichment boundary: transitions, reordering, hooks, structure and neutral summaries are allowed; unsupported concrete experiences, outcomes, emotions and professional claims are not.
- [x] 2.3 Update each style profile's writing guidance and examples to require a distinct opening and preserve style-specific structure without introducing a shared copy-paste template.
- [x] 2.4 Apply the same rough-material semantics to body field regeneration and restyling so a selected field is rewritten from the current context instead of returned verbatim.

## 3. Add anti-repetition and quality gates

- [x] 3.1 Implement a normalized source-overlap check that detects long copied spans and copied openings while protecting short topics, names, numbers and necessary factual phrases.
- [x] 3.2 Replace length-only success criteria with complementary checks for fact coverage, structural richness, distinct opening, source overlap and existing safety boundaries.
- [x] 3.3 Feed source-overlap and enrichment failures back into the Agent revision loop with actionable rewrite instructions, and fail without a pseudo-success draft when the revision budget is exhausted.
- [x] 3.4 Add deterministic tests for exact opening reuse, paragraph-splitting reuse, natural paraphrase, short facts and required factual phrases.

## 4. Align offline behavior and persistence boundaries

- [x] 4.1 Update the stub generator to demonstrate transformation of concise material without treating the stub output as a verbatim source projection.
- [x] 4.2 Verify ContentBrief persistence, failed-run recovery and draft restoration continue to preserve the original material while exposing only the generated user result in the editor.
- [x] 4.3 Verify no model raw response, internal material plan or overlap diagnostics are added to ordinary client payloads or user-visible editor fields.

## 5. Validate end-to-end content usefulness

- [x] 5.1 Add server regression cases covering keyword input, one-sentence input,流水账 input, mixed facts and constraints, and input that already contains polished prose.
- [x] 5.2 Add model-gateway/Agent tests proving the output keeps source facts, avoids unsupported additions, and does not begin with a copied source paragraph.
- [x] 5.3 Add Flutter widget and API-client tests for the revised input hint and unchanged ContentBrief request shape.
- [x] 5.4 Add evaluation cases and scorecard dimensions for source transformation, enrichment usefulness, factual coverage and source-overlap rate.
- [x] 5.5 Run client/server validation and strict OpenSpec validation before handing the change to implementation review.

## 1. Freeze the product contract

- [ ] 1.1 Update the current product and API contract docs to state the content-first core, user-facing output boundary, and non-goals.
- [ ] 1.2 Define `ContentBrief`, `domain_id`, domain context, and the user result projection in the cross-platform contract.
- [ ] 1.3 Define compatibility rules for converting legacy `SourceExperience` payloads into the new content brief.
- [ ] 1.4 Define the boundary between primary content editing and secondary candidate/version/runtime capabilities.

## 2. Establish domain strategy packs

- [ ] 2.1 Add the domain strategy pack port and a versioned parenting strategy pack contract.
- [ ] 2.2 Move parenting-only input, style context, quality rules, and safety policy references behind the parenting pack boundary.
- [ ] 2.3 Validate that an unavailable or disabled domain cannot silently fall back to another domain.
- [ ] 2.4 Add tests proving the generic content workflow can accept a future-domain-shaped context without a new top-level workflow branch.

## 3. Rework content generation around focus

- [ ] 3.1 Adapt the generation service and prompts to accept `focus` as the highest-priority content subject.
- [ ] 3.2 Distinguish focus, source facts, opinions, and constraints in the internal content context and fact ledger.
- [ ] 3.3 Add deterministic and model-backed checks that title candidates and topic angle represent focus before secondary constraints.
- [ ] 3.4 Add regression cases such as “宝宝周岁宴 / 不办大型酒宴” and verify the title centers on “宝宝周岁宴”.

## 4. Separate internal quality from user-facing results

- [ ] 4.1 Keep trace, Fact Ledger, Claim Audit, policy findings, and AgentRun diagnostics in internal/server-facing models or authorized diagnostics.
- [ ] 4.2 Add a user-facing issue projection with category-specific, concise, actionable messages.
- [ ] 4.3 Change safety evaluation so ordinary content and natural paraphrases do not produce irrelevant medical/medication warnings.
- [ ] 4.4 Preserve blocking safety and export gates for real domain-policy violations.
- [ ] 4.5 Add tests for ordinary non-medical content, medical context without advice, diagnosis/medication requests, and fabricated high-risk claims.

## 5. Simplify the Flutter product flow

- [ ] 5.1 Replace the primary parenting-only input form with focus, raw material, optional domain context, images, and style selection.
- [ ] 5.2 Remove Agent execution trace, model-step summaries, full Claim Audit, and detailed internal findings from the default editor page.
- [ ] 5.3 Keep title, body, hashtags, image suggestions, optional cover copy, edit, copy, save, and retry as the primary result flow.
- [ ] 5.4 Move version history, Diff, candidate history, publish records, and complex asset operations behind secondary entry points or defer their UI.
- [ ] 5.5 Replace hardcoded account/column IDs with real account and enabled-column selection from the account context.
- [ ] 5.6 Add widget tests that assert the primary page shows content results and does not show Agent trace or irrelevant audit text.

## 6. Align persistence and API paths

- [ ] 6.1 Make the main generation, async AgentRun, save, field regeneration, and restore paths use the same content brief, domain context, quality policy, and user result projection.
- [ ] 6.2 Preserve internal audit snapshots and run diagnostics without exposing them as the default client presentation model.
- [ ] 6.3 Add API contract tests for focus preservation, domain context resolution, blocking issue projection, and legacy payload compatibility.

## 7. Update evaluation and living documentation

- [ ] 7.1 Update baseline cases and scorecards to measure focus alignment, account/ style fit, fact fidelity, usefulness, and user editing cost.
- [ ] 7.2 Remove Agent trace visibility from product acceptance criteria while retaining internal trace requirements for evaluation and debugging.
- [ ] 7.3 Synchronize `openspec/specs/`, `docs/product/`, `docs/contracts/`, `docs/decisions/`, `docs/learning/`, and the Agent roadmap with this change.
- [ ] 7.4 Run strict OpenSpec validation and document unresolved implementation gaps before starting code work.
- [ ] 7.5 Update evaluation, async-run, and editing-interaction specifications so internal Agent capabilities cannot become accidental C-end requirements.

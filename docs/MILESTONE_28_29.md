# Phase 4 — Replacement, saved papers and revisions

Planned objectives: 28–29 October 2026. Implemented early at the student's request on 25 October. Version 0.4.0. Functionality takes priority over a visual redesign.

## Delivered

- [x] Choose a numbered question and inspect compatible unused alternatives.
- [x] Match subject, unit, type, marks and difficulty exactly; preserve demo/production eligibility.
- [x] Recheck candidate content/revision on Apply; reject stale alternatives.
- [x] Revalidate the whole paper after replacement, with no changes to balance or blueprint.
- [x] Save full, immutable snapshots atomically and safely retry an identical save.
- [x] Browse saved history and reopen both student/key previews after restart.
- [x] Preserve historical question/answer content after bank changes.
- [x] Create new unsaved revision copies linked to saved parents; save without overwriting originals.
- [x] Preserve Review when setup/bank changes, and protect unsaved work at discard/close boundaries.
- [x] Validate corrupt or unsupported saved records before showing them.
- [x] Keep schema version 2 and existing data paths; no Phase 3 migration required.
- [x] Run 114 automated tests, source compilation, GUI import and command-line smoke checks.
- [ ] Complete Phase 4 Windows GUI interaction, scaling and keyboard acceptance.
- [ ] Observe representative users and record completion/ease/satisfaction.

## User workflow

Generate → Review → select question number → Replace question → inspect candidate → Apply replacement → Save paper.

Saved papers → select entry → Open paper (read-only), or Create revision → Replace question → Save paper. The old paper and new revision remain independent entries. A revision retains the original blueprint; new blueprint requirements require a newly generated paper.

## Data and correctness

The saved JSON includes the complete blueprint, ordered question snapshots, options, answers, rubrics, eligibility flags, totals, timestamps, version and original seed. Reopen reads this data directly rather than recreating it from current bank records. Optional parent ID and replacement count identify revisions and manual replacement activity.

The initial seed does not reconstruct replacements. Exact saved contents are authoritative. Review state inside an old paper is historical; saving/reopening does not claim its questions are still approved in the current bank. New alternatives must satisfy current eligibility. There is no authentication, encryption, paper deletion UI or per-replacement audit trail.

## Verification and next milestone

See TEST_RESULTS.md for automated evidence and the Windows manual checklist. Earlier Windows generation and blueprint persistence were confirmed by the user; that evidence does not verify the new controls. PDF export, backup/restore, final Windows acceptance, user testing and visual polish remain next work.

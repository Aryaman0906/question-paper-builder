# Desktop workspace — 0.6.0

The redesign keeps the working Python/Tkinter architecture and gives the app a consistent visual language. No web server, browser login, JavaScript frontend or additional GUI dependency is needed.

## Visual system

| Element | Treatment |
|---|---|
| Navigation | Dark navy sidebar, numbered destinations, active-page highlight, Ctrl+1–7 shortcuts |
| Workspace | Light grey canvas, white cards, clear page titles and short descriptions |
| Primary actions | Indigo buttons for creating, saving, approving and generating |
| Typography | Segoe UI on Windows; DejaVu Sans fallback; monospace text for code-bearing fields |
| Data tables | Taller rows, alternating backgrounds, readable selection state and internal scrollbars |
| Previews | White paper surface, section hierarchy, amber demonstration warning, preserved source text |
| Small windows | Reflowing overview cards, scrollable pages/sidebar and focus-driven control visibility |

The overview reads actual database records. “Ready for exams” counts only active, approved, non-demo questions; it is not a guarantee that every blueprint can be fulfilled. Availability still checks the exact selected blueprint.

The question bank puts the prompt immediately after the ID, uses compact review labels and retains complete content in the lower detail panel. The divider can be dragged to resize the table and detail areas. The editor, CSV importer, blueprint editor, replacement dialog and backup dialog share the same native styles.

## Reference sites

Reviewed on 25 October 2026, using the examples supplied by the user:

- [Create Question Paper](https://createquestionpaper.in/): prominent creation entry point and clear user tasks.
- [QP Creator](https://qpcreator.com/): clear primary action and grouped feature information.
- [Examin8](https://examin8.com/): setup, curation/review and export as a guided sequence.
- [Eklavvya question paper generator](https://www.eklavvya.com/free-question-paper-generator/): distinct setup, generation and preview areas.

These informed the workflow hierarchy. The palette and desktop layouts are original; no logos, screenshots, brand assets or marketing claims were copied. Website-only AI, payment and account features were not added.

## Actual application screenshots

Rendered with Tk 8.6 on Linux using bundled demo questions. Windows uses its installed Segoe UI font and native window decorations, so details can differ.

![Workspace overview](images/workspace.png)

![Student paper in Paper studio](images/paper-studio.png)

## Update and acceptance

Close the running app and replace the application code with 0.6.0. Run `py -3.12 main.py`; the title bar should show 0.6.0. Keep the default database in its existing location. No schema migration or dependency installation is required by this redesign.

Automated evidence is in [TEST_RESULTS.md](TEST_RESULTS.md). Before submission, check the following on the user's Windows computer:

- [ ] Open each sidebar page at the usual screen size and 125%/150% Windows scaling.
- [ ] Use Tab/Shift+Tab, Ctrl+1–7 and the page scrollbars; verify that focused controls remain reachable.
- [ ] Edit a coding question, scroll to marking guidance, save and re-open it.
- [ ] Load a blueprint, check availability, generate, replace a question and save a revision.
- [ ] Export student and teacher PDFs; confirm the correct audience and indentation.
- [ ] Make and restore a disposable backup, confirming the recovery copy and reopen behavior.
- [ ] Observe a teacher completing a paper and record any confusing labels or steps before collecting satisfaction feedback.

The redesign changes presentation. It does not change selection rules, saved-paper immutability, PDF formatting, backup safeguards or demo eligibility.

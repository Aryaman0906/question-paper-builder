# CSV import guide

Use **Question bank → Save CSV template** or `data/Question_Import_Template.csv`. Fill a copy and save as comma-separated UTF-8 CSV. XLSX and legacy ANSI files are not supported. A UTF-8 BOM is accepted.

## Columns

All 15 header names must appear exactly once; column order may change. Unknown columns are rejected.

| Columns | Rules |
|---|---|
| id | 1–64 ASCII letters, numbers, dots, underscores or hyphens; first character a letter/number. Unique even against archived records. |
| subject, unit | Required text. Labels should match the blueprint exactly; comparison is case-sensitive. |
| topic | Optional text. |
| kind | Exactly `MCQ`, `Short answer` or `Coding`. |
| marks | Positive ASCII whole number, at most nine digits. No decimals, signs or scientific notation. |
| difficulty | Exactly `Easy`, `Medium` or `Hard`. |
| prompt, answer, rubric | Required text. Multiline content and indentation are preserved. |
| option_a, option_b, option_c, option_d | MCQ: four nonempty, distinct option texts. Other types: leave blank. |
| correct_option | MCQ: A, B, C or D (lowercase accepted). Other types: leave blank. |

Files are limited to **2 MiB and 1,000 nonempty records**. Very large individual CSV fields can also be rejected by Python's CSV parser. Blank records with the correct number of columns are skipped. Missing/extra columns or unclosed quotes block the import.

Spreadsheet software normally quotes commas, double quotes and line breaks correctly when saving CSV. When editing by hand, quote cells containing commas/newlines and double any quotation marks inside the quoted cell. Do not replace code indentation with escaped text such as literal `\n`.

## Preview and commit

The preview displays physical **end line**, question ID, status, prompt and row errors. End line identifies the last line of a record, including records whose quoted cells span several lines. Select a row to inspect its full question, answer, rubric and options.

Preview never writes to the database. Fix all row/file errors in the source CSV and use **Reload file**. Import is enabled only when every record is valid. At confirmation, the exact previewed records are rechecked against the current database under a write lock. If any record is invalid or a database insert fails, the entire batch is rolled back. Nothing is partially imported. If the external file changes after preview, reload it to use the new contents.

Every imported record is a new non-demo draft awaiting human review. CSV has no approval or demo-origin columns. It cannot update an existing ID, including an archived ID. Reimporting the same file fails rather than duplicating it. For corrections to an existing question, use **Edit**.

Duplicate content means the same subject and normalized prompt: Unicode NFC, consistent newlines and outer whitespace removed. Internal indentation and case remain significant. This does not detect paraphrases.

## Supplied examples

- `Example_Questions.csv`: three valid drafts, including an MCQ, multiline coding answer and Unicode text. The coding answer returns 5 for `A cup of TEA`, 0 for an empty string and 0 for `rhythm`.
- `Invalid_Example_Do_Not_Import.csv`: one valid row and a negative-mark row; the whole file is blocked. After importing the valid example, duplicate IDs are also reported.

Use a fresh practice database when demonstrating imports repeatedly. Do not delete your working database to reset a demo.

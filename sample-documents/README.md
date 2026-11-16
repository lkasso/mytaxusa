# Sample documents: Milo Ledger

Fictional documents for the lab. All PDFs are fictional and not for filing.

Taxpayer: Milo Ledger, Single, Los Angeles. Filing the 2026 return. The 2025 return is the prior year.

| Folder | What it is | Expected review |
| --- | --- | --- |
| `00-prior-year-2025` | Milo's 2025 return: one W-2 (wages $58,000), no dependents. | n/a |
| `01-milo-clean` | 2026 return that matches its W-2 and 1099-INT. | `pass`, no client questions |
| `02-milo-needs-review` | 2026 return with the W-2 entered wrong and a new dependent. | `hold`, questions about the W-2 and Avery |

`app/seed.py` loads these into every new browser session when the app starts through `run.py`: three returns on the Saved returns page, documents attached, prior year linked. Nothing is entered or uploaded by hand. Tests and other app factories do not seed.

To reload them, stop the server, delete `instance/practice.sqlite3` and restart it. No cookie clearing is needed. To enter a case by hand instead, create a return from its `entries.json`, upload its PDFs, and link the 2025 return under Prior year on the Documents page. Do not apply extracted W-2 values: in the needs-review case the mismatch is the point.

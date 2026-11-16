# MyTaxUSA

MyTaxUSA is a federal tax preparation application owned and operated by Fake, Inc. This repository contains its server-rendered frontend, Python backend, calculation rules, document processing, and SQLite persistence. It also contains the integration scaffold for an agent-based return review.

## Application flow

Users create or reopen a return from the welcome screen. The return workflow has five sections:

| Section | Function |
| --- | --- |
| Personal | Taxpayer and spouse details, filing status, and dependents. |
| Income | W-2 wages, taxable interest, unemployment compensation, and withholding. |
| Deductions / Credits | Standard deduction and supported dependent credits. |
| Misc | Federal estimated payments, extension payments, and remaining scope questions. |
| Summary | Calculated totals, diagnostic findings, review results, and Form 1040 download. |

Save and Continue validates and saves the current page. Previous Page saves valid entries; invalid edits are not saved when navigating back. Section navigation displays saved values. Returns can be reopened, cleared, or deleted.

Dependent and employer forms are added individually, up to six of each per return. Interest and unemployment each have a Yes/No question. Their amount fields are required only when the corresponding answer is Yes. Unsupported dropdown choices are disabled and labeled Not supported; the backend also rejects those choices.

## Supported calculations

The implemented rules support Single and Married Filing Jointly returns with W-2 wages, taxable interest, and unemployment compensation. They calculate a base standard deduction, progressive income tax, and a limited nonrefundable credit for qualifying children and older qualifying-child dependents. Withholding, estimated payments, and extension payments contribute to the balance calculation.

The ruleset is `classroom-2026-v1`. The tax year is 2026 and the prior year is 2025. The numbers are fixed classroom values (including a $14,600 Single or $29,200 joint base standard deduction), not real 2026 figures. Dependent qualification returns eligible, ineligible, or needs_information.

State returns, itemized deductions, business and rental income, investment sales, cryptocurrency calculations, refundable credits, qualifying-relative dependents, credit phaseouts, and special-case tax treatment are outside the implemented scope. Additional standard deductions for age or blindness and returns for filers claimed by someone else are also unsupported. The rules do not implement all federal tax requirements, and the application does not transmit returns to the IRS.

## Frontend and backend

The frontend uses Jinja templates, CSS, and JavaScript. Flask renders HTML on the server. There is no separate frontend application or frontend build step.

| Component | Location | Responsibility |
| --- | --- | --- |
| Application factory | `app/__init__.py` | Configuration, service initialization, and route registration. |
| Routes | `app/routes/` | Requests, sessions, submissions, uploads, downloads, and review execution. |
| Validation | `app/validation/` | Required fields, formats, numeric limits, and unavailable choices. |
| Services | `app/services/` | Workflow, calculation rules, diagnostics, documents, extraction, and PDF output. |
| Repositories | `app/repositories/` | SQLite queries and transactions for returns and reviews. |
| Templates | `app/templates/` | HTML forms, summaries, document management, and review results. |
| Static assets | `app/static/` | Styles, scripts, images, and bundled presentation assets. |

A submission is validated before persistence. Services calculate totals and findings from the saved facts. Routes render the next page or return validation errors. Rules, diagnostics, and validation do not depend on Flask.

`filing.js` manages conditional inputs, add/remove controls, inline errors, PDF uploads, and extraction results. `review.js` disables repeated review submissions while the request runs. The welcome screen uses standard links and a standalone stylesheet.

## Diagnostics

`app/services/diagnostics.py` returns structured findings with a code, severity, field, message, and correction link. Checks include missing information, duplicate identifiers, incomplete W-2s, dependent qualification, unsupported situations, and prior-year differences.

Errors hide final totals and block summary completion and Form 1040 downloads. Warnings do not block completion. Intermediate summaries check sections reached so far; the final summary checks the complete return. Fields display inline errors, and summary findings link to the corresponding entries. Saving an earlier page clears the summary's reviewed status.

## PDF uploads and extraction

Documents attach to individual returns. Upload controls are available for W-2, 1099-INT, 1099-G, 1040-ES, and 4868 documents. Only PDFs are accepted, with limits of 5 MB and 20 pages per file. Extension, signature, and PDF structure are checked.

`app/services/extraction.py` uses pdfplumber to read selectable text and table cells. Python parsers map recognized labels to supported fields. Extraction is local and does not use an agent, LLM, external API, or OCR. Scanned PDFs and unrecognized layouts require manual entry. Missing and conflicting values are not converted to zero. Readable zero amounts are retained.

W-2 extraction includes supported wage and withholding boxes, employer name/address and EIN, and employee name/address. Uploads populate the next empty employer form. Re-extracting the same document reuses its assigned employer slot. Values remain editable and are saved through Save and Continue. Employee details stay with the W-2 rather than overwriting Personal information.

1099-INT and 1099-G extraction returns supported income and federal withholding amounts for review and application to the form. Blank amount boxes produce missing-value messages. 1040-ES and 4868 documents are attachments only; their payment amounts are entered manually.

Files have random storage names and are stored outside the public static directory. Downloads check ownership. Clearing or deleting a return removes its attachment records and files. Clear return targets the return displayed on the submitted page.

## Prior-year comparison

A user can link another owned return as a prior-year reference. Changes to filing status or dependent count produce warnings. Income changes exceeding both 25% and $1,000 also produce a warning. Comparisons do not modify either return. The link points to the saved return's current contents, not an immutable annual snapshot.

## Form 1040 download

`app/services/form1040.py` fills a bundled IRS Form 1040 layout (the 2024 form, used as a practice layout) using pypdf. ReportLab adds not-for-filing labels and a notes page. The PDF contains saved taxpayer details and supported calculated totals. Additional dependents beyond the form's four rows appear in the notes.

The download endpoint recalculates diagnostics and returns correction links instead of a PDF when blocking findings remain. Signature and bank-account fields are blank. Supporting Schedules 1, 3, and 8812 are not generated, so the download is not a complete filing package.

The template is bundled under `app/assets/pdf/` and originates from the [IRS Direct File repository](https://github.com/IRS-Public/direct-file). That repository also informed the separation of facts, calculation rules, and blocking checks. No IRS calculation runtime is bundled. PDF generation requires no network access.

## Agent capability

The repository is prepared for a pre-filing review agent using the Claude Agent SDK. The current integration contains:

| Component | Current implementation |
| --- | --- |
| Runner contract | Async `run_review(ctx)` accepting return context and returning a `ReviewOutcome`. |
| Snapshot | Return facts, prior-year information, and attachment metadata with a change hash. |
| Report schema | Verdict, summary, findings, client questions, and suspicious-content fields, with a JSON schema and a validation function. |
| Workspace | `workspace.py` builds a temporary folder per review: return, prior year, diagnostics, document text, and the skill template. |
| Request handler | `POST /review` executes the runner, saves the outcome or error, and redirects to Summary. |
| Persistence | One review row per run, including report, audit list, cost, turns, and errors. |
| Interface | Summary-page action, saved verdict/findings, audit steps, and stale-review notification. |

The runner is a placeholder that returns `None`. `workspace.py` and `workspace-template/` (two provided skills) are finished starter code. The lab (start at `LAB.md`, which links to one page per step) has learners build the agent, a `CLAUDE.md`, a third skill, a subagent and hooks. The default action therefore records and displays a no-report error. Tests substitute a runner without making external calls.

The remaining work is the agent: SDK execution, conventions, skills, a subagent, hooks, and audit records. The request handler does not currently enforce the report validator. Review execution runs within the request; there are no background workers or streaming endpoints.

Agent verdicts do not currently gate summary completion or PDF downloads. A commented-out check in `app/routes/filing.py` provides an integration point for requiring a fresh review without a hold verdict. Deterministic diagnostics remain the active gate.

## Storage and sessions

SQLite stores returns, completion state, section values, dependents, W-2s, attachment metadata, prior-return links, and reviews. Tables initialize automatically. Monetary calculations use `Decimal`.

Local runtime files are excluded from Git:

| Path | Contents |
| --- | --- |
| `instance/practice.sqlite3` | Saved application records. |
| `instance/session.key` | Persistent browser-session signing key. |
| `instance/documents/` | Uploaded document contents. |
| `tmp/` | Temporary verification output. |

Signed browser sessions identify the owner and active return. Tax values remain server-side. State-changing forms use CSRF tokens; session cookies are HTTP-only and use a SameSite policy. Saved data survives restarts.

Sign in opens the welcome screen; it is not authentication. Accounts and account recovery are not implemented. Clearing browser cookies loses interface access to the previous session's returns.

## Routes

| Route | Function |
| --- | --- |
| `/` | Homepage. |
| `/welcome` | Welcome screen. |
| `/returns` | Saved returns. |
| `/returns/new` | POST: create a blank return. |
| `/returns/<identifier>/open` | POST: select an owned return. |
| `/returns/<identifier>/delete` | POST: delete an owned return. |
| `/filing/<step>` | GET/POST: display or save a workflow page. |
| `/filing/reset` | POST: clear the specified owned return. |
| `/return-resources` | Documents and prior-year reference management. |
| `/documents/upload` | POST: attach a typed PDF and extract supported fields. |
| `/documents/<document_id>` | Download an attachment for the active owned return. |
| `/documents/<document_id>/extract` | POST: extract an existing attachment. |
| `/diagnostics` | Current findings as JSON. |
| `/return/form-1040.pdf` | Download the labeled Form 1040. |
| `/review` | POST: execute the review runner and return to Summary. |

## Repository layout

```text
app/
  __init__.py
  assets/pdf/
  repositories/
  routes/
  services/
    rules/
    review_agent/
    diagnostics.py
    documents.py
    extraction.py
    w2_identity.py
    form1040.py
    filing.py
    field_errors.py
    workflow.py
  validation/
  templates/
  static/
sample-documents/
tests/
README.md
run.py
pyproject.toml
uv.lock
```

`sample-documents/` contains static fictional PDFs, manual entry guides, and expected results. It is one taxpayer, Milo Ledger: a clean 2026 return, a 2026 return that needs review, and a 2025 prior-year return. His W-2 and 1099-INT use government-template examples. `app/seed.py` (a lab fixture, on only when `run.py` starts the app) loads all three, with documents attached and the prior year linked, into each new browser session. The expected agent verdict is in `expected-results.json`.

## Running locally

Requirements: Python 3.11 or newer and uv.

```sh
uv run run.py
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000). uv installs the project dependencies. The server binds to the local machine.

To load optional backend environment variables:

```sh
uv run --env-file .env run.py
```

`.env` is excluded from Git. The application and placeholder reviewer do not require an API key. Credentials are not stored in templates or frontend scripts.

## Tests

```sh
uv run python -m unittest discover -s tests -v
```

Tests cover workflow validation, calculations, conditional income, dependent and employer records, PDF extraction, document ownership and cleanup, prior-year warnings, Form 1040 downloads, and review persistence and error handling. Test data uses temporary storage.

The optional browser check exercises the interface through PDF import and Form 1040 download:

```sh
uv run --with playwright playwright install chromium
uv run --with playwright python tests/browser_flow.py
```

# Deal Page Simplification And Production Rebuild Plan

## Faststrap Review Context

Primary reference: `neo-admin/` itself, especially the newly split Project, Blog, and Submission pages.

Faststrap guidance used:

- Faststrap components and Bootstrap layout first.
- HTMX for filters, saves, partial refreshes, confirmations, and live document actions.
- Custom CSS only for admin brand polish and surface treatment.
- Prefer focused list/detail pages over one clumsy workspace trying to do every job.
- Keep actions semantic: buttons for actions, links for navigation, icon buttons with accessible labels for compact destructive actions.

## Current State Summary

The Deal page has already moved in the right direction. It is no longer one giant page: the detail area is split into `deal_overview.py`, `deal_documents.py`, `deal_edit.py`, `deal_detail.py`, and shared `deal_helpers.py`.

The remaining problem is conceptual rather than only visual. The UI is still built around a pipeline-first mental model, while the real usage you described is document-first/project-first:

- some clients follow proposal -> quote -> invoice
- some only need a quote
- some only need an invoice
- some are friends or uncertain leads where a full workflow is unnecessary
- some projects can contain multiple documents over time

The current UI partially supports quick standalone documents, but the interface still explains itself as a pipeline, and the data layer still assumes a single document per kind in several places.

## Key Findings

### 1. The root Deal page should become project/document-first, not pipeline-first

Current file: `app/presentation/pages/deals. py`

The root workspace currently presents `Pipeline Records` as the main surface, then has pipeline stage filters as the dominant navigation. This is useful for workflow tracking, but it is not the best entry point for your real admin use.

Recommended new information architecture:

- Primary section: `Project Document Workspaces`
- Each card/row represents one project/client record.
- The card shows document chips: proposal, quote, invoice, plus counts/status.
- Opening a project reveals all documents in that project.
- Standalone invoice/quote/proposal records still live under a lightweight project shell.
- Secondary section: `Workflow Queue`
- Workflow Queue shows only records that are actively moving through proposal -> quote -> invoice -> paid.

This matches your own idea: the project/client becomes the container, and documents are the things inside it.

### 2. Quick Document exists, but the post-save redirect is wrong

Current file: `app/routes/deals.py`

`/deals/quick` redirects to:

```text
/deals?deal_id={result.deal_id}
```

But `deals()` does not accept or use `deal_id`, so the user returns to the list instead of the generated record. This makes the quick standalone workflow feel broken.

Target behavior:

```text
/deals/{result.deal_id}?view=documents
```

The generated document should be visible immediately with copy/open/send actions.

### 3. Submission-to-deal prefill is linked, but not implemented

Current files:

- `app/presentation/pages/submissions.py`
- `app/routes/deals.py`
- `app/presentation/pages/deals.py`

The Submission detail page links to:

```text
/deals?from_submission={entry_id}&from_kind={kind}
```

But the Deal route/page does not consume those query parameters. That means "Convert to Deal" currently navigates to Deals but does not actually prefill client details.

Target behavior:

- `/deals/new?from_submission=...` opens a new project/document workspace form.
- Client name, email, phone, subject/service, message, budget, and timeline are prefilled.
- The first action asks what to create: proposal, quote, invoice, or project shell only.

### 4. The document model is still too restrictive for production flexibility

Current files:

- `app/infrastructure/sql/003_client_pipeline.sql`
- `app/infrastructure/deal_repository.py`

The original schema includes a unique constraint on `(deal_id, kind)`. Even if later migrations add link versioning, the mental model still leans toward one proposal, one quote, and one invoice per deal.

For production flexibility, a project should be able to have:

- multiple proposals
- multiple quotes
- multiple invoices
- revised versions
- package-specific quotes/invoices
- ad-hoc standalone invoices

Target model:

- `client_deals` = project/client workspace.
- `client_documents` = many documents under that workspace.
- `kind` remains proposal/quote/invoice.
- `version_number`, `status`, `source_document_id`, `package_name`, and `created_from` tell the story.
- Remove or replace the unique `(deal_id, kind)` constraint.

### 5. There is no document delete action

Current file: `app/presentation/pages/deal_documents.py`

The detail documents tab has open/copy/download/status actions, but no delete icon button per document. You asked specifically for project documents arranged well with a delete icon button.

Target behavior:

- Each document card has a compact icon-only delete button.
- Use Faststrap `ConfirmDialog` or a standard modal confirmation.
- Deleting a document should not delete the whole project/client workspace.
- Deleting the last document should leave the project shell, unless the user deletes the deal itself.

### 6. Link management is routed but not exposed enough in the UI

Current files:

- `app/routes/deals.py`
- `app/infrastructure/deal_repository.py`
- `app/presentation/pages/deal_documents.py`

Routes exist for revoke/regenerate/resend link actions, but document cards mostly expose copy/open/download/status actions. Production users need visible, grouped document link actions.

Target UI:

- `Copy link`
- `Open client portal`
- `Resend`
- `Regenerate`
- `Revoke`
- `Download PDF`

Use a Faststrap `Dropdown` or compact action cluster so the cards do not become noisy.

### 7. The section editor has duplicate/competing implementations

Current files:

- `app/presentation/pages/deal_edit.py`
- `assets/js/modules/deal_sections.js`
- `assets/js/admin.js`

`deal_edit.py` defines an inline section manager with ids like:

```text
section-title-input
section-content-input
sections-json-field
sectionEditModal
```

But `assets/js/modules/deal_sections.js` looks for ids/data attributes like:

```text
deal-section-title-input
deal-section-content-input
sections_json
deal-section-modal
data-deal-sections
```

`admin.js` calls `initDealSections()`, but the rendered edit page does not match the external module. This creates a maintenance trap and makes future AI draft insertion fragile.

Target behavior:

- Keep one section editor only.
- Prefer external `deal_sections.js` with stable `data-*` hooks.
- Remove inline JavaScript from `deal_edit.py`.
- Render the section manager markup with Faststrap `Modal`, `Button`, `Textarea`, `Input`, and Bootstrap utility classes.

### 8. Deal overview can still crash on malformed `sections_json`

Current file: `app/presentation/pages/deal_overview.py`

The overview tab directly does:

```python
json.loads(selected.sections_json)
```

without a safe parser. Public documents and PDFs have stronger guards, but the admin overview can still fail if a malformed or non-dict section enters the database.

Target behavior:

- Add one shared parser helper, for example `parse_document_sections(raw)`.
- Use it in admin overview, edit page, public document portal, PDF builder, repository validation, and tests.
- Ignore invalid items instead of crashing.

### 9. Documents do not round-trip document-level `sections_json`

Current files:

- `app/infrastructure/deal_repository.py`
- `app/presentation/pages/public_documents.py`

The domain model supports `DealDocument.sections_json`, and the public portal prefers document-level sections before deal-level sections. But the Supabase select for documents does not include `sections_json`, and `save_deal_document()` writes sections only onto the deal payload, not the document payload.

Target behavior:

- Select `client_documents.sections_json`.
- Save proposal sections to the document being edited.
- When generating a quote/invoice from a proposal, intentionally choose whether to inherit sections, summarize sections, or clear them. Do not silently lose them.

### 10. Line items are still plain text, while the UI wants packages/options

Current files:

- `app/presentation/pages/deal_documents.py`
- `app/infrastructure/deal_repository.py`
- `app/presentation/pages/public_documents.py`
- `app/infrastructure/deal_pdf.py`

The line item parser is pipe-delimited text. It works, but it is not friendly for a production admin where you are building proposal packages, quotation options, invoice milestones, or friend invoices quickly.

Target behavior:

- Keep text import support for speed.
- Add a structured line-item editor with repeated rows.
- Store line items as JSON in Supabase, as the current repository already sends JSON to `client_documents.line_items`.
- Render package groups from structured data, not fragile label prefixes like `Package A - ...`.

### 11. Faststrap is used well in places, but Deal still has raw/custom-heavy areas

Good current usage:

- `Card`, `Row`, `Col`, `Badge`, `EmptyState`, `Modal`, `Spinner`, `SEO`, `Fx`
- HTMX for navigation and saves
- shared admin shell and page helpers

Needs tightening:

- Prefer `ConfirmDialog` for delete/revoke/reset actions.
- Use `Dropdown` for dense document actions.
- Use `StatusBadge` consistently for document statuses.
- Consider `DataTable` for sortable document/project lists if a table layout is chosen.
- Use `FormSection`/`FormGroup` patterns or existing `floating_field` consistently instead of mixed inline labels/styles.
- Replace text-only `Edit`/`Del` section buttons with icon buttons and accessible labels.

### 12. The root page currently creates one modal per deal

Current file: `app/presentation/pages/deals.py`

Quick preview modals are rendered for every deal in the list. This follows the Project/Blog pattern and is acceptable for small lists, but Deals can grow faster than portfolio projects.

Target behavior:

- Keep root-level modals for now if list size remains small.
- For production scale, load preview modals lazily via HTMX endpoint.
- A drawer or modal loaded on demand would keep HTML smaller.

## Recommended New UX

### `/deals`

Purpose: choose a project/client workspace or create a document quickly.

Top area:

- KPI cards: Projects, Documents, Open approvals, Outstanding invoices.
- Primary actions:
  - New Project Workspace
  - Quick Proposal
  - Quick Quote
  - Quick Invoice

Primary section: `Project Document Workspaces`

Each card/row:

- Project/client name
- Client/contact
- Total value or outstanding value
- Document chips with counts/statuses
- Last activity date
- Actions: open, quick add document, delete project

Secondary section: `Workflow Queue`

Shows only workflow-driven records:

- Lead
- Proposal awaiting response
- Quote awaiting acceptance
- Invoice awaiting payment
- Paid/delivered

This can be a compact `DataTable` or responsive `Card` list.

### `/deals/new`

Purpose: create a project shell or first document.

Steps:

1. Client and project basics.
2. Choose starting point:
   - Project shell only
   - Proposal
   - Quote
   - Invoice
3. Document details.
4. Money, payment terms, due/valid dates.
5. Optional sections and line items.

Use Faststrap-first components:

- `FormSection`
- `Row`/`Col`
- `ToggleGroup`
- `Select`
- `Input`
- `Textarea`
- `Modal`
- `LoadingButton` or existing `loading_action_button`

### `/deals/{deal_id}`

Purpose: project/client document workspace.

Recommended tab structure:

- `Documents`: default tab
- `Workflow`: timeline/queue state
- `Client & Project`: compact edit form
- `Settings`: danger zone, link defaults, payment defaults

Documents tab:

- grouped document cards or table
- sortable by kind, status, updated date, amount
- create any document type from this project
- delete icon per document
- actions dropdown per document

Workflow tab:

- show proposal -> quote -> invoice only when applicable
- document-derived statuses, not a forced path
- generate-next buttons live here, not inside every document card

Client & Project tab:

- edit client/project metadata only
- no document-specific fields mixed in

Document editor page/modal:

- edit one document at a time
- title/status/kind/amount/dates/payment account
- sections
- line items
- AI draft tools
- preview public view

## Implementation Plan

### Phase 1: Stabilize Current Deal Bugs

1. Fix `/deals/quick` redirect to open the generated record at `/deals/{deal_id}?view=documents`.
2. Implement `from_submission` prefill or remove the misleading link until implemented.
3. Add a shared safe section parser.
4. Replace unsafe `json.loads()` in `deal_overview.py`.
5. Include `sections_json` in document Supabase selects.
6. Save document-level `sections_json` when editing proposal documents.
7. Add tests for malformed sections in admin overview, public portal, and PDF rendering.

### Phase 2: Introduce Document-Centric Repository Methods

Add repository functions:

- `list_deal_workspaces(search="", document_kind="all", status="all")`
- `list_documents_for_deal(deal_id)`
- `get_document(document_id)`
- `save_document(...)`
- `delete_document(document_id)`
- `create_project_workspace(...)`
- `create_quick_document(...)`

Keep existing functions temporarily as compatibility wrappers.

### Phase 3: Database Migration

Create a new SQL migration, likely `011_flexible_client_documents.sql`.

Migration goals:

- Drop/replace unique `(deal_id, kind)` constraint if it still exists.
- Add indexes for `deal_id`, `kind`, `status`, `updated_at`.
- Add or confirm:
  - `version_number`
  - `source_document_id`
  - `package_name`
  - `created_from`
  - `sections_json`
  - `revoked_at`
  - `last_sent_at`
- Ensure delete cascades remain correct from `client_deals` to `client_documents`.
- Keep public token uniqueness.

### Phase 4: Rebuild `/deals` Root Workspace

Files likely affected:

- `app/presentation/pages/deals.py`
- `app/routes/deals.py`
- `assets/css/_surfaces.css`
- `assets/css/_layout.css`

Build:

- `deal_workspace_header()`
- `deal_workspace_metrics()`
- `deal_workspace_actions()`
- `project_document_workspace_list()`
- `workflow_queue_panel()`
- `quick_document_modal()`

Faststrap-first choices:

- `Row`, `Col`, `Card`, `MetricCard` or existing `summary_card`
- `DataTable` if table presentation is chosen
- `EmptyState`
- `Modal`
- `Dropdown`
- `StatusBadge`
- `ConfirmDialog`

### Phase 5: Rebuild Deal Detail Around Documents

Files likely affected:

- `app/presentation/pages/deal_detail.py`
- `app/presentation/pages/deal_documents.py`
- `app/presentation/pages/deal_overview.py`
- `app/presentation/pages/deal_edit.py`
- `app/presentation/pages/deal_helpers.py`

Target split:

- `deal_workspace_detail.py`: page shell/header/nav
- `deal_document_list.py`: document cards/table
- `deal_document_editor.py`: single document editor
- `deal_workflow.py`: optional workflow timeline/generate-next
- `deal_project_form.py`: project/client metadata only

Default view should be documents, not overview.

### Phase 6: Replace Section Editor

Files affected:

- `app/presentation/pages/deal_edit.py`
- `assets/js/modules/deal_sections.js`
- `assets/js/modules/ai_draft.js`
- `assets/js/admin.js`

Build one implementation:

- render stable `data-*` hooks from Python
- use the external module only
- remove inline section editor JavaScript
- make AI draft insertions update the same hidden field and rendered section list
- add accessible labels to edit/delete/reorder buttons

### Phase 7: Add Structured Line Item Editor

Build a line item component that supports:

- package/group name
- label
- description
- quantity
- unit price
- computed total
- add/remove row
- import from pipe text

Short-term implementation can use progressive enhancement with JavaScript because repeated row editing is genuinely client-side heavy. Keep saving through the existing HTMX form.

Long-term implementation can move line items to their own HTMX partial endpoints.

### Phase 8: Add Document Delete And Link Actions

Routes:

- `POST /deals/documents/delete`
- `POST /deals/documents/link`

UI:

- delete icon button with `ConfirmDialog`
- actions dropdown per document
- status updates remain visible
- toast on success/failure
- refresh only the document list where possible

### Phase 9: Tests And QA

Add or update tests:

- `/deals` renders project/document workspace language.
- `/deals/quick` redirects to generated detail page on mocked success.
- submission conversion prefill appears in new-deal form.
- malformed `sections_json` does not crash admin overview.
- document-level `sections_json` is selected and rendered.
- multiple documents of same kind can be listed under one deal.
- document delete route handles missing id, read-only mode, and mocked success.
- link revoke/regenerate/resend actions appear in document card HTML.
- public proposal/quote/invoice still render.
- PDF generation still works with sections and line items.

Manual browser QA:

- desktop `/deals`
- mobile `/deals`
- create quick invoice
- open generated project documents
- delete a document
- regenerate/revoke link
- convert submission to deal
- edit sections
- generate PDF
- open public document portal

## Proposed File Ownership After Rebuild

```text
app/presentation/pages/deals.py
  Root deal workspace only.

app/presentation/pages/deal_detail.py
  Thin dispatcher/page shell for one project workspace.

app/presentation/pages/deal_document_list.py
  Document collection UI.

app/presentation/pages/deal_document_editor.py
  Single document form/editor.

app/presentation/pages/deal_project_form.py
  Client/project metadata form.

app/presentation/pages/deal_workflow.py
  Optional workflow timeline and generate-next UI.

app/presentation/pages/deal_helpers.py
  Formatting, status colors, small reusable UI helpers only.

app/infrastructure/deal_repository.py
  Persistence and document/workspace operations.

app/domain/models.py
  DealWorkspace, DealDocument, save result dataclasses.
```

## Recommended First Commit Scope

Do not rebuild everything in one risky commit.

First commit should include:

- quick redirect fix
- submission prefill support
- safe section parser
- document-level `sections_json` select/save
- tests for those fixes

Second commit:

- root `/deals` UI restructure into project/document workspace plus workflow queue

Third commit:

- document delete/link action UI and repository functions

Fourth commit:

- section editor cleanup

Fifth commit:

- structured line-item editor

## Final Direction

The cleanest product direction is:

> Deals are not primarily a pipeline. Deals are project/client workspaces that contain documents. Workflow is an optional lens on top of those documents.

That unlocks exactly the flexibility you want: a formal client can move through the full workflow, while a friend or uncertain lead can receive just an invoice or quote without the admin pretending there is a full pipeline behind it.

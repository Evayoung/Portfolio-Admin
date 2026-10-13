# Neo Admin Usability Redesign Implementation Plan

## Goal

Make common admin work faster and easier to scan while preserving the existing Neo Admin brand, FastHTML/Faststrap stack, route structure, Supabase model, HTMX behavior, and public portfolio/document experiences.

This is an implementation plan, not a proposal to replace the application architecture. `domain / infrastructure / presentation / routes` and the CSS import hub already provide the right separation. Keep styling in `_brand.css`, `_typography.css`, `_layout.css`, `_surfaces.css`, and `_interactions.css`; use Bootstrap/Faststrap for responsive structure and HTMX for navigation and partial updates.

## Target experience

- Operational records open in a two-panel workspace: searchable/filterable list on the left, selected record and its primary actions on the right.
- Content editors expose the relevant preview and save/publish state without making users repeatedly leave the collection.
- Client documents are grouped under **Lead or Client → Project → Documents**, with document kind/status as filters. A project can have no document yet, one document, or several documents of the same kind over time.
- Long forms remain focused and usable on mobile. Desktop split panes collapse to a list-then-detail flow on narrow screens; they do not shrink into unusable columns.
- Existing public pages, URLs, data ownership, accessibility labels, and empty/loading/error feedback remain intact.

## Implementation progress

**Started 2026-10-13.** The first implementation pass now covers the core workspace pattern and localized P3 refinements:

- Deals: client/project list and selected document workspace, combined document kind/status filtering, broader search, and return-to-workspace after quick document creation.
- Projects and Blog: query-restorable list/detail selection with inline editing or preview, while retaining focused editor routes.
- AI Assistant: input and generated-draft panels side by side.
- Settings: grouped profile form and removal of duplicated profile summary panels from other settings pages.
- Submissions: selectable inbox and in-context review/update panel.
- Media: responsive preview-first asset gallery with icon-only Open/Copy/Manage actions and clear usage guidance.
- Dashboard: removed the repeated deal metric strip.
- CV: added section jump links to the existing section managers.

Python compilation, diff whitespace checks, and local markup rendering have passed for Deals filters/selection plus Submissions, Media, CV, AI Assistant, and Profile Settings. Deals review confirmed that combined kind/status filters match a single document and search finds client email and document numbers. Keyboard focus within selectable rows now receives the same highlight as pointer hover. A real-browser review across desktop/mobile and history navigation is still required before calling the redesign complete.

### Playwright visual review — 2026-10-13

- Reviewed the redesigned admin pages in Chrome driven by Playwright at 1440 px and 390 px widths. The changed views have no page-level horizontal overflow at the narrow viewport; all seven paired workspaces stack on mobile and their paired columns now align at the top on desktop.
- Fixed two browser-visible layout issues: Submissions had inherited the Deals grid class and stacked its desktop panels; right columns in several `g-4` rows canceled Bootstrap's top gutter and sat above their paired panels.
- Styled the shared radio toggles and filter chips so the selected option is visible, added `aria-current="page"` to the active Settings section, and hid the Media upload indicator until HTMX marks it as in progress.
- Browser navigation confirmed that Deals filter selection survives refresh, and Projects/Blog selection survives refresh and browser back/forward.
- The review server ran with dotenv loading disabled, dummy credentials, and no external service keys. The external HTMX CDN was blocked in the initial pass; during the continuation the bundled Faststrap HTMX script loaded and list/filter GET updates worked. No live data was changed.

### Verification continuation - 2026-10-13

- Rechecked all changed admin routes in Chrome at 1440 px and 390 px. No page-level horizontal overflow or browser JavaScript errors. Project and Blog row selection updates the URL, and Deals filter selection clears the prior deal selection in the URL.
- Fixed an AI Assistant regression found during a safe local POST: the result renderer imported from `deals.py` had been removed during the page split, causing HTTP 500. It now uses the shared document-draft fragment and returns the configured-provider guidance when no provider is available.
- Updated stale smoke-test assertions for the new Settings, Projects, and Blog layouts. PDF extraction checks now use `pypdf`, declared in `requirements.txt`; PDF route/content checks are included in the final local run.
- No live Supabase writes or external AI requests were made. End-to-end save/publish/delete, media upload, and successful AI generation still need verification in an explicitly configured environment. Two seeded editorial images resolve to missing local asset paths during browser review.

### Phase status

- **Phase 0:** Architecture and routes inspected during implementation; route/query/write behavior is covered by focused smoke checks. A consolidated inventory remains useful for handoff but does not block the UI work.
- **Phases 1-4:** Redesign slices implemented across Deals, Projects, Blog, AI Assistant, Settings, Submissions, Media, Dashboard, and CV.
- **Phase 5:** Desktop/mobile visual pass, selection/history checks, public document checks, and PDF checks completed locally. Configured-service success flows and manual keyboard/contrast review remain outstanding.

### Deals screen polish slice

- Each document is now a Faststrap accordion, closed by default, with type, title, status, and amount in its summary. Multiple documents can stay open while comparing them.
- Document action controls are icon-only with accessible names and hover titles. Touch targets stay 44 px at narrow widths; package choice and AI generation controls keep descriptive text.
- At mobile widths up to 390 px, kind/status filters scroll horizontally and the search field shares a row with its action. This removes the excessive wrapping and blank search gap seen at 320 px.
- Playwright review at 320, 360, 390, and 1440 px found no page-level horizontal overflow or JavaScript errors. Keyboard activation opens the accordions, and opening one does not close another. No live writes were made.

### Media gallery and dependency slice

- Replaced the squeezed three-column asset list with a Faststrap responsive grid: one full-width card on mobile and two cards from tablet widths onward.
- Asset cards now lead with a larger image/file preview, readable metadata and 44 px icon-only open, copy, and manage controls with accessible names and titles.
- Added practical gallery guidance for project covers, article artwork, logos, and client downloads. Empty library guidance remains explicit; no fake uploaded records were added.
- Raised the declared Faststrap minimum from 0.8.0 to 0.9.0, matching the app's existing minimum-version policy.
- A temporary in-memory card preview at 320, 360, 390, 768, 1024, 1199, 1200, and 1440 px stayed within the viewport; card action targets measured 44 px. The gallery remains one column until the XL breakpoint so it can breathe inside the existing 7/5 workspace split. The real route correctly showed its empty state with external data sources disabled.

## Scope and priority

| Priority | Area | Level | Outcome |
|---|---|---|---|
| P0 | Deals and client documents | Workflow rebuild | Project/client workspace is the primary organizing view; all related documents are easy to find and act on. |
| P1 | Projects | Major | Collection and editing become one list/detail workflow, with a focused editor for long content. |
| P1 | Blog | Major | Article collection and editing become one list/detail workflow with clear draft/published state. |
| P2 | AI Draft Assistant | Major | Inputs and generated draft can be reviewed and iterated side by side. |
| P2 | Settings | Major | Settings are grouped by task and have stable local navigation; remove redundant/overloaded profile presentation. |
| P3 | Submissions, Media, Dashboard, CV | Minor to moderate | Improve action hierarchy, scanability, and section navigation without replacing their useful structures. |

## Work plan

### Phase 0 — Baseline and shared interaction contract

1. Capture the current routes, query parameters, HTMX targets, write actions, empty states, and data relationships for each in-scope page.
2. Use `sj_admin` Inquiries/Orders as the interaction reference for list/detail behavior. Reuse the pattern and adapt its visual language to Neo Admin; do not copy its styling wholesale.
3. Define shared presentation helpers only where multiple pages need the same behavior: selected list row, record list panel, detail header/action area, status line, and mobile back-to-list control.
4. Keep each page’s view composition in `presentation/pages`; keep data access in repositories and business rules outside the page renderer.
5. Confirm route behavior for direct links, refresh, browser back/forward, and HTMX navigation before converting a page.

**Completion gate:** a short page/route inventory exists; the first workspace can be implemented without changing public URLs or moving persistence logic into presentation code.

### Phase 1 — Deals: client/project document workspace (P0)

Use [`DEAL_PAGE_SIMPLIFICATION_PLAN.md`](DEAL_PAGE_SIMPLIFICATION_PLAN.md) as the detailed technical companion. Reconcile it with current code before implementation: document deletion and link routes already exist, and document sections are already parsed in shared domain code; verify exact current behavior rather than duplicating those tasks.

1. Make `/deals` lead with **Client / Project Workspaces**. Show client or lead, project title, stage, latest activity, document counts/types/statuses, and a clear open action. Add search across client, company, project, and document fields.
2. Put document kind and status filters inside the workspace. Keep a compact optional workflow queue for proposals awaiting response, quotes awaiting acceptance, and invoices awaiting payment.
3. Make the selected workspace detail show Documents first. Group rows/cards by document type and date/version; expose open, copy-link, download, status, link management, and delete actions with accessible labels and confirmation for destructive actions.
4. Preserve the current `client_deals` → `client_documents` ownership. Do not add a separate lead/client hierarchy or database migration unless code inspection proves the current relationship cannot represent the agreed grouping and repeated document kinds.
5. Support lead conversion by carrying available submission contact, project, scope, budget, and timeline information into the workspace creation flow. Ensure a quick document save opens the newly created workspace and its document.
6. Keep public `/documents/{token}` and PDF rendering separate from admin workspace redesign.

**Main files:** `app/presentation/pages/deals.py`, `deal_detail.py`, `deal_overview.py`, `deal_documents.py`, `deal_edit.py`, `deal_helpers.py`, `app/routes/deals.py`, and existing `app/infrastructure/deal_repository.py` only where required. Keep current route compatibility; add fragments/endpoints only when needed for list selection or partial refresh.

**Completion gate:** an admin can find a client by name, open the project, identify every document, create another document of an existing kind, and act on it without losing workspace context; standalone invoice/quote flows and public links still work.

### Phase 2 — Projects and Blog collection/editor workspaces (P1)

1. Convert Projects from a grid with separate full-page editing into a two-panel collection: compact project rows on desktop, selected project summary/editor in the detail pane. Keep category, featured, search, published/draft, and media selection reachable without a modal stack of preview cards.
2. Keep long narrative editing comfortable: the detail pane may link to a dedicated focused editor, but selecting a project should expose the common edit/publish actions in context.
3. Convert Blog to the same interaction contract, with category/search, publication state, article preview, and editor actions in context. Preserve a focused writing view for long article content if needed.
4. Store selection/filter state in URLs or query parameters so direct links, refresh, and browser history restore the current record. Use HTMX for list/detail updates and keep fallback links functional.
5. Remove redundant per-record Quick Preview/Edit controls only after equivalent preview/edit actions are available in the selected detail pane.

**Main files:** `app/presentation/pages/projects.py`, `blog_admin.py`, relevant routes in `app/routes/projects.py` and `blog.py`, plus shared CSS partials. Repository APIs should only change if existing search/filter methods are insufficient.

**Completion gate:** selecting and editing a project or post does not force an avoidable round trip to another page; long-form content remains usable at desktop and mobile widths.

### Phase 3 — AI Assistant and Settings (P2)

**AI Draft Assistant**

1. Arrange draft type/context controls and generated draft in a clear input/result workspace.
2. Keep the result visible after generation, with copy, regenerate, and explicit insert/use actions where the destination is known. Do not silently overwrite a deal or document.
3. Add clear loading, generation error, empty result, and success feedback; keep AI configuration in Settings.

**Settings**

1. Group Profile, Access, Payment Accounts, AI Providers, and Health under stable local navigation with a clear active section.
2. On Profile, group identity, contact/social links, and SEO fields with headings and contextual help. Remove or reduce the large read-only identity panel when it merely duplicates the adjacent form.
3. Keep save state adjacent to the relevant form and preserve independent settings routes and write permissions.

**Main files:** `app/presentation/pages/ai_assistant.py`, `settings_admin.py`, related routes, and focused CSS updates.

**Completion gate:** each page has one clear primary task, and the user can see what changed or what failed without scanning away from the form/result.

### Phase 4 — Smaller refinements (P3)

1. **Submissions:** improve list-row scan order (name, source/date, status) and make the next workflow action prominent. Preserve its current two-panel detail flow.
2. **Media:** group asset actions by frequency: primary Open/Copy, secondary Edit/Replace, destructive Delete. Keep upload/library split and provide clear selection/filter feedback.
3. **Dashboard:** distinguish attention-needed workflow signals from descriptive totals; remove visual competition between repeated metric groups where the data overlaps.
4. **CV:** add a section index to the editor and clear saved/unsaved state. Preserve the public-style preview and PDF action.

**Completion gate:** no page is rebuilt where the existing composition already serves its workflow; improvements remain localized and consistent.

### Phase 5 — Responsive, accessibility, and regression review

For every changed workflow, verify desktop and mobile layouts, keyboard operation, visible focus, semantic headings, discernible icon-button labels, contrast, and empty/loading/error/success states. Verify direct URL entry, refresh, browser back/forward, HTMX updates, and ordinary-link fallback. Recheck that public portfolio pages, public document links, and PDF output are unchanged.

Do not treat tests alone as proof of visual quality. Use a browser pass for the changed flows and record any remaining manual checks.

## Implementation boundaries

- Preserve the current architecture and existing CSS partial organization.
- Prefer Faststrap components and Bootstrap responsive utilities; use custom CSS for Neo Admin identity and surface treatment.
- Keep JavaScript limited to behavior HTMX/Bootstrap cannot handle cleanly. Put reusable JavaScript in existing `assets/js/modules/`, not inline in page renderers.
- Avoid a broad redesign of public portfolio pages or the client-facing document portal in this work.
- Avoid database migrations during UI phases unless confirmed data-model constraints block the desired workflow. If a migration is necessary, document backup, migration, and rollback requirements before applying it.

## Suggested delivery sequence

1. Phase 0 inventory and interaction contract.
2. Phase 1 deals/client documents, shipped in small slices: root workspace, selected detail, create/convert flows, then action polish.
3. Phase 2 Projects and Blog, one module at a time using the proven workspace pattern.
4. Phase 3 AI Assistant and Settings.
5. Phase 4 minor refinements.
6. Phase 5 browser and regression review across all changed pages.

Start with Phase 1. It addresses the most consequential information-architecture problem and establishes the reusable pattern for the other list/detail pages.

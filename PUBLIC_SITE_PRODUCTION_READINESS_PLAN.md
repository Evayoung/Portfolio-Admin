# Public Site and Neo Admin Production Readiness Plan

**Prepared:** 2026-10-13
**Scope:** `neoportfolio` public FastHTML site and `neo-admin` content/admin application
**Purpose:** Close the content ownership, security, resilience, SEO, and verification gaps found in the local audit before declaring the public site production-ready.

## Executive decision

The local public site currently renders its main routes, passes its 29 smoke tests, serves its checked static assets, and has no horizontal overflow at the reviewed 390 px and 1440 px viewports. Contact and booking routes return safe offline delivery options when Supabase writes are unavailable.

This is not yet a production sign-off. The deployed site and configured Supabase flows were not verified. Neo Admin does not manage every public-facing collection, the public deployment currently requires a Supabase service-role key, content reads can silently fall back to seed data, and the seed sync can replace hand-edited records.

Keep the existing separation of concerns. Extend `neo-admin/app/domain`, `app/infrastructure`, `app/presentation`, and `app/routes`; keep public rendering and data access in the equivalent `neoportfolio` modules. Avoid rewriting the public site or changing its existing URLs as a first step.

## Findings this plan covers

| Finding | Required outcome |
|---|---|
| Services, pricing, testimonials, and several home-page sections are not editable in Neo Admin | Every public content collection has an explicit source of truth and a supported admin editing workflow |
| Admin SEO fields are not applied to public page metadata | Site and page-specific SEO values are used by public routes and generated metadata |
| The public Vercel app requires `SUPABASE_SERVICE_ROLE_KEY` to accept submissions | Public submission writes use a narrowly scoped path; privileged keys remain in the admin or a trusted server-side function |
| Form throttling is in-memory and relies on forwarded client headers | Limits work across instances and use a trusted request identity or managed edge limit |
| Seed sync deletes/replaces hand-managed collections | Seed import is previewable, non-destructive by default, and cannot silently replace editorial work |
| Synchronous Supabase and GitHub reads can slow rendering; failures fall back to seed content without clear diagnostics | Reads are bounded and observable; cached/fallback content has an understood freshness policy |
| Unknown project and blog URLs return HTTP 200; health is only a liveness response | Missing records return 404 and deployment checks distinguish liveness from readiness |
| Media uploads require copying URLs into project/blog fields | Editors can choose an existing library asset while preserving current URL fields and public URLs |
| Production data, writes, and deployment could not be tested in this audit | A safe staging verification and rollout gate exists before production sign-off |

## Content ownership contract

Agree on this ownership matrix before changing schemas. A public value should not be independently editable in two places.

| Public data | Current source | Planned admin surface |
|---|---|---|
| Projects and project technology | `projects`, `project_tech_stack` | Existing Projects workspace |
| Blog posts, publication time, and tags | `blog_posts`, `blog_tags`, `blog_post_tags` | Existing Blog workspace |
| CV/profile and resume sections | `cv_meta` and `cv_*` tables | Existing CV workspace and profile settings |
| Services and deliverables | `services`, `service_deliverables` | New Services workspace with ordered deliverables |
| Pricing tiers and points | `pricing_tiers`, `pricing_points` | New Pricing workspace with ordered points |
| Testimonials | `testimonials` | New Testimonials workspace with visibility and order |
| Home identity, hero/about copy, stats, and SEO | Mixture of `site_settings` and Python constants | Profile/Website Content settings, with a documented field-to-page map |
| Portfolio category labels/order | `PORTFOLIO_FILTERS` and project category strings | Managed category list, or a deliberately derived list with stable labels and ordering |
| Uploaded images/files | `media_assets` and public URL fields | Existing Media workspace plus an asset picker in project/blog editors |
| Contact and booking inquiries | `contact_submissions`, `booking_requests` | Existing Submissions workspace |

The migration should retain `image_url`/public URL compatibility. Do not introduce foreign keys to media assets unless the public site and existing content can migrate without invalidating stored URLs.

## Phases

### Phase 0 — Baseline, schema map, and staging safety

**Priority:** Start immediately; no live writes.

1. Record the current public route list, admin route list, the fields each public page reads, and the fields each admin form writes. Use the ownership matrix above as the checklist.
2. Inspect the deployed Supabase schema and migration revision in a read-only session. Compare it with `neo-admin/app/infrastructure/sql/001_initial_schema.sql` and later migrations; document any drift before planning schema changes.
3. Create or identify a staging Vercel deployment and a staging Supabase project. Confirm the staging URL, migration head, backup/restore path, and separate credentials before any staging write.
4. Save current production content counts and export a restorable snapshot before changing policies or any sync tooling. Do not run `sync_supabase_seed.py` against production as part of discovery.
5. Establish a public route/content baseline: current SEO metadata, published project/blog IDs, current home-page values, and the behavior of inquiry fallback links.

**Acceptance gate:** a reviewed field/source map, staging environment, schema comparison, and verified restore procedure exist. No production data has been modified.

### Phase 1 — Remove privileged database access from public submissions

**Priority:** P0 security and abuse-control work.

**Implementation status (2026-10-13):** Public code now uses the anon key for reads and submissions, validates bounded fields and email server-side, preserves the existing honeypot, and ignores caller-supplied client-IP headers in local development. The additive SQL migration clears legacy table and column grants, grants anon inserts on visitor-controlled submission columns only, checks row bounds and default status/source, and grants limited public reads for site settings plus visible project, blog, service, and pricing children. The user reports that migration 011 was applied and checks 1–5 passed; the Supabase environment and live form behavior still need confirmation. Shared rate limiting is still outstanding, and the public Vercel environment key should only be removed after staging writes pass.

1. Use the reviewed column-level anonymous insert policy for `contact_submissions` and `booking_requests`; keep status, source, notes, and other administrative fields outside the public insert grant.
2. Run `011_public_submission_boundary_checks.sql` in the staging SQL editor; compare the table/column and existing policy results to `001_initial_schema.sql`. Resolve any drift before applying `011_public_submission_boundary.sql`.
3. After applying the migration in staging, rerun the checks and submit disposable contact and booking requests. Confirm each appears once in Neo Admin, can be updated, and that invalid and oversized values are rejected. Remove the public site's service-role environment variable only after this passes.
4. Validate and normalize email, text length, field sizes, and service/budget/timeline bounds on the server. The existing contact and booking honeypot is retained. Keep user-entered text as data; never render it as trusted HTML.
5. Replace process-local throttling with a shared or edge-level rate limit. Do not treat an arbitrary `X-Forwarded-For` value as authenticated identity; only trust headers inserted by the hosting platform. Vercel documents that it overwrites this header on incoming requests.
6. Preserve the current WhatsApp/email fallback when direct delivery fails. Report clearly whether a message was stored or only prepared for the visitor.
7. Add server-side structured logs for accepted, rejected, rate-limited, and failed deliveries without logging message bodies or credentials.

**Files involved:** `neoportfolio/config.py`, `routes.py`, `services/submission_service.py`, `app/infrastructure/sql/011_public_submission_boundary.sql`, and `app/infrastructure/sql/011_public_submission_boundary_checks.sql`; deployment environment configuration remains for the staging rollout.

**Acceptance gate:** staging contact and booking submissions reach their intended admin inbox once; invalid, oversized, honeypot, and throttled requests are rejected safely; no public runtime needs the service-role key; fallback links remain useful during an induced write failure.

### Phase 2 — Give Neo Admin complete ownership of public content

**Priority:** P0 data completeness; can proceed in parallel with Phase 1 after Phase 0.

**Implementation status (2026-10-14):** Services, Pricing, and Testimonials have admin workspaces with ordered child lists, visibility controls, service-role writes, and audit events. The Home Content workspace edits home-page copy, journey, stats, experience, skills, highlights, SEO keywords, and profile/hero/booking/CV image URLs. Project and blog image fields include a picker backed by Media Library. Admin project/blog reads use the service role so unpublished records and intentionally empty collections are represented correctly. Migration 012 adds the public-readable, admin-writable home content record and seeds current home values; the user reports running it, but the resulting row and Admin project connection have not yet been verified. A dry-run-first importer is ready to copy bundled image files into Supabase Storage, add Media Library metadata, and repoint matching project/blog/home image URLs. The Media workspace now links directly to Home Page and Project image settings. Staging persistence and public rendering remain unverified; the importer still needs to be run against the intended Supabase project.

1. Add a Website Content navigation group and focused editors for **Services**, **Pricing**, and **Testimonials**. Reuse the existing workspace interaction patterns, but use domain-specific repositories for parent/child ordering rather than forcing nested records into flat generic CRUD.
2. Support create/edit/archive or visibility, ordering, validation, and preview for each collection:
   - Services: slug, title, summary, lead, timeline, price, icon, visible, ordered deliverables.
   - Pricing: title, price, highlight, visible, ordered pricing points.
   - Testimonials: quote, author, role, company, visible, order.
3. Identify all public home-page constants in `neoportfolio/content.py` and CV constants used only for About/Home. Move editable copy and stats into documented settings/content records. Keep executable behavior and presentation-only defaults in code; do not turn arbitrary HTML into editable content without sanitization and an explicit editor contract. **Implemented:** home copy, stats, experience, skills, journey, highlights, keyword metadata, and main image URLs have a focused editor and public read path.
4. Replace hardcoded portfolio filter categories with an admin-managed category list or derive them from published projects using stable ordering and labels. Ensure a project created with a new category is discoverable from the public UI. **Implemented:** public filters and admin choices derive categories from current records.
5. Extend the Project and Blog editors with a searchable Media picker. The selected value should continue to populate the existing public URL field so old content keeps rendering. **Implemented:** image pickers preserve the current URL field and support existing manual URLs.
6. Retain the existing Blog tags workflow; include tags and publish timestamp in the ownership tests so a future generic resource cannot bypass it.
7. Add an audit trail for changes to public content, visibility, and ordering, using the existing admin audit infrastructure where practical.

**Files likely involved:** `neo-admin/app/schema.py`, `app/presentation/shell.py`, new/updated `app/presentation/pages/*`, `app/routes/*`, and focused repositories; corresponding additive migrations in `app/infrastructure/sql`; `neoportfolio/content.py`, `services/content_service.py`, and public page renderers.

**Acceptance gate:** an admin can create, edit, reorder, preview, publish/hide, and remove each managed collection in staging. Each change appears on the correct public route and disappears or updates after unpublishing. A new project category is visible. Existing URL-based media records continue to work.

### Phase 3 — Make seed/bootstrap synchronization safe

**Priority:** P0 data-loss prevention before the new editors are used for substantial live content.

**Implementation status (2026-10-13):** The seed CLI now defaults to a local content-count preview and makes no Supabase request. `--apply` is deliberately refused while the importer still replaces editorial rows. This is the first safety slice; the non-destructive natural-key importer and staging idempotency checks remain outstanding.

1. Split one-time seed/bootstrap from ongoing editorial content operations. Normal deployment must not reset editorial tables.
2. Change seed tooling to default to a dry-run summary showing inserts, updates, skips, and any proposed removals. Require an explicit `--apply` for writes.
3. Make upserts stable by natural key and update only fields owned by the seed source. Never clear CV sections, testimonials, pricing points, service deliverables, or tag links merely to load defaults.
4. Require an explicit, separate prune option for deleting stale seeded rows; prevent pruning rows marked as admin-managed or edited after import.
5. Add idempotency and a staging test proving two dry-runs and two applies have the same expected final state. Keep production restore instructions next to the command.
6. Document which data is code-owned, admin-owned, or imported once. Remove or rename any command whose apparent “sync” behavior can overwrite live editorial content.

**Files likely involved:** `neo-admin/app/infrastructure/content_sync.py`, `sync_supabase_seed.py`, the README/runbook, and sync-specific tests.

**Acceptance gate:** default command performs no writes; dry-run accurately previews changes; repeated apply is idempotent; a test with admin-edited CV/service/testimonial rows proves those rows are preserved.

### Phase 4 — Public metadata, URLs, and operational resilience

**Priority:** P1 correctness and availability.

1. Build public `PageMeta` from `site_settings` with sensible code defaults. Add page-level overrides for project and blog title/description, canonical URL, Open Graph image, and publication date where content exists.
2. Ensure page metadata uses the admin SEO fields. Escape URL/XML content in sitemap output and return an XML content type.
3. Return HTTP 404 for unknown project/blog slugs while keeping a helpful not-found page. Update existing tests that currently assert 200 for these routes.
4. Keep `/health` as a fast liveness check and add a separate readiness check for required dependencies. Avoid a slow external round-trip on every health probe.
5. Measure page-load database calls. Remove duplicate reads within one render, set short explicit timeouts, and add bounded caching for relatively static public content. Define a cache freshness target and how admin changes invalidate or age out cached values.
6. Add observable status for Supabase/GitHub fallback paths. Do not silently imply that seeded values are current when a live read failed. Keep the public fallback behavior graceful while logging source and freshness without exposing secrets.
7. Cache GitHub stats/repository responses and use the existing static fallback on API errors or rate limiting; avoid serial external requests on every visitor page render.

**Files likely involved:** `neoportfolio/content.py`, `services/content_service.py`, `services/github_service.py`, `routes.py`, `ui/home.py`, `pages/blog.py`, `pages/project_detail.py`, and SEO helper usage.

**Acceptance gate:** admin SEO changes appear in page source; canonical/sitemap URLs are correct; unknown slugs return 404; health and readiness semantics are documented; simulated upstream failures are bounded, logged, and do not produce blank pages; measured page requests meet an agreed latency budget.

### Phase 5 — Staging end-to-end, visual, and accessibility review

**Priority:** Required before production sign-off.

1. On staging, verify Projects, Blog (including tags and publish timestamps), Services, Pricing, Testimonials, CV, profile/SEO, and media selection from admin save through public rendering.
2. Submit unique disposable contact and booking requests; confirm each appears once in the correct Admin inbox with all fields and status transitions. Verify that failed storage returns the correct fallback.
3. Verify generated web/print/PDF resume after a CV update, including links, content freshness, and no unintended changes to the tracked/static PDF artifact.
4. Review public routes at 320, 360, 390, 768, 1024, and 1440 px: home, project list/detail, blog list/detail, CV/print, and booking/contact. Check images, focus order, labels, contrast, keyboard navigation, dialogs, filter behavior, and browser back/forward.
5. Test empty, loading, database failure, GitHub rate-limit, invalid slug, form validation, and rate-limit states. Run automated accessibility checks, then manually review any failures that require judgment.
6. Verify Vercel build/rewrites, asset responses, environment variables, secrets separation, robots, sitemap, canonical URLs, and health/readiness behavior against the deployed staging URL.
7. Capture the known-good staging commit, migration head, smoke results, and rollback steps. Promote only after content owners approve the public presentation.

**Acceptance gate:** all critical admin-to-public workflows pass on staging; no P0/P1 defects remain; migration and rollback are rehearsed; performance, accessibility, responsive, and monitoring checks have recorded results. Production verification remains separate and uses approved disposable records.

## Suggested delivery order

1. **Begin with Phase 0** and the Phase 3 dry-run protection. This establishes the data contract and reduces the chance of accidental content loss.
2. **Implement Phase 1** before enabling public database writes in production or changing credentials.
3. **Deliver Phase 2 in vertical slices:** Services, Pricing, Testimonials, then Home/SEO and category management, then Media picker. **Implementation slices are now in code.** Apply migration 012 and perform the guarded asset import, then verify each admin-to-public workflow in staging.
4. **Complete Phase 4** as public read paths move to the new content contract.
5. **Use Phase 5 as the release gate**, not a substitute for the implementation work.

## Do not do during implementation

- Do not read, paste, log, or commit `.env` secrets.
- Do not run the current seed sync against production.
- Do not point a local browser test at production forms or uploads.
- Do not remove the public fallback links until the replacement submission path passes staging failure tests.
- Do not change stored media URLs or public routes without a compatibility test and rollback path.

## Audit evidence and limitations

- Local public-site smoke suite: 29 passed; one third-party deprecation warning.
- Local routes reviewed at 390 px; primary content pages also reviewed at 1440 px. No page errors or horizontal overflow were observed in the reviewed pages.
- Checked local image, CSS, and JavaScript asset URLs returned HTTP 200.
- No live Supabase credentials were loaded and no live database writes were made.
- The live Vercel URL could not be fetched through the available browser service during the audit; deployment parity remains unverified.

Here is a comprehensive analysis of the `neo-admin` project.

---

# Neo Admin -- Comprehensive Project Analysis

## 1. Project Structure

```
C:\Users\Meshell\Desktop\FastHTML\neo-admin\
├── main.py                          # Entrypoint (serve)
├── conftest.py                      # Pytest fixtures
├── test_app.py                      # Test suite
├── requirements.txt                 # Dependencies
├── vercel.json                      # Vercel deployment config
├── .env / .env.example              # Environment variables
├── .python-version                  # Python version pin
├── .gitignore / .vercelignore       # Ignore files
├── README.md                        # "Portfolio-Admin"
├── Mcmoren_Website_Proposal.pdf     # Sample PDF
│
├── app/                             # Main application package
│   ├── __init__.py
│   ├── main.py                      # FastHTML app shell (core app setup)
│   ├── config.py                    # Settings dataclass from env
│   ├── theme.py                     # Faststrap theme + component defaults
│   │
│   ├── domain/
│   │   ├── __init__.py
│   │   └── models.py                # ~30 frozen dataclasses (AdminMetric, AdminDeal, etc.)
│   │
│   ├── infrastructure/
│   │   ├── __init__.py
│   │   ├── supabase_client.py       # Supabase config checks
│   │   ├── seed_data.py             # Static dashboard copy (METRICS, MODULES, ACTIVITY)
│   │   ├── auth_repository.py       # Login/auth logic
│   │   ├── project_repository.py    # CRUD for projects
│   │   ├── blog_repository.py       # CRUD for blog posts
│   │   ├── cv_repository.py         # CRUD for CV sections
│   │   ├── submission_repository.py # Inbox/contact form records
│   │   ├── deal_repository.py       # Deals, documents, public links
│   │   ├── deal_pdf.py              # PDF generation (ReportLab)
│   │   ├── media_repository.py      # Upload to Supabase Storage
│   │   ├── settings_repository.py   # Site profile CRUD
│   │   ├── payment_account_repository.py  # Bank account CRUD
│   │   ├── ai_settings_repository.py      # AI provider config CRUD
│   │   ├── ai_draft_repository.py         # Groq/OpenAI draft generation
│   │   ├── github_repository.py           # GitHub profile stats
│   │   ├── email_service.py               # Resend email (optional)
│   │   ├── content_sync.py                # Content sync helpers
│   │   └── sql/
│   │       ├── 001_initial_schema.sql
│   │       ├── 002_admin_access.sql
│   │       ├── 003_client_pipeline.sql
│   │       ├── 004_media_assets.sql
│   │       ├── 005_document_links_and_accounts.sql
│   │       ├── 006_production_hardening.sql
│   │       ├── 007_admin_production_hardening.sql
│   │       └── 008_sections_json.sql
│   │
│   ├── routes/                      # Route registration modules
│   │   ├── __init__.py              # setup_routes(app) - central registration
│   │   ├── helpers.py               # _safe_next_path
│   │   ├── auth.py                  # /login, /logout
│   │   ├── dashboard.py             # /, /dashboard/metrics, /dashboard/workspace-status
│   │   ├── projects.py              # /projects, /projects/save, /projects/upload-image, /projects/category/create
│   │   ├── blog.py                  # /blog, /blog/save
│   │   ├── cv.py                    # /cv, /cv/save, /cv/section/*/save (7 endpoints)
│   │   ├── submissions.py           # /submissions, /submissions/save
│   │   ├── deals.py                 # /deals, /deals/save, /deals/quick, /deals/ai-draft, /deals/delete, /deals/documents/*
│   │   ├── media.py                 # /media, /media/search, /media/upload, /media/update, /media/replace, /media/delete
│   │   ├── documents.py             # /documents/{token}, /documents/{token}/respond, /documents/{token}/pdf
│   │   ├── settings.py              # /settings, /settings/save, /settings/access, /settings/accounts*, /settings/ai-*
│   │   └── ai_assistant.py          # /ai-assistant, /ai-assistant/generate
│   │
│   └── presentation/
│       ├── __init__.py
│       ├── shell.py                 # page_frame(), admin_sidebar(), admin_bottom_nav(), admin_mobile_header(), admin_mobile_drawer()
│       ├── page_helpers.py          # Shared widgets: floating_field, textarea_field, toggle_pill_group, search_filter_bar, live_search_bar, loading_action_button, toast_fragment, summary_card, section_wrap
│       └── pages/
│           ├── __init__.py
│           ├── dashboard.py         # Overview page with metrics ring, module cards, workspace status
│           ├── auth.py              # Login page (no shell)
│           ├── projects.py          # Two-panel list/editor workspace
│           ├── blog_admin.py        # Two-panel list/editor workspace
│           ├── cv_admin.py          # CV editor with modal section management
│           ├── submissions.py       # Two-panel inbox with convert-to-deal modal
│           ├── deals.py             # Pipeline workspace with editor, quick doc, AI draft
│           ├── media.py             # Asset library with upload, edit, replace, delete modals
│           ├── settings_admin.py    # Profile, access, accounts, AI providers, health cards
│           ├── public_documents.py  # Client-facing document portal (separate design system)
│           └── ai_assistant.py      # Standalone AI draft page
│
└── assets/
    ├── css/
    │   ├── custom.css               # Entry point - imports all partials
    │   ├── _brand.css               # CSS custom properties (dark + light theme tokens)
    │   ├── _typography.css          # Font stacks (Space Grotesk + Inter), heading hierarchy
    │   ├── _layout.css              # Sidebar, mobile header, bottom nav, grid, responsive
    │   ├── _surfaces.css            # Card styles, surface variants, body background gradients
    │   ├── _interactions.css        # Buttons, nav links, form controls, filter chips, radio pills, line items
    │   └── doc-portal.css           # Separate design system for public document portal (1093 lines)
    ├── js/
    │   └── admin.js                 # Client-side behaviors (698 lines)
    ├── icon-192.png                 # PWA icon
    ├── icon-512.png                 # PWA icon
    └── generated/                   # Generated PDFs (gitignored)
```

---

## 2. FastHTML Entrypoint

**File: `C:\Users\Meshell\Desktop\FastHTML\neo-admin\main.py`**

Minimal top-level entrypoint. Imports `app` from `app.main` and calls `serve()`.

**File: `C:\Users\Meshell\Desktop\FastHTML\neo-admin\app\main.py`** (the real core)

This is the central app assembly. Key operations:
1. Creates `FastHTML(secret_key=..., session_cookie=...)`
2. Adds `Beforeware` with `_require_admin_login` for route protection, skipping `/login`, `/logout`, `/assets/*`, `/documents/*`, etc.
3. Calls `add_bootstrap(app, theme=NEO_ADMIN_THEME, mode="dark", use_cdn=...)` -- Faststrap Bootstrap integration
4. Calls `add_pwa(...)` -- PWA manifest, service worker, caching config
5. Calls `setup_theme_defaults()` -- sets component defaults
6. Conditionally mounts local assets via `mount_assets()` when not on Vercel CDN
7. Adds global `<head>` links: Google Fonts (Space Grotesk + Inter), custom CSS, admin JS
8. Calls `setup_routes(app)` to wire all route modules

---

## 3. Theme / Defaults Module

**File: `C:\Users\Meshell\Desktop\FastHTML\neo-admin\app\theme.py`**

- Defines `BRAND` color dict: primary `#2DB8E8` (cyan), secondary `#F3A53D` (amber), success `#6CD8A4`, info `#7F9BFF`, warning `#F2C35B`, danger `#FF727E`, light `#F4F8FB`, dark `#091321`
- Creates `NEO_ADMIN_THEME` via `faststrap.create_theme(...)`
- `setup_theme_defaults()` calls `set_component_defaults()` for Button (size="md"), Card (cls="border-0 shadow-sm"), Badge (pill=True)

---

## 4. Route Layout and Page Files

### Route Registration (`app/routes/__init__.py`)
Central `setup_routes(app)` registers all modules in order:
1. `auth` -- login/logout (first, so auth logic is live before any protected route)
2. `dashboard` -- root `/` and HTMX partials
3. `projects`, `blog`, `cv`, `submissions`, `deals`, `media`, `documents`, `settings`, `ai_assistant`

### Complete Route Map

| Route | Method | Handler | Purpose |
|---|---|---|---|
| `/` | GET | `overview()` | Dashboard overview |
| `/dashboard/metrics` | GET | `dashboard_metrics()` | Auto-refresh metrics ring (HTMX) |
| `/dashboard/workspace-status` | GET | `dashboard_workspace_status()` | LazyLoad workspace card (HTMX) |
| `/login` | GET | `login()` | Login form |
| `/login` | POST | `login_submit()` | Authenticate + session |
| `/logout` | GET | `logout()` | Clear session |
| `/projects` | GET | `projects()` | Projects workspace |
| `/projects/save` | POST | `project_save()` | Save project |
| `/projects/upload-image` | POST | `projects_upload_image()` | HTMX image upload |
| `/projects/category/create` | POST | `project_category_create()` | Dynamic category add |
| `/blog` | GET | `blog()` | Blog workspace |
| `/blog/save` | POST | `blog_save()` | Save blog post |
| `/cv` | GET | `cv()` | CV workspace |
| `/cv/save` | POST | `cv_save()` | Save CV profile |
| `/cv/section/core_skills/save` | POST | save core skills | Section CRUD |
| `/cv/section/competencies/save` | POST | save competencies | Section CRUD |
| `/cv/section/work_history/save` | POST | save work history | Section CRUD |
| `/cv/section/education/save` | POST | save education | Section CRUD |
| `/cv/section/certifications/save` | POST | save certs | Section CRUD |
| `/cv/section/tools/save` | POST | save tools | Section CRUD |
| `/cv/section/languages/save` | POST | save languages | Section CRUD |
| `/submissions` | GET | `submissions()` | Inbox workspace |
| `/submissions/save` | POST | `submissions_save()` | Update submission |
| `/deals` | GET | `deals()` | Pipeline workspace |
| `/deals/save` | POST | `deals_save()` | Save deal/document |
| `/deals/quick` | POST | `deals_quick_document_save()` | Quick document creation |
| `/deals/delete` | POST | `deals_delete()` | Delete deal |
| `/deals/ai-draft` | POST | `deals_ai_draft()` | AI draft generation |
| `/deals/documents/update` | POST | `deal_document_update()` | Status change |
| `/deals/documents/link` | POST | `deal_document_link_action()` | Revoke/regenerate/resend |
| `/deals/{deal_id}/documents/{document_kind}/pdf` | GET | `deal_document_pdf()` | PDF download |
| `/media` | GET | `media()` | Media library |
| `/media/search` | GET | `media_search()` | HTMX live search |
| `/media/upload` | POST | `media_upload()` | File upload |
| `/media/update` | POST | `media_update()` | Metadata update |
| `/media/replace` | POST | `media_replace()` | File replacement |
| `/media/delete` | POST | `media_delete()` | Delete asset |
| `/documents/{token}` | GET | `public_document()` | Client portal |
| `/documents/{token}/respond` | POST | `public_document_respond()` | Client response |
| `/documents/{token}/pdf` | GET | `public_document_pdf()` | Client PDF download |
| `/settings` | GET | `settings_page()` | Settings workspace |
| `/settings/save` | POST | `settings_save()` | Save profile |
| `/settings/access` | POST | `settings_access_save()` | Change credentials |
| `/settings/accounts` | POST | `settings_account_save()` | Save payment account |
| `/settings/accounts/edit` | POST | `settings_account_edit()` | Load account in form |
| `/settings/accounts/delete` | POST | `settings_account_delete()` | Delete account |
| `/settings/ai-save` | POST | `settings_ai_save()` | Save AI provider |
| `/settings/ai-set-default` | POST | `settings_ai_set_default()` | Set default provider |
| `/settings/ai-delete` | POST | `settings_ai_delete()` | Delete AI provider |
| `/ai-assistant` | GET | `ai_assistant_get()` | AI assistant page |
| `/ai-assistant/generate` | POST | `ai_assistant_generate()` | Generate AI draft |

---

## 5. Asset Mounting (CSS, JS)

**Pattern** (`app/main.py` lines 56-91):

- **Faststrap bootstrap**: `add_bootstrap(app, theme=NEO_ADMIN_THEME, mode="dark", use_cdn=...)` injects Bootstrap CSS/JS, HTMX, and Bootstrap Icons either from CDN or local files
- **PWA**: `add_pwa(...)` registers service worker, manifest, pre-cache URLs
- **Local assets**: When `not settings.use_cdn` (i.e., local dev), `mount_assets(app, "assets", url_path="/assets")` serves the `assets/` directory at `/assets/`
- **Global `<head>` links**:
  - Google Fonts: Space Grotesk (400-700) + Inter (300-600)
  - `/assets/css/custom.css?v=1`
  - `/assets/js/admin.js?v=20260427c` (deferred)

**Vercel deployment** (`vercel.json`):
- Static assets served by `@vercel/static` build
- All other routes rewritten to `main.py` via `@vercel/python`

---

## 6. Custom CSS Files

### `custom.css` (entry point)
Imports all partials in cascade order, then adds section editor styles (`.deal-section-item`, etc.)

### `_brand.css` -- CSS Custom Properties
- Dark theme (default): deep navy backgrounds (`#07111f`), cyan primary, amber secondary, glassmorphism surfaces
- Light theme (`[data-bs-theme="light"]`): white surfaces, dark text, adjusted blues/ambers
- Defines `--admin-sidebar-width: 18.75rem`, `--admin-bottom-nav-height: 5.6rem`

### `_typography.css`
- Body font: Inter
- Heading font: Space Grotesk (used in `.admin-page-title`, `.admin-section-title`, `.admin-metric-value`, etc.)
- Kicker labels: uppercase, letter-spacing 0.16em, cyan color
- Project category labels, field labels, mobile title, brand title/subtitle all styled

### `_layout.css` -- Grid and Responsive (872 lines)
- Desktop: CSS Grid layout `grid-template-columns: var(--admin-sidebar-width) minmax(0, 1fr)`
- Sidebar: Sticky, `width: var(--admin-sidebar-width)`, glassmorphism with `backdrop-filter: blur(18px)`
- Mobile header: Sticky top bar with blur
- Bottom nav: Fixed bottom, 5-column grid, pill-shaped floating bar with shadow
- Mobile drawer: Offcanvas from left, `width: min(88vw, 22rem)`
- Pipeline strip: Horizontal stage counter grid (Deals page)
- Panel toggle: Mobile list/editor toggle button
- Detail blocks, filter rows, form groups, stack lists
- Extensive light theme overrides for sidebar, drawer, bottom nav, detail blocks

### `_surfaces.css` -- Card Styles (143 lines)
- Body background: radial gradient atmosphere (cyan + amber glows on dark)
- `.admin-surface-card`: Gradient background, border, shadow, hover border glow
- `.admin-project-card`: Selected state ring, new-item left amber border
- Module icon boxes, metric delta badges, unread badge
- Light theme body gradient and card overrides

### `_interactions.css` -- Buttons and Controls (508 lines)
- Sidebar nav links: hover/active cyan background, translateX micro-animation
- `.admin-nav-btn` / `.admin-module-btn`: Cyan translucent background, hover lift
- `.admin-install-btn`: Amber translucent background
- `.admin-filter-chip`: Pill-shaped filter buttons with active cyan state
- `.admin-radio-pill`: Toggle group pills for form selections
- `.admin-form-control`: Dark glassmorphism inputs with cyan focus
- HTMX loading spinner (CSS `::after` pseudo-element on `button.htmx-request`)
- Line items editor table styling
- CV section management cards and modal item rows
- Full light theme override for all interactive elements

### `doc-portal.css` -- Public Document Portal (1093 lines)
- Completely separate design system from admin
- Light-mode, print-optimized, brand-aligned
- Variables: `--doc-navy`, `--doc-cyan`, `--doc-amber`, `--doc-surface`
- Components: brand bar (sticky), logo mark, type badge, hero block, meta strip grid
- Section cards with navy headers and cyan accent bars
- Line items table with package grouping support
- Payment account panel, expiry warning banner, package selector radio group
- Response zone (dark navy background, primary/ghost/pay buttons)
- Response history timeline
- Print styles (hides response zone, history, footer)
- HTMX button loading states
- Faststrap Markdown content styling for rendered markdown sections
- Mobile responsive (single-column meta, stacked CTAs)

---

## 7. Component Usage Patterns (Faststrap Components)

The project makes extensive use of **Faststrap** components throughout:

### Layout Components
- `Container`, `Row`, `Col` -- Bootstrap grid system
- `SidebarNavbar`, `SidebarNavItem` -- Desktop sidebar navigation
- `BottomNav`, `BottomNavItem` -- Mobile bottom navigation
- `Drawer` -- Mobile offcanvas menu and install instructions
- `ToastContainer` -- OOB toast notification container

### Feedback Components
- `Alert` -- Save/update status alerts with variant colors
- `Badge` -- Status indicators (Published, Draft, Featured, etc.)
- `Toast` -- OOB toast notifications (swapped into `#toast-container`)
- `EmptyState` -- Placeholder when lists have no items
- `MetricCard` -- Dashboard metric cards with delta/trend
- `SEO` -- `<title>`, `<meta>` tag generation

### Form Components
- `FloatingLabel` -- Floating input labels
- `FormGroup` -- Label + input wrapper with help text
- `FilterBar` -- Search/filter form with mode (apply vs auto)
- `ToggleGroup` -- Radio-style pill toggle groups
- `Modal` -- Bootstrap modals for CV sections, category creation, media CRUD, submission conversion

### Content Components
- `Icon` -- Bootstrap Icons integration
- `Markdown` -- Render markdown to HTML (used in document portal sections)
- `Card` -- Surface cards with consistent styling

### Preset Components
- `LoadingButton` (`faststrap.presets.LoadingButton`) -- HTMX-backed buttons with loading state
- `AutoRefresh` (`faststrap.presets.AutoRefresh`) -- Periodic HTMX polling (dashboard metrics every 30s)
- `LazyLoad` (`faststrap.presets.LazyLoad`) -- Deferred content loading (workspace status card)
- `toast_response()` (`faststrap.presets`) -- Toast + content response wrapper (document portal)

---

## 8. HTMX Usage Patterns

HTMX is deeply integrated as the primary interactivity mechanism:

### Form Submission Pattern (dominant pattern across all workspace pages)
```python
Form(
    # ... form fields ...
    loading_action_button("Save", endpoint="/path/save", target="#result-div"),
    Div(id="save-result"),
    action="/path/save",
    method="post",
    hx_post="/path/save",
    hx_target="#save-result",
    hx_swap="innerHTML",
    cls="admin-settings-form",
)
```

### Server Response Patterns
1. **Success**: Returns `(Response("", headers={"HX-Refresh": "true"}), toast_fragment(...))` -- triggers full page refresh + toast
2. **Failure**: Returns `status_alert(...)` -- swaps error into `#save-result` div
3. **Partial swap**: Returns a component (e.g., `_accounts_panel()`, `_ai_settings_card()`) with `hx_target` matching a card ID for `outerHTML` replacement

### Specific HTMX Patterns Used

- **`hx-post`** on all forms (projects, blog, CV, deals, submissions, settings, media, documents)
- **`hx-get`** on search/filter bar submissions
- **`hx-target` / `hx-swap`** targeting result divs (`innerHTML`) or whole sections (`outerHTML`)
- **`HX-Refresh: true`** header -- HTMX auto-refreshes the page on success
- **`HX-Redirect`** header -- Used by quick document creation to navigate to `/deals?deal_id=...`
- **`hx_vals`** -- JSON payload injection (deal delete button)
- **`hx-confirm`** -- Native confirm dialog (delete actions)
- **`hx_encoding="multipart/form-data"`** -- File uploads (project image, media upload/replace)
- **`hx_indicator`** -- Spinner display during requests
- **`hx_swap_oob="afterbegin:#toast-container"`** -- Out-of-band toast swap
- **`hx-on::after-request`** -- Post-request callback (category modal auto-close)
- **Auto-refresh polling**: `AutoRefresh` preset on dashboard metrics (30s interval)
- **Lazy loading**: `LazyLoad` preset for workspace status card
- **Live search**: `FilterBar` with `mode="auto"` and debounced GET requests (media search)

### Client-Side HTMX Hooks (`admin.js`)
- `htmx:configRequest` -- Serializes CV section data and deal sections before POST
- `htmx:afterSwap` -- Auto-initializes Bootstrap toasts from OOB swaps
- `htmx:beforeProcessResponse` -- Intercepts `HX-Refresh` when a modal is open to prevent mid-modal page reload
- `htmx:afterRequest` -- Handles post-save modal close + delayed page reload

---

## 9. Form Handling Patterns

### Architecture Pattern
Every workspace follows the same consistent pattern:

1. **Route module** (`app/routes/*.py`) receives form fields as typed parameters, calls repository functions, returns either success (HX-Refresh + toast) or error (status alert)
2. **Page module** (`app/presentation/pages/*.py`) renders the form with `hx_post`, `hx_target`, `hx_swap` pointing to the same route
3. **Repository module** (`app/infrastructure/*_repository.py`) handles data access (Supabase or seed data)
4. **Domain models** (`app/domain/models.py`) define frozen dataclasses for all entities

### Shared Form Helpers (`page_helpers.py`)
- `floating_field()` -- FloatingLabel wrapper with admin styling
- `textarea_field()` -- FormGroup with admin textarea
- `toggle_pill_group()` -- ToggleGroup as hidden input replacement for radio selects
- `search_filter_bar()` -- FilterBar with hidden fields for state preservation
- `live_search_bar()` -- Auto-submitting search with HTMX swap
- `loading_action_button()` -- LoadingButton with `hx_include="closest form"`
- `toast_fragment()` -- Toast with OOB swap
- `status_alert()` -- Alert for error/feedback messages
- `summary_card()` -- Metric summary card for workspace headers
- `section_wrap()` -- Section with Space Grotesk H2 title

### Form Data Flow
```
Browser Form (hx_post="/entity/save")
    --> Route handler (typed parameters from form)
        --> Repository function
            --> Supabase client (or seed data fallback)
        <-- Result dataclass (success/tone/message)
    <-- Starlette Response with HX-Refresh header + Toast
        OR status_alert HTML fragment
```

### Notable Special Cases
- **Line items editor**: Client-side JS serializes table rows to pipe-delimited text in a hidden input before form submit
- **Deal sections editor**: Client-side JS manages a JSON array in a hidden input; sections are reordered/edited in a Bootstrap modal, then auto-saved via `htmx.trigger(dealForm, 'submit')`
- **CV section modals**: Each section (skills, work history, education, etc.) uses `<template>` elements cloned by JS, serialized to JSON on `htmx:configRequest`
- **Document portal response**: Multi-action form (accept/decline/pay/comment) with package radio selection and client-side validation
- **File uploads**: Use `enctype="multipart/form-data"` with `hx_encoding` for Supabase Storage uploads

---

## 10. Navigation Structure

### Desktop Sidebar (`admin_sidebar()` in `shell.py`)
Full-height sticky sidebar with:
- **Brand block**: Logo initials + name + "Portfolio Admin" subtitle
- **Workspace nav**: 9 items via `SidebarNavbar` with Bootstrap Icons
- **Action buttons**: "Public Site" (external link), "Install App" (PWA trigger), "Sign Out"

### Navigation Items (NAV_ITEMS)
| Label | Route | Icon |
|---|---|---|
| Overview | `/` | `grid` |
| Projects | `/projects` | `kanban` |
| Blog | `/blog` | `journal-richtext` |
| CV | `/cv` | `file-earmark-person` |
| Submissions | `/submissions` | `inbox` |
| Deals | `/deals` | `briefcase` |
| AI Assistant | `/ai-assistant` | `robot` |
| Media | `/media` | `images` |
| Settings | `/settings` | `sliders` |

### Mobile Bottom Navigation (BOTTOM_NAV_ITEMS)
4 primary items + "Menu" button (opens offcanvas drawer):
| Label | Route | Icon |
|---|---|---|
| Overview | `/` | `grid` |
| Projects | `/projects` | `kanban` |
| Submissions | `/submissions` | `inbox` |
| Deals | `/deals` | `briefcase` |
| Menu | Offcanvas trigger | `list` |

### Mobile Header
Sticky top bar showing: logo + active page title + install button

### Mobile Drawer (Offcanvas)
Contains full navigation (all 9 items) + action buttons (Public Site, Install App, Sign Out)

### Install Drawer
Bottom offcanvas with PWA install instructions for iOS/Android

### Brand Resolution
- Site name is loaded from Supabase via `get_site_profile()` (cached with `lru_cache`)
- Falls back to `settings.owner_name` ("Olorundare Micheal")
- Sidebar title uses the last name portion
- Brand initials are derived from the first two words of the site name

### Active State
- Sidebar nav items: `active` class applied when `href == current` path
- Bottom nav items: Same logic, limited to 4 primary items
- Mobile header title: Resolved from `NAV_ITEMS` lookup by current path

---

## Summary of Key Architectural Decisions

1. **Clean Architecture**: Domain models -> Infrastructure (repositories) -> Presentation (pages) -> Routes. Each layer has clear responsibilities.
2. **Faststrap as UI framework**: Heavy use of Faststrap component library wrapping Bootstrap 5 with HTMX integration, providing `LoadingButton`, `FilterBar`, `ToggleGroup`, `AutoRefresh`, `LazyLoad`, `Modal`, `Toast`, etc.
3. **Dark-first design**: CSS custom properties with `[data-bs-theme="light"]` overrides for full light theme support.
4. **Two design systems**: Admin panel (dark glassmorphism) and document portal (light, print-optimized) have completely separate CSS.
5. **Supabase-first with graceful fallback**: All repositories check for Supabase config; seed data provides offline development.
6. **PWA-capable**: Service worker, manifest, install prompts, offline support via `add_pwa()`.
7. **HTMX everywhere**: All interactivity via HTMX with `HX-Refresh`, OOB toasts, partial swaps, and lazy loading -- no custom SPA framework.
8. **Deployed to Vercel**: `vercel.json` configures Python serverless function + static asset serving.
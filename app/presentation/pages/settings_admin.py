"""Settings workspace for Neo Admin."""

from __future__ import annotations

from fasthtml.common import A, Button, Div, Form, H2, H3, Input, Label, Option, P, Select, Span, Strong
from faststrap import Badge, Card, Col, EmptyState, Row, SEO

from app.config import settings
from app.infrastructure.ai_settings_repository import PROVIDER_PRESETS, get_active_provider, get_ai_providers, save_ai_provider, delete_ai_provider
from app.infrastructure.auth_repository import get_admin_access_profile
from app.infrastructure.github_repository import get_github_stats
from app.infrastructure.payment_account_repository import delete_payment_account, list_payment_accounts, save_payment_account
from app.infrastructure.settings_repository import get_site_profile
from app.infrastructure.supabase_client import service_role_is_configured, supabase_is_configured
from app.presentation.page_helpers import SectionWrap, floating_field, loading_action_button, status_alert, summary_card, textarea_field
from app.presentation.shell import page_frame


def settings_save_status_fragment(title: str, message: str, tone: str = "info") -> Div:
    return status_alert(title, message, tone)


def _health_row(label: str, ready: bool, note: str) -> Div:
    return Div(
        Div(
            Span(label, cls="admin-field-label"),
            Strong("Ready" if ready else "Needs setup"),
        ),
        Badge("OK" if ready else "Check", cls=f"{'text-bg-success' if ready else 'text-bg-warning'} admin-project-flag"),
        P(note, cls="admin-module-copy mb-0"),
        cls="admin-detail-block",
    )


def _ai_settings_card() -> Card:
    """Return the AI settings card for HTMX partial swaps (set-default / delete)."""
    ai_providers = get_ai_providers()
    active_provider = next((p for p in ai_providers if p.is_default), ai_providers[0] if ai_providers else None)

    provider_options_html = [
        Option(label, value=ptype)
        for ptype, (label, _) in PROVIDER_PRESETS.items()
    ]

    provider_rows = []
    for p in ai_providers:
        row_actions = []
        if not p.is_default:
            row_actions.append(
                A("Set Default", href=f"/settings/ai-set-default?id={p.config_id}",
                  cls="btn admin-install-btn btn-sm",
                  hx_post=f"/settings/ai-set-default?id={p.config_id}",
                  hx_target="#ai-settings-card", hx_swap="outerHTML"),
            )
        if p.source != "env":
            row_actions.append(
                A("Delete", href=f"/settings/ai-delete?id={p.config_id}",
                  cls="btn btn-outline-danger btn-sm",
                  hx_post=f"/settings/ai-delete?id={p.config_id}",
                  hx_target="#ai-settings-card", hx_swap="outerHTML",
                  hx_confirm="Delete this AI provider? This cannot be undone."),
            )
        provider_rows.append(
            Div(
                Div(
                    Div(Span("Label", cls="admin-field-label"), Strong(p.label)),
                    Div(Span("Type", cls="admin-field-label"), Strong(p.provider_type.title())),
                    Div(Span("Model", cls="admin-field-label"), Strong(p.model)),
                    Div(Span("Base URL", cls="admin-field-label"), Strong(p.base_url)),
                    Div(Span("API Key", cls="admin-field-label"), Strong(p.api_key if p.api_key else "Not set")),
                    Div(Span("Source", cls="admin-field-label"), Strong(p.source.title())),
                    cls="admin-field-grid",
                ),
                Div(
                    Badge("Default", cls="text-bg-success admin-project-flag me-2") if p.is_default else "",
                    *row_actions,
                    cls="mt-2 d-flex gap-2 flex-wrap",
                ),
                cls="admin-detail-block mb-3",
            )
        )

    ai_provider_form = Form(
        Input(type="hidden", name="config_id", value="new"),
        Row(
            Col(floating_field("Provider Label", "label", "", placeholder="e.g. My Groq Key"), span=12, md=6),
            Col(
                Div(
                    Label("Provider Type", cls="admin-form-label"),
                    Select(
                        *provider_options_html,
                        name="provider_type",
                        cls="form-select admin-form-control",
                        id="ai-provider-type",
                    ),
                    cls="admin-form-group",
                ),
                span=12, md=6, cls="mt-3 mt-md-0",
            ),
            cls="g-3",
        ),
        Row(
            Col(floating_field("Base URL", "base_url", "", placeholder="https://api.groq.com/openai/v1"), span=12, md=6),
            Col(floating_field("Model", "model", "", placeholder="llama-3.3-70b-versatile"), span=12, md=6, cls="mt-3 mt-md-0"),
            cls="g-3 mt-1",
        ),
        floating_field("API Key", "api_key", "", input_type="password", placeholder="sk-..."),
        Div(
            Span("Set as default provider", cls="admin-check-label"),
            Input(type="checkbox", name="set_default", value="1", cls="form-check-input admin-check-input"),
            cls="admin-check-row mt-2",
        ),
        Div(
            loading_action_button("Save AI Provider", endpoint="/settings/ai-save", target="#ai-save-result"),
            Span(
                "Live sync enabled" if service_role_is_configured() else "Add the service-role key to enable saving",
                cls="admin-save-note",
            ),
            cls="admin-form-actions mt-4",
        ),
        Div(id="ai-save-result", cls="mt-3"),
        action="/settings/ai-save",
        method="post",
        hx_post="/settings/ai-save",
        hx_target="#ai-save-result",
        hx_swap="innerHTML",
        cls="admin-settings-form",
    )

    return Card(
        Div(
            H3("AI Provider Settings", cls="admin-subsection-title"),
            P("Manage AI providers for drafting proposals, quotes, invoices, and more. Add multiple providers and choose the default.", cls="admin-module-copy"),
            Div(
                Div(Span("Active Provider", cls="admin-field-label"), Strong(active_provider.label if active_provider else "None configured")),
                Div(Span("Active Model", cls="admin-field-label"), Strong(active_provider.model if active_provider else "N/A")),
                Div(Span("Active Endpoint", cls="admin-field-label"), Strong(active_provider.base_url if active_provider else "N/A")),
                cls="admin-field-grid admin-detail-block mb-4",
            ) if active_provider else "",
            Div(H3("Saved Providers", cls="admin-subsection-title h6"), *provider_rows) if provider_rows else EmptyState(icon="cpu", title="No AI providers configured", description="Add your first provider below to enable AI-powered drafting.", cls="py-3"),
            Div(H3("Add / Edit Provider", cls="admin-subsection-title"), ai_provider_form, cls="mt-4"),
            cls="admin-panel-stack",
        ),
        cls="admin-surface-card h-100",
        id="ai-settings-card",
    )


def _account_form(account=None) -> Form:
    """Return the payment account form, pre-filled if editing."""
    aid = account.account_id if account else ""
    return Form(
        Input(type="hidden", name="account_id", value=aid),
        Row(
            Col(floating_field("Account Label", "label", account.label if account else "", placeholder="Primary business account", required=True), span=12, md=6),
            Col(floating_field("Bank Name", "bank_name", account.bank_name if account else "", placeholder="Access Bank", required=True), span=12, md=6, cls="mt-3 mt-md-0"),
            cls="g-3",
        ),
        Row(
            Col(floating_field("Account Name", "account_name", account.account_name if account else "", placeholder="Olorundare Micheal", required=True), span=12, md=6),
            Col(floating_field("Account Number", "account_number", account.account_number if account else "", placeholder="0123456789", required=True), span=12, md=6, cls="mt-3 mt-md-0"),
            cls="g-3 mt-1",
        ),
        textarea_field("Internal Note", "note", account.note if account else "", rows=3, placeholder="Use this account for deposits, final invoices, USD transfers, or specific client types."),
        Div(
            Span("Mark as default", cls="admin-check-label"),
            Input(type="checkbox", name="is_default", value="1", cls="form-check-input admin-check-input", checked=(account.is_default if account else False)),
            cls="admin-check-row mt-2",
        ),
        Div(
            loading_action_button("Save Payment Account", endpoint="/settings/accounts", target="#accounts-section"),
            Span(
                "Live sync enabled" if service_role_is_configured() else "Add the service-role key to enable saving",
                cls="admin-save-note",
            ),
            cls="admin-form-actions mt-4",
        ),
        action="/settings/accounts",
        method="post",
        hx_post="/settings/accounts",
        hx_target="#accounts-section",
        hx_swap="outerHTML",
        cls="admin-settings-form",
    )


def _accounts_panel(edit_account=None) -> Card:
    """Return the payment accounts card for HTMX partial swaps."""
    accounts = list_payment_accounts()
    account_rows = [
        Div(
            Div(Span(account.label, cls="admin-field-label"), Strong(account.bank_name)),
            Div(Span("Account Name", cls="admin-field-label"), Strong(account.account_name)),
            Div(Span("Account Number", cls="admin-field-label"), Strong(account.account_number)),
            Div(Span("Default", cls="admin-field-label"), Strong("Yes" if account.is_default else "No")),
            Div(
                Button("Edit", type="button", cls="btn admin-install-btn btn-sm",
                       hx_post=f"/settings/accounts/edit?id={account.account_id}",
                       hx_target="#accounts-section", hx_swap="outerHTML"),
                Button("Delete", type="button", cls="btn btn-outline-danger btn-sm",
                       hx_post=f"/settings/accounts/delete?id={account.account_id}",
                       hx_target="#accounts-section", hx_swap="outerHTML",
                       hx_confirm="Delete this payment account? This cannot be undone."),
                cls="d-flex gap-2 mt-2",
            ),
            cls="admin-field-grid admin-detail-block mb-3",
        )
        for account in accounts
    ]
    return Card(
        Div(
            H3("Payment Accounts", cls="admin-subsection-title"),
            P("Saved accounts become available when drafting invoice links and PDF exports, so you can choose the receiving account per client workflow.", cls="admin-module-copy"),
            Div(*account_rows, cls="mb-4") if account_rows else "",
            Div(H3("Add / Edit Account", cls="admin-subsection-title"), _account_form(edit_account), cls="mt-4"),
            cls="admin-panel-stack",
        ),
        cls="admin-surface-card h-100",
        id="accounts-section",
    )


def settings_workspace_page() -> tuple:
    profile = get_site_profile()
    access = get_admin_access_profile()
    github = get_github_stats()
    identity_panel = Card(
        Div(
            Div(
                Span("Public identity", cls="admin-kicker"),
                H2(profile.full_name, cls="admin-section-title mb-2"),
                P("This workspace manages the profile and metadata the public portfolio uses for branding, contact details, and SEO defaults.", cls="admin-module-copy mb-0"),
                cls="admin-detail-copy",
            ),
            Div(
                Badge(profile.source.title(), cls="text-bg-secondary admin-metric-delta"),
                Badge("Write enabled" if service_role_is_configured() else "Read-only for now", cls=f"{'text-bg-success' if service_role_is_configured() else 'text-bg-warning'} admin-metric-delta"),
                cls="d-flex flex-wrap gap-2 mt-3",
            ),
            Div(
                Row(
                    Col(
                        Div(
                            H3("Current Profile", cls="admin-subsection-title"),
                            Div(
                                Div(Span("Display Name", cls="admin-field-label"), Strong(profile.full_name)),
                                Div(Span("Role", cls="admin-field-label"), Strong(profile.role)),
                                Div(Span("Site Label", cls="admin-field-label"), Strong(profile.site_name)),
                                Div(Span("Site URL", cls="admin-field-label"), Strong(profile.site_url)),
                                cls="admin-field-grid",
                            ),
                            cls="admin-detail-block",
                        ),
                        span=12,
                        md=6,
                    ),
                    Col(
                        Div(
                            H3("Contact & SEO", cls="admin-subsection-title"),
                            Div(
                                Div(Span("Email", cls="admin-field-label"), Strong(profile.email)),
                                Div(Span("Phone", cls="admin-field-label"), Strong(profile.phone)),
                                Div(Span("Location", cls="admin-field-label"), Strong(profile.location)),
                                Div(Span("SEO Title", cls="admin-field-label"), Strong(profile.seo_title)),
                                cls="admin-field-grid",
                            ),
                            cls="admin-detail-block",
                        ),
                        span=12,
                        md=6,
                        cls="mt-4 mt-md-0",
                    ),
                    cls="g-4 mt-1",
                ),
                cls="mt-4",
            ),
            cls="admin-panel-stack",
        ),
        cls="admin-surface-card h-100",
    )

    form = Form(
        Row(
            Col(floating_field("Full Name", "full_name", profile.full_name, placeholder="Olorundare Micheal Babawale", required=True), span=12, md=7),
            Col(floating_field("Role", "role", profile.role, placeholder="Full-Stack & AI Systems Architect", required=True), span=12, md=5, cls="mt-3 mt-md-0"),
            cls="g-3",
        ),
        Row(
            Col(floating_field("Site Label", "site_name", profile.site_name, placeholder="Micheal Olorundare Portfolio", required=True), span=12, md=6),
            Col(floating_field("Site URL", "site_url", profile.site_url, input_type="url", placeholder="https://your-domain.com", required=True), span=12, md=6, cls="mt-3 mt-md-0"),
            cls="g-3 mt-1",
        ),
        Row(
            Col(floating_field("Email", "email", profile.email, input_type="email", placeholder="name@example.com"), span=12, md=6),
            Col(floating_field("Phone", "phone", profile.phone, placeholder="+234..."), span=12, md=6, cls="mt-3 mt-md-0"),
            cls="g-3 mt-1",
        ),
        Row(
            Col(floating_field("WhatsApp", "whatsapp", profile.whatsapp, placeholder="+234..."), span=12, md=6),
            Col(floating_field("Location", "location", profile.location, placeholder="Ilorin, Nigeria"), span=12, md=6, cls="mt-3 mt-md-0"),
            cls="g-3 mt-1",
        ),
        Row(
            Col(floating_field("GitHub URL", "github", profile.github, input_type="url", placeholder="https://github.com/..."), span=12, md=6),
            Col(floating_field("LinkedIn URL", "linkedin", profile.linkedin, input_type="url", placeholder="https://linkedin.com/in/..."), span=12, md=6, cls="mt-3 mt-md-0"),
            cls="g-3 mt-1",
        ),
        textarea_field("SEO Title", "seo_title", profile.seo_title, rows=2, required=True, placeholder="Portfolio SEO title"),
        textarea_field("SEO Description", "seo_description", profile.seo_description, rows=5, required=True, placeholder="Default meta description"),
        Div(
            loading_action_button("Save Settings", endpoint="/settings/save", target="#settings-save-result"),
            Span(
                "Live sync enabled" if service_role_is_configured() else "Add the service-role key to enable saving",
                cls="admin-save-note",
            ),
            cls="admin-form-actions mt-4",
        ),
        Div(id="settings-save-result", cls="mt-3"),
        action="/settings/save",
        method="post",
        hx_post="/settings/save",
        hx_target="#settings-save-result",
        hx_swap="innerHTML",
        cls="admin-settings-form",
    )

    editor_panel = Card(
        Div(
            H3("Settings Editor", cls="admin-subsection-title"),
            P("The site label powers the public short-name brand, while the profile and contact fields sync into the public portfolio and CV surfaces.", cls="admin-module-copy"),
            form,
            cls="admin-panel-stack",
        ),
        cls="admin-surface-card h-100",
    )

    access_form = Form(
        floating_field("Login Email", "login_email", access.login_email, input_type="email", placeholder="admin@neoportfolio.dev", required=True, autocomplete="username"),
        floating_field("New Password", "password", "", input_type="password", placeholder="Leave blank to keep the current password", autocomplete="new-password"),
        floating_field("Confirm Password", "confirm_password", "", input_type="password", placeholder="Repeat the new password", autocomplete="new-password"),
        Div(
            loading_action_button("Save Admin Access", endpoint="/settings/access", target="#access-save-result"),
            Span(
                "Credentials are hashed before storage" if service_role_is_configured() else "Add the service-role key to enable saving",
                cls="admin-save-note",
            ),
            cls="admin-form-actions mt-4",
        ),
        Div(id="access-save-result", cls="mt-3"),
        action="/settings/access",
        method="post",
        hx_post="/settings/access",
        hx_target="#access-save-result",
        hx_swap="innerHTML",
        cls="admin-settings-form",
    )

    access_panel = Card(
        Div(
            H3("Admin Access", cls="admin-subsection-title"),
            P("Seeded credentials get you in the first time. After that, you can rotate the login email and password here without touching code.", cls="admin-module-copy"),
            Div(
                Div(Span("Current Login", cls="admin-field-label"), Strong(access.login_email)),
                Div(Span("Credential Source", cls="admin-field-label"), Strong(access.source.title())),
                cls="admin-field-grid admin-detail-block mb-4",
            ),
            access_form,
            cls="admin-panel-stack",
        ),
        cls="admin-surface-card h-100",
    )

    account_panel = _accounts_panel()

    github_card = Card(
        Div(
            H3("GitHub Pulse", cls="admin-subsection-title"),
            P(
                "Open-source proof from your GitHub profile. Stays graceful even when the API is unavailable.",
                cls="admin-module-copy",
            ),
            Div(
                Div(Span("Profile", cls="admin-field-label"), Strong(github.username)),
                Div(Span("Public Repos", cls="admin-field-label"), Strong(str(github.public_repos))),
                Div(Span("Stars", cls="admin-field-label"), Strong(str(github.stars))),
                Div(Span("Followers", cls="admin-field-label"), Strong(str(github.followers))),
                Div(Span("Recent Commits", cls="admin-field-label"), Strong(str(github.recent_commits))),
                Div(Span("Source", cls="admin-field-label"), Strong(github.source.title())),
                cls="admin-field-grid mt-3",
            ),
            cls="admin-panel-stack",
        ),
        cls="admin-surface-card h-100",
    )

    ai_card = _ai_settings_card()

    active_provider = get_active_provider()

    production_card = Card(
        Div(
            H3("Production Health", cls="admin-subsection-title"),
            P("Quick visibility for the environment pieces that decide whether the admin can read, write, email, and generate shareable links.", cls="admin-module-copy"),
            Div(
                _health_row("Supabase Read", supabase_is_configured(), "Requires SUPABASE_URL and SUPABASE_ANON_KEY."),
                _health_row("Supabase Write", service_role_is_configured(), "Requires SUPABASE_SERVICE_ROLE_KEY for admin saves and uploads."),
                _health_row("Email Sending", settings.email_enabled, "Requires RESEND_API_KEY plus a valid sender domain when email actions are added."),
                _health_row("AI Drafting", bool(active_provider and active_provider.api_key), "Requires an AI provider with a valid API key configured in AI Provider Settings above."),
                _health_row("Public Base URL", settings.base_url.startswith("https://"), "Use the deployed https admin URL so copied document links are production-safe."),
                _health_row("GitHub Pulse", bool(settings.github_access_token), "Optional, but improves GitHub stats reliability and rate limits."),
                cls="admin-settings-stack",
            ),
            cls="admin-panel-stack",
        ),
        cls="admin-surface-card h-100",
    )

    return (
        *SEO(
            title=f"{settings.app_name} | Settings",
            description="Settings workspace for managing public identity, profile links, and SEO defaults.",
            url=f"{settings.base_url}/settings",
        ),
        *page_frame(
            Row(
                summary_card("Profile Source", profile.source.title(), "Where the current public identity data is being loaded from."),
                summary_card("Brand Label", profile.site_name.replace(" Portfolio", ""), "This drives the public short-name brand treatment."),
                summary_card("Public URL", profile.site_url.replace("https://", ""), "Primary domain used in SEO and public links."),
                cls="g-4",
            ),
            # Sub-navigation for settings sections
            Div(
                A("Profile", href="#settings-profile", cls="admin-filter-chip active"),
                A("Access", href="#settings-access", cls="admin-filter-chip"),
                A("Accounts", href="#settings-accounts", cls="admin-filter-chip"),
                A("AI Providers", href="#settings-ai", cls="admin-filter-chip"),
                A("Health", href="#settings-health", cls="admin-filter-chip"),
                cls="admin-filter-row mb-4",
            ),
            SectionWrap(
                "Settings Workspace",
                Row(
                    # Identity panel — reference only; hidden on mobile to prioritise the edit forms
                    Col(identity_panel, span=12, lg=5, cls="d-none d-lg-block"),
                    Col(
                        Div(
                            Div(editor_panel, id="settings-profile"),
                            Div(access_panel, id="settings-access"),
                            Div(account_panel, id="settings-accounts"),
                            Div(ai_card, id="settings-ai"),
                            Div(production_card, id="settings-health"),
                            github_card,
                            cls="admin-settings-stack",
                        ),
                        span=12,
                        lg=7,
                    ),
                    cls="g-4",
                ),
            ),
            current="/settings",
            title="Settings",
        ),
    )

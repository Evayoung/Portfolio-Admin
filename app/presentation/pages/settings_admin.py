"""Settings workspace for Neo Admin — subpage views and ConfirmDialog modals."""

from __future__ import annotations

from fasthtml.common import A, Button, Div, Form, H2, H3, Input, Label, Option, P, Select, Span, Strong
from faststrap import Badge, Card, Col, EmptyState, Fx, Row, SEO
from faststrap.components.feedback.confirm import ConfirmDialog

from app.config import settings
from app.infrastructure.ai_settings_repository import PROVIDER_PRESETS, get_active_provider, get_ai_providers, save_ai_provider, delete_ai_provider
from app.infrastructure.auth_repository import get_admin_access_profile
from app.infrastructure.github_repository import get_github_stats
from app.infrastructure.payment_account_repository import delete_payment_account, list_payment_accounts, save_payment_account
from app.infrastructure.settings_repository import get_site_profile
from app.infrastructure.supabase_client import service_role_is_configured, supabase_is_configured
from app.presentation.page_helpers import SectionWrap, floating_field, loading_action_button, status_alert, textarea_field
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


def settings_tab_bar(active_tab: str = "profile") -> Div:
    tabs = [
        ("Profile", "/settings", "profile"),
        ("Access", "/settings/access", "access"),
        ("Accounts", "/settings/accounts", "accounts"),
        ("AI Providers", "/settings/ai", "ai"),
        ("Health & Services", "/settings/health", "health"),
    ]
    return Div(
        *[
            A(
                label,
                href=href,
                aria_label=f"Settings Section: {label}",
                aria_current="page" if active_tab == tab_id else None,
                cls=f"admin-filter-chip{' active' if active_tab == tab_id else ''}",
            )
            for label, href, tab_id in tabs
        ],
        cls="admin-filter-row mb-4",
    )


def _ai_settings_card() -> Card:
    """Return the AI settings card for HTMX partial swaps."""
    ai_providers = get_ai_providers()
    active_provider = next((p for p in ai_providers if p.is_default), ai_providers[0] if ai_providers else None)

    provider_options_html = [
        Option(label, value=ptype)
        for ptype, (label, _) in PROVIDER_PRESETS.items()
    ]

    provider_rows = []
    modals = []
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
            modal_id = f"delete-ai-modal-{p.config_id}"
            modals.append(
                ConfirmDialog(
                    f"Delete AI provider \"{p.label}\"? This cannot be undone.",
                    confirm_text="Delete Provider",
                    cancel_text="Cancel",
                    title=f"Delete AI Provider: {p.label}",
                    variant="danger",
                    dialog_id=modal_id,
                    hx_confirm_method="post",
                    hx_confirm_url=f"/settings/ai-delete?id={p.config_id}",
                    hx_target="#ai-settings-card",
                    hx_swap="outerHTML",
                )
            )
            row_actions.append(
                Button("Delete", type="button",
                       cls="btn admin-danger-btn btn-sm",
                       data_bs_toggle="modal", data_bs_target=f"#{modal_id}"),
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
            *modals,
            Div(H3("Add / Edit Provider", cls="admin-subsection-title"), ai_provider_form, cls="mt-4"),
            cls="admin-panel-stack",
        ),
        cls=[Fx.base, Fx.fade_in, "admin-surface-card h-100"],
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
    account_rows = []
    modals = []
    for account in accounts:
        modal_id = f"delete-account-modal-{account.account_id}"
        modals.append(
            ConfirmDialog(
                f"Delete payment account \"{account.label}\" ({account.bank_name})? This cannot be undone.",
                confirm_text="Delete Account",
                cancel_text="Cancel",
                title=f"Delete Payment Account: {account.label}",
                variant="danger",
                dialog_id=modal_id,
                hx_confirm_method="post",
                hx_confirm_url=f"/settings/accounts/delete?id={account.account_id}",
                hx_target="#accounts-section",
                hx_swap="outerHTML",
            )
        )
        account_rows.append(
            Div(
                Div(Span(account.label, cls="admin-field-label"), Strong(account.bank_name)),
                Div(Span("Account Name", cls="admin-field-label"), Strong(account.account_name)),
                Div(Span("Account Number", cls="admin-field-label"), Strong(account.account_number)),
                Div(Span("Default", cls="admin-field-label"), Strong("Yes" if account.is_default else "No")),
                Div(
                    Button("Edit", type="button", cls="btn admin-install-btn btn-sm",
                           hx_post=f"/settings/accounts/edit?id={account.account_id}",
                           hx_target="#accounts-section", hx_swap="outerHTML"),
                    Button("Delete", type="button", cls="btn admin-danger-btn btn-sm",
                           data_bs_toggle="modal", data_bs_target=f"#{modal_id}"),
                    cls="d-flex gap-2 mt-2",
                ),
                cls="admin-field-grid admin-detail-block mb-3",
            )
        )

    return Card(
        Div(
            H3("Payment Accounts", cls="admin-subsection-title"),
            P("Saved accounts become available when drafting invoice links and PDF exports, so you can choose the receiving account per client workflow.", cls="admin-module-copy"),
            Div(*account_rows, cls="mb-4") if account_rows else "",
            *modals,
            Div(H3("Add / Edit Account", cls="admin-subsection-title"), _account_form(edit_account), cls="mt-4"),
            cls="admin-panel-stack",
        ),
        cls=[Fx.base, Fx.fade_in, "admin-surface-card h-100"],
        id="accounts-section",
    )


def settings_profile_page() -> tuple:
    profile = get_site_profile()
    profile_form = Form(
        Div(
            H3("Identity and website", cls="admin-subsection-title"),
            Row(
                Col(floating_field("Full Name", "full_name", profile.full_name, placeholder="Your public display name", required=True), span=12, md=7),
                Col(floating_field("Role", "role", profile.role, placeholder="Your professional role", required=True), span=12, md=5),
                cls="g-3",
            ),
            Row(
                Col(floating_field("Site Label", "site_name", profile.site_name, placeholder="Portfolio name", required=True), span=12, md=6),
                Col(floating_field("Site URL", "site_url", profile.site_url, input_type="url", placeholder="https://your-domain.com", required=True), span=12, md=6),
                cls="g-3 mt-1",
            ),
            cls="admin-form-section",
        ),
        Div(
            H3("Contact details", cls="admin-subsection-title"),
            Row(
                Col(floating_field("Email", "email", profile.email, input_type="email", placeholder="name@example.com"), span=12, md=6),
                Col(floating_field("Phone", "phone", profile.phone, placeholder="+234..."), span=12, md=6),
                cls="g-3",
            ),
            Row(
                Col(floating_field("WhatsApp", "whatsapp", profile.whatsapp, placeholder="+234..."), span=12, md=6),
                Col(floating_field("Location", "location", profile.location, placeholder="Ilorin, Nigeria"), span=12, md=6),
                cls="g-3 mt-1",
            ),
            cls="admin-form-section",
        ),
        Div(
            H3("Public links", cls="admin-subsection-title"),
            Row(
                Col(floating_field("GitHub URL", "github", profile.github, input_type="url", placeholder="https://github.com/..."), span=12, md=6),
                Col(floating_field("LinkedIn URL", "linkedin", profile.linkedin, input_type="url", placeholder="https://linkedin.com/in/..."), span=12, md=6),
                cls="g-3",
            ),
            cls="admin-form-section",
        ),
        Div(
            H3("Search preview", cls="admin-subsection-title"),
            textarea_field("SEO Title", "seo_title", profile.seo_title, rows=2, required=True, placeholder="Portfolio SEO title"),
            textarea_field("SEO Description", "seo_description", profile.seo_description, rows=4, required=True, placeholder="Short description used in search and sharing previews"),
            cls="admin-form-section",
        ),
        Div(
            loading_action_button("Save Profile", endpoint="/settings/save", target="#settings-save-result"),
            Span(
                f"Source: {profile.source.title()} | " + ("Live sync enabled" if service_role_is_configured() else "Add the service-role key to enable saving"),
                cls="admin-save-note",
            ),
            cls="admin-form-actions mt-3",
        ),
        Div(id="settings-save-result", cls="mt-3"),
        action="/settings/save",
        method="post",
        hx_post="/settings/save",
        hx_target="#settings-save-result",
        hx_swap="innerHTML",
        cls="admin-settings-form",
    )
    return (
        *SEO(
            title=f"{settings.app_name} | Profile Settings",
            description="Manage the public profile, contact information, links, and search metadata.",
            url=f"{settings.base_url}/settings",
        ),
        *page_frame(
            Div(
                settings_tab_bar("profile"),
                Card(
                    Div(
                        H2("Public profile", cls="admin-section-title mb-1"),
                        P("Update the information used across your portfolio, CV, contact surfaces, and search previews.", cls="admin-module-copy mb-4"),
                        profile_form,
                        cls="admin-panel-stack",
                    ),
                    cls="admin-surface-card",
                ),
            ),
            current="/settings",
            title="Profile Settings",
        ),
    )

def settings_access_page() -> tuple:
    access = get_admin_access_profile()

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
            H3("Admin Access Credentials", cls="admin-subsection-title"),
            P("Seeded credentials get you in the first time. After that, you can rotate the login email and password here without touching code.", cls="admin-module-copy"),
            Div(
                Div(Span("Current Login", cls="admin-field-label"), Strong(access.login_email)),
                Div(Span("Credential Source", cls="admin-field-label"), Strong(access.source.title())),
                cls="admin-field-grid admin-detail-block mb-4",
            ),
            access_form,
            cls="admin-panel-stack",
        ),
        cls=[Fx.base, Fx.fade_in, "admin-surface-card h-100"],
    )

    return (
        *SEO(
            title=f"{settings.app_name} | Admin Access",
            description="Manage login credentials for the Neo Admin dashboard.",
            url=f"{settings.base_url}/settings/access",
        ),
        *page_frame(
            SectionWrap(
                "Settings Workspace",
                Div(
                    settings_tab_bar("access"),
                    access_panel,
                ),
            ),
            current="/settings",
            title="Admin Access Credentials",
        ),
    )


def settings_accounts_page() -> tuple:
    return (
        *SEO(
            title=f"{settings.app_name} | Payment Accounts",
            description="Manage bank and payment accounts for deal invoices.",
            url=f"{settings.base_url}/settings/accounts",
        ),
        *page_frame(
            SectionWrap(
                "Settings Workspace",
                Div(
                    settings_tab_bar("accounts"),
                    _accounts_panel(),
                ),
            ),
            current="/settings",
            title="Payment Accounts",
        ),
    )


def settings_ai_page() -> tuple:
    return (
        *SEO(
            title=f"{settings.app_name} | AI Provider Settings",
            description="Manage AI providers for proposal and quote drafting.",
            url=f"{settings.base_url}/settings/ai",
        ),
        *page_frame(
            SectionWrap(
                "Settings Workspace",
                Div(
                    settings_tab_bar("ai"),
                    _ai_settings_card(),
                ),
            ),
            current="/settings",
            title="AI Provider Settings",
        ),
    )


def settings_health_page() -> tuple:
    github = get_github_stats()
    active_provider = get_active_provider()

    production_card = Card(
        Div(
            H3("Production Health Checks", cls="admin-subsection-title"),
            P("Quick visibility for the environment pieces that decide whether the admin can read, write, email, and generate shareable links.", cls="admin-module-copy"),
            Div(
                _health_row("Supabase Read", supabase_is_configured(), "Requires SUPABASE_URL and SUPABASE_ANON_KEY."),
                _health_row("Supabase Write", service_role_is_configured(), "Requires SUPABASE_SERVICE_ROLE_KEY for admin saves and uploads."),
                _health_row("Email Sending", settings.email_enabled, "Requires RESEND_API_KEY plus a valid sender domain when email actions are added."),
                _health_row("AI Drafting", bool(active_provider and active_provider.api_key), "Requires an AI provider with a valid API key configured in AI Provider Settings."),
                _health_row("Public Base URL", settings.base_url.startswith("https://"), "Use the deployed https admin URL so copied document links are production-safe."),
                _health_row("GitHub Pulse", bool(settings.github_access_token), "Optional, but improves GitHub stats reliability and rate limits."),
                cls="admin-settings-stack",
            ),
            cls="admin-panel-stack",
        ),
        cls=[Fx.base, Fx.fade_in, "admin-surface-card h-100"],
    )

    github_card = Card(
        Div(
            H3("GitHub Pulse", cls="admin-subsection-title"),
            P("Open-source proof from your GitHub profile. Stays graceful even when the API is unavailable.", cls="admin-module-copy"),
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
        cls=[Fx.base, Fx.fade_in, "admin-surface-card h-100 mt-4"],
    )

    return (
        *SEO(
            title=f"{settings.app_name} | Production Health",
            description="Production environment health checks and GitHub pulse.",
            url=f"{settings.base_url}/settings/health",
        ),
        *page_frame(
            SectionWrap(
                "Settings Workspace",
                Div(
                    settings_tab_bar("health"),
                    production_card,
                    github_card,
                ),
            ),
            current="/settings",
            title="Production Health & Pulse",
        ),
    )


def settings_workspace_page(tab: str = "profile") -> tuple:
    """Master dispatcher for settings subpages."""
    if tab == "access":
        return settings_access_page()
    elif tab == "accounts":
        return settings_accounts_page()
    elif tab == "ai":
        return settings_ai_page()
    elif tab == "health":
        return settings_health_page()
    return settings_profile_page()

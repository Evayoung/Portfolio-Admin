"""Settings routes — site profile, admin access, payment accounts, AI providers."""

from __future__ import annotations

from typing import Any

try:
    from ..infrastructure.ai_settings_repository import delete_ai_provider, get_ai_providers, save_ai_provider
    from ..infrastructure.auth_repository import save_admin_access
    from ..infrastructure.payment_account_repository import delete_payment_account, get_payment_account, save_payment_account
    from ..infrastructure.settings_repository import save_site_profile
    from ..presentation.pages.settings_admin import settings_save_status_fragment, settings_workspace_page
    from ..presentation.page_helpers import toast_fragment
except ImportError:
    from infrastructure.ai_settings_repository import delete_ai_provider, get_ai_providers, save_ai_provider
    from infrastructure.auth_repository import save_admin_access
    from infrastructure.payment_account_repository import delete_payment_account, get_payment_account, save_payment_account
    from infrastructure.settings_repository import save_site_profile
    from presentation.pages.settings_admin import settings_save_status_fragment, settings_workspace_page
    from presentation.page_helpers import toast_fragment


def _hx_refresh_response(message: str, title: str = "Saved") -> Any:
    """Return HX-Refresh with a toast notification."""
    from starlette.responses import Response
    return (
        Response("", status_code=200, headers={"HX-Refresh": "true"}),
        toast_fragment(title, message, variant="success"),
    )


def setup_settings_routes(app: Any) -> None:
    @app.get("/settings")
    def settings_page() -> Any:
        return settings_workspace_page()

    @app.post("/settings/save")
    def settings_save(
        site_name: str = "",
        site_url: str = "",
        full_name: str = "",
        role: str = "",
        email: str = "",
        phone: str = "",
        whatsapp: str = "",
        location: str = "",
        github: str = "",
        linkedin: str = "",
        seo_title: str = "",
        seo_description: str = "",
    ) -> Any:
        result = save_site_profile(
            site_name=site_name,
            site_url=site_url,
            full_name=full_name,
            role=role,
            email=email,
            phone=phone,
            whatsapp=whatsapp,
            location=location,
            github=github,
            linkedin=linkedin,
            seo_title=seo_title,
            seo_description=seo_description,
        )
        if result.success:
            return _hx_refresh_response("Site profile updated successfully.")
        title_text = "Save not completed"
        return settings_save_status_fragment(title_text, result.message, tone=result.tone)

    @app.post("/settings/access")
    def settings_access_save(
        login_email: str = "",
        password: str = "",
        confirm_password: str = "",
    ) -> Any:
        result = save_admin_access(login_email=login_email, password=password, confirm_password=confirm_password)
        if result.success:
            return _hx_refresh_response("Admin access updated successfully.")
        title_text = "Save not completed"
        return settings_save_status_fragment(title_text, result.message, tone=result.tone)

    @app.post("/settings/accounts")
    def settings_account_save(
        label: str = "",
        bank_name: str = "",
        account_name: str = "",
        account_number: str = "",
        note: str = "",
        is_default: str = "",
    ) -> Any:
        from ..presentation.pages.settings_admin import _accounts_panel

        result = save_payment_account(
            label=label,
            bank_name=bank_name,
            account_name=account_name,
            account_number=account_number,
            note=note,
            is_default=bool(is_default),
        )
        if result.success:
            return (_accounts_panel(), toast_fragment("Account saved", result.message))
        return (settings_save_status_fragment("Save not completed", result.message, tone=result.tone),)

    @app.post("/settings/accounts/edit")
    def settings_account_edit(id: str = "") -> Any:
        from ..presentation.pages.settings_admin import _accounts_panel

        account = get_payment_account(id) if id else None
        return _accounts_panel(edit_account=account)

    @app.post("/settings/accounts/delete")
    def settings_account_delete(id: str = "") -> Any:
        from ..presentation.pages.settings_admin import _accounts_panel

        result = delete_payment_account(id)
        if result.success:
            return (_accounts_panel(), toast_fragment("Account deleted", result.message))
        return (settings_save_status_fragment("Delete not completed", result.message, tone=result.tone),)

    @app.post("/settings/ai-save")
    def settings_ai_save(
        config_id: str = "new",
        label: str = "",
        provider_type: str = "groq",
        base_url: str = "",
        model: str = "",
        api_key: str = "",
        set_default: str = "",
    ) -> Any:
        from ..infrastructure.ai_settings_repository import PROVIDER_PRESETS
        from ..presentation.pages.settings_admin import _ai_settings_card

        resolved_url = base_url.strip() or dict(PROVIDER_PRESETS).get(provider_type, ("", ""))[1]
        result = save_ai_provider(
            config_id=config_id,
            label=label,
            provider_type=provider_type,
            base_url=resolved_url,
            model=model,
            api_key=api_key,
            set_default=bool(set_default),
        )
        if result.success:
            return (_ai_settings_card(), toast_fragment("AI provider saved", result.message))
        return (_ai_settings_card(), settings_save_status_fragment("Save not completed", result.message, tone=result.tone))

    @app.post("/settings/ai-set-default")
    def settings_ai_set_default(id: str = "") -> Any:
        from ..presentation.pages.settings_admin import _ai_settings_card

        if id:
            providers = get_ai_providers()
            for p in providers:
                if p.config_id == id:
                    save_ai_provider(config_id=id, label=p.label, provider_type=p.provider_type, base_url=p.base_url, model=p.model, api_key="***unchanged***" if p.api_key else "", set_default=True)
                    break
        return _ai_settings_card()

    @app.post("/settings/ai-delete")
    def settings_ai_delete(id: str = "") -> Any:
        from ..presentation.pages.settings_admin import _ai_settings_card

        if id:
            delete_ai_provider(id)
        return _ai_settings_card()

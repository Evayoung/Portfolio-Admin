"""Settings routes — site profile, admin access, payment accounts."""

from __future__ import annotations

from typing import Any

try:
    from ..infrastructure.auth_repository import save_admin_access
    from ..infrastructure.payment_account_repository import save_payment_account
    from ..infrastructure.settings_repository import save_site_profile
    from ..presentation.pages.settings_admin import settings_save_status_fragment, settings_workspace_page
except ImportError:
    from infrastructure.auth_repository import save_admin_access
    from infrastructure.payment_account_repository import save_payment_account
    from infrastructure.settings_repository import save_site_profile
    from presentation.pages.settings_admin import settings_save_status_fragment, settings_workspace_page


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
        title_text = "Settings saved" if result.success else "Save not completed"
        return settings_save_status_fragment(title_text, result.message, tone=result.tone)

    @app.post("/settings/access")
    def settings_access_save(
        login_email: str = "",
        password: str = "",
        confirm_password: str = "",
    ) -> Any:
        result = save_admin_access(login_email=login_email, password=password, confirm_password=confirm_password)
        title_text = "Admin access saved" if result.success else "Save not completed"
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
        result = save_payment_account(
            label=label,
            bank_name=bank_name,
            account_name=account_name,
            account_number=account_number,
            note=note,
            is_default=bool(is_default),
        )
        title_text = "Payment account saved" if result.success else "Save not completed"
        return settings_save_status_fragment(title_text, result.message, tone=result.tone)

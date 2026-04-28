"""Public-facing client document viewer for proposals, quotes, and invoices."""

from __future__ import annotations

from datetime import date, datetime

from fasthtml.common import (
    A, Button, Div, Form, H1, H2, H3, Input, P, Script, Span, Strong,
    Table, Tbody, Td, Textarea, Tfoot, Th, Thead, Tr,
)
from faststrap import Icon, SEO

from app.config import settings
from app.infrastructure.deal_repository import get_document_by_token, list_document_responses
from app.infrastructure.payment_account_repository import get_default_payment_account, get_payment_account
from app.infrastructure.settings_repository import get_site_profile


# ── Helpers ───────────────────────────────────────────────────────────────────

def _money(value: int) -> str:
    return f"₦{value:,.0f}"


def _lines(raw: str) -> list[str]:
    return [line.strip() for line in (raw or "").splitlines() if line.strip()]


def _line_items(raw: str) -> list[tuple[str, str, str, str]]:
    rows: list[tuple[str, str, str, str]] = []
    for line in _lines(raw):
        parts = [p.strip() for p in line.split("|")]
        title  = parts[0] if len(parts) > 0 else ""
        detail = parts[1] if len(parts) > 1 else ""
        qty    = parts[2] if len(parts) > 2 else "1"
        amount = parts[3] if len(parts) > 3 else "0"
        if title:
            rows.append((title, detail, qty, amount))
    return rows


def _is_expired(valid_until: str | None) -> bool:
    if not valid_until:
        return False
    try:
        exp = datetime.strptime(valid_until, "%Y-%m-%d").date()
        return exp < date.today()
    except ValueError:
        return False


def _doc_type_label(kind: str) -> str:
    return {"proposal": "Technical Proposal", "quote": "Project Quotation", "invoice": "Payment Invoice"}.get(kind, "Client Document")


def _action_copy(kind: str) -> str:
    return {
        "proposal": "Review the scope and delivery plan, then share your decision or questions below.",
        "quote": "Review this fixed-scope quotation and let me know if you would like to proceed or adjust.",
        "invoice": "Use the payment account below to complete the transfer, then mark it as paid so I can confirm.",
    }.get(kind, "Review this document and respond below.")


def _response_action_cls(action: str) -> str:
    return {
        "accepted": "accepted",
        "rejected": "rejected",
        "commented": "commented",
        "payment_submitted": "payment_submitted",
    }.get(action, "commented")


# ── Logo mark (light doc variant) ────────────────────────────────────────────

def _doc_logo_mark(profile) -> Span:
    name = (getattr(profile, "site_name", "") or "").replace(" Portfolio", "").strip()
    if not name:
        name = getattr(profile, "full_name", "") or "NA"
    words = [w for w in name.replace("-", " ").split() if w]
    if len(words) >= 2:
        f, s = words[0][0].upper(), words[1][0].upper()
    elif words:
        token = words[0][:2].upper()
        f, s = token[0], token[1] if len(token) > 1 else token[0]
    else:
        f, s = "N", "A"
    return Span(
        Span(f, cls="doc-logo-letter"),
        Span(s, cls="doc-logo-letter doc-logo-letter-alt"),
        cls="doc-logo",
    )


# ── Brand bar ─────────────────────────────────────────────────────────────────

def _brand_bar(profile, kind: str) -> Div:
    return Div(
        Div(
            Div(
                _doc_logo_mark(profile),
                Div(
                    Span(
                        (getattr(profile, "site_name", "") or "").replace(" Portfolio", "").strip()
                        or getattr(profile, "full_name", "") or settings.owner_name,
                        cls="doc-brand-name",
                    ),
                    Span(getattr(profile, "role", "") or "Full-Stack Developer", cls="doc-brand-role"),
                    cls="doc-brand-text",
                ),
                cls="doc-brand-identity",
            ),
            Span(_doc_type_label(kind), cls="doc-type-badge"),
            cls="doc-brand-bar-inner",
        ),
        cls="doc-brand-bar",
    )


# ── Meta strip ────────────────────────────────────────────────────────────────

def _meta_cell(label: str, value: str) -> Div:
    return Div(
        Span(label, cls="doc-meta-label"),
        Span(value or "—", cls="doc-meta-value"),
        cls="doc-meta-cell",
    )


def _meta_strip(deal, document, profile) -> Div:
    issued = datetime.now().strftime("%d %b %Y")
    return Div(
        _meta_cell("Prepared For", deal.company or deal.client_name),
        _meta_cell("Prepared By", getattr(profile, "full_name", "") or settings.owner_name),
        _meta_cell("Document No.", document.document_number),
        _meta_cell(
            "Valid Until" if document.kind != "invoice" else "Due Date",
            document.valid_until if document.kind != "invoice" else (document.due_date or "On receipt"),
        ),
        cls="doc-meta-strip",
    )


# ── Section card ──────────────────────────────────────────────────────────────

def _section_card(title: str, lines: list[str], *, fallback: str = "") -> Div:
    content = lines or ([fallback] if fallback else [])
    if not content:
        return ""
    return Div(
        Div(
            Div(cls="doc-section-accent"),
            H2(title, cls="doc-section-title"),
            cls="doc-section-head",
        ),
        Div(
            *[P(line, cls="doc-body-text") for line in content],
            cls="doc-card-body",
        ),
        cls="doc-card",
    )


# ── Line items table ──────────────────────────────────────────────────────────

def _line_items_table(deal, document) -> Div:
    items = _line_items(deal.line_items_text)
    total = document.total_amount

    rows = []
    for title, detail, qty, amount in items:
        try:
            amt_int = int(float(amount or "0"))
        except ValueError:
            amt_int = 0
        rows.append(
            Tr(
                Td(
                    Div(title),
                    Div(detail, cls="doc-table-detail") if detail else "",
                ),
                Td(qty),
                Td(_money(amt_int)),
            )
        )

    if not rows:
        rows.append(
            Tr(
                Td(Div(deal.project_title), Div(deal.summary, cls="doc-table-detail")),
                Td("1"),
                Td(_money(total)),
            )
        )

    return Div(
        Div(
            Div(cls="doc-section-accent"),
            H2("Investment", cls="doc-section-title"),
            cls="doc-section-head",
        ),
        Div(
            Table(
                Thead(
                    Tr(
                        Th("Component / Service"),
                        Th("Qty"),
                        Th("Amount"),
                    )
                ),
                Tbody(*rows),
                Tfoot(
                    Tr(
                        Td(Strong("Total"), colspan="2"),
                        Td(Strong(_money(total))),
                    )
                ),
                cls="doc-table",
            ),
            cls="doc-table-wrap",
        ),
        cls="doc-card",
        style="overflow:hidden;",
    )


# ── Payment account panel ─────────────────────────────────────────────────────

def _payment_account_panel(account) -> Div:
    return Div(
        Div(
            Div(cls="doc-section-accent"),
            H2("Payment Account", cls="doc-section-title"),
            cls="doc-section-head",
        ),
        Div(
            Div(
                Div(
                    Span("Account Label", cls="doc-account-label"),
                    Span(account.label, cls="doc-account-value"),
                    cls="doc-account-field",
                ),
                Div(
                    Span("Bank", cls="doc-account-label"),
                    Span(account.bank_name, cls="doc-account-value"),
                    cls="doc-account-field",
                ),
                Div(
                    Span("Account Name", cls="doc-account-label"),
                    Span(account.account_name, cls="doc-account-value"),
                    cls="doc-account-field",
                ),
                Div(
                    Span("Account Number", cls="doc-account-label"),
                    Span(account.account_number, cls="doc-account-value", id="doc-account-number"),
                    cls="doc-account-field",
                ),
                cls="doc-account-grid",
            ),
            P(account.note, cls="doc-account-note") if account.note else "",
            Button(
                Icon("clipboard", cls="me-2"),
                "Copy Account Number",
                type="button",
                cls="doc-btn-primary mt-4",
                style="font-size:0.88rem; min-height:2.6rem; padding:0.6rem 1.1rem;",
                data_copy_target=account.account_number,
                data_copy_label="Copy Account Number",
            ),
            cls="doc-card-body",
        ),
        cls="doc-card",
    )


# ── Expiry banner ─────────────────────────────────────────────────────────────

def _expiry_banner(valid_until: str) -> Div:
    return Div(
        Icon("exclamation-triangle-fill", cls="doc-expiry-icon"),
        P(
            f"This document expired on {valid_until}. "
            "You can still submit a comment, but acceptance is no longer available. "
            "Please contact me to request a refreshed document.",
            cls="doc-expiry-copy",
        ),
        cls="doc-expiry-banner",
    )


# ── Response zone ─────────────────────────────────────────────────────────────

def _response_zone(document, token: str, message: str = "", tone: str = "info", *, expired: bool = False) -> Div:
    is_proposal_or_quote = document.kind in {"proposal", "quote"}
    is_invoice = document.kind == "invoice"

    accept_btn = (
        Button(
            Icon("check-circle-fill", cls="me-2"),
            "Accept" if document.kind == "proposal" else "Confirm Quote",
            type="submit",
            name="action",
            value="accepted",
            cls="doc-btn-primary",
            disabled=expired,
            style="opacity:0.45; cursor:not-allowed;" if expired else "",
        )
        if is_proposal_or_quote else ""
    )

    reject_btn = (
        Button(
            Icon("x-circle", cls="me-2"),
            "Decline",
            type="submit",
            name="action",
            value="rejected",
            cls="doc-btn-ghost",
            disabled=expired,
            style="opacity:0.45; cursor:not-allowed;" if expired else "",
        )
        if is_proposal_or_quote else ""
    )

    pay_btn = (
        Button(
            Icon("check2-circle", cls="me-2"),
            "I Have Paid",
            type="submit",
            name="action",
            value="payment_submitted",
            cls="doc-btn-primary doc-btn-pay",
        )
        if is_invoice else ""
    )

    comment_btn = Button(
        Icon("chat-text", cls="me-2"),
        "Send Comment",
        type="submit",
        name="action",
        value="commented",
        cls="doc-btn-ghost",
    )

    feedback = (
        Div(message, cls=f"doc-response-feedback {tone}")
        if message else ""
    )

    return Form(
        Div(
            H3("Your Response", cls="doc-response-title"),
            P(
                "Acceptance has been disabled — this document has expired." if expired
                else "Your response is sent directly to me. I'll follow up within 24 hours.",
                cls="doc-response-copy",
            ),
            cls="doc-response-head",
        ),
        Div(
            feedback,
            Div(
                Input(
                    type="text",
                    name="responder_name",
                    placeholder="Your name",
                    cls="doc-response-input",
                    required=True,
                ),
                Input(
                    type="email",
                    name="responder_email",
                    placeholder="Your email address",
                    cls="doc-response-input",
                    required=True,
                ),
                style="display:grid; grid-template-columns:1fr 1fr; gap:0.75rem;",
                cls="doc-name-email-row",
            ),
            Textarea(
                name="comment",
                placeholder="Add your questions, approval note, or payment confirmation here…",
                rows=5,
                cls="doc-response-input doc-response-textarea",
            ),
            Div(
                accept_btn,
                pay_btn,
                reject_btn,
                comment_btn,
                cls="doc-cta-row",
            ),
            cls="doc-response-body",
        ),
        action=f"/documents/{token}/respond",
        method="post",
        cls="doc-response-zone",
    )


# ── Response history ──────────────────────────────────────────────────────────

def _response_history(responses) -> Div:
    if not responses:
        return ""
    items = [
        Div(
            Span(
                r.action.replace("_", " ").title(),
                cls=f"doc-history-action {_response_action_cls(r.action)}",
            ),
            P(r.comment or "No comment supplied.", cls="doc-history-comment"),
            Span(
                f"{r.responder_name or 'Client'}  ·  {r.created_at}",
                cls="doc-history-meta",
            ),
            cls="doc-history-item",
        )
        for r in responses
    ]
    return Div(
        Div(
            Div(cls="doc-section-accent"),
            H2("Response History", cls="doc-section-title"),
            cls="doc-section-head",
        ),
        Div(
            Div(*items, cls="doc-history-list"),
            cls="doc-card-body",
        ),
        cls="doc-card",
    )


# ── Footer strip ──────────────────────────────────────────────────────────────

def _doc_footer(profile, deal, document) -> Div:
    email = getattr(profile, "email", "") or ""
    phone = getattr(profile, "phone", "") or ""
    name  = getattr(profile, "full_name", "") or settings.owner_name
    contact_parts = [name]
    if email:
        contact_parts.append(email)
    if phone:
        contact_parts.append(phone)

    return Div(
        P(
            *[
                Span(part + ("  ·  " if i < len(contact_parts) - 1 else ""))
                if i < len(contact_parts) - 1
                else Span(part)
                for i, part in enumerate(contact_parts)
            ],
            cls="doc-footer-contact",
        ),
        A(
            Icon("download", cls="me-2"),
            "Download PDF",
            href=f"/deals/{deal.deal_id}/documents/{document.kind}/pdf",
            cls="doc-download-btn",
        ),
        cls="doc-footer",
    )


# ── Clipboard JS ──────────────────────────────────────────────────────────────

_COPY_SCRIPT = Script("""
(function(){
  document.addEventListener('click', function(e){
    var btn = e.target.closest('[data-copy-target]');
    if(!btn) return;
    var text = btn.dataset.copyTarget;
    var label = btn.dataset.copyLabel || btn.textContent.trim();
    navigator.clipboard.writeText(text).then(function(){
      btn.textContent = 'Copied!';
      setTimeout(function(){ btn.textContent = label; }, 1800);
    }).catch(function(){
      btn.textContent = 'Copy failed';
      setTimeout(function(){ btn.textContent = label; }, 2000);
    });
  });
})();
""")

# Mobile name/email row responsive fix
_NAME_EMAIL_SCRIPT = Script("""
(function(){
  function fixNameEmailRow(){
    var rows = document.querySelectorAll('.doc-name-email-row');
    rows.forEach(function(row){
      if(window.innerWidth < 600){
        row.style.gridTemplateColumns = '1fr';
      } else {
        row.style.gridTemplateColumns = '1fr 1fr';
      }
    });
  }
  fixNameEmailRow();
  window.addEventListener('resize', fixNameEmailRow);
})();
""")


# ── Main page function ────────────────────────────────────────────────────────

def document_portal_page(*, token: str, message: str = "", tone: str = "info") -> tuple:
    deal, document = get_document_by_token(token)
    profile = get_site_profile()

    # ── 404 state ────────────────────────────────────────────────────────────
    if not deal or not document:
        return (
            *SEO(
                title="Document Not Found",
                description="The requested client document could not be found.",
                url=f"{settings.base_url}/documents/{token}",
            ),
            _doc_stylesheet_link(),
            Div(
                Div(
                    Div(_doc_logo_mark(profile), style="margin-bottom:1.25rem;"),
                    H1("Document not found", cls="doc-not-found-title"),
                    P(
                        "This link may have expired or the document is no longer available. "
                        "Please contact me directly if you need a fresh copy.",
                        cls="doc-not-found-copy",
                    ),
                    cls="doc-not-found-card",
                ),
                cls="doc-not-found doc-shell",
            ),
            _COPY_SCRIPT,
        )

    # ── Data ─────────────────────────────────────────────────────────────────
    account = (
        get_payment_account(document.payment_account_id)
        if document.payment_account_id
        else get_default_payment_account()
    )
    responses = list_document_responses(document.document_id)
    expired = _is_expired(document.valid_until)

    # ── Section cards ─────────────────────────────────────────────────────────
    background_card = _section_card(
        "Background & Objective",
        _lines(deal.background_text or deal.summary),
        fallback=deal.summary,
    )
    scope_card = _section_card(
        "Scope of Work",
        _lines(deal.scope_notes),
        fallback=deal.summary,
    )
    options_card = _section_card("Options & Delivery Path", _lines(deal.option_notes_text))
    timeline_card = _section_card("Timeline", _lines(deal.timeline_text))
    terms_card = _section_card("Payment Terms", _lines(deal.payment_terms))
    exclusions_card = _section_card("What Is Not Included", _lines(deal.exclusions_text))
    closing_card = _section_card("Closing Note", _lines(deal.closing_note))

    investment_table = _line_items_table(deal, document)
    account_panel = _payment_account_panel(account) if (document.kind == "invoice" and account) else ""
    expiry_banner = _expiry_banner(document.valid_until) if expired else ""
    response_zone = _response_zone(document, token, message, tone, expired=expired)
    history = _response_history(responses)

    return (
        *SEO(
            title=f"{document.title} — {_doc_type_label(document.kind)}",
            description=deal.summary,
            url=f"{settings.base_url}/documents/{token}",
        ),
        _doc_stylesheet_link(),
        Div(
            _brand_bar(profile, document.kind),
            Div(
                # Hero
                Div(
                    Span(_doc_type_label(document.kind), cls="doc-kicker"),
                    H1(document.title, cls="doc-title"),
                    P(deal.project_title, cls="doc-subtitle"),
                    Div(
                        Span(
                            document.status.replace("_", " ").title(),
                            cls=f"doc-status-pill {document.status}",
                        ),
                        Span(document.document_number, cls="doc-status-pill draft"),
                        cls="doc-status-row",
                    ),
                    P(_action_copy(document.kind), cls="doc-action-copy"),
                    cls="doc-hero",
                ),
                # Meta strip
                _meta_strip(deal, document, profile),
                # Expiry warning
                expiry_banner,
                # Content sections
                background_card,
                scope_card,
                options_card,
                timeline_card,
                terms_card,
                investment_table,
                account_panel,
                exclusions_card,
                closing_card,
                # Response
                response_zone,
                history,
                # Footer
                _doc_footer(profile, deal, document),
                cls="doc-page",
            ),
            cls="doc-shell",
        ),
        _COPY_SCRIPT,
        _NAME_EMAIL_SCRIPT,
    )


def _doc_stylesheet_link():
    """Return a Link tag injecting doc-portal.css — separate from admin.css."""
    from fasthtml.common import Link
    return Link(rel="stylesheet", href="/assets/doc-portal.css")

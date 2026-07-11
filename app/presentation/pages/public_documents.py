"""Public-facing client document viewer for proposals, quotes, and invoices."""

from __future__ import annotations

import json
from datetime import date, datetime

from fasthtml.common import (
    A, Button, Div, Form, H1, H2, H3, Input, Label, P, Script, Span, Strong,
    Table, Tbody, Td, Textarea, Tfoot, Th, Thead, Tr,
)
from faststrap import Col, Icon, Markdown, Modal, Row, SEO
from faststrap.components.feedback.modern_toast import ModernToastStack

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
    # Use only first initial for a cleaner, more compact brand mark
    f = (words[0][0].upper()) if words else "N"
    return Span(
        Span(f, cls="doc-logo-letter"),
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
                        ((getattr(profile, "site_name", "") or "").replace(" Portfolio", "").strip().split(None, 1)[0]
                         if (getattr(profile, "site_name", "") or "").replace(" Portfolio", "").strip()
                         else (getattr(profile, "full_name", "") or settings.owner_name).split(None, 1)[0]),
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


def _dynamic_sections(sections_json: str) -> list[Div]:
    """Render sections from JSON using Faststrap Markdown component."""
    # Section titles that belong in PDF/print only — not on the interactive web portal
    _PDF_ONLY_TITLES = {"acceptance", "your response", "signature", "sign off", "sign-off"}

    try:
        sections = json.loads(sections_json) if sections_json else []
    except (json.JSONDecodeError, TypeError):
        sections = []
    if not sections:
        return []
    cards = []
    for section in sorted(sections, key=lambda s: s.get("order", 0) if isinstance(s, dict) else 0):
        if not isinstance(section, dict):
            continue
        title = section.get("title", "")
        content = section.get("content", "")
        if not title and not content:
            continue
        # Skip sections that are only meaningful in a printed/PDF context
        if title.strip().lower() in _PDF_ONLY_TITLES:
            continue
        cards.append(
            Div(
                Div(
                    Div(cls="doc-section-accent"),
                    H2(title, cls="doc-section-title"),
                    cls="doc-section-head",
                ),
                Div(
                    Markdown(content),
                    cls="doc-card-body",
                ),
                cls="doc-card",
            )
        )
    return cards


# ── Line items table ──────────────────────────────────────────────────────────

def _line_items_table(deal, document) -> Div:
    import re
    raw_items = _line_items(deal.line_items_text)
    total = document.total_amount

    # Group line items by package prefix
    groups = {}
    for title, detail, qty, amount in raw_items:
        group_key = None
        for prefix in ["Package", "Option"]:
            match = re.match(r"^(" + prefix + r"\s+\w+)\s*[-:]\s*(.*)$", title, re.IGNORECASE)
            if match:
                group_key = match.group(1).strip()
                title = match.group(2).strip()
                break
        if not group_key:
            for prefix in ["Package", "Option"]:
                match = re.match(r"^(" + prefix + r"\s+\w+)\s+(.*)$", title, re.IGNORECASE)
                if match:
                    group_key = match.group(1).strip()
                    title = match.group(2).strip()
                    break
        if not group_key:
            group_key = "Standard"
        groups.setdefault(group_key, []).append((title, detail, qty, amount))

    # If there are no items, show default deal info
    if not raw_items:
        groups["Standard"] = [(deal.project_title, deal.summary, "1", str(total))]

    # If multiple packages/options exist, render them as separate options tables
    if len(groups) > 1 or "Standard" not in groups:
        package_cards = []
        for pkg_name, pkg_items in groups.items():
            rows = []
            pkg_total = 0
            for title, detail, qty, amount in pkg_items:
                try:
                    amt_int = int(float(amount or "0"))
                except ValueError:
                    amt_int = 0
                pkg_total += amt_int * int(qty or "1")
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
            package_cards.append(
                Div(
                    H3(pkg_name, cls="doc-table-group-header mt-3 mb-2", style="font-size: 1rem; font-weight: 700; color: var(--navy);"),
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
                                    Td(Strong("Option Total"), colspan="2"),
                                    Td(Strong(_money(pkg_total))),
                                )
                            ),
                            cls="doc-table mb-3",
                        ),
                        cls="doc-table-wrap",
                    ),
                    cls="doc-investment-option",
                )
            )
        return Div(
            Div(
                Div(cls="doc-section-accent"),
                H2("Investment Options", cls="doc-section-title"),
                cls="doc-section-head",
            ),
            Div(*package_cards, style="padding: 0 1.25rem 1.25rem 1.25rem;"),
            cls="doc-card",
            style="overflow:hidden;",
        )

    # Standard single total layout
    rows = []
    for title, detail, qty, amount in groups.get("Standard", []):
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


# ── Package selector (shown in response zone when there are multiple options) ──

def _extract_package_names(line_items_text: str) -> list[str]:
    """Extract distinct Package/Option group names from line items text."""
    import re
    names = []
    seen = set()
    for line in _lines(line_items_text or ""):
        parts = [p.strip() for p in line.split("|")]
        title = parts[0] if parts else ""
        group_key = None
        for prefix in ["Package", "Option"]:
            match = re.match(r"^(" + prefix + r"\s+\w+)\s*[-:\s]", title, re.IGNORECASE)
            if match:
                group_key = match.group(1).strip()
                break
        if group_key and group_key not in seen:
            seen.add(group_key)
            names.append(group_key)
    return names


# ── Confirmation modals ──────────────────────────────────────────────────────

def _accept_confirmation_modal(document, token: str) -> Modal:
    """Modal that confirms before accepting a proposal or quote."""
    action_label = "Accept" if document.kind == "proposal" else "Confirm Quote"
    return Modal(
        P(
            f"You are about to {action_label.lower()} this {document.kind}. "
            "This action will be recorded and cannot be undone from this portal.",
            cls="mb-3 doc-modal-text",
        ),
        P("Add a note (optional):", cls="fw-semibold mb-2 doc-modal-label"),
        Textarea(
            name="confirm_comment",
            id="accept-confirm-comment",
            placeholder="e.g. Approved, looks good, proceed...",
            rows=3,
            cls="form-control doc-modal-input",
        ),
        footer=Div(
            Button("Cancel", type="button", cls="doc-btn-ghost doc-btn-modal-ghost", data_bs_dismiss="modal"),
            Button(
                Icon("check-circle-fill", cls="me-2"),
                f"Confirm {action_label}",
                type="button",
                cls="doc-btn-primary doc-btn-modal-confirm",
                id="accept-confirm-btn",
            ),
            cls="d-flex gap-2 justify-content-end",
        ),
        modal_id="acceptConfirmModal",
        title=f"{action_label}?",
        centered=True,
        size="sm",
        cls="doc-modal",
    )


def _decline_confirmation_modal(document, token: str) -> Modal:
    """Modal that requires a reason before declining a proposal or quote."""
    return Modal(
        P(
            "Please share a brief reason for declining. "
            "This helps me improve future proposals.",
            cls="mb-3 doc-modal-text",
        ),
        P("Reason for declining (required):", cls="fw-semibold mb-2 doc-modal-label"),
        Textarea(
            name="confirm_comment",
            id="decline-confirm-comment",
            placeholder="e.g. Budget is too high, timeline doesn't work, chose another vendor...",
            rows=4,
            cls="form-control doc-modal-input",
            required=True,
        ),
        Div(
            Icon("exclamation-circle", cls="me-2 text-warning"),
            Span("A reason is required to complete this action.", cls="small doc-modal-hint"),
            cls="mt-2",
        ),
        footer=Div(
            Button("Cancel", type="button", cls="doc-btn-ghost doc-btn-modal-ghost", data_bs_dismiss="modal"),
            Button(
                Icon("x-circle", cls="me-2"),
                "Confirm Decline",
                type="button",
                cls="doc-btn-danger doc-btn-modal-danger",
                id="decline-confirm-btn",
            ),
            cls="d-flex gap-2 justify-content-end",
        ),
        modal_id="declineConfirmModal",
        title="Decline Proposal?",
        centered=True,
        size="sm",
        cls="doc-modal",
    )


def _payment_confirmation_modal(document, token: str, account=None) -> Modal:
    """Modal that confirms payment submission."""
    account_info = ""
    if account:
        account_info = Div(
            Div(
                Span("Bank", cls="doc-modal-label"),
                Span(f"{account.bank_name} — {account.account_number}", cls="doc-modal-value"),
                cls="mb-2",
            ),
            cls="doc-modal-account p-3 rounded mb-3",
        )
    return Modal(
        P(
            "Confirm that you have completed the payment. "
            "The admin will verify and update the invoice status.",
            cls="mb-3 doc-modal-text",
        ),
        account_info,
        P("Add a note (optional):", cls="fw-semibold mb-2 doc-modal-label"),
        Textarea(
            name="confirm_comment",
            id="payment-confirm-comment",
            placeholder="e.g. Paid via bank transfer, ref: ABC123...",
            rows=3,
            cls="form-control doc-modal-input",
        ),
        footer=Div(
            Button("Cancel", type="button", cls="doc-btn-ghost doc-btn-modal-ghost", data_bs_dismiss="modal"),
            Button(
                Icon("check2-circle", cls="me-2"),
                "Confirm Payment Sent",
                type="button",
                cls="doc-btn-primary doc-btn-modal-confirm",
                id="payment-confirm-btn",
            ),
            cls="d-flex gap-2 justify-content-end",
        ),
        modal_id="paymentConfirmModal",
        title="Confirm Payment?",
        centered=True,
        size="sm",
        cls="doc-modal",
    )


# ── Response zone ─────────────────────────────────────────────────────────────

def _response_zone(document, token: str, message: str = "", tone: str = "info", *, expired: bool = False, deal=None) -> Div:
    is_proposal_or_quote = document.kind in {"proposal", "quote"}
    is_invoice = document.kind == "invoice"

    # Detect multiple packages so we can show a selector
    package_names = _extract_package_names(getattr(deal, "line_items_text", "") or "") if deal else []
    has_packages = len(package_names) > 1

    package_selector = ""
    if has_packages and is_proposal_or_quote and not expired:
        radio_items = [
            Label(
                Input(
                    type="radio",
                    id=f"pkg_{i}",
                    name="selected_package",
                    value=name,
                    cls="doc-pkg-radio",
                ),
                Span(name, cls="doc-pkg-label"),
                cls="doc-pkg-option",
            )
            for i, name in enumerate(package_names)
        ]
        package_selector = Div(
            Div(
                Icon("layers", cls="me-2 doc-pkg-icon"),
                Span("Which package are you interested in?", cls="doc-pkg-question"),
                cls="doc-pkg-head",
            ),
            Div(*radio_items, cls="doc-pkg-list"),
            cls="doc-pkg-selector",
        )

    is_open = document.status in {"sent", "draft"}
    is_decision_disabled = expired or not is_open

    status_msg = "Your response is sent directly to me. I'll follow up within 24 hours."
    if expired:
        status_msg = "Acceptance has been disabled — this document has expired."
    elif document.status == "accepted":
        status_msg = "This document has been accepted. You can still send a comment below."
    elif document.status == "rejected":
        status_msg = "This document has been declined. You can still send a comment below."

    # Accept button — JS validates package before opening modal
    accept_btn = (
        Button(
            Icon("check-circle-fill", cls="me-2"),
            "Accept" if document.kind == "proposal" else "Confirm Quote",
            type="button",
            cls="doc-btn-primary",
            id="doc-open-accept-modal",
            disabled=is_decision_disabled,
            style="opacity:0.45; cursor:not-allowed;" if is_decision_disabled else "",
        )
        if is_proposal_or_quote else ""
    )

    # Decline button — JS validates package before opening modal
    reject_btn = (
        Button(
            Icon("x-circle", cls="me-2"),
            "Decline",
            type="button",
            cls="doc-btn-ghost",
            id="doc-open-decline-modal",
            disabled=is_decision_disabled,
            style="opacity:0.45; cursor:not-allowed;" if is_decision_disabled else "",
        )
        if is_proposal_or_quote else ""
    )

    # Payment button — opens confirmation modal (no package validation needed)
    pay_btn = (
        Button(
            Icon("check2-circle", cls="me-2"),
            "I Have Paid",
            type="button",
            cls="doc-btn-primary doc-btn-pay",
            data_bs_toggle="modal",
            data_bs_target="#paymentConfirmModal",
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

    # Hidden fields for modal-driven submissions
    hidden_action = Input(type="hidden", name="action", id="hidden-action-field", value="")
    hidden_comment = Input(type="hidden", name="comment", id="hidden-comment-field", value="")

    js_script = Script("""
        document.addEventListener('DOMContentLoaded', function() {
            var form = document.querySelector('.doc-response-zone');
            if (!form) return;

            // ── Package validation ──
            function validatePackageSelected() {
                var radios = document.getElementsByName('selected_package');
                if (radios.length === 0) return true;
                for (var i = 0; i < radios.length; i++) { if (radios[i].checked) return true; }
                var selector = document.querySelector('.doc-pkg-selector');
                if (selector) {
                    selector.classList.add('doc-pkg-error-state');
                    var errorMsg = selector.querySelector('.doc-pkg-error');
                    if (!errorMsg) {
                        errorMsg = document.createElement('div');
                        errorMsg.className = 'doc-pkg-error';
                        errorMsg.innerText = 'Please select a package option before continuing.';
                        selector.appendChild(errorMsg);
                    }
                }
                return false;
            }

            document.querySelectorAll('.doc-pkg-radio').forEach(function(radio) {
                radio.addEventListener('change', function() {
                    var selector = document.querySelector('.doc-pkg-selector');
                    if (selector) {
                        selector.classList.remove('doc-pkg-error-state');
                        var errorMsg = selector.querySelector('.doc-pkg-error');
                        if (errorMsg) errorMsg.remove();
                    }
                });
            });

            // ── Helper: show loading state on button ──
            function btnLoading(btn) {
                btn.setAttribute('data-original-html', btn.innerHTML);
                btn.disabled = true;
                btn.style.pointerEvents = 'none';
                btn.innerHTML = '<span class="doc-btn-spinner-icon"></span> Processing...';
            }

            // ── Helper: submit form via hidden submit button (triggers HTMX natively) ──
            function submitFormAction(action, comment) {
                document.getElementById('hidden-action-field').value = action;
                document.getElementById('hidden-comment-field').value = comment || '';
                // Use the hidden submit button to trigger HTMX form handling
                var submitter = document.getElementById('doc-hidden-submit');
                if (submitter) { submitter.click(); return; }
                // Fallback: native form submit
                form.submit();
            }

            // ── Helper: close any Bootstrap modal by ID ──
            function closeModal(modalId) {
                var el = document.getElementById(modalId);
                if (!el) return;
                var instance = bootstrap.Modal.getInstance(el);
                if (instance) { instance.hide(); return; }
                // Fallback: force close
                el.classList.remove('show');
                el.style.display = 'none';
                document.querySelectorAll('.modal-backdrop').forEach(function(b) { b.remove(); });
                document.body.classList.remove('modal-open');
                document.body.style = '';
            }

            // ── Open Accept modal (with package validation) ──
            var openAcceptBtn = document.getElementById('doc-open-accept-modal');
            if (openAcceptBtn) {
                openAcceptBtn.addEventListener('click', function() {
                    if (!validatePackageSelected()) return;
                    var m = new bootstrap.Modal(document.getElementById('acceptConfirmModal'));
                    m.show();
                });
            }

            // ── Accept modal confirm ──
            var acceptConfirmBtn = document.getElementById('accept-confirm-btn');
            if (acceptConfirmBtn) {
                acceptConfirmBtn.addEventListener('click', function() {
                    var comment = document.getElementById('accept-confirm-comment');
                    btnLoading(this);
                    closeModal('acceptConfirmModal');
                    submitFormAction('accepted', comment ? comment.value : '');
                });
            }

            // ── Open Decline modal (with package validation) ──
            var openDeclineBtn = document.getElementById('doc-open-decline-modal');
            if (openDeclineBtn) {
                openDeclineBtn.addEventListener('click', function() {
                    if (!validatePackageSelected()) return;
                    var m = new bootstrap.Modal(document.getElementById('declineConfirmModal'));
                    m.show();
                });
            }

            // ── Decline modal confirm ──
            var declineConfirmBtn = document.getElementById('decline-confirm-btn');
            if (declineConfirmBtn) {
                declineConfirmBtn.addEventListener('click', function() {
                    var comment = document.getElementById('decline-confirm-comment');
                    if (!comment || !comment.value.trim()) {
                        comment.style.borderColor = 'var(--doc-danger)';
                        comment.focus();
                        return;
                    }
                    btnLoading(this);
                    closeModal('declineConfirmModal');
                    submitFormAction('rejected', comment.value);
                });
            }

            // ── Payment modal confirm ──
            var paymentConfirmBtn = document.getElementById('payment-confirm-btn');
            if (paymentConfirmBtn) {
                paymentConfirmBtn.addEventListener('click', function() {
                    var comment = document.getElementById('payment-confirm-comment');
                    btnLoading(this);
                    closeModal('paymentConfirmModal');
                    submitFormAction('payment_submitted', comment ? comment.value : '');
                });
            }

            // ── Reset decline comment border on input ──
            var declineComment = document.getElementById('decline-confirm-comment');
            if (declineComment) {
                declineComment.addEventListener('input', function() {
                    this.style.borderColor = '';
                });
            }
        });
    """)

    return Form(
        Div(
            H3("Your Response", cls="doc-response-title"),
            P(
                status_msg,
                cls="doc-response-copy",
            ),
            cls="doc-response-head",
        ),
        Div(
            feedback,
            package_selector,
            Row(
                Col(
                    Input(
                        type="text",
                        name="responder_name",
                        placeholder="Your name",
                        cls="doc-response-input w-100",
                        required=True,
                    ),
                    span=12,
                    sm=6,
                ),
                Col(
                    Input(
                        type="email",
                        name="responder_email",
                        placeholder="Your email address",
                        cls="doc-response-input w-100",
                        required=True,
                    ),
                    span=12,
                    sm=6,
                ),
                cls="g-3 doc-name-email-row",
            ),
            Textarea(
                name="comment",
                id="main-comment-field",
                placeholder="Add your questions, approval note, or payment confirmation here...",
                rows=5,
                cls="doc-response-input doc-response-textarea",
            ),
            hidden_action,
            hidden_comment,
            Div(
                accept_btn,
                pay_btn,
                reject_btn,
                comment_btn,
                cls="doc-cta-row",
            ),
            cls="doc-response-body",
        ),
        js_script,
        Button(type="submit", id="doc-hidden-submit", style="position:absolute; left:-9999px; width:1px; height:1px; opacity:0; pointer-events:none;"),
        hx_post=f"/documents/{token}/respond",
        hx_target="body",
        hx_swap="innerHTML",
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
            href=f"/documents/{document.public_token}/pdf",
            cls="doc-download-btn",
        ),
        cls="doc-footer",
    )



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
            )
    )

    # ── Data ─────────────────────────────────────────────────────────────────
    account = (
        get_payment_account(document.payment_account_id)
        if document.payment_account_id
        else get_default_payment_account()
    )
    responses = list_document_responses(document.document_id)
    expired = _is_expired(document.valid_until)

    # ── Section cards (dynamic or fixed) ──────────────────────────
    has_sections = deal.sections_json and deal.sections_json.strip() not in ("", "[]")
    if has_sections:
        narrative_cards = _dynamic_sections(deal.sections_json)
    else:
        narrative_cards = [
            _section_card("Background & Objective", _lines(deal.background_text or deal.summary), fallback=deal.summary),
            _section_card("Scope of Work", _lines(deal.scope_notes), fallback=deal.summary),
            _section_card("Options & Delivery Path", _lines(deal.option_notes_text)),
            _section_card("Timeline", _lines(deal.timeline_text)),
            _section_card("Payment Terms", _lines(deal.payment_terms)),
            _section_card("What Is Not Included", _lines(deal.exclusions_text)),
            _section_card("Closing Note", _lines(deal.closing_note)),
        ]

    investment_table = _line_items_table(deal, document)
    account_panel = _payment_account_panel(account) if (document.kind == "invoice" and account) else ""
    expiry_banner = _expiry_banner(document.valid_until) if expired else ""

    # Payment terms bridge card — shown between investment and response form
    payment_terms_card = ""
    if deal.payment_terms and deal.payment_terms.strip():
        payment_terms_card = Div(
            Div(
                Div(cls="doc-section-accent"),
                H2("Payment Terms", cls="doc-section-title"),
                cls="doc-section-head",
            ),
            Div(
                *[P(line, cls="doc-body-text") for line in _lines(deal.payment_terms)],
                cls="doc-card-body",
            ),
            cls="doc-card",
        )

    response_zone = _response_zone(document, token, message, tone, expired=expired, deal=deal)
    history = _response_history(responses)

    # Confirmation modals for irreversible actions
    accept_modal = _accept_confirmation_modal(document, token)
    decline_modal = _decline_confirmation_modal(document, token)
    payment_modal = _payment_confirmation_modal(document, token, account)

    return (
        *SEO(
            title=f"{document.title} — {_doc_type_label(document.kind)}",
            description=deal.summary,
            url=f"{settings.base_url}/documents/{token}",
        ),
        _doc_stylesheet_link(),
        ModernToastStack(position="top-end", gap=2, id="toast-container"),
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
                *narrative_cards,
                investment_table,
                payment_terms_card,
                account_panel,
                # Response
                response_zone,
                history,
                # Footer
                _doc_footer(profile, deal, document),
                cls="doc-page",
            ),
            # Confirmation modals
            accept_modal,
            decline_modal,
            payment_modal,
            cls="doc-shell",
        ),
    )


def _doc_stylesheet_link():
    """Return a Link tag injecting doc-portal.css — separate from admin.css."""
    from fasthtml.common import Link
    import time
    # Bust browser cache by adding version query param
    return Link(rel="stylesheet", href=f"/assets/css/doc-portal.css?v={int(time.time())}")

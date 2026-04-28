"""Repository boundary for the client pipeline workspace."""

from __future__ import annotations

import json
import secrets
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.config import settings
from app.domain.models import AdminDeal, ClientDocumentResponse, DealDocument, DealSaveResult, DealWorkspaceSummary
from app.infrastructure.supabase_client import service_role_is_configured, supabase_is_configured
import app.infrastructure.email_service as email_svc


LOCAL_DEALS = (
    AdminDeal(
        deal_id="deal-farmtech",
        client_name="FarmTech Africa",
        client_email="ops@farmtech.africa",
        client_phone="+2348000001111",
        company="FarmTech Africa",
        project_title="Farm Operations Dashboard",
        service_type="custom-saas",
        stage="proposal",
        summary="A multi-role dashboard for cooperative operations, reporting, and mobile field updates.",
        background_text="FarmTech Africa needs a reliable internal system for field activity, reporting, approvals, and cooperative visibility as operations scale across teams and locations.",
        scope_notes="Discovery, UX structure, Supabase-backed admin surfaces, and phased delivery for MVP to launch.",
        option_notes_text=(
            "Option A | Fast launch build | A focused MVP with the essential roles, reporting, and field updates in one streamlined release.\n"
            "Option B | Growth-ready platform | The MVP plus a stronger reporting foundation, admin controls, and room for future workflow automation."
        ),
        tech_stack=("FastHTML", "Faststrap", "Supabase", "HTMX"),
        timeline_text="Discovery and architecture in week 1, build in weeks 2-4, launch hardening in week 5.",
        payment_terms="50% deposit before kickoff, 30% at the internal review milestone, 20% on delivery.",
        line_items_text=(
            "Product discovery | Requirements, information architecture, and delivery map | 1 | 120000\n"
            "Admin dashboard build | Workflow, documents, and content management module | 1 | 380000\n"
            "Client-facing portal | Public experience, forms, and polished responsive UI | 1 | 350000"
        ),
        exclusions_text="ERP integrations, advanced analytics warehousing, native mobile apps, and multilingual rollout are outside this first engagement and can be scoped separately.",
        closing_note="This proposal is designed to give FarmTech Africa a strong operational foundation first, with a delivery path that stays practical and easy to extend after launch.",
        amount_ngn=850000,
        deposit_percent=50,
        source="local",
        documents=(
            DealDocument(
                document_id="doc-farmtech-proposal",
                kind="proposal",
                status="sent",
                title="Farm Operations Dashboard Proposal",
                document_number="PRO-20260427-FARM",
                public_token="farmtech-proposal-demo",
                payment_account_id="",
                total_amount=850000,
                valid_until="2026-05-10",
                due_date="",
                updated_at="2026-04-27",
            ),
        ),
        latest_document=DealDocument(
            document_id="doc-farmtech-proposal",
            kind="proposal",
            status="sent",
                title="Farm Operations Dashboard Proposal",
                document_number="PRO-20260427-FARM",
                public_token="farmtech-proposal-demo",
                payment_account_id="",
                total_amount=850000,
            valid_until="2026-05-10",
            due_date="",
            updated_at="2026-04-27",
        ),
    ),
    AdminDeal(
        deal_id="deal-olivette",
        client_name="Olivette Studio",
        client_email="hello@olivette.studio",
        client_phone="+2348000002222",
        company="Olivette Studio",
        project_title="Launch Site Refresh",
        service_type="quick-build",
        stage="invoiced",
        summary="A fast-turn landing page refresh with booking funnel improvements and content cleanup.",
        background_text="Olivette Studio needed a cleaner launch surface with stronger calls to action, better mobile spacing, and fewer friction points in the booking path.",
        scope_notes="Fixed-scope refresh focused on launch readiness, no CMS rebuild required.",
        option_notes_text="Quick Quote | Fixed-scope redesign and conversion cleanup | 5 working days",
        tech_stack=("FastHTML", "Faststrap", "Analytics"),
        timeline_text="Delivery in 5 working days after content handoff and deposit confirmation.",
        payment_terms="70% deposit to start, 30% due within 3 days of go-live signoff.",
        line_items_text=(
            "Landing page redesign | Hero, trust blocks, and CTA refresh | 1 | 95000\n"
            "Conversion flow cleanup | Booking path and analytics polish | 1 | 55000"
        ),
        exclusions_text="Long-form CMS migration, ecommerce, and deeper backend integrations were not part of this fixed-scope refresh.",
        closing_note="This quote keeps the work intentionally lean so the launch can move quickly while preserving a clear path for future enhancements.",
        amount_ngn=150000,
        deposit_percent=70,
        source="local",
        documents=(
            DealDocument(
                document_id="doc-olivette-quote",
                kind="quote",
                status="accepted",
                title="Launch Site Refresh Quote",
                document_number="QUO-20260418-OLIV",
                public_token="olivette-quote-demo",
                payment_account_id="",
                total_amount=150000,
                valid_until="2026-05-01",
                due_date="",
                updated_at="2026-04-18",
            ),
            DealDocument(
                document_id="doc-olivette-invoice",
                kind="invoice",
                status="sent",
                title="Launch Site Refresh Deposit Invoice",
                document_number="INV-20260420-OLIV",
                public_token="olivette-invoice-demo",
                payment_account_id="acct-local-main",
                total_amount=105000,
                valid_until="",
                due_date="2026-04-30",
                updated_at="2026-04-20",
            ),
        ),
        latest_document=DealDocument(
            document_id="doc-olivette-invoice",
            kind="invoice",
            status="sent",
                title="Launch Site Refresh Deposit Invoice",
                document_number="INV-20260420-OLIV",
                public_token="olivette-invoice-demo",
                payment_account_id="acct-local-main",
                total_amount=105000,
            valid_until="",
            due_date="2026-04-30",
            updated_at="2026-04-20",
        ),
    ),
)


def _rest_headers(*, prefer: str | None = None) -> dict[str, str]:
    headers = {
        "apikey": settings.supabase_service_role_key,
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
        "Content-Type": "application/json",
    }
    if prefer:
        headers["Prefer"] = prefer
    return headers


def _rest_request(
    method: str,
    path: str,
    *,
    params: dict[str, str] | None = None,
    payload: object | None = None,
    prefer: str | None = None,
) -> object:
    query = f"?{urlencode(params)}" if params else ""
    url = f"{settings.supabase_url.rstrip('/')}/rest/v1/{path}{query}"
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(url, data=body, method=method, headers=_rest_headers(prefer=prefer))
    with urlopen(request, timeout=20) as response:
        raw = response.read()
        if not raw:
            return None
        return json.loads(raw.decode("utf-8"))


def _line_items_to_text(items: list[dict[str, object]]) -> str:
    lines: list[str] = []
    for item in items:
        label = str(item.get("label") or "").strip()
        description = str(item.get("description") or "").strip()
        quantity = str(item.get("quantity") or "1").strip()
        unit_price = str(item.get("unit_price") or "0").strip()
        if label:
            lines.append(" | ".join((label, description, quantity, unit_price)))
    return "\n".join(lines)


def _document_from_supabase(row: dict[str, object]) -> DealDocument:
    return DealDocument(
        document_id=str(row.get("id") or ""),
        kind=str(row.get("kind") or "proposal"),
        status=str(row.get("status") or "draft"),
        title=str(row.get("title") or "Untitled document"),
        document_number=str(row.get("document_number") or ""),
        public_token=str(row.get("public_token") or ""),
        payment_account_id=str(row.get("payment_account_id") or ""),
        total_amount=int(row.get("total_amount") or 0),
        valid_until=str(row.get("valid_until") or ""),
        due_date=str(row.get("due_date") or ""),
        updated_at=str(row.get("updated_at") or "")[:10],
    )


def _deal_from_supabase(row: dict[str, object]) -> AdminDeal:
    tech_rows = row.get("tech_stack") or []
    tech_stack = tuple(str(item).strip() for item in tech_rows if str(item).strip())
    documents = tuple(
        sorted(
            (_document_from_supabase(item) for item in (row.get("client_documents") or [])),
            key=lambda item: (item.updated_at, item.document_number),
            reverse=True,
        )
    )
    latest = documents[0] if documents else None
    return AdminDeal(
        deal_id=str(row.get("id") or ""),
        client_name=str(row.get("client_name") or ""),
        client_email=str(row.get("client_email") or ""),
        client_phone=str(row.get("client_phone") or ""),
        company=str(row.get("company") or ""),
        project_title=str(row.get("project_title") or ""),
        service_type=str(row.get("service_type") or "custom-build"),
        stage=str(row.get("stage") or "lead"),
        summary=str(row.get("summary") or ""),
        background_text=str(row.get("background_text") or ""),
        scope_notes=str(row.get("scope_notes") or ""),
        option_notes_text=str(row.get("option_notes_text") or ""),
        tech_stack=tech_stack,
        timeline_text=str(row.get("timeline_text") or ""),
        payment_terms=str(row.get("payment_terms") or ""),
        line_items_text=_line_items_to_text(list(row.get("client_documents")[0].get("line_items") if row.get("client_documents") else [])),
        exclusions_text=str(row.get("exclusions_text") or ""),
        closing_note=str(row.get("closing_note") or ""),
        amount_ngn=int(row.get("amount_ngn") or 0),
        deposit_percent=int(row.get("deposit_percent") or 50),
        source="supabase",
        documents=documents,
        latest_document=latest,
    )


def _load_supabase_deals() -> tuple[AdminDeal, ...]:
    rows = _rest_request(
        "GET",
        "client_deals",
        params={
            "select": (
                "id,client_name,client_email,client_phone,company,project_title,service_type,stage,summary,"
                "background_text,scope_notes,option_notes_text,tech_stack,timeline_text,payment_terms,exclusions_text,closing_note,"
                "amount_ngn,deposit_percent,updated_at,"
                "client_documents(id,kind,status,title,document_number,public_token,total_amount,valid_until,due_date,updated_at,line_items,payment_account_id)"
            ),
            "order": "updated_at.desc",
        },
    )
    if not isinstance(rows, list):
        return ()
    return tuple(_deal_from_supabase(row) for row in rows)


def _load_local_deals() -> tuple[AdminDeal, ...]:
    return LOCAL_DEALS


def _load_deals() -> tuple[AdminDeal, ...]:
    if supabase_is_configured() and service_role_is_configured():
        try:
            items = _load_supabase_deals()
            if items:
                return items
        except (HTTPError, URLError, TimeoutError, ValueError, KeyError, TypeError):
            pass
    return _load_local_deals()


def list_deals(*, stage: str = "all", document_kind: str = "all", search: str = "") -> tuple[AdminDeal, ...]:
    items = _load_deals()
    if stage != "all":
        items = tuple(item for item in items if item.stage == stage)
    if document_kind != "all":
        items = tuple(item for item in items if any(document.kind == document_kind for document in item.documents))
    if search.strip():
        query = search.strip().lower()
        items = tuple(
            item
            for item in items
            if query in item.client_name.lower()
            or query in item.company.lower()
            or query in item.project_title.lower()
            or query in item.summary.lower()
        )
    return items


def get_deal(deal_id: str) -> AdminDeal | None:
    for item in _load_deals():
        if item.deal_id == deal_id:
            return item
    return None


def get_deal_by_document_id(document_id: str) -> AdminDeal | None:
    """Reverse-lookup a deal from a document_id — used for email dispatch."""
    for deal in _load_deals():
        for doc in deal.documents:
            if doc.document_id == document_id:
                return deal
    # Fallback: try Supabase if configured
    if service_role_is_configured():
        try:
            rows = _rest_request(
                "GET",
                "client_documents",
                params={"select": "deal_id", "id": f"eq.{document_id}", "limit": "1"},
            )
            if isinstance(rows, list) and rows:
                return get_deal(str(rows[0].get("deal_id") or ""))
        except Exception:  # noqa: BLE001
            pass
    return None


def get_document_by_token(token: str) -> tuple[AdminDeal | None, DealDocument | None]:
    for deal in _load_deals():
        for document in deal.documents:
            if document.public_token == token:
                return deal, document
    return None, None


def list_document_responses(document_id: str) -> tuple[ClientDocumentResponse, ...]:
    if not document_id.strip():
        return ()
    if not service_role_is_configured():
        return ()
    try:
        rows = _rest_request(
            "GET",
            "client_document_responses",
            params={
                "select": "id,action,comment,responder_name,created_at",
                "document_id": f"eq.{document_id}",
                "order": "created_at.desc",
            },
        )
    except (HTTPError, URLError, TimeoutError, ValueError):
        return ()
    if not isinstance(rows, list):
        return ()
    return tuple(
        ClientDocumentResponse(
            response_id=str(row.get("id") or ""),
            action=str(row.get("action") or ""),
            comment=str(row.get("comment") or ""),
            responder_name=str(row.get("responder_name") or ""),
            created_at=str(row.get("created_at") or "")[:16].replace("T", " "),
        )
        for row in rows
    )


def get_deal_workspace_summary() -> DealWorkspaceSummary:
    items = _load_deals()
    documents = [document for item in items for document in item.documents]
    source = items[0].source.title() if items else "Local"
    return DealWorkspaceSummary(
        total=len(items),
        proposals=sum(1 for document in documents if document.kind == "proposal"),
        quotes=sum(1 for document in documents if document.kind == "quote"),
        invoices=sum(1 for document in documents if document.kind == "invoice"),
        source=source,
    )


def _parse_tech_stack(raw: str) -> list[str]:
    return [part.strip() for part in raw.replace("\n", ",").split(",") if part.strip()]


def _parse_line_items(raw: str) -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        parts = [part.strip() for part in line.split("|")]
        label = parts[0] if len(parts) > 0 else ""
        description = parts[1] if len(parts) > 1 else ""
        quantity_text = parts[2] if len(parts) > 2 else "1"
        price_text = parts[3] if len(parts) > 3 else "0"
        try:
            quantity = max(1, int(quantity_text or "1"))
        except ValueError:
            quantity = 1
        try:
            unit_price = max(0, int(float(price_text or "0")))
        except ValueError:
            unit_price = 0
        if label:
            items.append(
                {
                    "label": label,
                    "description": description,
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "line_total": quantity * unit_price,
                }
            )
    return items


def _generate_document_number(kind: str, deal_id: str) -> str:
    prefix = {"proposal": "PRO", "quote": "QUO", "invoice": "INV"}.get(kind, "DOC")
    return f"{prefix}-{datetime.now(timezone.utc):%Y%m%d}-{deal_id.replace('-', '').upper()[:4]}"


def _generate_public_token(kind: str, deal_id: str) -> str:
    return f"{kind[:3]}-{deal_id.replace('-', '')[:6]}-{secrets.token_urlsafe(8)}".lower()


def save_document_response(
    *,
    token: str,
    action: str,
    responder_name: str,
    responder_email: str,
    comment: str,
) -> tuple[bool, str, str]:
    deal, document = get_document_by_token(token)
    if not deal or not document:
        return False, "danger", "This document link is not valid anymore."
    if action not in {"accepted", "rejected", "commented", "payment_submitted"}:
        return False, "warning", "Choose a valid response action."
    if not service_role_is_configured():
        return False, "info", "Supabase write path is not configured yet, so client responses cannot be recorded from this environment."
    payload = {
        "document_id": document.document_id,
        "action": action,
        "responder_name": responder_name.strip(),
        "responder_email": responder_email.strip(),
        "comment": comment.strip(),
    }
    try:
        _rest_request("POST", "client_document_responses", payload=payload, prefer="return=representation")
        if action == "accepted" and document.kind in {"proposal", "quote"}:
            _rest_request(
                "PATCH",
                "client_documents",
                params={"id": f"eq.{document.document_id}"},
                payload={"status": "accepted"},
                prefer="return=minimal",
            )
        if action == "payment_submitted" and document.kind == "invoice":
            _rest_request(
                "PATCH",
                "client_deals",
                params={"id": f"eq.{deal.deal_id}"},
                payload={"stage": "invoiced"},
                prefer="return=minimal",
            )
        messages = {
            "accepted": "The document has been marked as accepted. You can follow up from the admin dashboard.",
            "rejected": "The rejection note has been recorded.",
            "commented": "The comment has been saved.",
            "payment_submitted": "The payment confirmation has been sent. It will still need to be confirmed from the admin dashboard.",
        }
        # — Notify admin
        email_svc.notify_document_response(
            client_name=responder_name.strip(),
            client_email=responder_email.strip(),
            action=action,
            document_kind=document.kind,
            project_title=deal.project_title,
            comment=comment.strip(),
            deal_id=deal.deal_id,
        )
        # — Confirm to client
        email_svc.send_response_confirmation_to_client(
            client_name=responder_name.strip(),
            client_email=responder_email.strip(),
            action=action,
            document_kind=document.kind,
            project_title=deal.project_title,
        )
        return True, "success", messages[action]
    except HTTPError as exc:
        details = exc.read().decode("utf-8", errors="ignore")
        return False, "danger", f"Supabase rejected the document response. {details or exc.reason}"
    except (URLError, TimeoutError, ValueError) as exc:
        return False, "danger", f"Could not reach Supabase to save the document response. {exc}"


def update_document_status(
    *,
    deal_id: str,
    document_id: str,
    document_kind: str,
    status: str,
) -> tuple[bool, str, str]:
    if not deal_id.strip() or not document_id.strip():
        return False, "warning", "A valid deal document is required before updating workflow state."
    if document_kind not in {"proposal", "quote", "invoice"}:
        return False, "warning", "Choose a valid document type before updating workflow state."
    if status not in {"draft", "sent", "accepted", "paid", "expired"}:
        return False, "warning", "Choose a valid document status before updating workflow state."
    if not service_role_is_configured():
        return False, "info", "Supabase write path is not configured yet, so document workflow updates cannot be saved from this environment."

    deal_stage = None
    if status == "sent":
        deal_stage = {
            "proposal": "proposal",
            "quote": "quoted",
            "invoice": "invoiced",
        }.get(document_kind)
    elif status == "paid" and document_kind == "invoice":
        deal_stage = "paid"

    try:
        _rest_request(
            "PATCH",
            "client_documents",
            params={"id": f"eq.{document_id}"},
            payload={"status": status},
            prefer="return=minimal",
        )
        if deal_stage:
            _rest_request(
                "PATCH",
                "client_deals",
                params={"id": f"eq.{deal_id}"},
                payload={"stage": deal_stage},
                prefer="return=minimal",
            )
        messages = {
            "sent": "The document is now marked as sent and the deal stage has been advanced.",
            "paid": "The invoice is now marked as paid and the deal has been moved to the paid stage.",
            "accepted": "The document is now marked as accepted.",
            "expired": "The document is now marked as expired.",
            "draft": "The document is now back in draft.",
        }
        # — When admin marks sent, email the client their document link
        if status == "sent":
            try:
                deal = get_deal_by_document_id(document_id)
                document_obj = next((d for d in deal.documents if d.document_id == document_id), None) if deal else None
                if deal and document_obj and document_obj.public_token:
                    from app.config import settings as _s
                    doc_url = f"{_s.base_url.rstrip('/')}/documents/{document_obj.public_token}"
                    email_svc.send_document_link_to_client(
                        client_name=deal.client_name,
                        client_email=deal.client_email,
                        document_kind=document_kind,
                        project_title=deal.project_title,
                        document_url=doc_url,
                        valid_until=document_obj.valid_until or "",
                    )
            except Exception:  # noqa: BLE001 — email is best-effort
                pass
        return True, "success", messages.get(status, "The document workflow state has been updated.")
    except HTTPError as exc:
        details = exc.read().decode("utf-8", errors="ignore")
        return False, "danger", f"Supabase rejected the document workflow update. {details or exc.reason}"
    except (URLError, TimeoutError, ValueError) as exc:
        return False, "danger", f"Could not reach Supabase to update the document workflow. {exc}"


def save_deal_document(
    *,
    deal_id: str,
    client_name: str,
    client_email: str,
    client_phone: str,
    company: str,
    project_title: str,
    service_type: str,
    stage: str,
    document_kind: str,
    document_status: str,
    document_title: str,
    summary: str,
    background_text: str,
    scope_notes: str,
    option_notes_text: str,
    tech_stack: str,
    timeline_text: str,
    payment_terms: str,
    line_items: str,
    exclusions_text: str,
    closing_note: str,
    payment_account_id: str,
    amount_ngn: str,
    deposit_percent: str,
    valid_until: str,
    due_date: str,
) -> DealSaveResult:
    if not client_name.strip() or not client_email.strip() or not project_title.strip() or not document_title.strip():
        return DealSaveResult(
            success=False,
            tone="warning",
            message="Client name, client email, project title, and document title are required before saving.",
            source="Validation",
        )

    if stage not in {"lead", "proposal", "quoted", "invoiced", "paid", "delivered"}:
        return DealSaveResult(False, "warning", "Choose a valid pipeline stage.", "Validation")
    if document_kind not in {"proposal", "quote", "invoice"}:
        return DealSaveResult(False, "warning", "Choose a valid document type.", "Validation")
    if document_status not in {"draft", "sent", "accepted", "paid", "expired"}:
        return DealSaveResult(False, "warning", "Choose a valid document status.", "Validation")

    try:
        amount_value = max(0, int(amount_ngn or "0"))
        deposit_value = max(0, min(100, int(deposit_percent or "50")))
    except ValueError:
        return DealSaveResult(False, "warning", "Amount and deposit percentage must be whole numbers.", "Validation")

    if not service_role_is_configured():
        return DealSaveResult(
            success=False,
            tone="info",
            message="Supabase write path is not configured yet. Add SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY to enable saving.",
            source="Local seed data",
            deal_id=deal_id or None,
        )

    parsed_line_items = _parse_line_items(line_items)
    subtotal = sum(int(item["line_total"]) for item in parsed_line_items) or amount_value
    total_amount = subtotal
    deal_payload = {
        "client_name": client_name.strip(),
        "client_email": client_email.strip(),
        "client_phone": client_phone.strip(),
        "company": company.strip(),
        "project_title": project_title.strip(),
        "service_type": service_type.strip() or "custom-build",
        "stage": stage,
        "summary": summary.strip(),
        "background_text": background_text.strip(),
        "scope_notes": scope_notes.strip(),
        "option_notes_text": option_notes_text.strip(),
        "tech_stack": _parse_tech_stack(tech_stack),
        "timeline_text": timeline_text.strip(),
        "payment_terms": payment_terms.strip(),
        "exclusions_text": exclusions_text.strip(),
        "closing_note": closing_note.strip(),
        "amount_ngn": amount_value,
        "deposit_percent": deposit_value,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        saved_deal_id = deal_id.strip()
        if saved_deal_id:
            rows = _rest_request(
                "PATCH",
                "client_deals",
                params={"id": f"eq.{saved_deal_id}"},
                payload=deal_payload,
                prefer="return=representation",
            )
        else:
            rows = _rest_request(
                "POST",
                "client_deals",
                payload=deal_payload,
                prefer="return=representation",
            )
        row = rows[0] if isinstance(rows, list) and rows else None
        if not row or "id" not in row:
            return DealSaveResult(False, "danger", "Supabase did not return the saved deal record.", "Supabase")
        saved_deal_id = str(row["id"])

        existing_rows = _rest_request(
            "GET",
            "client_documents",
            params={
                "select": "id,document_number,public_token",
                "deal_id": f"eq.{saved_deal_id}",
                "kind": f"eq.{document_kind}",
                "limit": "1",
            },
        )
        existing = existing_rows[0] if isinstance(existing_rows, list) and existing_rows else None
        document_number = str(existing.get("document_number") or _generate_document_number(document_kind, saved_deal_id)) if existing else _generate_document_number(document_kind, saved_deal_id)
        public_token = str(existing.get("public_token") or _generate_public_token(document_kind, saved_deal_id)) if existing else _generate_public_token(document_kind, saved_deal_id)
        document_payload = {
            "deal_id": saved_deal_id,
            "kind": document_kind,
            "status": document_status,
            "document_number": document_number,
            "public_token": public_token,
            "title": document_title.strip(),
            "summary": summary.strip(),
            "timeline_text": timeline_text.strip(),
            "payment_terms": payment_terms.strip(),
            "line_items": parsed_line_items,
            "subtotal": subtotal,
            "tax_amount": 0,
            "total_amount": total_amount,
            "valid_until": valid_until.strip() or None,
            "due_date": due_date.strip() or None,
            "payment_account_id": payment_account_id.strip() or None,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        if existing and existing.get("id"):
            _rest_request(
                "PATCH",
                "client_documents",
                params={"id": f"eq.{existing['id']}"},
                payload=document_payload,
                prefer="return=representation",
            )
        else:
            _rest_request(
                "POST",
                "client_documents",
                params={"on_conflict": "deal_id,kind"},
                payload=document_payload,
                prefer="resolution=merge-duplicates,return=representation",
            )

        action = "updated" if deal_id.strip() else "created"
        return DealSaveResult(
            success=True,
            tone="success",
            message=f"{document_kind.title()} draft {action}. The deal is now tracked in the {stage.replace('-', ' ')} stage.",
            source="Supabase",
            deal_id=saved_deal_id,
        )
    except HTTPError as exc:
        details = exc.read().decode("utf-8", errors="ignore")
        return DealSaveResult(False, "danger", f"Supabase rejected the deal save request. {details or exc.reason}", "Supabase", deal_id=deal_id or None)
    except (URLError, TimeoutError, ValueError) as exc:
        return DealSaveResult(False, "danger", f"Could not reach Supabase to save the client pipeline record. {exc}", "Supabase", deal_id=deal_id or None)

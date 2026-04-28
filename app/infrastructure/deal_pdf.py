"""Branded PDF generation for proposals, quotes, and invoices."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.domain.models import AdminDeal
from app.infrastructure.payment_account_repository import get_default_payment_account, get_payment_account
from app.infrastructure.settings_repository import get_site_profile


BASE_DIR = Path(__file__).resolve().parents[2]
# Vercel has a read-only filesystem — write PDFs to /tmp there, local assets/generated elsewhere
import os as _os
OUTPUT_DIR = Path("/tmp") if _os.getenv("VERCEL") else BASE_DIR / "assets" / "generated"

NAVY = colors.HexColor("#07111F")
NAVY_SOFT = colors.HexColor("#102033")
CYAN = colors.HexColor("#46C8EE")
CYAN_SOFT = colors.HexColor("#DFF7FF")
CYAN_RULE = colors.HexColor("#46C8EE")
TEXT = colors.HexColor("#132131")
MUTED = colors.HexColor("#5A6A7D")
LINE = colors.HexColor("#D9E8F0")
WHITE = colors.white
WATERMARK_COLOR = colors.HexColor("#E8F0F5")


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "kicker": ParagraphStyle("DealPdfKicker", parent=base["BodyText"], fontName="Helvetica-Bold", fontSize=9, leading=11, textColor=CYAN),
        "title": ParagraphStyle("DealPdfTitle", parent=base["Heading1"], fontName="Helvetica-Bold", fontSize=22, leading=25, textColor=WHITE),
        "subtitle": ParagraphStyle("DealPdfSubtitle", parent=base["BodyText"], fontName="Helvetica", fontSize=10.5, leading=14, textColor=NAVY_SOFT),
        "meta": ParagraphStyle("DealPdfMeta", parent=base["BodyText"], fontName="Helvetica", fontSize=8.5, leading=11, textColor=WHITE),
        "section": ParagraphStyle("DealPdfSection", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=10.5, leading=12, textColor=WHITE, alignment=1),
        "body": ParagraphStyle("DealPdfBody", parent=base["BodyText"], fontName="Helvetica", fontSize=9.2, leading=14, textColor=TEXT),
        "small": ParagraphStyle("DealPdfSmall", parent=base["BodyText"], fontName="Helvetica", fontSize=8.2, leading=11, textColor=MUTED),
        "label": ParagraphStyle("DealPdfLabel", parent=base["BodyText"], fontName="Helvetica-Bold", fontSize=8.3, leading=11, textColor=MUTED),
        "table_head": ParagraphStyle("DealPdfTableHead", parent=base["BodyText"], fontName="Helvetica-Bold", fontSize=8.5, leading=10.5, textColor=WHITE),
        "table_cell": ParagraphStyle("DealPdfTableCell", parent=base["BodyText"], fontName="Helvetica", fontSize=8.4, leading=11, textColor=TEXT),
        "footer": ParagraphStyle("DealPdfFooter", parent=base["BodyText"], fontName="Helvetica", fontSize=7.6, leading=10, textColor=MUTED, alignment=1),
    }


def _money(value: int) -> str:
    return f"N{value:,.0f}"


def _lines(raw: str) -> list[str]:
    return [line.strip() for line in raw.splitlines() if line.strip()]


def _line_items(raw: str) -> list[tuple[str, str, str, int]]:
    items: list[tuple[str, str, str, int]] = []
    for line in _lines(raw):
        parts = [part.strip() for part in line.split("|")]
        title = parts[0] if len(parts) > 0 else ""
        detail = parts[1] if len(parts) > 1 else ""
        qty = parts[2] if len(parts) > 2 else "1"
        try:
            amount = int(float(parts[3])) if len(parts) > 3 and parts[3] else 0
        except ValueError:
            amount = 0
        if title:
            items.append((title, detail, qty, amount))
    return items


def _option_rows(raw: str) -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    for line in _lines(raw):
        parts = [part.strip() for part in line.split("|")]
        title = parts[0] if len(parts) > 0 else ""
        summary = parts[1] if len(parts) > 1 else ""
        note = parts[2] if len(parts) > 2 else ""
        if title:
            rows.append((title, summary, note))
    return rows


def _section_banner(title: str, styles: dict[str, ParagraphStyle]) -> Table:
    table = Table([[Paragraph(title, styles["section"])]], colWidths=[170 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), CYAN),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table


def _body_card(content: list, *, width: float = 170 * mm) -> Table:
    card = Table([[content]], colWidths=[width])
    card.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), WHITE),
                ("BOX", (0, 0), (-1, -1), 0.6, LINE),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    return card


def _build_option_table(deal: AdminDeal, styles: dict[str, ParagraphStyle]) -> Table | None:
    rows = _option_rows(deal.option_notes_text)
    if not rows:
        return None
    data = [
        [
            Paragraph("Option", styles["table_head"]),
            Paragraph("Summary", styles["table_head"]),
            Paragraph("Cost / Note", styles["table_head"]),
        ]
    ]
    for title, summary, note in rows:
        data.append(
            [
                Paragraph(title, styles["table_cell"]),
                Paragraph(summary or "-", styles["table_cell"]),
                Paragraph(note or "-", styles["table_cell"]),
            ]
        )
    table = Table(data, colWidths=[34 * mm, 92 * mm, 44 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY_SOFT),
                ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
                ("BOX", (0, 0), (-1, -1), 0.6, LINE),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, LINE),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    return table


def _build_line_item_table(deal: AdminDeal, styles: dict[str, ParagraphStyle]) -> tuple[Table, int]:
    items = _line_items(deal.line_items_text)
    subtotal = sum(amount for *_rest, amount in items) or deal.amount_ngn
    data = [
        [
            Paragraph("Component", styles["table_head"]),
            Paragraph("Description", styles["table_head"]),
            Paragraph("Qty", styles["table_head"]),
            Paragraph("Amount", styles["table_head"]),
        ]
    ]
    for title, detail, qty, amount in items:
        data.append(
            [
                Paragraph(title, styles["table_cell"]),
                Paragraph(detail or "-", styles["table_cell"]),
                Paragraph(qty, styles["table_cell"]),
                Paragraph(_money(amount), styles["table_cell"]),
            ]
        )
    if len(data) == 1:
        data.append(
            [
                Paragraph(deal.project_title, styles["table_cell"]),
                Paragraph(deal.summary or "-", styles["table_cell"]),
                Paragraph("1", styles["table_cell"]),
                Paragraph(_money(deal.amount_ngn), styles["table_cell"]),
            ]
        )
    data.append(
        [
            Paragraph("Total", styles["table_cell"]),
            Paragraph("", styles["table_cell"]),
            Paragraph("", styles["table_cell"]),
            Paragraph(_money(subtotal), styles["table_cell"]),
        ]
    )
    table = Table(data, colWidths=[46 * mm, 74 * mm, 16 * mm, 34 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY_SOFT),
                ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
                ("BACKGROUND", (0, -1), (-1, -1), CYAN_SOFT),
                ("BOX", (0, 0), (-1, -1), 0.6, LINE),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, LINE),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    return table, subtotal


def _payment_account_table(account, styles: dict[str, ParagraphStyle]) -> Table:
    table = Table(
        [
            [Paragraph("<b>Account Label</b>", styles["label"]), Paragraph(account.label, styles["body"])],
            [Paragraph("<b>Bank</b>", styles["label"]), Paragraph(account.bank_name, styles["body"])],
            [Paragraph("<b>Account Name</b>", styles["label"]), Paragraph(account.account_name, styles["body"])],
            [Paragraph("<b>Account Number</b>", styles["label"]), Paragraph(account.account_number, styles["body"])],
            [Paragraph("<b>Note</b>", styles["label"]), Paragraph(account.note or "-", styles["body"])],
        ],
        colWidths=[42 * mm, 128 * mm],
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), WHITE),
                ("BOX", (0, 0), (-1, -1), 0.6, LINE),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, LINE),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    return table


def _document_label(document_kind: str) -> str:
    return {
        "proposal": "TECHNICAL PROPOSAL",
        "quote": "PROJECT QUOTATION",
        "invoice": "PAYMENT INVOICE",
    }.get(document_kind, "CLIENT DOCUMENT")


def _next_steps_copy(document_kind: str, deal: AdminDeal, subtotal: int, deposit_amount: int) -> list[str]:
    if document_kind == "proposal":
        return [
            "Review the scope, assumptions, and phased delivery plan.",
            "Share approval, requested adjustments, or clarification notes through the client link or by email.",
            f"On approval, the project can move into kickoff with a {deal.deposit_percent}% startup invoice ({_money(deposit_amount)}).",
        ]
    if document_kind == "quote":
        return [
            "Confirm the fixed-scope deliverables and quoted amount.",
            "Respond before the validity window closes so timing and pricing stay reserved.",
            f"Once accepted, the work can move forward with the agreed deposit structure against the {_money(subtotal)} total.",
        ]
    return [
        "Use the payment details in this invoice to complete the transfer.",
        "After payment, mark it as submitted from the client link so the admin side can confirm and close the billing step.",
        f"This invoice references the current project total of {_money(subtotal)} and should be paid by the due date shown above.",
    ]


def _bullet_card(lines: list[str], styles: dict[str, ParagraphStyle], *, width: float = 170 * mm) -> Table:
    items = [Paragraph(f"• {line}", styles["body"]) for line in lines]
    return _body_card(items, width=width)


def _cyan_rule() -> Table:
    """A full-width cyan accent rule — sits directly below the header block."""
    rule = Table([[""]], colWidths=[170 * mm])
    rule.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), CYAN_RULE),
                ("TOPPADDING", (0, 0), (-1, -1), 1.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    return rule


def _watermark_text(document_kind: str, status: str) -> str | None:
    """Return a watermark label for non-finalised documents."""
    if status in {"accepted", "paid"}:
        return None
    labels = {
        "draft": "DRAFT",
        "sent": "AWAITING APPROVAL",
        "expired": "EXPIRED",
        "rejected": "DECLINED",
    }
    return labels.get(status)


def _footer(canvas, doc):
    canvas.saveState()
    # Page number
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(MUTED)
    canvas.drawCentredString(A4[0] / 2, 10 * mm, f"Page {doc.page}")
    # Diagonal watermark for non-finalised documents
    watermark = getattr(doc, "_watermark", None)
    if watermark:
        canvas.setFont("Helvetica-Bold", 56)
        canvas.setFillColor(WATERMARK_COLOR)
        canvas.translate(A4[0] / 2, A4[1] / 2)
        canvas.rotate(38)
        canvas.drawCentredString(0, 0, watermark)
    canvas.restoreState()


def build_deal_document_pdf(deal: AdminDeal, document_kind: str) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    styles = _styles()
    profile = get_site_profile()
    document = next((item for item in deal.documents if item.kind == document_kind), deal.latest_document)
    payment_account = None
    if document and document.kind == "invoice":
        payment_account = get_payment_account(document.payment_account_id) if document.payment_account_id else get_default_payment_account()
    output_path = OUTPUT_DIR / f"{deal.deal_id}-{document_kind}.pdf"

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
    )
    # Attach watermark label so _footer can read it
    status = document.status if document else "draft"
    doc._watermark = _watermark_text(document_kind, status)

    header = Table(
        [[
            Paragraph(f"{_document_label(document_kind)}<br/>{document.title if document else f'{document_kind.title()} Document'}", styles["title"]),
            Paragraph(
                f"{profile.full_name}<br/>{profile.email}<br/>{datetime.now():%B %Y}",
                styles["meta"],
            ),
        ]],
        colWidths=[110 * mm, 60 * mm],
    )
    header.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), NAVY),
                ("LEFTPADDING", (0, 0), (-1, -1), 14),
                ("RIGHTPADDING", (0, 0), (-1, -1), 14),
                ("TOPPADDING", (0, 0), (-1, -1), 14),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )

    cover_meta = Table(
        [
            [Paragraph("<b>Prepared for</b>", styles["label"]), Paragraph(deal.company or deal.client_name, styles["body"])],
            [Paragraph("<b>Prepared by</b>", styles["label"]), Paragraph(profile.full_name, styles["body"])],
            [Paragraph("<b>Document No.</b>", styles["label"]), Paragraph(document.document_number if document else "-", styles["body"])],
            [Paragraph("<b>Stage</b>", styles["label"]), Paragraph(deal.stage.replace("_", " ").title(), styles["body"])],
            [Paragraph("<b>Valid Until</b>", styles["label"]), Paragraph(document.valid_until if document and document.valid_until else "-", styles["body"])],
            [Paragraph("<b>Due Date</b>", styles["label"]), Paragraph(document.due_date if document and document.due_date else "-", styles["body"])],
        ],
        colWidths=[36 * mm, 134 * mm],
    )
    cover_meta.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), WHITE),
                ("BOX", (0, 0), (-1, -1), 0.6, LINE),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, LINE),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )

    option_table = _build_option_table(deal, styles)
    line_item_table, subtotal = _build_line_item_table(deal, styles)
    deposit_amount = round(subtotal * (deal.deposit_percent / 100))
    next_steps = _next_steps_copy(document_kind, deal, subtotal, deposit_amount)
    story = [
        header,
        _cyan_rule(),
        Spacer(1, 8),
        Paragraph(_document_label(document_kind), styles["kicker"]),
        Spacer(1, 4),
        Paragraph(deal.project_title, ParagraphStyle("ProjectTitle", parent=styles["body"], fontName="Helvetica-Bold", fontSize=16, leading=19, textColor=NAVY)),
        Spacer(1, 6),
        Paragraph(deal.summary, styles["subtitle"]),
        Spacer(1, 12),
        cover_meta,
        Spacer(1, 14),
        _section_banner("Background & Objective", styles),
        Spacer(1, 6),
        _body_card([Paragraph(deal.background_text or deal.summary, styles["body"])]),
        Spacer(1, 12),
        _section_banner("Scope of Work", styles),
        Spacer(1, 6),
        _body_card([Paragraph(line, styles["body"]) for line in _lines(deal.scope_notes)] or [Paragraph(deal.scope_notes or "-", styles["body"])]),
        Spacer(1, 12),
    ]
    if option_table:
        story.extend([
            _section_banner("Options", styles),
            Spacer(1, 6),
            option_table,
            Spacer(1, 12),
        ])
    if payment_account:
        story.extend(
            [
                _section_banner("Payment Details", styles),
                Spacer(1, 6),
                _payment_account_table(payment_account, styles),
                Spacer(1, 12),
            ]
        )
    story.extend([
        _section_banner("Timeline", styles),
        Spacer(1, 6),
        _body_card([Paragraph(line, styles["body"]) for line in _lines(deal.timeline_text)] or [Paragraph(deal.timeline_text or "-", styles["body"])]),
        Spacer(1, 12),
        _section_banner("Investment & Payment Schedule", styles),
        Spacer(1, 6),
        line_item_table,
        Spacer(1, 8),
        _body_card(
            [
                Paragraph(f"Total engagement value: <b>{_money(subtotal)}</b>", styles["body"]),
                Spacer(1, 5),
                Paragraph(f"Suggested deposit to start: <b>{deal.deposit_percent}% ({_money(deposit_amount)})</b>", styles["body"]),
                Spacer(1, 5),
                Paragraph(deal.payment_terms or "Payment schedule to be confirmed before kickoff.", styles["body"]),
            ]
        ),
        Spacer(1, 12),
        _section_banner("What Is Not Included", styles),
        Spacer(1, 6),
        _body_card([Paragraph(line, styles["body"]) for line in _lines(deal.exclusions_text)] or [Paragraph(deal.exclusions_text or "Any exclusions can be clarified before acceptance.", styles["body"])]),
        Spacer(1, 12),
        _section_banner("Closing Note", styles),
        Spacer(1, 6),
        _body_card([Paragraph(deal.closing_note or "I look forward to discussing the scope and next steps with you.", styles["body"])]),
        Spacer(1, 12),
        _section_banner("Next Steps", styles),
        Spacer(1, 6),
        _bullet_card(next_steps, styles),
        Spacer(1, 14),
        Paragraph(f"{profile.full_name}  ·  {profile.email}  ·  {profile.phone}", styles["footer"]),
        Spacer(1, 4),
        Paragraph("View online: share the client link for interactive acceptance and response.", styles["footer"]),
    ])
    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return output_path

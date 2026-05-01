"""Email notification service using the Resend API.

All functions are safe to call when email is not configured — they
log a debug message and return False without raising.  This means
callers never need to guard against missing config.

Usage:
    Set RESEND_API_KEY and ADMIN_NOTIFY_EMAIL in .env to enable.
    Optionally set EMAIL_FROM (defaults to noreply@neoportfolio.dev).
"""

from __future__ import annotations

import json
import logging
from html import escape
import urllib.error
import urllib.request
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)

_RESEND_URL = "https://api.resend.com/emails"


# ── Core sender ───────────────────────────────────────────────────────────────

def _send(*, to: str, subject: str, html: str) -> bool:
    """Send one email via the Resend API.  Returns True on success."""
    if not settings.email_enabled or not settings.resend_api_key:
        logger.debug("Email not configured — skipping: %s", subject)
        return False
    if not to:
        logger.debug("No recipient — skipping: %s", subject)
        return False

    payload = json.dumps({
        "from": settings.email_from,
        "to": [to],
        "subject": subject,
        "html": html,
    }).encode("utf-8")

    req = urllib.request.Request(
        _RESEND_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {settings.resend_api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            ok = 200 <= resp.status < 300
            if not ok:
                logger.warning("Resend returned %s for: %s", resp.status, subject)
            return ok
    except urllib.error.HTTPError as exc:
        logger.warning("Resend HTTP %s: %s", exc.code, exc.read().decode("utf-8", errors="replace"))
        return False
    except Exception as exc:  # noqa: BLE001
        logger.warning("Email send failed (%s): %s", type(exc).__name__, exc)
        return False


# ── Email templates ───────────────────────────────────────────────────────────

def _base_html(*, title: str, body: str, cta_label: str = "", cta_url: str = "") -> str:
    safe_title = escape(title)
    safe_cta_label = escape(cta_label)
    safe_cta_url = escape(cta_url, quote=True)
    cta_block = ""
    if safe_cta_label and safe_cta_url:
        cta_block = f"""
        <div style="margin:28px 0 0;">
          <a href="{safe_cta_url}"
             style="display:inline-block;padding:12px 28px;background:#46c8ee;color:#082032;
                    border-radius:999px;font-weight:700;font-size:15px;text-decoration:none;">
            {safe_cta_label}
          </a>
        </div>"""
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{safe_title}</title></head>
<body style="margin:0;padding:0;background:#f2f6fb;font-family:Inter,system-ui,sans-serif;">
  <div style="max-width:540px;margin:40px auto;background:#fff;border-radius:12px;
              border:1px solid #d9e8f0;overflow:hidden;box-shadow:0 2px 12px rgba(7,17,31,.07);">
    <div style="background:#07111f;padding:20px 28px;border-bottom:3px solid #46c8ee;">
      <span style="color:#46c8ee;font-weight:700;font-size:1rem;letter-spacing:.02em;">Neo Admin</span>
    </div>
    <div style="padding:28px 28px 32px;">
      {body}
      {cta_block}
      <p style="margin:32px 0 0;color:#8596aa;font-size:12px;border-top:1px solid #eaf1f7;padding-top:16px;">
        This is an automated message from Neo Admin. Do not reply to this email.
      </p>
    </div>
  </div>
</body></html>"""


def _field(label: str, value: str) -> str:
    safe_label = escape(label)
    safe_value = escape(value or "-")
    value = safe_value
    return f"""<div style="margin-bottom:10px;">
      <span style="color:#8596aa;font-size:11px;font-weight:700;letter-spacing:.1em;
                   text-transform:uppercase;">{safe_label}</span><br>
      <span style="color:#132131;font-size:14px;font-weight:600;">{value or "—"}</span>
    </div>"""


# ── Notification functions ────────────────────────────────────────────────────

def notify_new_submission(*, name: str, email: str, kind: str, subject: str, message: str) -> bool:
    """Alert the admin when a new submission arrives from the public portfolio."""
    admin_url = f"{settings.base_url}/submissions"
    body = f"""
    <h2 style="margin:0 0 6px;color:#07111f;font-size:20px;font-weight:700;">New {kind.title()} Received</h2>
    <p style="color:#5a6a7d;margin:0 0 20px;">A new inquiry just came in through the public portfolio contact form.</p>
    <div style="background:#f4f7fb;border-radius:8px;padding:16px;border:1px solid #d9e8f0;">
      {_field("Name", name)}
      {_field("Email", email)}
      {_field("Type", kind.title())}
      {_field("Subject / Service", subject)}
      {_field("Message", message[:400] + ("..." if len(message) > 400 else ""))}
    </div>"""
    return _send(
        to=settings.admin_notify_email,
        subject=f"[Neo Admin] New {kind.title()}: {name}",
        html=_base_html(title=f"New {kind.title()}", body=body, cta_label="Open in Submissions", cta_url=admin_url),
    )


def notify_document_response(
    *,
    client_name: str,
    client_email: str,
    action: str,
    document_kind: str,
    project_title: str,
    comment: str,
    deal_id: str,
) -> bool:
    """Alert the admin when a client responds to a proposal, quote, or invoice link."""
    action_label = action.replace("_", " ").title()
    deal_url = f"{settings.base_url}/deals?deal_id={deal_id}"
    body = f"""
    <h2 style="margin:0 0 6px;color:#07111f;font-size:20px;font-weight:700;">Client Response: {action_label}</h2>
    <p style="color:#5a6a7d;margin:0 0 20px;">
      {client_name} has responded to the <strong>{document_kind.title()}</strong> for <strong>{project_title}</strong>.
    </p>
    <div style="background:#f4f7fb;border-radius:8px;padding:16px;border:1px solid #d9e8f0;">
      {_field("Client", client_name)}
      {_field("Email", client_email)}
      {_field("Action", action_label)}
      {_field("Document", document_kind.title())}
      {_field("Project", project_title)}
      {_field("Comment", comment or "No comment provided")}
    </div>"""
    return _send(
        to=settings.admin_notify_email,
        subject=f"[Neo Admin] {action_label}: {project_title}",
        html=_base_html(title=f"Client Response: {action_label}", body=body, cta_label="Open Deal", cta_url=deal_url),
    )


def send_document_link_to_client(
    *,
    client_name: str,
    client_email: str,
    document_kind: str,
    project_title: str,
    document_url: str,
    valid_until: str = "",
) -> bool:
    """Send the client their document link when a document is marked as 'sent'."""
    kind_label = {"proposal": "Technical Proposal", "quote": "Project Quotation", "invoice": "Payment Invoice"}.get(
        document_kind, "Document"
    )
    validity = f"<br>This document is valid until <strong>{valid_until}</strong>." if valid_until else ""
    body = f"""
    <h2 style="margin:0 0 6px;color:#07111f;font-size:20px;font-weight:700;">Your {kind_label} is Ready</h2>
    <p style="color:#5a6a7d;margin:0 0 20px;">
      Hi {client_name}, please find your <strong>{kind_label}</strong> for
      <strong>{project_title}</strong> at the link below.{validity}
    </p>
    <p style="color:#5a6a7d;font-size:13px;">
      You can review, accept, decline, or send a comment directly from the link.
      No account needed.
    </p>"""
    return _send(
        to=client_email,
        subject=f"{kind_label}: {project_title}",
        html=_base_html(title=kind_label, body=body, cta_label=f"Review {kind_label}", cta_url=document_url),
    )


def send_response_confirmation_to_client(
    *,
    client_name: str,
    client_email: str,
    action: str,
    document_kind: str,
    project_title: str,
) -> bool:
    """Send a confirmation to the client after they respond to a document."""
    action_label = action.replace("_", " ").title()
    messages = {
        "accepted": "Great news — your acceptance has been recorded. I'll be in touch shortly to confirm next steps.",
        "rejected": "Your response has been recorded. I'll follow up to understand your concerns and see how we can adjust.",
        "commented": "Your comment has been received. I'll review and respond as soon as possible.",
        "payment_submitted": "Your payment notification has been received. I'll confirm once the transfer is verified.",
    }
    msg = messages.get(action, "Your response has been recorded. I'll follow up soon.")
    body = f"""
    <h2 style="margin:0 0 6px;color:#07111f;font-size:20px;font-weight:700;">Response Confirmed: {action_label}</h2>
    <p style="color:#5a6a7d;margin:0 0 20px;">Hi {client_name}, thank you for your response.</p>
    <div style="background:#f4f7fb;border-radius:8px;padding:16px;border:1px solid #d9e8f0;">
      {_field("Document", document_kind.title())}
      {_field("Project", project_title)}
      {_field("Your Action", action_label)}
    </div>
    <p style="color:#132131;margin:20px 0 0;">{msg}</p>"""
    return _send(
        to=client_email,
        subject=f"[{project_title}] Response Confirmed — {action_label}",
        html=_base_html(title="Response Confirmed", body=body),
    )

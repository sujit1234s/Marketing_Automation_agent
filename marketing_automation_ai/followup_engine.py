import os
from datetime import datetime, timedelta
import requests

try:
    import frappe
    from frappe.utils import now_datetime, get_datetime
except ImportError:
    frappe = None
    now_datetime = datetime.now
    get_datetime = lambda x: x if isinstance(x, datetime) else datetime.fromisoformat(str(x))


def _send_followup_message(to_phone: str, text: str) -> bool:
    """Send follow-up text via Meta Graph API if configured."""
    token = os.getenv("META_ACCESS_TOKEN", "").strip()
    phone_number_id = os.getenv("META_PHONE_NUMBER_ID", "").strip()
    if not token or not phone_number_id or not to_phone:
        return False

    clean_phone = "".join(ch for ch in str(to_phone) if ch.isdigit())
    url = f"https://graph.facebook.com/v22.0/{phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": clean_phone,
        "type": "text",
        "text": {"body": text},
    }
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=20)
        return res.status_code in (200, 201)
    except requests.RequestException:
        return False


def _already_followed_up(lead_name: str, marker: str = "[AUTO-FOLLOWUP]") -> bool:
    """Avoid sending duplicate automated follow-ups for the same lead."""
    if not frappe or not lead_name:
        return False
    return bool(
        frappe.db.exists(
            "Comment",
            {
                "reference_doctype": "Lead",
                "reference_name": lead_name,
                "content": ["like", f"%{marker}%"],
            },
        )
    )


def run_scheduled_followups():
    """Frappe cron scheduler job (every 15 mins) for pending WhatsApp leads."""
    if not frappe:
        return

    cutoff_time = now_datetime() - timedelta(hours=24)

    leads = frappe.get_all(
        "Lead",
        filters={
            "source": "WhatsApp",
            "modified": ["<=", cutoff_time],
        },
        fields=["name", "lead_name", "first_name", "mobile_no", "status"],
        limit_page_length=50,
    )

    for lead in leads:
        if lead.get("status") in ("Converted", "Do Not Contact"):
            continue

        phone = (lead.get("mobile_no") or "").strip()
        if not phone:
            continue

        lead_id = lead["name"]
        if _already_followed_up(lead_id):
            continue

        display_name = lead.get("first_name") or lead.get("lead_name") or "नमस्कार"
        followup_text = (
            f"नमस्कार {display_name}, आमच्या मागील मेसेजबाबत तुम्हाला काही प्रश्न किंवा "
            "मदत हवी आहे का? आम्ही मदतीसाठी तयार आहोत!"
        )

        sent = _send_followup_message(phone, followup_text)

        try:
            frappe.get_doc(
                {
                    "doctype": "Comment",
                    "comment_type": "Comment",
                    "reference_doctype": "Lead",
                    "reference_name": lead_id,
                    "content": (
                        f"<b>[AUTO-FOLLOWUP]</b> {'Sent' if sent else 'Logged (Pending/No API)'}: "
                        f"{frappe.utils.escape_html(followup_text)}"
                    ),
                }
            ).insert(ignore_permissions=True)
        except Exception:
            frappe.log_error(
                frappe.get_traceback(),
                "Marketing Automation AI Follow-Up Log Error",
            )
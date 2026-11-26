import json
import os
from pathlib import Path
import requests

try:
    import frappe
except ImportError:
    frappe = None


def _load_knowledge_base() -> str:
    """Read knowledge_base.txt from project root if available."""
    base_dir = Path(__file__).resolve().parent.parent.parent
    kb_path = base_dir / "knowledge_base.txt"
    if kb_path.exists():
        return kb_path.read_text(encoding="utf-8").strip()
    return ""


def _generate_ai_reply(user_message: str, knowledge_base: str) -> str:
    """Generate reply using Gemini API first, with Groq fallback."""
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    groq_key = os.getenv("GROQ_API_KEY", "").strip()

    prompt = (
        "You are a helpful WhatsApp marketing assistant. "
        "Answer clearly, concisely, and politely using the knowledge base below.\n\n"
        f"Knowledge Base:\n{knowledge_base}\n\n"
        f"Customer Message:\n{user_message}"
    )

    if gemini_key:
        try:
            url = (
                "https://generativelanguage.googleapis.com/v1beta/models/"
                f"gemini-2.0-flash:generateContent?key={gemini_key}"
            )
            payload = {"contents": [{"parts": [{"text": prompt}]}]}
            res = requests.post(url, json=payload, timeout=25)
            if res.status_code == 200:
                data = res.json()
                candidates = data.get("candidates") or []
                if candidates:
                    parts = (candidates[0].get("content") or {}).get("parts") or []
                    if parts and parts[0].get("text"):
                        return parts[0]["text"].strip()
        except requests.RequestException:
            pass

    if groq_key:
        try:
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {groq_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.4,
            }
            res = requests.post(url, headers=headers, json=payload, timeout=25)
            if res.status_code == 200:
                content = (
                    (res.json().get("choices") or [{}])[0]
                    .get("message", {})
                    .get("content", "")
                )
                if content:
                    return content.strip()
        except requests.RequestException:
            pass

    return "धन्यवाद! तुमचा मेसेज आम्हाला मिळाला आहे. आमची टीम लवकरच तुमच्याशी संपर्क साधेल."


def _send_whatsapp_via_meta(to_phone: str, message_text: str) -> bool:
    """Send WhatsApp text message via Meta Graph API if configured."""
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
        "text": {"body": message_text},
    }
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=20)
        return res.status_code in (200, 201)
    except requests.RequestException:
        return False


def _sync_crm_lead(sender: str, message_text: str, ai_reply: str) -> None:
    """Create or update Lead in Frappe and log conversation."""
    if not frappe or not sender:
        return

    lead_name = frappe.db.get_value("Lead", {"mobile_no": sender}, "name")
    if not lead_name:
        lead = frappe.get_doc(
            {
                "doctype": "Lead",
                "first_name": sender,
                "mobile_no": sender,
                "source": "WhatsApp",
            }
        )
        lead.insert(ignore_permissions=True)
        lead_name = lead.name

    frappe.get_doc(
        {
            "doctype": "Comment",
            "comment_type": "Comment",
            "reference_doctype": "Lead",
            "reference_name": lead_name,
            "content": (
                f"<b>WhatsApp Incoming:</b> {frappe.utils.escape_html(message_text)}<br>"
                f"<b>AI Reply:</b> {frappe.utils.escape_html(ai_reply)}"
            ),
        }
    ).insert(ignore_permissions=True)


def on_whatsapp_message_insert(doc, method=None):
    """Frappe doc_events hook for WhatsApp Message after_insert."""
    if not frappe:
        return

    msg_type = getattr(doc, "type", None) or getattr(doc, "message_type", None)
    if msg_type and str(msg_type).lower() != "incoming":
        return

    sender = (
        getattr(doc, "from_number", None)
        or getattr(doc, "sender", None)
        or getattr(doc, "mobile_no", None)
        or ""
    ).strip()
    message_text = (
        getattr(doc, "message", None)
        or getattr(doc, "content", None)
        or getattr(doc, "body", None)
        or ""
    ).strip()

    if not message_text:
        return

    knowledge_base = _load_knowledge_base()
    ai_reply = _generate_ai_reply(message_text, knowledge_base)

    try:
        _sync_crm_lead(sender, message_text, ai_reply)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Marketing Automation AI CRM Sync Error")

    sent = _send_whatsapp_via_meta(sender, ai_reply)
    if not sent and frappe.db.exists("DocType", "WhatsApp Message"):
        try:
            out_doc = frappe.get_doc(
                {
                    "doctype": "WhatsApp Message",
                    "type": "Outgoing",
                    "to": sender,
                    "message": ai_reply,
                }
            )
            out_doc.insert(ignore_permissions=True)
        except Exception:
            frappe.log_error(frappe.get_traceback(), "Marketing Automation AI Outgoing Log Error")
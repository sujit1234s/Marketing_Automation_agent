import os
import json
from datetime import datetime, timezone, timedelta
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from dotenv import load_dotenv

load_dotenv()

FRAPPE_URL = os.getenv("FRAPPE_URL", "https://erpnext-rko-pjv.m.frappe.cloud")
FRAPPE_API_KEY = os.getenv("FRAPPE_API_KEY")
FRAPPE_API_SECRET = os.getenv("FRAPPE_API_SECRET")

session = requests.Session()
retries = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[502, 503, 504],
    allowed_methods=["GET", "POST", "PUT"]
)
session.mount("https://", HTTPAdapter(max_retries=retries))
session.headers.update({
    "Authorization": f"token {FRAPPE_API_KEY}:{FRAPPE_API_SECRET}",
    "Content-Type": "application/json",
    "Accept": "application/json"
})


def _normalize_mobile(mobile: str) -> tuple[str, str]:
    raw = str(mobile or "").strip()
    digits = "".join(filter(str.isdigit, raw))
    if not digits:
        return "", ""
    clean_10 = digits[-10:] if len(digits) >= 10 else digits
    formatted = raw if raw.startswith("+") else f"+{digits}"
    return clean_10, formatted


def _split_name(profile_name: str, fallback_suffix: str = "") -> tuple[str, str]:
    cleaned = (profile_name or "").strip()
    if cleaned:
        parts = cleaned.split(" ", 1)
        return parts[0], (parts[1] if len(parts) > 1 else "")
    return "WhatsApp Lead", fallback_suffix


def log_timeline(doctype: str, docname: str, html_content: str) -> bool:
    if not doctype or not docname:
        return False
    payload = {
        "comment_type": "Comment",
        "reference_doctype": doctype,
        "reference_name": docname,
        "content": html_content
    }
    res = session.post(f"{FRAPPE_URL}/api/resource/Comment", json=payload, timeout=20)
    return res.status_code in (200, 201)


def save_or_update_note(title: str, html_content: str) -> str | None:
    for doctype in ["CRM Note", "Note"]:
        url = f"{FRAPPE_URL}/api/resource/{doctype}"
        res = session.get(
            url,
            params={"filters": json.dumps([["title", "=", title]]), "fields": '["name"]'},
            timeout=20
        )
        if res.status_code == 200:
            existing = res.json().get("data", [])
            payload = {"title": title, "content": html_content}
            if existing:
                note_id = existing[0]["name"]
                if session.put(f"{url}/{note_id}", json=payload, timeout=20).status_code == 200:
                    return note_id
            else:
                post_res = session.post(url, json=payload, timeout=20)
                if post_res.status_code in (200, 201):
                    return post_res.json()["data"]["name"]
    return None


def find_or_create_contact(
    first_name: str,
    last_name: str = "",
    mobile: str = "",
    email: str = "",
    lead_doctype: str | None = None,
    lead_name: str | None = None,
) -> tuple[str | None, str]:
    clean_mobile, formatted_mobile = _normalize_mobile(mobile)
    clean_email = (email or "").strip()
    url = f"{FRAPPE_URL}/api/resource/Contact"

    if clean_mobile:
        res = session.get(
            url,
            params={
                "filters": json.dumps([["mobile_no", "like", f"%{clean_mobile}"]]),
                "fields": '["name"]'
            },
            timeout=20
        )
        if res.status_code == 200 and res.json().get("data"):
            return res.json()["data"][0]["name"], "Matched Contact"

    if clean_email:
        res = session.get(
            url,
            params={
                "filters": json.dumps([["email_id", "=", clean_email]]),
                "fields": '["name"]'
            },
            timeout=20
        )
        if res.status_code == 200 and res.json().get("data"):
            return res.json()["data"][0]["name"], "Matched Contact"

    payload = {
        "first_name": (first_name or "WhatsApp").strip(),
        "last_name": (last_name or "").strip(),
        "mobile_no": formatted_mobile,
        "email_id": clean_email,
        "status": "Passive",
    }
    if formatted_mobile:
        payload["phone_nos"] = [{"phone": formatted_mobile, "is_primary_mobile_no": 1}]
    if clean_email:
        payload["email_ids"] = [{"email_id": clean_email, "is_primary": 1}]
    if lead_doctype and lead_name:
        payload["links"] = [{"link_doctype": lead_doctype, "link_name": lead_name}]

    create_res = session.post(url, json=payload, timeout=20)
    if create_res.status_code in (200, 201):
        return create_res.json().get("data", {}).get("name"), "Created Contact"

    if "links" in payload:
        payload.pop("links")
        retry_res = session.post(url, json=payload, timeout=20)
        if retry_res.status_code in (200, 201):
            return retry_res.json().get("data", {}).get("name"), "Created Contact"

    return None, "Contact Failed"


def _link_contact_to_lead(lead_doctype: str, lead_id: str, contact_id: str | None) -> None:
    if not contact_id or not lead_id:
        return
    for fieldname in ("contact", "contact_name"):
        res = session.put(
            f"{FRAPPE_URL}/api/resource/{lead_doctype}/{lead_id}",
            json={fieldname: contact_id},
            timeout=20,
        )
        if res.status_code == 200:
            return


def sync_new_lead(
    first_name: str,
    last_name: str,
    mobile: str,
    email: str,
    raw_enquiry: str,
    clean_reply: str,
    source: str = "Google Business Profile"
) -> str:
    clean_mobile, formatted_mobile = _normalize_mobile(mobile)
    url = f"{FRAPPE_URL}/api/resource/CRM Lead"
    filters = [["mobile_no", "like", f"%{clean_mobile}"]] if clean_mobile else [
        ["first_name", "=", first_name],
        ["last_name", "=", last_name],
    ]

    res = session.get(url, params={"filters": json.dumps(filters), "fields": '["name"]'}, timeout=20)
    timeline_html = (
        f"<b>Parent Enquiry:</b> <i>\"{raw_enquiry}\"</i><br><br>"
        f"<b>Suggested Reply:</b><br>{clean_reply.replace(chr(10), '<br>')}"
    )

    if res.status_code == 200 and res.json().get("data"):
        lead_id = res.json()["data"][0]["name"]
        contact_id, _ = find_or_create_contact(
            first_name=first_name,
            last_name=last_name,
            mobile=formatted_mobile,
            email=email,
            lead_doctype="CRM Lead",
            lead_name=lead_id,
        )
        _link_contact_to_lead("CRM Lead", lead_id, contact_id)
        log_timeline("CRM Lead", lead_id, timeline_html)
        return lead_id

    payload = {
        "first_name": first_name,
        "last_name": last_name,
        "mobile_no": formatted_mobile,
        "email_id": email,
        "status": "New",
        "source": source
    }
    create_res = session.post(url, json=payload, timeout=20)
    if create_res.status_code in (200, 201):
        lead_id = create_res.json().get("data", {}).get("name")
        contact_id, _ = find_or_create_contact(
            first_name=first_name,
            last_name=last_name,
            mobile=formatted_mobile,
            email=email,
            lead_doctype="CRM Lead",
            lead_name=lead_id,
        )
        _link_contact_to_lead("CRM Lead", lead_id, contact_id)
        log_timeline("CRM Lead", lead_id, timeline_html)
        return lead_id
    return None


def get_incoming_whatsapp_messages(limit: int = 10) -> list[dict]:
    url = f"{FRAPPE_URL}/api/resource/WhatsApp Message"
    params = {
        "filters": json.dumps([["type", "=", "Incoming"]]),
        "fields": json.dumps(["name", "from", "message", "profile_name", "creation"]),
        "order_by": "creation desc",
        "limit_page_length": limit,
    }
    res = session.get(url, params=params, timeout=20)
    if res.status_code == 200:
        return res.json().get("data", [])
    return []


def _create_lead_record(
    first_name: str,
    last_name: str,
    full_name: str,
    formatted_mobile: str,
    clean_mobile: str,
) -> tuple[str | None, str | None]:
    """Creates a Lead in Frappe CRM ('CRM Lead') or ERPNext ('Lead') and returns (doctype, lead_id)."""
    candidates = [
        (
            "CRM Lead",
            [
                {
                    "first_name": first_name,
                    "last_name": last_name,
                    "lead_name": full_name,
                    "mobile_no": formatted_mobile,
                    "status": "New",
                    "source": "WhatsApp",
                },
                {
                    "first_name": first_name,
                    "last_name": last_name,
                    "lead_name": full_name,
                    "mobile_no": formatted_mobile,
                    "status": "New",
                },
            ],
        ),
        (
            "Lead",
            [
                {
                    "first_name": first_name,
                    "last_name": last_name,
                    "lead_name": full_name,
                    "mobile_no": formatted_mobile,
                    "status": "Open",
                    "source": "WhatsApp",
                },
                {
                    "first_name": first_name,
                    "last_name": last_name,
                    "lead_name": full_name,
                    "mobile_no": formatted_mobile,
                    "status": "Open",
                },
            ],
        ),
    ]

    for doctype, payloads in candidates:
        url = f"{FRAPPE_URL}/api/resource/{doctype}"
        if clean_mobile:
            check_res = session.get(
                url,
                params={
                    "filters": json.dumps([["mobile_no", "like", f"%{clean_mobile}"]]),
                    "fields": '["name"]'
                },
                timeout=20,
            )
            if check_res.status_code == 200 and check_res.json().get("data"):
                return doctype, check_res.json()["data"][0]["name"]

        for payload in payloads:
            create_res = session.post(url, json=payload, timeout=20)
            if create_res.status_code in (200, 201):
                lead_id = create_res.json().get("data", {}).get("name")
                if lead_id:
                    return doctype, lead_id

    return None, None


def sync_whatsapp_lead(
    mobile: str,
    profile_name: str,
    user_msg: str,
    ai_reply: str = ""
) -> str | None:
    clean_mobile, formatted_mobile = _normalize_mobile(mobile)
    if not clean_mobile:
        return None

    first_name, last_name = _split_name(profile_name, fallback_suffix=clean_mobile)
    full_name = f"{first_name} {last_name}".strip()

    reply_block = (
        f"<br><br><b>🤖 AI Agent Reply:</b><br>{ai_reply.replace(chr(10), '<br>')}"
        if ai_reply else ""
    )
    timeline_html = (
        f"<div style='border-left: 3px solid #25D366; padding-left: 10px;'>"
        f"<b>💬 WhatsApp Message ({formatted_mobile}):</b> <i>\"{user_msg}\"</i>"
        f"{reply_block}"
        f"</div>"
    )

    lead_doctype, lead_id = _create_lead_record(
        first_name=first_name,
        last_name=last_name,
        full_name=full_name,
        formatted_mobile=formatted_mobile,
        clean_mobile=clean_mobile,
    )

    contact_id, _ = find_or_create_contact(
        first_name=first_name,
        last_name=last_name,
        mobile=formatted_mobile,
        lead_doctype=lead_doctype,
        lead_name=lead_id,
    )

    if lead_doctype and lead_id:
        _link_contact_to_lead(lead_doctype, lead_id, contact_id)
        log_timeline(lead_doctype, lead_id, timeline_html)
        return lead_id

    return None


def send_whatsapp_message(to_mobile: str, reply_text: str, lead_id: str | None = None) -> bool:
    url = f"{FRAPPE_URL}/api/resource/WhatsApp Message"
    clean_to = "".join(filter(str.isdigit, str(to_mobile)))

    payload = {
        "type": "Outgoing",
        "to": clean_to,
        "message_type": "Manual",
        "content_type": "text",
        "message": reply_text,
        "whatsapp_account": "Frappe WhatsApp",
    }

    res = session.post(url, json=payload, timeout=20)
    return res.status_code in (200, 201)


def is_within_business_hours() -> bool:
    ist = timezone(timedelta(hours=5, minutes=30))
    now_ist = datetime.now(ist)
    return 9 <= now_ist.hour < 19


def send_whatsapp_template(
    to_mobile: str,
    template_name: str,
    variables: list[str],
    is_marketing: bool = True
) -> bool:
    if is_marketing and not is_within_business_hours():
        return False

    clean_to = "".join(filter(str.isdigit, str(to_mobile)))
    url = f"{FRAPPE_URL}/api/resource/WhatsApp Message"
    frappe_template_id = template_name if template_name.endswith("-en_US") else f"{template_name}-en_US"
    body_params = [{"type": "text", "text": str(v)} for v in variables]
    components = [{"type": "body", "parameters": body_params}] if body_params else []

    payload = {
        "type": "Outgoing",
        "to": clean_to,
        "message_type": "Template",
        "template": frappe_template_id,
        "whatsapp_account": "Frappe WhatsApp",
        "custom_template_data": json.dumps(components),
    }

    res = session.post(url, json=payload, timeout=20)
    return res.status_code in (200, 201)
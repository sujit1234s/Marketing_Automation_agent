import json
import os
import re
from datetime import datetime
from typing import Any
from urllib.parse import quote
from zoneinfo import ZoneInfo

import requests


def _load_env_file() -> None:
    """Loads key=value pairs from a local .env file if present without overriding existing env vars."""
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, val = stripped.split("=", 1)
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = val


_load_env_file()

FRAPPE_URL: str = os.environ.get("FRAPPE_URL", "").rstrip("/")
FRAPPE_API_KEY: str = os.environ.get("FRAPPE_API_KEY", "").strip()
FRAPPE_API_SECRET: str = os.environ.get("FRAPPE_API_SECRET", "").strip()

WHATSAPP_ACCESS_TOKEN: str = os.environ.get("WHATSAPP_ACCESS_TOKEN", "").strip()
WHATSAPP_PHONE_NUMBER_ID: str = os.environ.get("WHATSAPP_PHONE_NUMBER_ID", "").strip()
WHATSAPP_GRAPH_VERSION: str = os.environ.get("WHATSAPP_GRAPH_VERSION", "v21.0").strip()
LOCAL_TZ: str = os.environ.get("LOCAL_TZ", "Asia/Kolkata").strip()

session = requests.Session()
headers: dict[str, str] = {
    "Content-Type": "application/json",
    "Accept": "application/json",
}
if FRAPPE_API_KEY and FRAPPE_API_SECRET:
    headers["Authorization"] = f"token {FRAPPE_API_KEY}:{FRAPPE_API_SECRET}"
session.headers.update(headers)

_ensured_sources: set[str] = set()


def _split_name(full_name: str, fallback_suffix: str = "") -> tuple[str, str]:
    cleaned = re.sub(r"\s+", " ", (full_name or "").strip())
    if not cleaned:
        suffix = fallback_suffix.strip()
        return ("Parent", suffix if suffix else "Inquiry")
    parts = cleaned.split(" ")
    if len(parts) == 1:
        return (parts[0], fallback_suffix.strip() if fallback_suffix else "Lead")
    first_name = parts[0]
    last_name = " ".join(parts[1:])
    if fallback_suffix and fallback_suffix.lower() not in last_name.lower():
        last_name = f"{last_name} {fallback_suffix.strip()}".strip()
    return (first_name, last_name)


def _normalize_phone(phone: str) -> str:
    digits = re.sub(r"\D", "", phone or "")
    if len(digits) == 10:
        return f"91{digits}"
    return digits


def _extract_doc_name(response: requests.Response) -> str | None:
    try:
        data = response.json()
    except ValueError:
        return None
    doc = data.get("data")
    if isinstance(doc, dict):
        name = doc.get("name")
        if name:
            return str(name)
    return None


def _ensure_lead_source(source_name: str) -> None:
    """Creates a Lead Source master record if it doesn't exist yet."""
    if not FRAPPE_URL or not source_name or source_name in _ensured_sources:
        return
    try:
        url = f"{FRAPPE_URL}/api/resource/Lead Source"
        res = session.get(
            url,
            params={
                "filters": json.dumps([["name", "=", source_name]]),
                "fields": json.dumps(["name"]),
                "limit_page_length": 1,
            },
            timeout=15,
        )
        if res.status_code == 200 and (res.json().get("data") or []):
            _ensured_sources.add(source_name)
            return

        create_res = session.post(
            url,
            json={"source_name": source_name},
            timeout=15,
        )
        if create_res.status_code in (200, 201, 409):
            _ensured_sources.add(source_name)
    except requests.RequestException:
        pass


def find_or_create_contact(
    first_name: str,
    last_name: str = "",
    phone: str = "",
    email: str = "",
    lead_doctype: str | None = None,
    lead_name: str | None = None,
) -> tuple[str | None, bool]:
    """Finds an existing Contact by email/phone/name or creates one and links it to the Lead."""
    if not FRAPPE_URL:
        return (None, False)

    full_name = f"{first_name} {last_name}".strip()
    contact_url = f"{FRAPPE_URL}/api/resource/Contact"
    existing_name: str | None = None

    try:
        for filters in (
            [["email_id", "=", email]] if email else [],
            [["mobile_no", "=", phone]] if phone else [],
            [["first_name", "=", first_name], ["last_name", "=", last_name]]
            if last_name
            else [["first_name", "=", first_name]],
        ):
            if not filters:
                continue
            res = session.get(
                contact_url,
                params={
                    "filters": json.dumps(filters),
                    "fields": json.dumps(["name"]),
                    "limit_page_length": 1,
                },
                timeout=15,
            )
            if res.status_code == 200:
                rows = res.json().get("data") or []
                if rows and rows[0].get("name"):
                    existing_name = str(rows[0]["name"])
                    break

        if existing_name:
            if lead_doctype and lead_name:
                _link_contact_to_lead(lead_doctype, lead_name, existing_name)
            return (existing_name, False)

        payload: dict[str, Any] = {
            "first_name": first_name,
            "last_name": last_name or "Lead",
        }
        if full_name:
            payload["full_name"] = full_name
        if email:
            payload["email_ids"] = [{"email_id": email, "is_primary": 1}]
        if phone:
            payload["phone_nos"] = [{"phone": phone, "is_primary_mobile_no": 1}]
        if lead_doctype and lead_name:
            payload["links"] = [
                {"link_doctype": lead_doctype, "link_name": lead_name}
            ]

        create_res = session.post(contact_url, json=payload, timeout=15)
        if create_res.status_code in (200, 201):
            created_id = _extract_doc_name(create_res)
            if created_id and lead_doctype and lead_name:
                _link_contact_to_lead(lead_doctype, lead_name, created_id)
            return (created_id, True)
    except requests.RequestException as exc:
        print(f"⚠️ Contact lookup/creation error: {exc}")

    return (None, False)


def _link_contact_to_lead(lead_doctype: str, lead_name: str, contact_id: str | None) -> None:
    """Ensures a Contact <-> Lead link exists on the Contact if possible."""
    if not FRAPPE_URL or not contact_id or not lead_doctype or not lead_name:
        return
    try:
        url = f"{FRAPPE_URL}/api/resource/Contact/{quote(contact_id, safe='')}"
        res = session.get(url, timeout=15)
        if res.status_code != 200:
            return
        doc = (res.json().get("data") or {})
        links = list(doc.get("links") or [])
        already_linked = any(
            row.get("link_doctype") == lead_doctype and row.get("link_name") == lead_name
            for row in links
        )
        if not already_linked:
            links.append({"link_doctype": lead_doctype, "link_name": lead_name})
            session.put(url, json={"links": links}, timeout=15)
    except requests.RequestException:
        pass


def log_timeline(doctype: str, docname: str, content_html: str) -> bool:
    """Logs a Comment entry onto a Frappe document timeline."""
    if not FRAPPE_URL or not doctype or not docname:
        return False

    payload = {
        "doctype": "Comment",
        "comment_type": "Comment",
        "reference_doctype": doctype,
        "reference_name": docname,
        "content": content_html,
    }
    try:
        res = session.post(f"{FRAPPE_URL}/api/resource/Comment", json=payload, timeout=15)
        if res.status_code in (200, 201):
            return True

        # Fallback to Frappe's add_comment method if direct Comment insert is restricted
        alt = session.post(
            f"{FRAPPE_URL}/api/method/frappe.desk.form.utils.add_comment",
            json={
                "reference_doctype": doctype,
                "reference_name": docname,
                "content": content_html,
                "comment_email": FRAPPE_API_KEY or "Administrator",
                "comment_by": "Nestio AI Agent",
            },
            timeout=15,
        )
        return alt.status_code in (200, 201)
    except requests.RequestException as exc:
        print(f"⚠️ Failed to log timeline on {doctype} {docname}: {exc}")
        return False


def _find_or_create_social_lead(
    source_label: str,
    full_name: str,
    first_name: str,
    last_name: str,
    timeline_html: str,
    phone: str = "",
) -> str | None:
    if not FRAPPE_URL:
        print("⚠️ FRAPPE_URL is not set; skipping CRM sync.")
        return None

    _ensure_lead_source(source_label)

    for doctype in ("CRM Lead", "Lead"):
        url = f"{FRAPPE_URL}/api/resource/{doctype}"
        filter_candidates: list[list[Any]] = []
        if phone:
            filter_candidates.append(["mobile_no", "=", phone])
        filter_candidates.append(["lead_name", "=", full_name])
        filter_candidates.append([["first_name", "=", first_name], ["last_name", "=", last_name]])

        try:
            for flt in filter_candidates:
                filters = flt if (isinstance(flt, list) and flt and isinstance(flt[0], list)) else [flt]
                check = session.get(
                    url,
                    params={
                        "filters": json.dumps(filters),
                        "fields": json.dumps(["name"]),
                        "limit_page_length": 1,
                    },
                    timeout=20,
                )
                if check.status_code == 200:
                    rows = check.json().get("data") or []
                    if rows and rows[0].get("name"):
                        lead_id = str(rows[0]["name"])
                        contact_id, _ = find_or_create_contact(
                            first_name=first_name,
                            last_name=last_name,
                            phone=phone,
                            lead_doctype=doctype,
                            lead_name=lead_id,
                        )
                        _link_contact_to_lead(doctype, lead_id, contact_id)
                        log_timeline(doctype, lead_id, timeline_html)
                        return lead_id

            base_fields: dict[str, Any] = {
                "first_name": first_name,
                "last_name": last_name,
                "lead_name": full_name,
            }
            if phone:
                base_fields["mobile_no"] = phone

            payloads = [
                {
                    **base_fields,
                    "status": "New" if doctype == "CRM Lead" else "Open",
                    "source": source_label,
                },
                base_fields,
            ]

            for payload in payloads:
                res = session.post(url, json=payload, timeout=20)
                if res.status_code in (200, 201):
                    lead_id = _extract_doc_name(res)
                    if lead_id:
                        contact_id, _ = find_or_create_contact(
                            first_name=first_name,
                            last_name=last_name,
                            phone=phone,
                            lead_doctype=doctype,
                            lead_name=lead_id,
                        )
                        _link_contact_to_lead(doctype, lead_id, contact_id)
                        log_timeline(doctype, lead_id, timeline_html)
                        return lead_id
                else:
                    print(f"⚠️ {doctype} POST failed ({res.status_code}): {res.text}")
        except requests.RequestException as exc:
            print(f"⚠️ Frappe request failed for {doctype}: {exc}")

    return None


def sync_linkedin_lead(
    profile_name: str,
    linkedin_url: str,
    raw_text: str,
    post_context: str,
    ai_reply: str,
    intent: str = "admission_inquiry",
) -> str | None:
    first_name, last_name = _split_name(profile_name, fallback_suffix="(LinkedIn)")
    full_name = f"{first_name} {last_name}".strip()
    formatted_reply = ai_reply.replace("\n", "<br>")
    profile_display = (
        f"<a href='{linkedin_url}'>{linkedin_url}</a>" if linkedin_url else full_name
    )
    timeline_html = (
        f"<div style='border-left: 3px solid #0A66C2; padding-left: 10px;'>"
        f"<b>💼 LinkedIn ({intent})</b> — {profile_display}<br>"
        f"<b>Context:</b> <i>{post_context}</i><br>"
        f'<b>Incoming Comment/Message:</b> <i>"{raw_text}"</i><br><br>'
        f"<b>🤖 Drafted Reply:</b><br>{formatted_reply}"
        f"</div>"
    )
    return _find_or_create_social_lead(
        source_label="LinkedIn",
        full_name=full_name,
        first_name=first_name,
        last_name=last_name,
        timeline_html=timeline_html,
    )


def sync_facebook_lead(
    profile_name: str,
    facebook_url: str,
    raw_text: str,
    post_context: str,
    ai_reply: str,
    intent: str = "admission_inquiry",
) -> str | None:
    first_name, last_name = _split_name(profile_name, fallback_suffix="(Facebook)")
    full_name = f"{first_name} {last_name}".strip()
    formatted_reply = ai_reply.replace("\n", "<br>")
    profile_display = (
        f"<a href='{facebook_url}'>{facebook_url}</a>" if facebook_url else full_name
    )
    timeline_html = (
        f"<div style='border-left: 3px solid #1877F2; padding-left: 10px;'>"
        f"<b>📘 Facebook ({intent})</b> — {profile_display}<br>"
        f"<b>Context:</b> <i>{post_context}</i><br>"
        f'<b>Incoming Comment/Message:</b> <i>"{raw_text}"</i><br><br>'
        f"<b>🤖 Drafted Reply:</b><br>{formatted_reply}"
        f"</div>"
    )
    return _find_or_create_social_lead(
        source_label="Facebook",
        full_name=full_name,
        first_name=first_name,
        last_name=last_name,
        timeline_html=timeline_html,
    )


def sync_whatsapp_lead(
    sender_name: str,
    phone: str,
    raw_text: str,
    ai_reply: str = "",
    intent: str = "admission_inquiry",
) -> str | None:
    normalized_phone = _normalize_phone(phone)
    first_name, last_name = _split_name(sender_name, fallback_suffix="(WhatsApp)")
    full_name = f"{first_name} {last_name}".strip()
    formatted_reply = (ai_reply or "").replace("\n", "<br>")
    reply_block = f"<br><br><b>🤖 Drafted Reply:</b><br>{formatted_reply}" if formatted_reply else ""
    timeline_html = (
        f"<div style='border-left: 3px solid #25D366; padding-left: 10px;'>"
        f"<b>💬 WhatsApp ({intent})</b> — {full_name} ({normalized_phone or phone})<br>"
        f'<b>Incoming Message:</b> <i>"{raw_text}"</i>'
        f"{reply_block}"
        f"</div>"
    )
    return _find_or_create_social_lead(
        source_label="WhatsApp",
        full_name=full_name,
        first_name=first_name,
        last_name=last_name,
        timeline_html=timeline_html,
        phone=normalized_phone or phone,
    )


def is_within_business_hours(now: datetime | None = None) -> bool:
    """Checks Mon-Sat, 10:00 AM - 4:00 PM in the configured campus timezone."""
    try:
        tz = ZoneInfo(LOCAL_TZ)
    except Exception:
        tz = ZoneInfo("Asia/Kolkata")

    current = now.astimezone(tz) if now else datetime.now(tz)
    # weekday(): Monday=0 ... Saturday=5, Sunday=6
    if current.weekday() > 5:
        return False
    start = current.replace(hour=10, minute=0, second=0, microsecond=0)
    end = current.replace(hour=16, minute=0, second=0, microsecond=0)
    return start <= current <= end


def send_whatsapp_message(to_phone: str, text_body: str) -> dict[str, Any]:
    """Sends a free-form WhatsApp Cloud API text message within the 24-hour session window."""
    recipient = _normalize_phone(to_phone)
    if not WHATSAPP_ACCESS_TOKEN or not WHATSAPP_PHONE_NUMBER_ID:
        return {
            "ok": False,
            "error": "Missing WHATSAPP_ACCESS_TOKEN or WHATSAPP_PHONE_NUMBER_ID",
            "recipient": recipient,
        }

    url = f"https://graph.facebook.com/{WHATSAPP_GRAPH_VERSION}/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": recipient,
        "type": "text",
        "text": {"preview_url": False, "body": text_body},
    }
    try:
        res = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=20,
        )
        data = res.json() if res.content else {}
        return {
            "ok": res.status_code in (200, 201),
            "status_code": res.status_code,
            "response": data,
        }
    except requests.RequestException as exc:
        return {"ok": False, "error": str(exc)}


def send_whatsapp_template(
    to_phone: str,
    template_name: str,
    language_code: str = "en",
    components: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Sends an approved WhatsApp Cloud API template message."""
    recipient = _normalize_phone(to_phone)
    if not WHATSAPP_ACCESS_TOKEN or not WHATSAPP_PHONE_NUMBER_ID:
        return {
            "ok": False,
            "error": "Missing WHATSAPP_ACCESS_TOKEN or WHATSAPP_PHONE_NUMBER_ID",
            "recipient": recipient,
        }

    url = f"https://graph.facebook.com/{WHATSAPP_GRAPH_VERSION}/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    template_obj: dict[str, Any] = {
        "name": template_name,
        "language": {"code": language_code},
    }
    if components:
        template_obj["components"] = components

    payload = {
        "messaging_product": "whatsapp",
        "to": recipient,
        "type": "template",
        "template": template_obj,
    }
    try:
        res = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=20,
        )
        data = res.json() if res.content else {}
        return {
            "ok": res.status_code in (200, 201),
            "status_code": res.status_code,
            "response": data,
        }
    except requests.RequestException as exc:
        return {"ok": False, "error": str(exc)}
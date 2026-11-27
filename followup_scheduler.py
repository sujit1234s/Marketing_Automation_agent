import os
import json
import time
from datetime import datetime
from frappe_client import session, FRAPPE_URL, send_whatsapp_template, log_timeline

SCHOOL_NAME = "Nestio Preschools"
DEFAULT_PROGRAM = "Nursery & Preschool Admissions"
STATE_FILE = os.path.join(os.path.dirname(__file__), "sent_followups.json")


def load_sent_state() -> dict[str, list[str]]:
    """Loads previously sent templates per lead from disk so restarts never duplicate messages."""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Could not read {STATE_FILE}: {e}")
    return {}


def save_sent_state(state: dict[str, list[str]]) -> None:
    """Persists sent template history to disk."""
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        print(f"⚠️ Could not write {STATE_FILE}: {e}")


def get_active_leads() -> list[dict]:
    """Fetches CRM Leads that haven't converted, closed, or opted out."""
    url = f"{FRAPPE_URL}/api/resource/CRM Lead"
    params = {
        "filters": json.dumps([
            ["status", "not in", ["Converted", "Do Not Contact", "Lost", "Junk"]]
        ]),
        "fields": json.dumps([
            "name", "lead_name", "first_name", "mobile_no", "status", "creation"
        ]),
        "limit_page_length": 200,
    }
    res = session.get(url, params=params, timeout=20)
    if res.status_code == 200:
        return res.json().get("data", [])
    print(f"⚠️ Failed to fetch CRM Leads ({res.status_code}): {res.text}")
    return []


def determine_next_followup(
    hours_since_creation: float,
    status: str,
    already_sent: set[str],
) -> tuple[str | None, list[str], bool]:
    """
    Determines the exact next template due in the 14-day sequence without narrow time windows.
    Returns: (template_name, variables, is_marketing)
    """
    # 1. Instant Welcome (Utility — within first 15 minutes of creation)
    if hours_since_creation <= 0.25 and status in ["Open", "New"]:
        if "followup_instant_welcome" not in already_sent:
            return "followup_instant_welcome", [], False

    # 2. Cold Lead Re-engagement (30+ days / 720+ hours)
    if hours_since_creation >= 720 and status == "Cold":
        if "followup_reengage_cold" not in already_sent:
            return "followup_reengage_cold", [], True

    # 14-Day Nurturing Sequence for Active Leads (checks from latest milestone backwards)
    if status in ["Open", "New"]:
        if hours_since_creation >= 336 and "followup_day14_final" not in already_sent:
            return "followup_day14_final", [], True

        if hours_since_creation >= 168 and "followup_day7_proof" not in already_sent:
            return "followup_day7_proof", [], True

        if hours_since_creation >= 72 and "followup_day3_value" not in already_sent:
            return "followup_day3_value", [], True

        if hours_since_creation >= 24 and "followup_day1_gentle" not in already_sent:
            return "followup_day1_gentle", [], True

    return None, [], True


def build_variables(template_name: str, parent_name: str, program: str) -> list[str]:
    """Maps dynamic lead values to the exact placeholder order of each template."""
    if template_name == "followup_instant_welcome":
        return [parent_name, SCHOOL_NAME, program]
    if template_name == "followup_day1_gentle":
        return [parent_name, program, SCHOOL_NAME]
    if template_name == "followup_day3_value":
        return [
            parent_name,
            SCHOOL_NAME,
            "Play-based NEP Curriculum",
            "CCTV-monitored safe campus",
            "Experienced educators",
        ]
    if template_name == "followup_day7_proof":
        return [
            parent_name,
            "Our daughter loves going to Nestio every morning!",
            "Priya Kulkarni",
            SCHOOL_NAME,
        ]
    if template_name == "followup_day14_final":
        return [parent_name, SCHOOL_NAME]
    if template_name == "followup_reengage_cold":
        return [
            parent_name,
            SCHOOL_NAME,
            "New academic term seats open",
            "Weekend activity workshop",
        ]
    return []


def process_scheduled_followups():
    now = datetime.now()
    leads = get_active_leads()
    sent_state = load_sent_state()
    state_changed = False

    for lead in leads:
        lead_id = lead["name"]
        mobile = (lead.get("mobile_no") or "").strip()
        if not mobile:
            continue

        parent_name = (lead.get("first_name") or lead.get("lead_name") or "Parent").strip()
        status = lead.get("status", "Open")
        created_at = datetime.fromisoformat(lead["creation"].split(".")[0])
        hours_since_creation = (now - created_at).total_seconds() / 3600.0

        already_sent = set(sent_state.get(lead_id, []))
        template_to_send, _, is_marketing = determine_next_followup(
            hours_since_creation, status, already_sent
        )

        if not template_to_send:
            continue

        variables = build_variables(template_to_send, parent_name, DEFAULT_PROGRAM)
        sent = send_whatsapp_template(
            to_mobile=mobile,
            template_name=template_to_send,
            variables=variables,
            is_marketing=is_marketing,
            reference_doctype="CRM Lead",
            reference_name=lead_id,
        )

        if sent:
            sent_state.setdefault(lead_id, []).append(template_to_send)
            state_changed = True
            log_timeline(
                "CRM Lead",
                lead_id,
                f"📤 <b>Automated Follow-Up Sent:</b> <code>{template_to_send}</code>",
            )
            print(f"✅ Sent {template_to_send} to {parent_name} ({mobile})")

    if state_changed:
        save_sent_state(sent_state)


if __name__ == "__main__":
    print("📅 Nestio Automated 14-Day Follow-Up Scheduler Running (Checking every 15 mins)...")
    while True:
        try:
            process_scheduled_followups()
        except KeyboardInterrupt:
            print("\n🛑 Follow-Up Scheduler stopped.")
            break
        except Exception as e:
            print(f"⚠️ Scheduler Error: {e}")
        time.sleep(900) 
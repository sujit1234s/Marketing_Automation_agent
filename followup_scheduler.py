import json
import time
from datetime import datetime
from frappe_client import session, FRAPPE_URL, send_whatsapp_template, log_timeline

SCHOOL_NAME = "Nestio Preschools"
DEFAULT_PROGRAM = "Nursery & Preschool Admissions"

# Tracks sent campaigns in memory during the current run: {(lead_id, template_name)}
SENT_CAMPAIGNS: set[tuple[str, str]] = set()


def get_active_leads() -> list[dict]:
    """Fetches Leads that haven't converted, closed, or been marked Do Not Contact."""
    url = f"{FRAPPE_URL}/api/resource/Lead"
    params = {
        "filters": json.dumps([
            ["status", "not in", ["Converted", "Do Not Contact", "Lost"]]
        ]),
        "fields": json.dumps([
            "name", "lead_name", "first_name", "mobile_no", "status", "creation"
        ]),
        "limit_page_length": 100,
    }
    res = session.get(url, params=params, timeout=20)
    if res.status_code == 200:
        return res.json().get("data", [])
    print(f"⚠️ Failed to fetch leads ({res.status_code}): {res.text}")
    return []


def process_scheduled_followups():
    now = datetime.now()
    leads = get_active_leads()

    for lead in leads:
        lead_id = lead["name"]
        mobile = (lead.get("mobile_no") or "").strip()
        if not mobile:
            continue

        parent_name = lead.get("first_name") or lead.get("lead_name") or "Parent"
        status = lead.get("status", "Open")
        created_at = datetime.fromisoformat(lead["creation"].split(".")[0])
        hours_since_creation = (now - created_at).total_seconds() / 3600.0

        template_to_send = None
        variables: list[str] = []
        is_marketing = True

        # 1. Instant Follow-Up (Utility — within ~9 minutes of creation for new/open leads)
        if hours_since_creation <= 0.15 and status in ["Open", "New"]:
            template_to_send = "followup_instant_welcome"
            variables = [parent_name, SCHOOL_NAME, DEFAULT_PROGRAM]
            is_marketing = False

        # 2. Day 1 Follow-Up (Marketing — 24h to 26h after creation)
        elif 24 <= hours_since_creation < 26 and status in ["Open", "New"]:
            template_to_send = "followup_day1_gentle"
            variables = [parent_name, DEFAULT_PROGRAM, SCHOOL_NAME]

        # 3. Day 3 Follow-Up (Marketing — 72h to 74h after creation)
        elif 72 <= hours_since_creation < 74 and status in ["Open", "New"]:
            template_to_send = "followup_day3_value"
            variables = [
                parent_name,
                SCHOOL_NAME,
                "Play-based NEP Curriculum",
                "CCTV-monitored safe campus",
                "Experienced educators",
            ]

        # 4. Day 7 Follow-Up (Marketing — 168h to 170h after creation)
        elif 168 <= hours_since_creation < 170 and status in ["Open", "New"]:
            template_to_send = "followup_day7_proof"
            variables = [
                parent_name,
                "Our daughter loves going to Nestio every morning!",
                "Priya Kulkarni",
                SCHOOL_NAME,
            ]

        # 5. Day 14 Follow-Up (Marketing — 336h to 338h after creation)
        elif 336 <= hours_since_creation < 338 and status in ["Open", "New"]:
            template_to_send = "followup_day14_final"
            variables = [parent_name, SCHOOL_NAME]

        # 8. Re-engagement Cold Lead (Marketing — 30+ days / 720+ hours)
        elif hours_since_creation >= 720 and status == "Cold":
            template_to_send = "followup_reengage_cold"
            variables = [
                parent_name,
                SCHOOL_NAME,
                "New academic term seats open",
                "Weekend activity workshop",
            ]

        if template_to_send and (lead_id, template_to_send) not in SENT_CAMPAIGNS:
            sent = send_whatsapp_template(
                to_mobile=mobile,
                template_name=template_to_send,
                variables=variables,
                is_marketing=is_marketing,
            )
            if sent:
                SENT_CAMPAIGNS.add((lead_id, template_to_send))
                log_timeline(
                    "Lead",
                    lead_id,
                    f"📤 <b>Automated Follow-Up Sent:</b> <code>{template_to_send}</code>",
                )
                print(f"✅ Sent {template_to_send} to {parent_name} ({mobile})")


if __name__ == "__main__":
    print("📅 Nestio Automated Follow-Up Scheduler Running (Checking every 15 mins)...")
    while True:
        try:
            process_scheduled_followups()
        except KeyboardInterrupt:
            print("\n🛑 Follow-Up Scheduler stopped.")
            break
        except Exception as e:
            print(f"⚠️ Scheduler Error: {e}")
        time.sleep(900)  # 15 minutes
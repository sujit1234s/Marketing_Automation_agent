import os
import time
from gemini_client import ask_ai
from frappe_client import (
    get_incoming_whatsapp_messages,
    sync_whatsapp_lead,
    send_whatsapp_message,
)

# ==============================================================================
# CONTROL SWITCH:
# True  -> Live mode: Reads incoming WhatsApp messages, updates CRM & sends reply
# False -> Dry-run mode: Prints AI reply in PyCharm Terminal only (no WhatsApp sent)
# ==============================================================================
SYNC_TO_CRM = True

PROCESSED_IDS: set[str] = set()


def load_knowledge_base() -> str:
    kb_path = os.path.join(os.path.dirname(__file__), "nestio_knowledge_base.txt")
    if os.path.exists(kb_path):
        with open(kb_path, "r", encoding="utf-8") as f:
            return f.read()
    return (
        "Nestio Preschools (Pimple Saudagar, Pune — by Space EC India Foundation). "
        "Programs: Playgroup (1.5-2.5 yrs), Nursery (2.5-3.5 yrs), Junior KG (3.5-4.5 yrs), Senior KG (4.5-5.5 yrs). "
        "Campus Tours: Mon-Sat, 10 AM to 4 PM."
    )


def generate_whatsapp_reply(parent_name: str, user_message: str, kb_context: str) -> str:
    prompt = f"""
You are the 24x7 WhatsApp Admissions Assistant for Nestio Preschools (Pimple Saudagar, Pune), operated by Space EC India Foundation.

STRICT RULES:
Language Match: Reply in the EXACT SAME language and script used by the parent (English, Marathi, Hindi, or Hinglish).
Format: Keep it warm, polite, and concise (under 75 words) suitable for mobile WhatsApp reading.
Accuracy: Answer strictly using the Knowledge Base below. Never guess exact rupee fees; invite them for a Campus Tour for the detailed fee sheet.
Conversion Goal: Always end with a friendly next step (asking their child's age or offering to book a Campus Visit).
Output ONLY the final WhatsApp message text—no quotes, headers, or notes.

KNOWLEDGE BASE:
{kb_context}

Parent Name: {parent_name or 'Parent'}
Parent Message: "{user_message}"
"""
    return ask_ai(prompt)


def handle_single_whatsapp_message(msg: dict, kb_context: str):
    global SYNC_TO_CRM

    sender_mobile = msg.get("from", "")
    user_text = (msg.get("message") or "").strip()
    profile_name = msg.get("profile_name") or ""

    if not sender_mobile or not user_text:
        return

    print("\n" + "=" * 65)
    print(f"📩 INCOMING WHATSAPP — {profile_name or sender_mobile} ({sender_mobile})")
    print("=" * 65)
    print(f"📥 Parent Query:\n \"{user_text}\"\n")

    # Opt-Out Compliance (STOP / NO / UNSUBSCRIBE)
    if user_text.upper() in {"STOP", "NO", "UNSUBSCRIBE"}:
        optout_reply = (
            "You have been unsubscribed from Nestio Preschools WhatsApp updates. "
            "Reply START anytime to re-subscribe. Thank you!"
        )
        print(f"🛑 Opt-Out Triggered -> {optout_reply}")
        if SYNC_TO_CRM:
            send_whatsapp_message(sender_mobile, optout_reply)
        return

    # Generate Multilingual RAG Reply
    ai_reply = generate_whatsapp_reply(profile_name, user_text, kb_context)
    print(f"🤖 AI Agent Reply:\n{ai_reply}\n")

    if SYNC_TO_CRM:
        lead_id = sync_whatsapp_lead(sender_mobile, profile_name, user_text, ai_reply)
        sent = send_whatsapp_message(sender_mobile, ai_reply, lead_id)
        if sent:
            print(f"📌 CRM & WhatsApp Sync -> Lead: {lead_id} | Reply Dispatched ✅")
    print("=" * 65)


def run_whatsapp_agent(poll_interval: int = 5):
    print("🚀 Nestio WhatsApp Chat AI Agent (Pillar 2) Running...")
    print(f"⚙️ SYNC_TO_CRM = {SYNC_TO_CRM} | Polling Frappe every {poll_interval}s (Press Ctrl+C to stop)\n")
    kb_context = load_knowledge_base()

    # Skip older existing messages at startup so old chats aren't re-replied
    for old_msg in get_incoming_whatsapp_messages(limit=20):
        PROCESSED_IDS.add(old_msg["name"])

    while True:
        try:
            recent_msgs = get_incoming_whatsapp_messages(limit=10)
            for msg in reversed(recent_msgs):
                msg_id = msg["name"]
                if msg_id not in PROCESSED_IDS:
                    PROCESSED_IDS.add(msg_id)
                    handle_single_whatsapp_message(msg, kb_context)
        except KeyboardInterrupt:
            print("\n🛑 WhatsApp Agent stopped.")
            break
        except Exception as e:
            print(f"⚠️ Polling Error: {e}")

        time.sleep(poll_interval)


if __name__ == "__main__":
    kb = load_knowledge_base()

    # 1. Dry-run verification (CRM & WhatsApp sending off so you can verify output first)
    SYNC_TO_CRM = False
    test_sample = {
        "name": "TEST-001",
        "from": "919850684018",
        "profile_name": "Sujit Sawant",
        "message": "नमस्कार, माझ्या ३ वर्षांच्या मुलासाठी नर्सरी ऍडमिशन आणि फी बद्दल माहिती हवी आहे.",
    }
    handle_single_whatsapp_message(test_sample, kb)

    # 2. Live Frappe WhatsApp Polling (comment out the 2 lines below if you only want dry-run)
    SYNC_TO_CRM = True
    run_whatsapp_agent(poll_interval=5)
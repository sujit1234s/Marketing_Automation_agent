from gemini_client import ask_ai
from frappe_client import (
    save_or_update_note,
    find_or_create_contact,
    log_timeline,
    sync_new_lead
)

# ==============================================================================
# CONTROL SWITCH:
# True  -> Outputs appear in BOTH PyCharm Terminal AND Frappe CRM UI
# False -> Outputs appear ONLY in PyCharm Terminal
# ==============================================================================
SYNC_TO_CRM = True


# 1. Local SEO Keyword Discovery
def capability_1_seo_keywords(business: str, location: str, programs: list[str]):
    prompt = (
        f"As a Local SEO Strategist for '{business}' in '{location}' offering {', '.join(programs)}, "
        f"list the top 10 high-intent local SEO keywords under: 1. Primary Keywords, 2. Program Keywords, 3. Parent-Intent Keywords. "
        f"Output ONLY the clean list."
    )
    output = ask_ai(prompt)
    print("\n" + "=" * 65 + "\n🔍 1. LOCAL SEO KEYWORDS\n" + "=" * 65 + f"\n{output}")
    if SYNC_TO_CRM:
        note_id = save_or_update_note("1. GBP Local SEO Keywords — Nestio Preschools", output.replace("\n", "<br>"))
        print(f"📌 CRM Sync -> Notes: {note_id}")


# 2. Rewrite SEO-Optimized GBP Content, Description & Services
def capability_2_optimize_gbp_content(business: str, location: str, raw_desc: str, keywords: str):
    prompt = (
        f"Rewrite the Google Business Profile 'About Us' description (under 750 chars) and 3 Service descriptions "
        f"(Playgroup, Nursery, Daycare) for '{business}' in '{location}'. Raw text: '{raw_desc}'. "
        f"Include keywords: {keywords}. Output ONLY the clean ready-to-paste copy."
    )
    output = ask_ai(prompt)
    print("\n" + "=" * 65 + "\n✍️ 2. SEO-OPTIMIZED GBP PROFILE & SERVICES\n" + "=" * 65 + f"\n{output}")
    if SYNC_TO_CRM:
        note_id = save_or_update_note("2. GBP SEO Profile & Services — Nestio Preschools", output.replace("\n", "<br>"))
        print(f"📌 CRM Sync -> Notes: {note_id}")


# 3. Event-Driven Customer Feedback / Review Handler (Responds ONLY when customer interacts)
def handle_customer_feedback_event(
    customer_name: str,
    mobile: str,
    email: str,
    feedback_text: str,
    rating: int | None = None
):
    """
    STRICT RULE:
    - Triggers ONLY when a customer actively submits a review, feedback, or question.
    - Does nothing if feedback_text is empty (zero unsolicited messages to silent contacts).
    """
    if not feedback_text or not feedback_text.strip():
        print(f"\n⏸️ No active interaction from {customer_name}. Skipping (Zero outbound spam).")
        return

    rating_label = f" ({rating}/5 ★)" if rating else ""
    print("\n" + "=" * 65)
    print(f"💬 ACTIVE CUSTOMER INTERACTION — {customer_name}{rating_label}")
    print("=" * 65)
    print(f"📥 Customer Input:\n   \"{feedback_text}\"\n")

    prompt = (
        f"You are the Google Business Profile AI Agent for Nestio Preschools (Pimple Saudagar, Pune). "
        f"A parent named '{customer_name}' just left the following feedback/message: '{feedback_text}'.\n"
        f"Write a warm, empathetic, local-SEO optimized reply directly addressing what they said. "
        f"Naturally include 'best preschool in Pimple Saudagar' and 'early childhood learning' where appropriate. "
        f"Output ONLY the ready-to-send reply message—no notes, headers, or extra commentary."
    )
    reply = ask_ai(prompt)
    print(f"✉️ Ready-to-Send Reply:\n{reply}\n")

    if SYNC_TO_CRM:
        parts = customer_name.strip().split(" ", 1)
        first_name = parts[0]
        last_name = parts[1] if len(parts) > 1 else "(Parent)"

        contact_id, status_msg = find_or_create_contact(first_name, last_name, mobile, email)
        if contact_id:
            header = f"⭐ Google Review{rating_label}" if rating else "💬 Customer Feedback / Query"
            timeline_html = (
                f"<div style='border-left: 3px solid #16a34a; padding-left: 10px;'>"
                f"<b>{header}:</b> <i>\"{feedback_text}\"</i><br><br>"
                f"<b>Suggested Reply:</b><br>{reply.replace(chr(10), '<br>')}"
                f"</div>"
            )
            log_timeline("Contact", contact_id, timeline_html)
            print(f"📌 CRM Sync -> {status_msg} (Timeline updated)")
    print("=" * 65)


# 4. SEO-Powered GBP Update Post
def capability_4_seo_gbp_post(topic: str, location: str = "Pimple Saudagar, Pune"):
    prompt = (
        f"Create an engaging, local-SEO optimized Google Business Profile post (max 120 words) for Nestio Preschools "
        f"in {location}. Topic: '{topic}'. Include local hashtags and a Call-to-Action to book a campus tour. "
        f"Output ONLY the post copy."
    )
    post = ask_ai(prompt)
    print("\n" + "=" * 65 + "\n📢 SEO-POWERED GBP POST\n" + "=" * 65 + f"\n{post}")
    if SYNC_TO_CRM:
        note_id = save_or_update_note("3. GBP Weekly SEO Post — Admissions 2026-27", post.replace("\n", "<br>"))
        print(f"📌 CRM Sync -> Notes: {note_id}")


# 5. New Prospect Enquiry -> Clean Parent Reply -> CRM Lead
def handle_new_google_enquiry(first_name: str, last_name: str, mobile: str, email: str, enquiry: str):
    if not enquiry or not enquiry.strip():
        return

    prompt = (
        f"You are an Admissions Counselor at Nestio Preschools, Pimple Saudagar, Pune. Write a warm, ready-to-send reply "
        f"to parent '{first_name}' answering: '{enquiry}'. Output ONLY the final message (no scores or notes). "
        f"Sign-off: 'Warm regards, Admissions Team - Nestio Preschools'"
    )
    clean_reply = ask_ai(prompt)
    print("\n" + "=" * 65 + f"\n🚀 NEW PROSPECT ENQUIRY ({first_name} {last_name})\n" + "=" * 65)
    print(f"📥 Enquiry: \"{enquiry}\"\n✉️ Reply:\n{clean_reply}")
    if SYNC_TO_CRM:
        result = sync_new_lead(first_name, last_name, mobile, email, enquiry, clean_reply)
        print(f"📌 CRM Sync -> {result}")
    print("=" * 65)


if __name__ == "__main__":
    # 1. SEO Keywords -> Notes
    capability_1_seo_keywords(
        "Nestio Preschools",
        "Pimple Saudagar, Pune",
        ["Playgroup", "Nursery", "Junior KG", "Senior KG", "Daycare"]
    )

    # 2. SEO GBP Content, Description & Services -> Notes
    capability_2_optimize_gbp_content(
        "Nestio Preschools",
        "Pimple Saudagar, Pune",
        "Preschool in Pimple Saudagar offering playgroup, nursery and daycare.",
        "best preschool in Pimple Saudagar, playgroup near me, early childhood learning Pune"
    )

    # 3. Active Customer Review -> Responds & syncs ONLY for this interacting customer
    handle_customer_feedback_event(
        customer_name="Sneha Joshi",
        mobile="9823123459",
        email="sneha.joshi1@example.com",
        rating=5,
        feedback_text="Amazing preschool with very supportive staff and fun activities for kids!"
    )

    # 4. Silent Customer (No interaction) -> Skipped cleanly
    handle_customer_feedback_event(
        customer_name="Rohit Sharma",
        mobile="9812345678",
        email="rohit.Sharma@example.com",
        feedback_text=""
    )

    # 5. SEO-Powered GBP Post -> Notes
    capability_4_seo_gbp_post("Admissions Open 2026-27 — Limited Seats for Playgroup & Nursery")

    # 6. New Prospect Enquiry -> CRM Lead
    handle_new_google_enquiry(
        first_name="Virat",
        last_name="Koli",
        mobile="0987654321",
        email="virat.koli@example.com",
        enquiry="Hi, I found Nestio Preschools on Google Maps. Want to know nursery fees and book a visit tomorrow."
    )
import time
from frappe_client import send_whatsapp_template

TEST_MOBILE = "919850684018"  # तुझा टेस्ट नंबर[cite: 8]
DELAY_SECONDS = 2

TEMPLATES_TO_TEST = [
    ("followup_instant_welcome", ["Sujit", "Nestio Preschools", "Nursery Admission"]),
    ("followup_day1_gentle", ["Sujit", "Nursery Admission", "Nestio Preschools"]),
    ("followup_day3_value", ["Sujit", "Nestio Preschools", "Play-based NEP Curriculum", "CCTV-monitored safe campus", "Experienced educators"]),
    ("followup_day7_proof", ["Sujit", "Our daughter loves going to Nestio every morning!", "Priya Kulkarni", "Nestio Preschools"]),
    ("followup_day14_final", ["Sujit", "Nestio Preschools"]),
    ("followup_after_call", ["Sujit", "Nursery program details", "Fee structure shared", "Campus tour on Saturday", "Nestio Preschools"]),
    ("followup_post_demo", ["Sujit", "Campus Tour", "Nestio Preschools"]),
    ("followup_reengage_cold", ["Sujit", "Nestio Preschools", "New academic term seats open", "Weekend activity workshop"]),
    ("followup_seasonal", ["Sujit", "New Academic Term", "Early bird admission benefit", "30th November", "https://nestiopreschools.in", "Nestio Preschools"]),
    ("followup_referral", ["Sujit", "Nestio Preschools", "a special parent referral gift"]),
    ("followup_payment_reminder", ["Sujit", "INV-2026-001", "Nursery Term 1 Fee", "05-Dec-2026", "INR 15,000", "https://nestiopreschools.in/pay", "Nestio Preschools"]),
    ("followup_winback", ["Sujit", "15%", "NESTIO15", "15-Dec-2026", "Nestio Preschools"]),
    ("followup_survey", ["Sujit", "Nestio Preschools", "https://g.page/r/nestio-review"]),
    ("followup_appointment", ["Sujit", "Nestio Preschools", "11:00 AM", "Pimple Saudagar Campus", "Nursery Campus Tour"]),
    ("followup_optout_confirm", ["Sujit", "Nestio Preschools"]),
]


def run_step_by_step_test(start_from: int = 1, interactive: bool = True):
    total = len(TEMPLATES_TO_TEST)
    print(f"🧪 Total templates: {total} | Target: {TEST_MOBILE}\n")

    for idx, (name, samples) in enumerate(TEMPLATES_TO_TEST, start=1):
        if idx < start_from:
            continue

        print("-" * 60)
        print(f"[{idx}/{total}] Template: {name}")
        print(f"Variables ({len(samples)}): {samples}")

        if interactive:
            choice = input("👉 Should we send (Enter = पाठवा, s = Skip, q = Quit): ").strip().lower()
            if choice == "q":
                print("🛑 Stopped by user.")
                break
            if choice == "s":
                print(f"⏭️ Skipped {name}")
                continue

        ok = send_whatsapp_template(
            to_mobile=TEST_MOBILE,
            template_name=name,
            variables=samples,
            is_marketing=False,
        )
        print(f"{'✅' if ok else '❌'} Result for {name}: Sent = {ok}")
        time.sleep(DELAY_SECONDS)


if __name__ == "__main__":
    run_step_by_step_test(start_from=1, interactive=True)
import requests
import os
from dotenv import load_dotenv
load_dotenv()

WABA_ID = os.getenv("WABA_ID")
ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN")
URL = f"https://graph.facebook.com/v25.0/{WABA_ID}/message_templates"

TEMPLATES = [
    {
        "name": "followup_instant_welcome",
        "category": "UTILITY",
        "body": "Hi {{1}}, Thank you for reaching out to {{2}}! 👋 We've received your enquiry about {{3}}. Our team is reviewing your details and will get back to you shortly. In the meantime, feel free to reply to this message with any questions. — Team {{2}}, Pimple Saudagar.",
        "samples": ["Sujit", "Nestio Preschools", "Nursery Admission"]
    },
    {
        "name": "followup_day1_gentle",
        "category": "MARKETING",
        "body": "Hi {{1}}, Just checking in — did you get a chance to review the information we shared? We'd love to help you with {{2}}. If you have any questions or would like to schedule a quick call, simply reply to this message. Looking forward to hearing from you! 😊 — Team {{3}}, Pimple Saudagar.",
        "samples": ["Sujit", "Nursery Admission", "Nestio Preschools"]
    },
    {
        "name": "followup_day3_value",
        "category": "MARKETING",
        "body": "Hi {{1}}, We thought you might find this helpful — here's what makes {{2}} different: ✅ {{3}} ✅ {{4}} ✅ {{5}} Have questions? Reply here and we'll walk you through it. — Team {{2}}, Pimple Saudagar.",
        "samples": ["Sujit", "Nestio Preschools", "Play-based NEP Curriculum", "CCTV-monitored safe campus", "Experienced educators"]
    },
    {
        "name": "followup_day7_proof",
        "category": "MARKETING",
        "body": "Hi {{1}}, Here's what our parents say about us: ⭐ \"{{2}}\" — {{3}} Ready to experience it yourself? Reply \"YES\" and we'll get you started. — Team {{4}}, Pimple Saudagar.",
        "samples": ["Sujit", "Our daughter loves going to Nestio every morning!", "Priya Kulkarni", "Nestio Preschools"]
    },
    {
        "name": "followup_day14_final",
        "category": "MARKETING",
        "body": "Hi {{1}}, This is our last check-in for now. We understand timing may not be right, and that's okay. If you'd like to revisit this later, just reply \"LATER\" and we'll follow up in a few weeks. Or reply \"NO\" to opt out completely. We're here whenever you're ready. 🙏 — Team {{2}}, Pimple Saudagar.",
        "samples": ["Sujit", "Nestio Preschools"]
    },
    {
        "name": "followup_after_call",
        "category": "UTILITY",
        "body": "Hi {{1}}, Thanks for taking the time to speak with us today! 📞 As discussed, here's a quick summary: {{2}} - {{3}} Next step: {{4}} Reply here if you need anything else. — Team {{5}}, Pimple Saudagar.",
        "samples": ["Sujit", "Nursery program details", "Fee structure shared", "Campus tour on Saturday", "Nestio Preschools"]
    },
    {
        "name": "followup_post_demo",
        "category": "MARKETING",
        "body": "Hi {{1}}, Hope you enjoyed the {{2}} yesterday! 🎉 What did you think? Any aspects you'd like to explore further? We're happy to schedule a deeper walkthrough or answer any questions. Just reply here. — Team {{3}}, Pimple Saudagar.",
        "samples": ["Sujit", "Campus Tour", "Nestio Preschools"]
    },
    {
        "name": "followup_reengage_cold",
        "category": "MARKETING",
        "body": "Hi {{1}}, It's been a while! 👋 We've made some updates at {{2}} that we thought you'd want to know about: {{3}} - {{4}} Interested in learning more? Reply \"YES\" and we'll share the details. — Team {{2}}, Pimple Saudagar.",
        "samples": ["Sujit", "Nestio Preschools", "New academic term seats open", "Weekend activity workshop"]
    },
    {
        "name": "followup_seasonal",
        "category": "MARKETING",
        "body": "Hi {{1}}, {{2}} is here! 🎊 To celebrate, we're offering {{3}} to new enrollments. This is a limited-time offer valid until {{4}}. Reply \"OFFER\" to claim yours or visit {{5}}. — Team {{6}}, Pimple Saudagar.",
        "samples": ["Sujit", "New Academic Term", "Early bird admission benefit", "30th November", "https://nestiopreschools.in", "Nestio Preschools"]
    },
    {
        "name": "followup_referral",
        "category": "MARKETING",
        "body": "Hi {{1}}, We're so glad you chose {{2}}! 🌟 Know someone who might benefit from our preschool programs? Share this message with them and you'll both get {{3}} as a thank-you. Thank you for spreading the word! 🙏 — Team {{2}}, Pimple Saudagar.",
        "samples": ["Sujit", "Nestio Preschools", "a special parent referral gift"]
    },
    {
        "name": "followup_payment_reminder",
        "category": "UTILITY",
        "body": "Hi {{1}}, This is a friendly reminder about invoice {{2}} for {{3}}, due on {{4}}. Amount: {{5}} Pay here: {{6}} If you've already paid, please ignore this message. Reply here for any questions. — Team {{7}}, Pimple Saudagar.",
        "samples": ["Sujit", "INV-2026-001", "Nursery Term 1 Fee", "05-Dec-2026", "INR 15,000", "https://nestiopreschools.in/pay", "Nestio Preschools"]
    },
    {
        "name": "followup_winback",
        "category": "MARKETING",
        "body": "Hi {{1}}, We miss you! 💙 It's been a while since we last connected. Here's a special benefit just for you: {{2}} off your next enrollment. Use code: {{3}} Valid until: {{4}} We'd love to welcome you back! — Team {{5}}, Pimple Saudagar.",
        "samples": ["Sujit", "15%", "NESTIO15", "15-Dec-2026", "Nestio Preschools"]
    },
    {
        "name": "followup_survey",
        "category": "UTILITY",
        "body": "Hi {{1}}, How was your experience with {{2}}? 🌟 Your feedback helps us improve. Please take 30 seconds to rate us: {{3}} Thank you for your time! — Team {{2}}, Pimple Saudagar.",
        "samples": ["Sujit", "Nestio Preschools", "https://g.page/r/nestio-review"]
    },
    {
        "name": "followup_appointment",
        "category": "UTILITY",
        "body": "Hi {{1}}, This is a reminder for your appointment with {{2}} tomorrow at {{3}}. Location: {{4}} Agenda: {{5}} Reply \"CONFIRM\" to confirm or \"RESCHEDULE\" to change. — Team {{2}}, Pimple Saudagar.",
        "samples": ["Sujit", "Nestio Preschools", "11:00 AM", "Pimple Saudagar Campus", "Nursery Campus Tour"]
    },
    {
        "name": "followup_optout_confirm",
        "category": "UTILITY",
        "body": "Hi {{1}}, You've been unsubscribed from our WhatsApp updates. You won't receive further marketing messages from us. If this was a mistake, reply \"START\" to re-subscribe. Thank you for your time. — Team {{2}}, Pimple Saudagar.",
        "samples": ["Sujit", "Nestio Preschools"]
    },
]

headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}

for tpl in TEMPLATES:
    payload = {
        "name": tpl["name"],
        "language": "en_US",
        "category": tpl["category"],
        "components": [
            {
                "type": "BODY",
                "text": tpl["body"],
                "example": {"body_text": [tpl["samples"]]}
            }
        ]
    }
    res = requests.post(URL, headers=headers, json=payload)
    print(f"{tpl['name']}: {res.status_code} -> {res.json()}")
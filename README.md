
# Marketing Automation Agent (`Marketing_Automation_agent`)

Multi-channel AI engagement and CRM lead-sync pipeline built for **Nestio Preschools** (Pimple Saudagar, Pune) and **Space EC India Foundation**.

## Key Capabilities
- **Intent Classification & Reply Drafting:** Categorizes inquiries (admissions, internships, partnerships, appreciation, complaints/sensitive topics, and noise) and drafts grounded replies.
- **Human-in-the-Loop Controls:** Supports terminal review (`Approve`, `Edit`, `Skip`) before finalizing outreach.
- **Frappe CRM Integration (`frappe_client.py`):** Handles lead creation, contact linking, deduplication, and timeline logging across channels (`LinkedIn`, `Facebook`, `WhatsApp`), alongside WhatsApp messaging and campus hours helpers.
- **Multi-Agent Workflows:** Modular scripts for LinkedIn (`main_linkedin_agent.py`, `trigger_linkdin_event.py`), Facebook (`facebook_agent.py`), and AI client integration (`gemini_client.py`).

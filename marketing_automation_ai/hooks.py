app_name = "marketing_automation_ai"
app_title = "Marketing Automation AI Agent"
app_publisher = "Marketing Automation AI Agent"
app_description = "Marketing Automation AI Agent for WhatsApp & CRM"
app_email = "support@example.com"
app_license = "MIT"

doc_events = {
    "WhatsApp Message": {
        "after_insert": "marketing_automation_ai.whatsapp_engine.on_whatsapp_message_insert"
    }
}

scheduler_events = {
    "cron": {
        "*/15 * * * *": [
            "marketing_automation_ai.followup_engine.run_scheduled_followups"
        ]
    }
}
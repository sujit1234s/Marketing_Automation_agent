from frappe_client import send_whatsapp_template

TEST_MOBILE = "919850684018"

if __name__ == "__main__":
    print("🧪 Testing WhatsApp Template send via Frappe...")
    ok = send_whatsapp_template(
        to_mobile=TEST_MOBILE,
        template_name="hello_world-en_US",
        variables=["Sujit", "Nestio Preschools", "Nursery Admission"],
        is_marketing=False,
    )
    print(f"Template Sent?: {ok}")
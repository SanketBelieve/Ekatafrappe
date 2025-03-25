import frappe

def validate(doc, method):
    if doc.opportunity_from == "Lead" and doc.party_name:
        lead = frappe.get_doc("Lead", doc.party_name)
        doc.custom_opportunity_category = lead.custom_opportunity_category
        doc.purpose = lead.custom_purpose
        doc.custom_lead_type = lead.type

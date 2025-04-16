import frappe

def validate(doc, method):
    print("**********OPP TRIGGER************")
    if doc.opportunity_from == "Lead" and doc.party_name:
        lead = frappe.get_doc("Lead", doc.party_name)
        doc.custom_opportunity_category = lead.custom_opportunity_category
        print("doc purpose",lead.custom_purpose,"\n\n\n")
        doc.purpose = lead.custom_purpose
        doc.custom_lead_type = lead.type

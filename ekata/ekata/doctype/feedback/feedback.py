import frappe
from frappe.model.document import Document

class Feedback(Document):
    def validate(self):
        """Automatically compute amount for child table and total_amount"""
        total_amount = 0

        for item in self.get("items"):  # Assuming 'items' is the child table field
            item.amount = item.qty * item.rate  # Compute amount
            total_amount += item.amount  # Sum up amounts
        
        self.total_amount = total_amount  # Update total amount in the main doc


@frappe.whitelist()
def create_feedback_from_opportunity(opportunity_name):
    """Create a Feedback record from an Opportunity and copy the Lead’s linked address."""
    opportunity = frappe.get_doc("Opportunity", opportunity_name)

    # ------------------------------------------------------------------
    # 1.  New Feedback shell
    # ------------------------------------------------------------------
    feedback = frappe.new_doc("Feedback")
    feedback.opportunity = opportunity.name
    feedback.type        = opportunity.custom_opportunity_category
    feedback.company     = opportunity.company
    # ------------------------------------------------------------------
    # 2.  Lead + Address (no more get_default_address)
    # ------------------------------------------------------------------
    if frappe.db.exists("Lead", opportunity.party_name):
        feedback.lead = opportunity.party_name,opportunity.party_name
        lead_entity=frappe.get_doc("Lead",opportunity.party_name)
        feedback.lead_purpose=lead_entity.custom_purpose
        # Grab the FIRST Address linked to this Lead via Dynamic Link
        address_name = frappe.db.get_value(
            "Dynamic Link",
            {
                "link_doctype": "Lead",
                "link_name": opportunity.party_name,
                "parenttype": "Address",
            },
            "parent",
            order_by="idx asc"   # pick the one that shows up first in the UI
        )
        print("address_name",address_name,"\n\n\n\n")
        if address_name:
            addr = frappe.get_doc("Address", address_name)
            feedback.city         = lead_entity.city
            feedback.state        = lead_entity.state
            feedback.country      = lead_entity.country
            feedback.lead_address = addr
            feedback.pin_code=addr.pincode

    # ------------------------------------------------------------------
    # 3.  Items
    # ------------------------------------------------------------------
    for item in opportunity.items:
        feedback.append(
            "items",
            {
                "item": item.item_code,
                "qty": item.qty,
                "rate": item.base_rate,
                "amount": item.qty * item.base_rate,
            },
        )

    feedback.total_amount = sum(d.amount for d in feedback.items)
    feedback.insert(ignore_permissions=True)
	
    frappe.msgprint(f"Feedback created successfully! 🎉",alert=True)
    return feedback.name


    
@frappe.whitelist()
def create_opportunity_from_feedback(feedback_name):
    feedback = frappe.get_doc("Feedback", feedback_name)

    if feedback.status != "Rejected":
        frappe.throw("Feedback status must be Rejected to create an Opportunity.")
    
    if not feedback.lead:
        frappe.throw("Feedback needs a Lead to create an Opportunity.")

    # Create new Opportunity
    opportunity = frappe.new_doc("Opportunity")
    opportunity.opportunity_from = "Lead"
    opportunity.lead = feedback.lead
    opportunity.enquiry_type = "Sales"
    opportunity.custom_opportunity_category = feedback.opportunity_category
    opportunity.purpose = feedback.opportunity_purpose
    opportunity.transaction_date = frappe.utils.nowdate()
    opportunity.custom_lead_type=feedback.lead_type
    # ✅ Manually fetch & assign party_name
    lead_name = frappe.db.get_value("Lead", feedback.lead, "name")
    opportunity.party_name = lead_name
    opportunity.contact_email=feedback.contact_email
    opportunity.contact_mobile=feedback.contact_phone
    opportunity.purpose=feedback.lead_purpose
    opportunity.opportunity_owner=frappe.session.user

    # Company setup
    opportunity.company = feedback.company or frappe.defaults.get_user_default("Company")

    # Set company address (if available)
    company_address = frappe.get_value("Dynamic Link", {
        "link_doctype": "Company",
        "link_name": opportunity.company,
        "parenttype": "Address"
    }, "parent")

    if company_address:
        opportunity.company_address = company_address

    # Optional: Link Feedback (if field exists in Opportunity)
    if frappe.get_meta("Opportunity").has_field("feedback_reference"):
        opportunity.feedback_reference = feedback.name

    # Add items
    for item in feedback.items:
        opportunity.append("items", {
            "item_code": item.item,
            "qty": item.qty,
            "rate": item.rate,
            "amount": item.amount,
            "schedule_date": frappe.utils.nowdate()
        })

    # 💥 Insert the doc (skip set_missing_values entirely)
    opportunity.insert()
    return opportunity.name



@frappe.whitelist()
def create_quotation_from_feedback(feedback_name):
    """Create a Quotation from a Feedback"""
    feedback = frappe.get_doc("Feedback", feedback_name)

    # Create a new Quotation document
    quotation = frappe.new_doc("Quotation")
    quotation.quotation_to="Customer"
    if feedback.customer:
        quotation.party_name=feedback.customer
    quotation.custom_opportunity_category=feedback.opportunity_category
    quotation.custom_purpose=feedback.opportunity_purpose
    quotation.custom_lead_type=feedback.lead_type
    company = feedback.company
    # Get primary address
    company_address = frappe.get_value("Dynamic Link", {
        "link_doctype": "Company",
        "link_name": company,
        "parenttype": "Address"
    }, "parent")
    # Assuming 'lead' field in Feedback maps to 'customer' in Quotation
    #quotation.customer = feedback.customer  
    #quotation.feedback = feedback.name  # Link to the Feedback

    # Copy Items from Feedback
    for item in feedback.items:
        quotation.append("items", {
            "item_code": item.item,  # Adjust field names as per your setup
            "qty": item.qty,
            "rate": item.rate,
            "amount": item.qty * item.rate
        })

    quotation.total = sum([d.amount for d in quotation.items])  # Compute total
    quotation.insert()  # Save the new document
    frappe.msgprint(f"Quotation '{quotation.name}' Created Successfully!", alert=True)
    return quotation.name  # Return the new document name

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
    """Create a Feedback record from an Opportunity"""
    opportunity = frappe.get_doc("Opportunity", opportunity_name)

    # Create a new Feedback document
    feedback = frappe.new_doc("Feedback")
    if frappe.db.exists("Lead", opportunity.party_name): 
         feedback.lead = opportunity.party_name  # Copy party_name to lead field
    feedback.opportunity = opportunity.name  # Store opportunity reference
    feedback.type = opportunity.custom_opportunity_category  # Copy custom type field
    feedback.company=opportunity.company
	# Validate if the lead exists
	
    # Copy Items from Opportunity
    for item in opportunity.items:
        feedback.append("items", {
            "item": item.item_code,  # Assuming 'item' is the field name
            "qty": item.qty,
            "rate": item.base_rate,
            "amount": item.qty * item.rate  # Compute amount here too
        })

    feedback.total_amount = sum([d.amount for d in feedback.items])  # Compute total
    feedback.insert()  # Save the new document
    frappe.msgprint(f"Feedback '{feedback.name}' Created Successfully!", alert=True)
    return feedback.name  # Return the new document name
    

@frappe.whitelist()
def create_quotation_from_feedback(feedback_name):
    """Create a Quotation from a Feedback"""
    feedback = frappe.get_doc("Feedback", feedback_name)

    # Create a new Quotation document
    quotation = frappe.new_doc("Quotation")
    quotation.quotation_to="Customer"
    if feedback.customer:
    	quotation.party_name=feedback.customer
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
    opportunity.transaction_date = frappe.utils.nowdate()

    # ✅ Manually fetch & assign party_name
    lead_name = frappe.db.get_value("Lead", feedback.lead, "name")
    opportunity.party_name = lead_name

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


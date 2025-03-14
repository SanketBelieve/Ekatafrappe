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

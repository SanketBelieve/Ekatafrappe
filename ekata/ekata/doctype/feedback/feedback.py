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
    """Create a Feedback record from an Opportunity, copying Opportunity-wise addresses first, then falling back to Lead addresses."""
    opportunity = frappe.get_doc("Opportunity", opportunity_name)

    feedback = frappe.new_doc("Feedback")
    feedback.opportunity = opportunity.name
    feedback.type = opportunity.custom_opportunity_category
    feedback.company = opportunity.company

    # --- Lead logic ---
    if frappe.db.exists("Lead", opportunity.party_name):
        feedback.lead = opportunity.party_name
        lead_entity = frappe.get_doc("Lead", opportunity.party_name)
        feedback.lead_purpose = lead_entity.custom_purpose

        # First linked address for display (any type, just for demo)
        lead_address_name = frappe.db.get_value(
            "Dynamic Link",
            {
                "link_doctype": "Lead",
                "link_name": opportunity.party_name,
                "parenttype": "Address",
            },
            "parent",
            order_by="idx asc"
        )
        print("First (any type) Lead Address Name:", lead_address_name)
        if lead_address_name:
            addr = frappe.get_doc("Address", lead_address_name)
            feedback.city = lead_entity.city
            feedback.state = lead_entity.state
            feedback.country = lead_entity.country
            feedback.lead_address = addr.name
            feedback.pin_code = addr.pincode
            feedback.address_line_1=addr.address_line1
            feedback.address_line_2=addr.address_line2
            
            print(f"Set Feedback Lead Address: {addr.name} (City: {lead_entity.city}, State: {lead_entity.state}, Country: {lead_entity.country}, Pincode: {addr.pincode})")

    # --- Billing Address: Try Opportunity, else Lead ---
    billing_address = get_address_with_fallback(
        opportunity_name=opportunity.name, 
        lead_name=opportunity.party_name, 
        address_type="Billing"
    )
    print("Selected Billing Address:", billing_address)
    if billing_address:
        feedback.opportunity_billing_address = billing_address

    # --- Shipping Address: Try Opportunity, else Lead ---
    shipping_address = get_address_with_fallback(
        opportunity_name=opportunity.name, 
        lead_name=opportunity.party_name, 
        address_type="Shipping"
    )
    print("Selected Shipping Address:", shipping_address)
    if shipping_address:
        feedback.opportunity_shipping_address = shipping_address

    # --- Add Items from Opportunity ---
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
        print(f"Added Item: {item.item_code}, Qty: {item.qty}, Rate: {item.base_rate}, Amount: {item.qty * item.base_rate}")

    feedback.total_amount = sum(d.amount for d in feedback.items)
    print("Calculated Total Amount:", feedback.total_amount)
    feedback.insert(ignore_permissions=True)

    print("Inserted Feedback Doc:", feedback.name)
    frappe.msgprint(f"Feedback created successfully! 🎉", alert=True)
    return feedback.name

def get_address_with_fallback(opportunity_name, lead_name, address_type):
    """
    Try to get Address of given type (Billing/Shipping) linked to Opportunity.
    If not found, try Lead.
    """
    # Try Opportunity
    address_name = get_address_for_entity(opportunity_name, "Opportunity", address_type)
    if address_name:
        print(f"Found {address_type} Address linked to Opportunity: {address_name}")
        return address_name
    # Fallback: Try Lead
    address_name = get_address_for_entity(lead_name, "Lead", address_type)
    if address_name:
        print(f"Found {address_type} Address linked to Lead: {address_name}")
        return address_name
    print(f"No {address_type} Address found for Opportunity or Lead.")
    return None

def get_address_for_entity(entity_name, entity_doctype, address_type):
    """
    Return the name of the first Address linked to this entity (Opportunity/Lead)
    with the given address_type.
    """
    address_links = frappe.db.sql("""
        SELECT parent FROM `tabDynamic Link`
        WHERE link_doctype=%s
          AND link_name=%s
          AND parenttype='Address'
        ORDER BY idx ASC
    """, (entity_doctype, entity_name), as_dict=1)

    for link in address_links:
        addr = frappe.get_doc("Address", link.parent)
        print(f"Checking {entity_doctype} Address {addr.name} for type {address_type} (Found: {getattr(addr, 'address_type', '')})")
        if getattr(addr, "address_type", "") == address_type:
            print(f"Matched {entity_doctype} Address for {address_type}: {addr.name}")
            return addr.name
    print(f"No {address_type} Address found for {entity_doctype}: {entity_name}")
    return None


    
@frappe.whitelist()
def create_opportunity_from_feedback(feedback_name):
    feedback = frappe.get_doc("Feedback", feedback_name)

    if feedback.status != "Rejected":
        frappe.throw("Feedback status must be Rejected to create an Opportunity.")

    if not feedback.lead:
        frappe.throw("Feedback needs a Lead to create an Opportunity.")

    opportunity = frappe.new_doc("Opportunity")
    opportunity.opportunity_from = "Lead"
    opportunity.lead = feedback.lead
    opportunity.enquiry_type = "Sales"
    opportunity.custom_opportunity_category = feedback.opportunity_category
    opportunity.purpose = feedback.opportunity_purpose
    opportunity.transaction_date = frappe.utils.nowdate()
    opportunity.custom_lead_type = feedback.lead_type
    opportunity.party_name = feedback.lead
    opportunity.contact_email = feedback.contact_email
    opportunity.contact_mobile = feedback.contact_phone
    opportunity.purpose = feedback.lead_purpose
    opportunity.opportunity_owner = frappe.session.user

    opportunity.company = feedback.company or frappe.defaults.get_user_default("Company")

    if frappe.get_meta("Opportunity").has_field("feedback_reference"):
        opportunity.feedback_reference = feedback.name

    for item in feedback.items:
        opportunity.append("items", {
            "item_code": item.item,
            "qty": item.qty,
            "rate": item.rate,
            "amount": item.amount,
            "schedule_date": frappe.utils.nowdate()
        })

    opportunity.insert()

    # --- Append Opportunity link to Lead Address ---
    if feedback.lead_address:
        address_doc = frappe.get_doc("Address", feedback.lead_address)
        address_doc.append("links", {
            "link_doctype": "Opportunity",
            "link_name": opportunity.name
        })
        address_doc.save(ignore_permissions=True)
        frappe.db.commit()
        print(f"Address {address_doc.name} now also links to Opportunity {opportunity.name}")

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

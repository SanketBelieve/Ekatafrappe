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
    """
    Create a Feedback record from an Opportunity, copying Opportunity-wise addresses first,
    then falling back to Lead addresses.
    """
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
            order_by="idx asc",
        )
        if lead_address_name:
            addr = frappe.get_doc("Address", lead_address_name)
            feedback.city = lead_entity.city
            feedback.state = lead_entity.state
            feedback.country = lead_entity.country
            feedback.lead_address = addr.name
            feedback.pin_code = addr.pincode
            feedback.address_line_1 = addr.address_line1
            feedback.address_line_2 = addr.address_line2

    # --- Billing Address: Try Opportunity, else Lead ---
    billing_address = get_address_with_fallback(
        opportunity_name=opportunity.name,
        lead_name=opportunity.party_name,
        address_role="billing",
    )
    if billing_address:
        feedback.opportunity_billing_address = billing_address

    # --- Shipping Address: Try Opportunity, else Lead ---
    shipping_address = get_address_with_fallback(
        opportunity_name=opportunity.name,
        lead_name=opportunity.party_name,
        address_role="shipping",
    )
    if shipping_address:
        feedback.opportunity_shipping_address = shipping_address

    # --- Add Items from Opportunity ---
    for item in opportunity.items:
        feedback.append(
            "items",
            {
                "item": item.item_code,
                "qty": item.qty or 1,
                "rate": item.base_rate or 0,
                "amount": item.qty * item.base_rate,
            },
        )

    feedback.total_amount = sum(d.amount for d in feedback.items)
    feedback.insert(ignore_permissions=True)
    frappe.msgprint(f"Feedback created successfully! 🎉", alert=True)
    return feedback.name


def get_address_with_fallback(opportunity_name, lead_name, address_role):
    """
    Try to get Address of given role (billing/shipping) linked to Opportunity.
    If not found, try Lead.
    """
    # Try Opportunity
    address_name = get_address_for_entity(opportunity_name, "Opportunity", address_role)
    if address_name:
        return address_name
    # Fallback: Try Lead
    address_name = get_address_for_entity(lead_name, "Lead", address_role)
    if address_name:
        return address_name
    return None


def get_address_for_entity(entity_name, entity_doctype, address_role):
    """
    Return the name of the first Address linked to this entity (Opportunity/Lead)
    with the given address_role ('billing' or 'shipping').
    """
    # Map role to ERPNext's standard flag fields
    strict_filters = {
        "billing": {"is_primary_address": 1, "is_shipping_address": 0, "disabled": 0},
        "shipping": {"is_primary_address": 0, "is_shipping_address": 1, "disabled": 0},
    }
    loose_flag = (
        "is_primary_address" if address_role == "billing" else "is_shipping_address"
    )

    address_links = frappe.db.sql(
        """
        SELECT parent FROM `tabDynamic Link`
        WHERE link_doctype=%s
          AND link_name=%s
          AND parenttype='Address'
        ORDER BY idx ASC
    """,
        (entity_doctype, entity_name),
        as_dict=1,
    )

    # Strict: Only single-role addresses
    for link in address_links:
        addr = frappe.get_doc("Address", link.parent)
        filters = strict_filters[address_role]
        if (
            getattr(addr, "is_primary_address", 0) == filters.get("is_primary_address")
            and getattr(addr, "is_shipping_address", 0)
            == filters.get("is_shipping_address")
            and getattr(addr, "disabled", 0) == 0
        ):
            return addr.name

    # Loose: Accept both flags true (for fallback)
    for link in address_links:
        addr = frappe.get_doc("Address", link.parent)
        if getattr(addr, loose_flag, 0) == 1 and getattr(addr, "disabled", 0) == 0:
            return addr.name

    # Last resort: any address
    for link in address_links:
        addr = frappe.get_doc("Address", link.parent)
        if getattr(addr, "disabled", 0) == 0:
            return addr.name
    return None


def get_customer_addresses(customer_name):
    """
    Returns a tuple: (billing_address_name, shipping_address_name) for a Customer.
    Ensures that, if possible, billing and shipping are not the same address.
    """
    # Get all addresses linked to this customer, sorted by creation date (newest first)
    addresses = frappe.get_all(
        "Address",
        filters={"disabled": 0},
        fields=["name", "is_primary_address", "is_shipping_address", "creation"],
        order_by="creation desc",
    )
    billing = None
    shipping = None

    # Get all addresses linked to customer
    address_objs = []
    for addr in addresses:
        doc = frappe.get_doc("Address", addr["name"])
        for link in getattr(doc, "links", []):
            if link.link_doctype == "Customer" and link.link_name == customer_name:
                address_objs.append((doc, addr))

    # Strict matching
    for doc, addr in address_objs:
        if doc.is_primary_address and not doc.is_shipping_address and not billing:
            billing = doc.name
        if doc.is_shipping_address and not doc.is_primary_address and not shipping:
            shipping = doc.name

    # If not found, try loose matching (address with either flag True)
    if not billing:
        for doc, addr in address_objs:
            if doc.is_primary_address and not billing:
                billing = doc.name
    if not shipping:
        for doc, addr in address_objs:
            if doc.is_shipping_address and not shipping:
                shipping = doc.name

    # If still not found, pick first address for each, but avoid overlap if possible
    if not billing and address_objs:
        billing = address_objs[0][0].name
    if not shipping and address_objs:
        # If billing already used the only address, shipping will also be the same, but if multiple exist, pick the next
        if billing and len(address_objs) > 1:
            for doc, addr in address_objs:
                if doc.name != billing:
                    shipping = doc.name
                    break
        if not shipping:
            shipping = address_objs[0][0].name

    return billing, shipping


@frappe.whitelist()
def create_quotation_from_feedback(feedback_name):
    """Creates a Quotation from Feedback using Customer's addresses and ensures billing/shipping aren't same if possible."""
    feedback = frappe.get_doc("Feedback", feedback_name)
    if not feedback.customer:
        frappe.throw("Feedback must have a Customer to create a Quotation.")
    if not feedback.items or len(feedback.items) == 0:
        frappe.throw("Cannot create Quotation: No items found in Feedback.")

    billing_address, shipping_address = get_customer_addresses(feedback.customer)

    quotation = frappe.new_doc("Quotation")
    quotation.quotation_to = "Customer"
    quotation.party_name = feedback.customer
    quotation.customer_name = feedback.customer
    quotation.custom_lead_type = feedback.lead_type

    if billing_address:
        quotation.billing_address_name = billing_address
    if shipping_address:
        quotation.shipping_address_name = shipping_address

    quotation.transaction_date = frappe.utils.nowdate()
    quotation.order_type = "Sales"  # Set dynamically if you wish

    for item in feedback.items:
        quotation.append(
            "items",
            {
                "item_code": item.item,
                "qty": item.qty,
                "rate": item.rate,
                "amount": item.amount,
                "schedule_date": frappe.utils.nowdate(),
            },
        )

    quotation.insert(ignore_permissions=True)
    frappe.msgprint(
        f"Quotation {quotation.name} created for Customer {feedback.customer}."
    )
    return quotation.name

import frappe
import math

from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note



def create_and_process_delivery_note(doc, method):
    """
    Create a Delivery Note from a Sales Order and apply composition items if needed.
    """
    # Check if shopify_order_id is not None
    if not doc.shopify_order_id:
        return

    # Create Delivery Note from Sales Order
    dn_doc = make_delivery_note(doc.name)

    # Fetch the first branch from the Branch doctype
    branch_name = frappe.get_all(
        "Branch",
        fields=["name"],
        limit_page_length=1,
        order_by="creation ASC",
    )

    # Set custom delivery note category to "Ecommerce-Blending"
    dn_doc.custom_delivery_note_category = "Ecommerce-Blending"

    # If branch is found, assign it to the Delivery Note
    if branch_name:
        dn_doc.branch = branch_name[0].get("name")

        # Set posting time and date
        dn_doc.set_posting_time = 1
        dn_doc.posting_date = frappe.utils.today()

        # Apply composition items if category is "Ecommerce-Blending"
        if dn_doc.custom_delivery_note_category == "Ecommerce-Blending":
            for item in dn_doc.items:
                # Fetch the composition of the item if it exists
                compositions = frappe.get_all(
                    "Composition of Items",
                    filters={"item": item.item_code},
                    fields=["item_qty", "name"],
                )

                for composition in compositions:
                    # Fetch child items from the composition table
                    composition_doc = frappe.get_doc("Composition of Items", composition.name)

                    for child in composition_doc.composition:
                        # Calculate the quantity based on item_qty per unit and original item quantity
                        total_qty = child.item_qty * item.qty

                        # Append the child item to Delivery Note with the calculated total quantity
                        dn_doc.append(
                            "items",
                            {
                                "item_code": child.item,
                                "qty": total_qty,
                                "uom": child.uom,
                                "conversion_factor": 1,
                                "warehouse": item.warehouse,
                                "description": f"Added from composition of {item.item_code}",
                            },
                        )

        # Insert the Delivery Note without submitting
        dn_doc.insert(ignore_permissions=True)
    else:
        frappe.throw("No branch found. Delivery Note not created.")



def apply_composition_items_only(dn_doc):
    """
    Apply item compositions to an existing Delivery Note without creating a new one.
    """
    # Check if the category is "Ecommerce-Blending"
    if dn_doc.custom_delivery_note_category != "Blending":
        return

    # Loop through items in the Delivery Note to process composition
    for item in dn_doc.items:
        # Fetch the composition of the item if it exists
        compositions = frappe.get_all(
            "Composition of Items",
            filters={"item": item.item_code},
            fields=["item_qty", "name"],
        )

        for composition in compositions:
            # Fetch child items from the composition table
            composition_doc = frappe.get_doc("Composition of Items", composition.name)

            for child in composition_doc.composition:
                # Calculate the quantity based on item_qty per unit and original item quantity
                total_qty = child.item_qty * item.qty

                # Append the child item to Delivery Note with the calculated total quantity
                dn_doc.append(
                    "items",
                    {
                        "item_code": child.item,
                        "qty": total_qty,
                        "uom": child.uom,
                        "conversion_factor": 1,
                        "warehouse": item.warehouse,
                        "description": f"Added from composition of {item.item_code}",
                    },
                )

    # Save the changes after applying composition items
    dn_doc.save()

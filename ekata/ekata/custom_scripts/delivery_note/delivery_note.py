import frappe
import math

from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note
# def before_save_delivery_note(doc, method):
#     """
#     Before saving the Delivery Note:
#     - Append BOM items while keeping the first item.
#     - Adjust BOM item quantity based on the Selling Price List.
#     - If UOM is 'Nos', round quantity to an integer.
#     - Enable 'Allow Zero Valuation Rate' to avoid valuation rate errors.
#     """
#     if doc.custom_delivery_note_type != "Blending":
#         return

#     if not doc.items:
#         return

#     new_items = []

#     # Get UOM from the first item
#     first_item_uom = doc.items[0].uom if doc.items[0].uom else doc.items[0].stock_uom
#     selling_price_list = doc.selling_price_list  # Get the Selling Price List from the document

#     for item in doc.items:
#         if not item.item_code:
#             continue

#         # Fetch the active BOM for the item
#         bom = frappe.get_value("BOM", {"item": item.item_code, "is_active": 1, "is_default": 1}, "name")

#         if not bom:
#             frappe.logger().warning(f"No active BOM found for item: {item.item_code}")
#             continue

#         # Fetch BOM Items
#         bom_items = frappe.get_all(
#             "BOM Item",
#             filters={"parent": bom},
#             fields=["item_code", "qty"]
#         )

#         for bom_item in bom_items:
#             # Fetch item details
#             item_details = frappe.get_value(
#                 "Item",
#                 bom_item["item_code"],
#                 ["item_name", "stock_uom", "description", "gst_hsn_code"],
#                 as_dict=True
#             )

#             if not item_details:
#                 frappe.logger().error(f"Item {bom_item['item_code']} not found in the Item master")
#                 continue

#             # Fetch Selling Price for the BOM item
#             selling_price = frappe.get_value(
#                 "Item Price",
#                 {"item_code": bom_item["item_code"], "price_list": selling_price_list},
#                 "price_list_rate"
#             )

#             if not selling_price or selling_price <= 0:
#                 frappe.logger().warning(f"No selling price found for item {bom_item['item_code']} in {selling_price_list}")
#                 continue

#             # Calculate quantity based on price ratio
#             adjusted_qty = (bom_item["qty"] * item.qty) / selling_price

#             # If UOM is 'Nos', round quantity to an integer
#             if first_item_uom == "Nos":
#                 adjusted_qty = math.ceil(adjusted_qty)

#             # Append BOM items with adjusted quantity and allow zero valuation rate
#             new_items.append({
#                 "item_code": bom_item["item_code"],
#                 "item_name": item_details["item_name"],
#                 "description": item_details["description"],
#                 "gst_hsn_code": item_details["gst_hsn_code"],  # Tax-related field
#                 "stock_uom": item_details["stock_uom"],
#                 "uom": first_item_uom,  # Use the same UOM as the first item
#                 "qty": adjusted_qty,  # Adjusted based on selling price
#                 "conversion_factor": 1,  # Fetch actual factor if required
#                 "allow_zero_valuation_rate": 1  # Enable zero valuation rate
#             })

#     # Append new BOM items while keeping the original items
#     for item in new_items:
#         doc.append("items", item)






def create_delivery_note(doc, method):
    # Check if shopify_order_id is not None
    if doc.shopify_order_id:
        # Create Delivery Note from Sales Order
        dn_doc = make_delivery_note(doc.name)
        
        # Fetch the first branch from the Branch doctype
        branch_name = frappe.get_all(
            "Branch", 
            fields=["name"], 
            limit_page_length=1, 
            order_by="creation ASC"
        )
        dn_doc.doc.custom_delivery_note_type="Blending"
        # If branch is found, set it and save the Delivery Note
        if branch_name:
            dn_doc.branch = branch_name[0].get("name")
            
            # Set posting time and date
            dn_doc.set_posting_time = 1
            dn_doc.posting_date = frappe.utils.today()
            
            # Insert and submit the Delivery Note
            dn_doc.insert(ignore_permissions=True)
        else:
            frappe.throw("No branch found. Delivery Note not created.")


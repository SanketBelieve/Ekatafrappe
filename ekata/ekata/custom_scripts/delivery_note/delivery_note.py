import frappe
from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note
from frappe.utils import today, flt

def create_and_process_delivery_note(doc, method):
    """
    On submit of a Shopify-linked Sales Order, spin up a draft Delivery Note
    whose extra lines are exploded from the corresponding BOM(s),
    scaled properly per BOM.quantity.
    """
    # Only run for ecommerce orders
    if not doc.shopify_order_id:
        return

    # 1️⃣ Create the DN draft
    dn = make_delivery_note(doc.name)

    # 2️⃣ Assign the very first Branch
    branch = frappe.get_all(
        "Branch",
        fields=["name"],
        limit_page_length=1,
        order_by="creation ASC"
    )
    if not branch:
        frappe.throw("No Branch found – cannot create Delivery Note.")
    dn.branch = branch[0].name

    # 3️⃣ Tag & stamp
    dn.custom_delivery_note_category = "Ecommerce-Blending"
    dn.set_posting_time = 1
    dn.posting_date = today()

    # 4️⃣ Explode each original line via its BOM
    for line in list(dn.items):
        # get all active, submitted BOMs for this item
        boms = frappe.get_all("BOM",
            filters={"item": line.item_code, "is_active": 1, "docstatus": 1},
            fields=["name"]
        )
        if not boms:
            continue  # no BOM → skip

        # pick the right one
        if len(boms) == 1:
            bom_name = boms[0].name
        else:
            chosen = getattr(doc, "custom_delivery_note_bom", None)
            valid = [b.name for b in boms]
            if not chosen or chosen not in valid:
                frappe.throw(
                    f"Multiple BOMs exist for {line.item_code}. "
                    f"Set Sales Order.custom_delivery_note_bom to one of: {', '.join(valid)}"
                )
            bom_name = chosen

        # fetch the BOM
        bom = frappe.get_doc("BOM", bom_name)
        base_qty = flt(bom.quantity) or 1.0

        # append each child scaled by (line.qty / base_qty)
        for bi in bom.items:
            qty_per_unit = flt(bi.qty) / base_qty
            total_qty = flt(qty_per_unit * flt(line.qty))

            # start with guaranteed-safe fields
            item_data = {
                "item_code":        bi.item_code,
                "item_name":        bi.item_name,
                "description":      bi.get("description"),
                "qty":              total_qty,
                "uom":              bi.uom,
                "stock_uom":        bi.get("stock_uom"),
                "conversion_factor": flt(bi.get("conversion_factor", 1)),
                "rate":             bi.get("rate"),
                "amount":           bi.get("amount"),
                "warehouse":        line.warehouse
            }

            # pull in any extra fields that actually exist on your BOM Item
            for fld in ("sourced_by_supplier", "supplier", "supplier_part_no",
                        "expense_account", "cost_center"):
                if hasattr(bi, fld):
                    item_data[fld] = getattr(bi, fld)

            dn.append("items", item_data)

    # 5️⃣ Finally insert the draft DN
    dn.insert(ignore_permissions=True)


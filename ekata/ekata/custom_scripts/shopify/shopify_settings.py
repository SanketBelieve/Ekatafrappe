import frappe
from frappe.utils import today, flt
from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note
import math


def handle_sales_order(doc, method):
    if doc.shopify_order_id:
        settings = frappe.get_single("Additional Shopify Settings")

        if settings.sales_order_cost_center:
            doc.cost_center = settings.sales_order_cost_center
            for item in doc.items:
                item.cost_center = settings.sales_order_cost_center

        if settings.terms_of_delivery_and_payment:
            doc.tc_name = settings.terms_of_delivery_and_payment
        doc.country_of_origin_of_goods = "India"
        doc.terms_of_delivery_and_payment = "100% Advance with order conformation"
        doc.custom_sales_type = "Roasted"

        if settings.payment_terms:
            doc.payment_terms_template = settings.payment_terms
            template = frappe.get_doc("Payment Terms Template", settings.payment_terms)
            doc.payment_schedule = []
            for term in template.terms:
                doc.append("payment_schedule", {
                    "payment_term": term.payment_term,
                    "due_date": frappe.utils.add_days(frappe.utils.nowdate(), term.credit_days or 0),
                    "invoice_portion": term.invoice_portion,
                    "payment_amount": (doc.base_rounded_total * term.invoice_portion / 100)
                })

        if settings.branch:
            doc.branch = settings.branch

        doc.save(ignore_permissions=True)
        frappe.msgprint("✅ Shopify settings applied to Sales Order.")


def handle_sales_invoice(doc, method):
    if doc.shopify_order_id:
        settings = frappe.get_single("Additional Shopify Settings")
        doc.supply = doc.place_of_supply
        doc.country_of_origin_of_goods = "India"
        doc.terms_of_delivery_and_payment = "100% Advance with order conformation"
        doc.custom_sales_order_type = "Roasted"

        if settings.terms_of_delivery_and_payment:
            doc.tc_name = settings.terms_of_delivery_and_payment
        if settings.payment_terms:
            doc.payment_terms_template = settings.payment_terms
        if settings.sales_invoice_debit_to:
            doc.debit_to = settings.sales_invoice_debit_to
        if settings.sales_order_cost_center:
            doc.cost_center = settings.sales_order_cost_center
        if settings.branch:
            doc.branch = settings.branch

        for item in doc.items:
            if settings.income_account:
                item.income_account = settings.income_account
            if settings.sales_order_cost_center:
                item.cost_center = settings.sales_order_cost_center

        doc.save(ignore_permissions=True)
        frappe.msgprint("✅ Shopify settings applied to Sales Invoice.")


def handle_payment_entry(doc, method):
    settings = frappe.get_single("Additional Shopify Settings")
    if settings.mode_of_payment:
        doc.mode_of_payment = settings.mode_of_payment

    for ref in doc.references:
        if ref.reference_doctype == "Sales Invoice":
            invoice = frappe.get_doc("Sales Invoice", ref.reference_name)
            if invoice.shopify_order_id and settings.paid_from_account:
                doc.paid_from = settings.paid_from_account
                break

    doc.save(ignore_permissions=True)
    frappe.msgprint("✅ Shopify settings applied to Payment Entry.")


# def create_and_process_delivery_note(doc, method):
#     # Only for Shopify orders
#     if not doc.shopify_order_id:
#         return

#     # 1️⃣ Create DN draft
#     dn = make_delivery_note(doc.name)

#     # 2️⃣ Assign the very first Branch
#     branch = frappe.get_all(
#         "Branch",
#         fields=["name"],
#         limit_page_length=1,
#         order_by="creation ASC"
#     )
#     if not branch:
#         frappe.throw("No Branch found – cannot create Delivery Note.")
#     dn.branch = branch[0].name

#     # 3️⃣ Tag & stamp
#     dn.custom_delivery_note_category = "Ecommerce-Blending"
#     dn.set_posting_time = 1
#     dn.posting_date = today()

#     # 4️⃣ Explode each SO line via its BOM
#     material_issue_items = []
#     used_boms = set()

#     for so_line in doc.items:
#         boms = frappe.get_all(
#             "BOM",
#             filters={"item": so_line.item_code, "is_active": 1, "docstatus": 1},
#             fields=["name"]
#         )
#         if not boms:
#             continue

#         # pick the right BOM
#         if len(boms) == 1:
#             bom_name = boms[0].name
#         else:
#             checked = frappe.get_all(
#                 "BOM",
#                 filters={"item": so_line.item_code, "custom_sales_order_automation": 1},
#                 fields=["name"],
#                 order_by="creation DESC",
#                 limit_page_length=1
#             )
#             bom_name = checked[0].name if checked else sorted([b.name for b in boms], reverse=True)[0]

#         bom = frappe.get_doc("BOM", bom_name)
#         used_boms.add(bom_name)

#         base_qty = flt(bom.quantity) or 1.0
#         for bi in bom.items:
#             total_qty = flt(bi.qty) / base_qty * flt(so_line.qty)
#             warehouse = bi.source_warehouse or so_line.warehouse
#             warehouse_qty = flt(frappe.db.get_value(
#                 "Bin",
#                 {"item_code": bi.item_code, "warehouse": warehouse},
#                 "actual_qty"
#             ) or 0.0)
#             warehouse_uom = frappe.db.get_value(
#                 "Bin",
#                 {"item_code": bi.item_code, "warehouse": warehouse},
#                 "stock_uom"
#             ) or None

#             # add raw material line
#             dn.append("custom_raw_material_items", {
#                 "item": bi.item_code,
#                 "uom": bi.uom,
#                 "qty": total_qty / bom.quantity,
#                 "warehouse": warehouse,
#                 "warehouse_qty": warehouse_qty,
#                 "weight": total_qty,
#                 "stock_uom": warehouse_uom,
#             })

#             # prepare Stock Entry line
#             material_issue_items.append({
#                 "item_code": bi.item_code,
#                 "qty": total_qty / bom.quantity,
#                 "uom": bi.uom,
#                 "stock_uom": bi.get("stock_uom"),
#                 "conversion_factor": flt(bi.get("conversion_factor", 1)),
#                 "s_warehouse": warehouse,
#             })

#     # 5️⃣ Record which BOMs were used
#     dn.custom_bom_used = ", ".join(sorted(used_boms))

#     # 6️⃣ Finalize DN (draft)
#     dn.insert(ignore_permissions=True)
#     frappe.msgprint(f"✅ Delivery Note created: {dn.name}")

#     # --- FG stock check (after dn.insert) ---
#     fg_ok = True
#     for line in dn.items:
#         available = flt(frappe.db.get_value(
#             "Bin",
#             {"item_code": line.item_code, "warehouse": line.warehouse},
#             "actual_qty"
#         ) or 0.0)
#         if available < flt(line.qty):
#             fg_ok = False
#             frappe.msgprint(
#                 f"⚠️ Insufficient stock for Finished Good {line.item_code}: "
#                 f"required {line.qty}, available {available}. DN stays Draft."
#             )
#             break

#     # --- Raw material stock check (before creating SE) ---
#     raw_ok = True
#     for mi in material_issue_items:
#         available = flt(frappe.db.get_value(
#             "Bin",
#             {"item_code": mi["item_code"], "warehouse": mi["s_warehouse"]},
#             "actual_qty"
#         ) or 0.0)
#         if available < flt(mi["qty"]):
#             raw_ok = False
#             frappe.msgprint(
#                 f"⚠️ Insufficient stock for Raw Material {mi['item_code']}: "
#                 f"required {mi['qty']}, available {available}. Stock Entry will be skipped."
#             )
#             break

#     # 7️⃣ Create & submit Material Issue only if **both** checks pass
#     if material_issue_items and fg_ok and raw_ok:
#         se = frappe.new_doc("Stock Entry")
#         se.stock_entry_type = "Material Issue"
#         se.purpose = "Material Issue"
#         se.company = doc.company
#         se.set_posting_time = 1
#         se.posting_date = today()
#         se.custom_linked_delivery_note = dn.name

#         for mi in material_issue_items:
#             se.append("items", mi)

#         se.insert(ignore_permissions=True)
#         se.submit()
#         dn.custom_stock_entry_linked = se.name
#         dn.custom_rm_stock_status = "Sufficient"
#         frappe.msgprint(f"✅ Stock Entry submitted: {se.name}")
#     else:
#         dn.custom_rm_stock_status = "Insufficient (Material Issue skipped)"

#     # 8️⃣ Submit or leave DN draft based on FG check
#     if fg_ok:
#         dn.custom_stock_status = "Sufficient"
#         dn.submit()
#         frappe.msgprint(f"✅ Delivery Note submitted: {dn.name}")
#     else:
#         dn.custom_stock_status = "Insufficient"
#         # already msgprinted above

#     dn.save(ignore_permissions=True)


def create_and_process_delivery_note(doc, method):
    # Only run for Shopify orders
    if not doc.shopify_order_id:
        return

    # ―――――――――――――――――――――――――――――――――
    #  UOM‐to‐base conversion map (all in grams)
    UOM_CONVERSION = {
        "g": 1,
        "gram": 1,
        "grams": 1,
        "gm": 1,
        "kg": 1000,
        "kgs": 1000,
        "kilogram": 1000,
        "kilograms": 1000,
    }

    def normalize_uom(uom_str):
        """
        Returns how many “base units (grams)” 1 unit of uom_str represents.
        If uom_str is unknown, fallback to 1.
        """
        return UOM_CONVERSION.get(uom_str.strip().lower(), 1)
    # ―――――――――――――――――――――――――――――――――

    # 1️⃣ Create a new Delivery Note as Draft
    dn = make_delivery_note(doc.name)

    # 2️⃣ Assign the very first Branch (by creation date)
    branch = frappe.get_all(
        "Branch",
        fields=["name"],
        limit_page_length=1,
        order_by="creation ASC"
    )
    if not branch:
        frappe.throw("No Branch found – cannot create Delivery Note.")
    dn.branch = branch[0].name

    # 3️⃣ Tag & stamp custom fields on the Delivery Note
    dn.custom_delivery_note_category = "Ecommerce-Blending"
    dn.set_posting_time = 1
    dn.posting_date = today()

    # 4️⃣ “Explode” each Sales Order line via its BOM
    material_issue_items = []  # we will build Stock Entry lines here
    used_boms = set()

    for so_line in doc.items:
        # Find active, submitted BOMs for this SO line’s item
        boms = frappe.get_all(
            "BOM",
            filters={"item": so_line.item_code, "is_active": 1, "docstatus": 1},
            fields=["name"]
        )
        if not boms:
            # No BOM for this item → skip
            continue

        # If exactly one BOM, pick it.
        # Otherwise, pick the BOM flagged with custom_sales_order_automation=1
        # (latest created), or fallback to highest‐lex name.
        if len(boms) == 1:
            bom_name = boms[0].name
        else:
            checked = frappe.get_all(
                "BOM",
                filters={
                    "item": so_line.item_code,
                    "custom_sales_order_automation": 1
                },
                fields=["name"],
                order_by="creation DESC",
                limit_page_length=1
            )
            if checked:
                bom_name = checked[0].name
            else:
                bom_name = sorted([b.name for b in boms], reverse=True)[0]

        bom = frappe.get_doc("BOM", bom_name)
        used_boms.add(bom_name)

        # “base_qty” is the quantity of FG that this BOM produces (in BOM’s UOM)
        base_qty = flt(bom.quantity) or 1.0

        # For each raw‐material row (bi) in this BOM:
        for bi in bom.items:
            # total_qty_in_bi_uom = (bi.qty / base_qty) × so_line.qty
            total_qty_in_bi_uom = flt(bi.qty) / base_qty * flt(so_line.qty)

            # Determine which warehouse to pull from
            warehouse = bi.source_warehouse or so_line.warehouse

            # “warehouse_qty” = actual_qty of Bin(item=bi.item_code, warehouse)
            warehouse_qty = flt(frappe.db.get_value(
                "Bin",
                {"item_code": bi.item_code, "warehouse": warehouse},
                "actual_qty"
            ) or 0.0)

            # “stock_uom” is the UOM in which the Bin holds stock for this item
            warehouse_uom = frappe.db.get_value(
                "Bin",
                {"item_code": bi.item_code, "warehouse": warehouse},
                "stock_uom"
            ) or None

            # ―――――――――――――――――――――――――――――――――
            # Compute normalized_qty (in “stock_uom”):
            #
            #   original_qty = total_qty_in_bi_uom   (this is in bi.uom)
            #   normalized_qty = original_qty × (factor(bi.uom)/factor(stock_uom))
            #
            # where factor(u) = how many grams 1 unit of that UOM represents.
            qty_factor = normalize_uom(bi.uom)
            stock_factor = normalize_uom(warehouse_uom)

            if stock_factor > 0:
                normalized_qty = total_qty_in_bi_uom * (qty_factor / stock_factor)
            else:
                # If warehouse_uom is missing/unrecognized, fallback:
                normalized_qty = total_qty_in_bi_uom
            # ―――――――――――――――――――――――――――――――――

            # Add a child‐row to custom_raw_material_items on the DN
            dn.append("custom_raw_material_items", {
                "item": bi.item_code,
                "uom": bi.uom,
                "qty": total_qty_in_bi_uom,
                "warehouse": warehouse,
                "warehouse_qty": warehouse_qty,
                "normalized_qty": normalized_qty,  # in stock_uom
                "weight": total_qty_in_bi_uom,
                "stock_uom": warehouse_uom,
            })

            # Prepare the Stock Entry “Material Issue” line using normalized_qty
            material_issue_items.append({
                "item_code": bi.item_code,
                "qty": normalized_qty,          # in stock_uom
                "uom": warehouse_uom,           # stock_uom
                "stock_uom": warehouse_uom,
                "conversion_factor": 1.0,        # already in stock_uom
                "s_warehouse": warehouse,
            })

    # 5️⃣ Record which BOMs were used (for traceability)
    dn.custom_bom_used = ", ".join(sorted(used_boms))

    # 6️⃣ Insert the Delivery Note as Draft
    dn.insert(ignore_permissions=True)
    frappe.msgprint(f"✅ Delivery Note created: {dn.name}")

    # ―――――――――――――――――――――――――――――――――
    # 7️⃣ Finished Good (FG) stock check (on dn.items):
    fg_ok = True
    for line in dn.items:
        available_fg = flt(frappe.db.get_value(
            "Bin",
            {"item_code": line.item_code, "warehouse": line.warehouse},
            "actual_qty"
        ) or 0.0)

        if available_fg < flt(line.qty):
            fg_ok = False
            frappe.msgprint(
                f"⚠️ Insufficient stock for Finished Good {line.item_code}: "
                f"required {line.qty}, available {available_fg}. DN will remain Draft."
            )
            break

    # 8️⃣ Raw Material (RM) stock check (on child table “custom_raw_material_items”):
    rm_ok = True
    for rm_row in dn.custom_raw_material_items:
        # If Bin’s available stock (warehouse_qty) is less than normalized_qty → insufficient
        if flt(rm_row.warehouse_qty) < flt(rm_row.normalized_qty):
            print("WAREHOUSE QTY AND NORMAL QTY",flt(rm_row.warehouse_qty),flt(rm_row.normalized_qty),"\n\n\n\n")
            rm_ok = False
            frappe.msgprint(
                f"⚠️ Insufficient stock for Raw Material {rm_row.item}:\n"
                f"→ Required ({rm_row.qty} {rm_row.uom}) "
                f"≈ {rm_row.normalized_qty:.2f} {rm_row.stock_uom},\n"
                f"→ Available {rm_row.warehouse_qty:.2f} {rm_row.stock_uom}.\n"
                f"Material Issue will be skipped."
            )
            break

    # 9️⃣ Create & Submit “Material Issue” Stock Entry only if both fg_ok and rm_ok are True
    if material_issue_items and fg_ok and rm_ok:
        se = frappe.new_doc("Stock Entry")
        se.stock_entry_type = "Material Issue"
        se.purpose = "Material Issue"
        se.company = doc.company
        se.set_posting_time = 1
        se.posting_date = today()
        se.custom_linked_delivery_note = dn.name

        for mi in material_issue_items:
            se.append("items", mi)

        se.insert(ignore_permissions=True)
        se.submit()

        dn.custom_stock_entry_linked = se.name
        dn.custom_rm_stock_status = "Sufficient"
        frappe.msgprint(f"✅ Stock Entry (Material Issue) submitted: {se.name}")
    else:
        print("fg and rm",fg_ok,rm_ok,"\n\n\n")
        if rm_ok:
            dn.custom_rm_stock_status = "Sufficient"
        else:
            dn.custom_rm_stock_status = "Insufficient"


    # 🔟 Finally, Submit or leave DN as Draft based on FG check
    if fg_ok:
        dn.custom_stock_status = "Sufficient"
        dn.submit()
        frappe.msgprint(f"✅ Delivery Note submitted: {dn.name}")
    else:
        dn.custom_stock_status = "Insufficient"
        # (The warning for FG insufficiency was already shown above.)

    # Save any custom fields that have changed
    dn.save(ignore_permissions=True)



def compute_bom_metrics(doc, method):

    try:
        # 1️⃣ Sum raw material qty
        total_raw_qty = flt(sum(flt(item.qty) for item in doc.items))
        doc.custom_total_raw_material_qty = total_raw_qty

        # 2️⃣ Get the RM to FG ratio
        ratio = doc.custom_fg_to_rm_weight_uom_ration
        if not ratio:
            frappe.msgprint("⚠️ 'custom_fg_to_rm_weight_uom_ration' is not set or zero.")
            return

        # 3️⃣ Normalize raw material qty into FG units
        normalized_rm_weight = total_raw_qty * ratio
        doc.custom_rm_weight_normalized = normalized_rm_weight

        # 4️⃣ Get actual FG weight
        fg_weight = doc.custom_item_weight*doc.quantity
        doc.custom_total_fg_weight= fg_weight

        # 5️⃣ Compute loss and percentage
        loss_qty = normalized_rm_weight - fg_weight
        #print(f"Debug ➤ Loss Qty: {normalized_rm_weight}-{fg_weight} {loss_qty}\n\n\n")
        doc.custom_qty_loss = loss_qty
        loss_percentage = flt((loss_qty / normalized_rm_weight * 100) if normalized_rm_weight else 0.0)
        doc.custom_loss_percentage = round(loss_percentage)

        frappe.msgprint(f"Debug ➤ FG Weight: {fg_weight}, Normalized RM: {normalized_rm_weight}")

        # ✅ Optional debug output
        
    except Exception as e:
        frappe.msgprint(f"❌ Error in compute_bom_metrics: {str(e)}")
        


def after_insert_customer(doc, method):
    # Step 1️⃣: Check if customer has Shopify Customer ID
    if not doc.shopify_customer_id:
        return  # Skip if no Shopify linkage

    # Step 2️⃣: Fetch values from "Additional Shopify Settings"
    settings = frappe.get_single("Additional Shopify Settings")
    company = settings.company
    customer_account = settings.customer_account

    # Step 3️⃣: If both fields are present
    if company and customer_account:
        # Step 4️⃣: Check if this account row already exists in Customer's accounts table
        already_exists = any(
            (row.company == company and row.account == customer_account)
            for row in doc.accounts
        )

        # Step 5️⃣: If not present, append new row
        if not already_exists:
            new_row = doc.append("accounts", {})
            new_row.company = company
            new_row.account = customer_account

            # Step 6️⃣: Save the updated Customer doc
            doc.save(ignore_permissions=True)
            frappe.db.commit()  # Commit to DB


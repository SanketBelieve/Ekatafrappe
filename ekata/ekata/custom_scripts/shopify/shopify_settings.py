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
#     try:
#         # Only run for Shopify orders
#         if not doc.shopify_order_id:
#             return

#         frappe.msgprint(f"🚀 Starting create_and_process_delivery_note for SO {doc.name}")

#         # ―――――――――――――――――――――――――――――――――
#         #  UOM‐to‐base conversion map (all in grams)
#         UOM_CONVERSION = {
#             "g": 1,
#             "gram": 1,
#             "grams": 1,
#             "gm": 1,
#             "kg": 1000,
#             "kgs": 1000,
#             "kilogram": 1000,
#             "kilograms": 1000,
#         }

#         def normalize_uom(uom_str):
#             """
#             Returns how many “base units (grams)” 1 unit of uom_str represents.
#             If uom_str is None or unknown, fallback to 1.
#             """
#             try:
#                 if not uom_str:
#                     frappe.log_error(
#                         title=f"normalize_uom: empty UOM in SO {doc.name}",
#                         message=frappe.get_traceback(),
#                     )
#                     return 1

#                 return UOM_CONVERSION.get(uom_str.strip().lower(), 1)

#             except Exception:
#                 frappe.log_error(
#                     title=f"normalize_uom error in SO {doc.name}",
#                     message=f"uom_str={uom_str}\n\n{frappe.get_traceback()}",
#                 )
#                 return 1

#         # 1️⃣ Create a new Delivery Note as Draft
#         dn = make_delivery_note(doc.name)

#         # 2️⃣ Assign the very first Branch (by creation date)
#         branch = frappe.get_all(
#             "Branch",
#             fields=["name"],
#             limit_page_length=1,
#             order_by="creation ASC",
#         )
#         if not branch:
#             frappe.throw("No Branch found – cannot create Delivery Note.")
#         dn.branch = branch[0].name

#         # 3️⃣ Tag & stamp custom fields on the Delivery Note
#         dn.custom_delivery_note_category = "Ecommerce-Blending"
#         dn.set_posting_time = 1
#         dn.posting_date = today()

#         # 4️⃣ “Explode” each Sales Order line via its BOM
#         material_issue_items = []
#         used_boms = set()

#         for so_line in doc.items:
#             try:
#                 # Find active, submitted BOMs for this SO line’s item
#                 boms = frappe.get_all(
#                     "BOM",
#                     filters={"item": so_line.item_code, "is_active": 1, "docstatus": 1},
#                     fields=["name"],
#                 )
#                 if not boms:
#                     frappe.log_error(
#                         title=f"No active BOM for item {so_line.item_code} in SO {doc.name}",
#                         message=frappe.get_traceback(),
#                     )
#                     continue

#                 # Pick BOM
#                 if len(boms) == 1:
#                     bom_name = boms[0].name
#                 else:
#                     checked = frappe.get_all(
#                         "BOM",
#                         filters={"item": so_line.item_code, "custom_sales_order_automation": 1},
#                         fields=["name"],
#                         order_by="creation DESC",
#                         limit_page_length=1,
#                     )
#                     if checked:
#                         bom_name = checked[0].name
#                     else:
#                         bom_name = sorted([b.name for b in boms], reverse=True)[0]

#                 bom = frappe.get_doc("BOM", bom_name)
#                 used_boms.add(bom_name)

#                 base_qty = flt(bom.quantity) or 1.0

#                 for bi in bom.items:
#                     total_qty_in_bi_uom = flt(bi.qty) / base_qty * flt(so_line.qty)

#                     warehouse = bi.source_warehouse or so_line.warehouse
#                     warehouse_qty = flt(
#                         frappe.db.get_value(
#                             "Bin",
#                             {"item_code": bi.item_code, "warehouse": warehouse},
#                             "actual_qty",
#                         )
#                         or 0.0
#                     )

#                     warehouse_uom = (
#                         frappe.db.get_value(
#                             "Bin",
#                             {"item_code": bi.item_code, "warehouse": warehouse},
#                             "stock_uom",
#                         )
#                         or ""
#                     )

#                     qty_factor = normalize_uom(bi.uom)
#                     stock_factor = normalize_uom(warehouse_uom)

#                     normalized_qty = (
#                         total_qty_in_bi_uom * (qty_factor / stock_factor)
#                         if stock_factor > 0
#                         else total_qty_in_bi_uom
#                     )

#                     dn.append(
#                         "custom_raw_material_items",
#                         {
#                             "item": bi.item_code,
#                             "uom": bi.uom,
#                             "qty": total_qty_in_bi_uom,
#                             "warehouse": warehouse,
#                             "warehouse_qty": warehouse_qty,
#                             "normalized_qty": normalized_qty,
#                             "weight": total_qty_in_bi_uom,
#                             "stock_uom": warehouse_uom,
#                         },
#                     )

#                     material_issue_items.append(
#                         {
#                             "item_code": bi.item_code,
#                             "qty": normalized_qty,
#                             "uom": warehouse_uom,
#                             "stock_uom": warehouse_uom,
#                             "conversion_factor": 1.0,
#                             "s_warehouse": warehouse,
#                         }
#                     )

#             except Exception:
#                 frappe.log_error(
#                     title=f"BOM processing error for item {so_line.item_code} in SO {doc.name}",
#                     message=frappe.get_traceback(),
#                 )
#                 continue

#         # 5️⃣ Record used BOMs
#         dn.custom_bom_used = ", ".join(sorted(used_boms))

#         # 6️⃣ Insert DN as Draft
#         dn.insert(ignore_permissions=True)
#         frappe.msgprint(f"✅ Delivery Note created: {dn.name}")

#         # 7️⃣ Finished Good (FG) stock check
#         fg_ok = True
#         for line in dn.items:
#             try:
#                 available_fg = flt(
#                     frappe.db.get_value(
#                         "Bin",
#                         {"item_code": line.item_code, "warehouse": line.warehouse},
#                         "actual_qty",
#                     )
#                     or 0.0
#                 )

#                 if available_fg < flt(line.qty):
#                     fg_ok = False
#                     frappe.msgprint(
#                         f"⚠️ Insufficient stock for Finished Good {line.item_code}: "
#                         f"required {line.qty}, available {available_fg}. DN will remain Draft."
#                     )
#                     break
#             except Exception:
#                 frappe.log_error(
#                     title=f"FG stock check error for item {line.item_code} in DN {dn.name}",
#                     message=frappe.get_traceback(),
#                 )
#                 fg_ok = False
#                 break

#         # 8️⃣ Raw Material (RM) stock check
#         rm_ok = True
#         for rm_row in dn.custom_raw_material_items:
#             try:
#                 if flt(rm_row.warehouse_qty) < flt(rm_row.normalized_qty):
#                     rm_ok = False
#                     frappe.msgprint(
#                         f"⚠️ Insufficient stock for Raw Material {rm_row.item}:\n"
#                         f"→ Required ({rm_row.qty} {rm_row.uom}) "
#                         f"≈ {rm_row.normalized_qty:.2f} {rm_row.stock_uom},\n"
#                         f"→ Available {rm_row.warehouse_qty:.2f} {rm_row.stock_uom}.\n"
#                         f"Material Issue will be skipped."
#                     )
#                     break
#             except Exception:
#                 frappe.log_error(
#                     title=f"RM stock check error for item {rm_row.item} in DN {dn.name}",
#                     message=frappe.get_traceback(),
#                 )
#                 rm_ok = False
#                 break

#         # 9️⃣ Create & Submit Stock Entry if fg_ok and rm_ok
#         if material_issue_items and fg_ok and rm_ok:
#             try:
#                 se = frappe.new_doc("Stock Entry")
#                 se.stock_entry_type = "Material Issue"
#                 se.purpose = "Material Issue"
#                 se.company = doc.company
#                 se.set_posting_time = 1
#                 se.posting_date = today()
#                 se.custom_linked_delivery_note = dn.name

#                 for mi in material_issue_items:
#                     se.append("items", mi)

#                 se.insert(ignore_permissions=True)
#                 se.submit()

#                 dn.custom_stock_entry_linked = se.name
#                 dn.custom_rm_stock_status = "Sufficient"
#                 frappe.msgprint(f"✅ Stock Entry (Material Issue) submitted: {se.name}")

#             except Exception:
#                 frappe.log_error(
#                     title=f"Stock Entry error in DN {dn.name}",
#                     message=f"SO {doc.name}\n\n{frappe.get_traceback()}",
#                 )
#                 dn.custom_rm_stock_status = "Error (See Logs)"
#         else:
#             if rm_ok:
#                 dn.custom_rm_stock_status = "Sufficient"
#             else:
#                 dn.custom_rm_stock_status = "Insufficient"

#         # 🔟 Finally, Submit or leave DN as Draft based on FG check
#         if fg_ok:
#             try:
#                 dn.custom_stock_status = "Sufficient"
#                 dn.submit()
#                 frappe.msgprint(f"✅ Delivery Note submitted: {dn.name}")
#             except Exception:
#                 frappe.log_error(
#                     title=f"DN submit error for DN {dn.name}",
#                     message=frappe.get_traceback(),
#                 )
#                 dn.custom_stock_status = "Error (See Logs)"
#         else:
#             dn.custom_stock_status = "Insufficient"

#         dn.save(ignore_permissions=True)
#         frappe.msgprint(f"✅ Delivery Note process finished for SO {doc.name}")

#     except Exception:
#         frappe.log_error(
#             title=f"Fatal error in create_and_process_delivery_note for SO {doc.name}",
#             message=frappe.get_traceback(),
#         )

def create_and_process_delivery_note(doc, method):
    try:
        # Only process Shopify orders
        if not doc.shopify_order_id:
            frappe.msgprint(f"⏭️ Skipping SO {doc.name}: no shopify_order_id")
            frappe.log_error(title="Skip Shopify hook", message=f"SO {doc.name} lacks shopify_order_id")
            return

        frappe.msgprint(f"🚀 Starting delivery note process for SO {doc.name}")

        # UOM conversion map (to grams)
        UOM_CONVERSION = {
            "g": 1, "gram": 1, "grams": 1, "gm": 1,
            "kg": 1000, "kgs": 1000, "kilogram": 1000, "kilograms": 1000,
        }
        def normalize_uom(uom_str):
            return UOM_CONVERSION.get((uom_str or "").strip().lower(), 1)

        # 1️⃣ Create a draft Delivery Note
        dn = make_delivery_note(doc.name)
        # default statuses (so they never stay blank)
        dn.custom_stock_status = "Insufficient"
        dn.custom_rm_stock_status = "Insufficient"
        frappe.msgprint(f"📋 Draft DN initiated: {dn.name}")

        # 2️⃣ Assign first-created Branch
        branch = frappe.get_all("Branch",
            fields=["name"],
            limit_page_length=1,
            order_by="creation ASC"
        )
        if not branch:
            frappe.msgprint("❌ No Branch found – cannot create DN.")
            frappe.log_error(title="Branch missing", message=f"SO {doc.name}: no Branch")
            return
        dn.branch = branch[0].name
        frappe.msgprint(f"🏷️ Branch set: {dn.branch}")

        # 3️⃣ Stamp custom fields
        dn.custom_delivery_note_category = "Ecommerce-Blending"
        dn.set_posting_time = 1
        dn.posting_date = today()
        frappe.msgprint("🕓 Custom fields stamped")

        # 4️⃣ “Explode” each SO line via BOM
        material_issue_items = []
        used_boms = set()
        for so_line in doc.items:
            try:
                boms = frappe.get_all("BOM",
                    filters={"item": so_line.item_code, "is_active": 1, "docstatus": 1},
                    fields=["name"]
                )
                if not boms:
                    frappe.msgprint(f"⚠️ No BOM for {so_line.item_code}")
                    continue

                # pick the right BOM
                if len(boms) == 1:
                    bom_name = boms[0].name
                else:
                    flagged = frappe.get_value("BOM",
                        {"item": so_line.item_code, "custom_sales_order_automation": 1},
                        "name"
                    )
                    bom_name = flagged or sorted([b.name for b in boms], reverse=True)[0]

                bom = frappe.get_doc("BOM", bom_name)
                used_boms.add(bom_name)
                base_qty = flt(bom.quantity) or 1.0

                for bi in bom.items:
                    qty = flt(bi.qty) / base_qty * flt(so_line.qty)
                    wh = bi.source_warehouse or so_line.warehouse
                    wh_qty = flt(frappe.db.get_value("Bin",
                        {"item_code": bi.item_code, "warehouse": wh},
                        "actual_qty"
                    ) or 0.0)
                    wh_uom = frappe.db.get_value("Bin",
                        {"item_code": bi.item_code, "warehouse": wh},
                        "stock_uom"
                    ) or bi.uom
                    norm_qty = qty * (normalize_uom(bi.uom) / normalize_uom(wh_uom))

                    # add to raw material table
                    dn.append("custom_raw_material_items", {
                        "item": bi.item_code,
                        "uom": bi.uom,
                        "qty": qty,
                        "warehouse": wh,
                        "warehouse_qty": wh_qty,
                        "normalized_qty": norm_qty,
                        "weight": qty,
                        "stock_uom": wh_uom,
                    })

                    # prepare Stock Entry lines
                    material_issue_items.append({
                        "item_code": bi.item_code,
                        "qty": norm_qty,
                        "uom": wh_uom,
                        "stock_uom": wh_uom,
                        "conversion_factor": 1.0,
                        "s_warehouse": wh,
                    })

                frappe.msgprint(f"✅ BOM {bom_name} processed for {so_line.item_code}")

            except Exception:
                err = frappe.get_traceback()
                frappe.log_error(title=f"BOM error for {so_line.item_code}", message=err)
                frappe.msgprint(f"❌ Error on BOM {so_line.item_code}, see error log")

        dn.custom_bom_used = ", ".join(sorted(used_boms)) or "None"
        dn.insert(ignore_permissions=True)
        frappe.msgprint(f"📝 Draft DN saved: {dn.name}")

        # 5️⃣ FG stock check
        fg_ok = True
        for it in dn.items:
            avail = flt(frappe.db.get_value("Bin",
                {"item_code": it.item_code, "warehouse": it.warehouse},
                "actual_qty"
            ) or 0.0)
            if avail < flt(it.qty):
                fg_ok = False
                frappe.msgprint(f"⚠️ FG short for {it.item_code}: needed {it.qty}, have {avail}")
                break

        # set FG status independently
        dn.custom_stock_status = "Sufficient" if fg_ok else "Insufficient"
        frappe.msgprint(f"📦 Finished Goods status: {dn.custom_stock_status}")

        # 6️⃣ RM stock check
        rm_ok = True
        for rm in dn.custom_raw_material_items:
            if flt(rm.warehouse_qty) < flt(rm.normalized_qty):
                rm_ok = False
                frappe.msgprint(f"⚠️ RM short for {rm.item}: needed {rm.normalized_qty:.2f}, have {rm.warehouse_qty:.2f}")
                break

        # set RM status independently
        dn.custom_rm_stock_status = "Sufficient" if rm_ok else "Insufficient"
        frappe.msgprint(f"🔧 Raw Materials status: {dn.custom_rm_stock_status}")

        # 7️⃣ Create & submit Stock Entry if both OK
        if fg_ok and rm_ok and material_issue_items:
            try:
                se = frappe.new_doc("Stock Entry")
                se.stock_entry_type = se.purpose = "Material Issue"
                se.company = doc.company
                se.set_posting_time = 1
                se.posting_date = today()
                se.custom_linked_delivery_note = dn.name

                for mi in material_issue_items:
                    se.append("items", mi)

                acc = frappe.db.get_value("Company", doc.company, "default_expense_account")
                if acc:
                    se.difference_account = acc

                se.insert(ignore_permissions=True)
                se.submit()
                dn.custom_stock_entry_linked = se.name
                frappe.msgprint(f"✅ Stock Entry created: {se.name}")
            except Exception:
                err = frappe.get_traceback()
                frappe.log_error(title=f"Stock Entry error for {dn.name}", message=err)
                frappe.msgprint("❌ Failed to create Stock Entry, see error log")

        else:
            frappe.msgprint("⏭️ Skipping Stock Entry: insufficient stock or no items to issue")

        # 8️⃣ Submit DN if FG ok, otherwise leave draft
        if fg_ok:
            try:
                dn.submit()
                frappe.msgprint(f"✅ Delivery Note submitted: {dn.name}")
            except Exception:
                err = frappe.get_traceback()
                frappe.log_error(title=f"DN submit error {dn.name}", message=err)
                frappe.msgprint("❌ Failed to submit DN, see error log")
        else:
            frappe.msgprint("⏭️ DN remains Draft due to FG shortage")

        # Final save to persist everything
        dn = frappe.get_doc("Delivery Note", dn.name)
        dn.save(ignore_permissions=True)
        frappe.msgprint("🎉 Delivery Note process complete!")

    except Exception:
        err = frappe.get_traceback()
        frappe.log_error(title=f"Fatal hook error for SO {doc.name}", message=err)
        frappe.msgprint("🚨 Fatal error – check error log")





def after_insert_customer(doc, method):

    # Step 1️⃣: Check if customer has Shopify Customer ID
    if not doc.shopify_customer_id:
        return  # Skip if no Shopify linkage

    # Step 2️⃣: Fetch values from "Additional Shopify Settings"
    settings = frappe.get_single("Additional Shopify Settings")
    company = settings.company
    customer_account = settings.customer_account
    frappe.log_error(f"❌ customer_name {doc.customer_name}", "Shopify Customer Note Automation")
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

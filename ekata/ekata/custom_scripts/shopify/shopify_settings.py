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


def create_and_process_delivery_note(doc, method):
    # Only for Shopify orders
    if not doc.shopify_order_id:
        return

    # 1️⃣ Create DN draft
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

    # 4️⃣ Explode each SO line via its BOM
    material_issue_items = []
    used_boms = set()

    for so_line in doc.items:
        boms = frappe.get_all(
            "BOM",
            filters={"item": so_line.item_code, "is_active": 1, "docstatus": 1},
            fields=["name"]
        )
        if not boms:
            continue

        if len(boms) == 1:
            bom_name = boms[0].name
            dn.custom_loss_percent = flt(boms[0].custom_loss_percentage)
        else:
            checked = frappe.get_all(
                "BOM",
                filters={"item": so_line.item_code, "custom_sales_order_automation": 1},
                fields=["name","custom_loss_percentage"],
                order_by="creation DESC",
                limit_page_length=1
            )
            bom_name = checked[0].name if checked else sorted([b.name for b in boms], reverse=True)[0]

        bom = frappe.get_doc("BOM", bom_name)
        used_boms.add(bom_name)

        base_qty = flt(bom.quantity) or 1.0
        for bi in bom.items:
            total_qty = flt(bi.qty) / base_qty * flt(so_line.qty)
            warehouse = bi.source_warehouse or so_line.warehouse
            warehouse_qty = flt(frappe.db.get_value(
                "Bin",
                {"item_code": bi.item_code, "warehouse": warehouse},
                "actual_qty"
            ) or 0.0)
            # ➡️ Add raw material line
            dn.append("custom_raw_material_items", {
                "item": bi.item_code,
                "uom": bi.uom,
                "qty": total_qty/bom.quantity,
                "warehouse": warehouse,
                "warehouse_qty": warehouse_qty,
                "weight": total_qty,
               
            })

            # 📝 Prepare Stock Entry line
            material_issue_items.append({
                "item_code": bi.item_code,
                "qty": total_qty/bom.quantity,
                "uom": bi.uom,
                "stock_uom": bi.get("stock_uom"),
                "conversion_factor": flt(bi.get("conversion_factor", 1)),
                "s_warehouse": warehouse,
            })

    # 5️⃣ Record which BOMs were used
    dn.custom_bom_used = ", ".join(sorted(used_boms))
    

    # 6️⃣ Finalize Delivery Note
    dn.insert(ignore_permissions=True)
    dn.submit()
    frappe.msgprint(f"✅ Delivery Note created: {dn.name}")

    # 7️⃣ Create draft Material Issue
    if material_issue_items:
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
        dn.custom_stock_entry_linked = se.name
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

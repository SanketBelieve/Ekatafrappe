import frappe
from frappe.utils import today, flt
from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note

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
    if not doc.shopify_order_id:
        return

    # Step 1: Create Delivery Note (finished goods only)
    dn = make_delivery_note(doc.name)

    branch = frappe.get_all("Branch", fields=["name"], limit_page_length=1, order_by="creation ASC")
    if not branch:
        frappe.throw("No Branch found – cannot create Delivery Note.")
    dn.branch = branch[0].name

    dn.custom_delivery_note_category = "Ecommerce-Blending"
    dn.set_posting_time = 1
    dn.posting_date = today()

    dn.insert(ignore_permissions=True)
    dn.submit()
    frappe.msgprint(f"✅ Delivery Note created and submitted: {dn.name}")

    # Step 2: BOM explosion → Material Issue + Raw Material Data
    material_issue_items = []
    total_weight = 0.0
    weight_uom = None
    used_bom_names = set()

    for line in doc.items:
        boms = frappe.get_all("BOM", filters={"item": line.item_code, "is_active": 1, "docstatus": 1}, fields=["name"])
        if not boms:
            continue

        # Smart BOM selection
        if len(boms) == 1:
            bom_name = boms[0].name
        else:
            checked_bom = frappe.get_all(
                "BOM",
                filters={
                    "item": line.item_code,
                    "is_active": 1,
                    "docstatus": 1,
                    "custom_sales_order_automation": 1
                },
                fields=["name"],
                order_by="creation DESC",
                limit_page_length=1
            )
            if checked_bom:
                bom_name = checked_bom[0].name
            else:
                latest_bom = frappe.get_all(
                    "BOM",
                    filters={"item": line.item_code, "is_active": 1, "docstatus": 1},
                    fields=["name"],
                    order_by="creation DESC",
                    limit_page_length=1
                )
                if not latest_bom:
                    frappe.throw(f"No valid BOM found for {line.item_code}")
                bom_name = latest_bom[0].name

        bom = frappe.get_doc("BOM", bom_name)
        base_qty = flt(bom.quantity) or 1.0
        used_bom_names.add(bom_name)

        for bi in bom.items:
            qty_per_unit = flt(bi.qty) / base_qty
            total_qty = flt(qty_per_unit * flt(line.qty))

            material_issue_items.append({
                "item_code": bi.item_code,
                "qty": total_qty,
                "uom": bi.uom,
                "stock_uom": bi.get("stock_uom"),
                "conversion_factor": flt(bi.get("conversion_factor", 1)),
                "s_warehouse": bi.get("source_warehouse") or line.warehouse
            })

            raw_item_row = {
                "item": bi.item_code,
                "uom": bi.uom,
                "qty": total_qty
            }

            if bi.uom and bi.uom.lower() in ("kg", "kgs", "kilogram", "kilograms", "gram", "grams", "g", "ton", "tons", "tonne", "tonnes"):
                factor = get_weight_conversion_factor(bi.uom)
                raw_item_row["weight"] = total_qty
                total_weight += total_qty * factor
                if not weight_uom:
                    weight_uom = "Kg"

            dn.append("custom_raw_material_items", raw_item_row)

        # Set raw material weight loss from BOM
        if hasattr(bom, "custom_raw_material_weight_loss"):
            dn.custom_loss_percent = bom.custom_raw_material_weight_loss

    # Set weight & BOM fields
    if total_weight:
        dn.custom_raw_material_weight = total_weight
        dn.custom_raw_material_weight_uom = weight_uom or "Kg"

    # Save BOMs used as comma-separated list
    if used_bom_names:
        dn.custom_bom_used = ", ".join(sorted(used_bom_names))

    dn.save(ignore_permissions=True)

    # Step 3: Create Material Issue as draft
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

        se.insert(ignore_permissions=True)  # 👈 Draft only
        frappe.msgprint(f"📦 Draft Material Issue created: {se.name}")

        dn.custom_stock_entry_linked = se.name
        dn.save(ignore_permissions=True)


def get_weight_conversion_factor(uom):
    """Convert any weight UOM to KG"""
    uom = (uom or "").strip().lower()
    if uom in ("kg", "kgs", "kilogram", "kilograms"):
        return 1
    elif uom in ("gram", "grams", "g"):
        return 0.001
    elif uom in ("ton", "tons", "tonne", "tonnes"):
        return 1000
    else:
        return 1  # fallback
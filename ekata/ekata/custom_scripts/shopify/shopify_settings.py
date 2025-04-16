import frappe

def handle_sales_order(doc, method):
    if doc.shopify_order_id:
        settings = frappe.get_single("Additional Shopify Settings")
        if settings.sales_order_cost_center:
            doc.cost_center = settings.sales_order_cost_center
            for item in doc.items:
                item.cost_center = settings.sales_order_cost_center
            doc.save(ignore_permissions=True)
            frappe.msgprint("✅ Cost Center from Shopify Settings applied to Sales Order")



def handle_sales_invoice(doc, method):
    if doc.shopify_order_id:
        settings = frappe.get_single("Additional Shopify Settings")

        # 🌏 Set supply info
        doc.supply = doc.place_of_supply
        doc.country_of_origin_of_goods = "India"

        # 🧾 Set `debit_to` and cost center
        if settings.sales_invoice_debit_to:
            doc.debit_to = settings.sales_invoice_debit_to
        if settings.sales_order_cost_center:
            doc.cost_center = settings.sales_order_cost_center

        for item in doc.items:
            # 💰 Income account
            if settings.income_account:
                item.income_account = settings.income_account

            # 🏢 Cost center
            if settings.sales_order_cost_center:
                item.cost_center = settings.sales_order_cost_center

            # 🇮🇳 Country of origin
         

        doc.save(ignore_permissions=True)
        frappe.msgprint("✅ Shopify fields applied: Debit To, Income Account, Cost Center, Place of Supply, Country of Origin 🇮🇳")



def handle_payment_entry(doc, method):
    settings = frappe.get_single("Additional Shopify Settings")

    for ref in doc.references:
        if ref.reference_doctype == "Sales Invoice":
            invoice = frappe.get_doc("Sales Invoice", ref.reference_name)
            if invoice.shopify_order_id and settings.paid_from_account:
                doc.paid_from = settings.paid_from_account
                doc.save(ignore_permissions=True)
                frappe.msgprint("✅ Paid From Account set from Shopify Settings")
                break


import frappe

def handle_sales_order(doc, method):
    if doc.shopify_order_id:
        settings = frappe.get_single("Additional Shopify Settings")

        # 📊 Cost Center
        if settings.sales_order_cost_center:
            doc.cost_center = settings.sales_order_cost_center
            for item in doc.items:
                item.cost_center = settings.sales_order_cost_center

        # 📜 Terms & Conditions (tc_name)
        if settings.terms_of_delivery_and_payment:
            doc.tc_name = settings.terms_of_delivery_and_payment

        # 💳 Payment Terms
        if settings.payment_terms:
            doc.payment_terms_template = settings.payment_terms

        doc.save(ignore_permissions=True)
        frappe.msgprint("✅ Shopify settings applied to Sales Order: Cost Center, Terms & Conditions, Payment Terms")


def handle_sales_invoice(doc, method):
    if doc.shopify_order_id:
        settings = frappe.get_single("Additional Shopify Settings")

        # 🌏 Supply Info
        doc.supply = doc.place_of_supply
        doc.country_of_origin_of_goods = "India"

        # 📜 Terms & Conditions (tc_name)
        if settings.terms_of_delivery_and_payment:
            doc.tc_name = settings.terms_of_delivery_and_payment

        # 💳 Payment Terms
        if settings.payment_terms:
            doc.payment_terms_template = settings.payment_terms

        # 🧾 Debit To & Cost Center
        if settings.sales_invoice_debit_to:
            doc.debit_to = settings.sales_invoice_debit_to
        if settings.sales_order_cost_center:
            doc.cost_center = settings.sales_order_cost_center

        # 🔄 Items: Income Account & Cost Center
        for item in doc.items:
            if settings.income_account:
                item.income_account = settings.income_account
            if settings.sales_order_cost_center:
                item.cost_center = settings.sales_order_cost_center

        doc.save(ignore_permissions=True)
        frappe.msgprint("✅ Shopify settings applied to Sales Invoice: Supply Info, Cost Center, Income Account, Terms & Conditions, Payment Terms")


def handle_payment_entry(doc, method):
    settings = frappe.get_single("Additional Shopify Settings")

    # 📜 Terms of Delivery & Payment (always 100% Advance)
    doc.terms_of_delivery_and_payment = "100% Advance with order conformation"

    # 💳 Mode of Payment
    if settings.mode_of_payment:
        doc.mode_of_payment = settings.mode_of_payment

    # 🏦 Paid From (if against a Shopify invoice)
    for ref in doc.references:
        if ref.reference_doctype == "Sales Invoice":
            invoice = frappe.get_doc("Sales Invoice", ref.reference_name)
            if invoice.shopify_order_id and settings.paid_from_account:
                doc.paid_from = settings.paid_from_account
                break

    doc.save(ignore_permissions=True)
    frappe.msgprint("✅ Shopify settings applied to Payment Entry: Terms of Delivery, Mode of Payment, Paid From Account")

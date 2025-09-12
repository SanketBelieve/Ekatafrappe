# Copyright (c) 2025, kiran.c@indictrans.in and contributors
# For license information, please see license.txt

# Copyright (c) 2025
# For Script Report: Customer Receivables by Customer Group

import frappe
from frappe import _

def execute(filters=None):
    if not filters:
        filters = {}

    columns = get_columns()
    data = get_data(filters)

    return columns, data


def get_columns():
    return [
        {
            "label": _("Customer Group"),
            "fieldname": "customer_group",
            "fieldtype": "Data",
            "width": 200,
        },
        {
            "label": _("Receivables"),
            "fieldname": "receivables",
            "fieldtype": "Currency",
            "width": 200,
        },
    ]


def get_conditions(filters):
    conditions = ["gle.docstatus = 1", "acc.account_type = 'Receivable'"]

    if filters.get("from_date"):
        conditions.append("gle.posting_date >= %(from_date)s")
    if filters.get("to_date"):
        conditions.append("gle.posting_date <= %(to_date)s")
    if filters.get("customer_group"):
        conditions.append("cust.customer_group = %(customer_group)s")

    return " AND ".join(conditions)


def get_data(filters):
    conditions = get_conditions(filters)

    query = f"""
        SELECT
            COALESCE(cust.customer_group, 'Unspecified') AS customer_group,
            SUM(gle.debit - gle.credit) AS receivables
        FROM `tabGL Entry` gle
        JOIN `tabAccount` acc ON gle.account = acc.name
        JOIN `tabCustomer` cust ON gle.party_type = 'Customer' AND gle.party = cust.name
        WHERE {conditions}
        GROUP BY cust.customer_group
        ORDER BY receivables DESC
    """

    return frappe.db.sql(query, filters, as_dict=True)

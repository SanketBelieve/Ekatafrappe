# Copyright (c) 2025, kiran.c@indictrans.in and contributors
# For license information, please see license.txt

# Copyright (c) 2025
# For Script Report: Supplier Payables by Supplier Group

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
            "label": _("Supplier Group"),
            "fieldname": "supplier_group",
            "fieldtype": "Data",
            "width": 200,
        },
        {
            "label": _("Payables"),
            "fieldname": "payables",
            "fieldtype": "Currency",
            "width": 200,
        },
    ]


def get_conditions(filters):
    conditions = ["gle.docstatus = 1", "acc.account_type = 'Payable'"]

    if filters.get("from_date"):
        conditions.append("gle.posting_date >= %(from_date)s")
    if filters.get("to_date"):
        conditions.append("gle.posting_date <= %(to_date)s")
    if filters.get("supplier_group"):
        conditions.append("sup.supplier_group = %(supplier_group)s")

    return " AND ".join(conditions)


def get_data(filters):
    conditions = get_conditions(filters)

    query = f"""
        SELECT
            COALESCE(sup.supplier_group, 'Unspecified') AS supplier_group,
            SUM(gle.credit - gle.debit) AS payables
        FROM `tabGL Entry` gle
        JOIN `tabAccount` acc ON gle.account = acc.name
        JOIN `tabSupplier` sup ON gle.party_type = 'Supplier' AND gle.party = sup.name
        WHERE {conditions}
        GROUP BY sup.supplier_group
        ORDER BY payables DESC
    """

    return frappe.db.sql(query, filters, as_dict=True)

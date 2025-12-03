# Copyright (c) 2025, kiran.c@indictrans.in and contributors
# For license information, please see license.txt

# import frappe


import frappe
def execute(filters=None):
    filters = filters or {}

    employee = filters.get("employee")
    from_date = filters.get("from_date")
    to_date = filters.get("to_date")

    columns = [
        {"label": "Employee", "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 150},
        {"label": "Employee Name", "fieldname": "employee_name", "fieldtype": "Data", "width": 200},
        {"label": "Leave Type", "fieldname": "leave_type", "fieldtype": "Data", "width": 150},
        {"label": "Total Leave Days", "fieldname": "total_leave_days", "fieldtype": "Float", "width": 150},
    ]

    conditions = "WHERE la.leave_type = 'Leave Without Pay' AND la.docstatus = 1 AND e.status = 'Active'"

    if employee:
        conditions += " AND la.employee = %(employee)s"

    if from_date:
        conditions += " AND la.from_date >= %(from_date)s"

    if to_date:
        conditions += " AND la.to_date <= %(to_date)s"

    data = frappe.db.sql(f"""
        SELECT DISTINCT
            la.employee,
            e.employee_name,
            la.leave_type,
            la.total_leave_days
        FROM `tabLeave Application` la
        LEFT JOIN `tabEmployee` e ON la.employee = e.name
        {conditions}
    """, filters, as_dict=True)

    return columns, data

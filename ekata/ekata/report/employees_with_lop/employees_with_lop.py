# Copyright (c) 2025, kiran.c@indictrans.in and contributors
# For license information, please see license.txt

# import frappe


import frappe

def execute(filters=None):
    filters = filters or {}
    employee = filters.get("employee", "")

    columns = [
        {"label": "Employee", "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 150},
        {"label": "Employee Name", "fieldname": "employee_name", "fieldtype": "Data", "width": 200},
        {"label": "Leave Type", "fieldname": "leave_type", "fieldtype": "Data", "width": 150},
        {"label": "Total Leave Days", "fieldname": "total_leave_days", "fieldtype": "Float", "width": 150},
    ]

    condition = ""
    if employee:
        condition = " AND la.employee = %(employee)s"

    data = frappe.db.sql(f"""
        SELECT DISTINCT
            la.employee,
            e.employee_name,
            la.leave_type,
            la.total_leave_days
        FROM `tabLeave Application` la
        LEFT JOIN `tabEmployee` e ON la.employee = e.name
        WHERE la.leave_type = 'Leave Without Pay'
        AND la.docstatus = 1
        AND e.status = 'Active'
        {condition}
    """, {"employee": employee}, as_dict=True)

    return columns, data

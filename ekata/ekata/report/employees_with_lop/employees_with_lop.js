// Copyright (c) 2025, kiran.c@indictrans.in and contributors
// For license information, please see license.txt

frappe.query_reports["Employees with LOP"] = {
    "filters": [
        {
            "fieldname": "from_date",
            "label": "From Date",
            "fieldtype": "Date"
        },
        {
            "fieldname": "to_date",
            "label": "To Date",
            "fieldtype": "Date"
        },
        {
            "fieldname": "employee",
            "label": "Employee",
            "fieldtype": "Link",
            "options": "Employee"
        }
    ]
}
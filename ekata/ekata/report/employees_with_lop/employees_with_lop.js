// Copyright (c) 2025, kiran.c@indictrans.in and contributors
// For license information, please see license.txt

frappe.query_reports["Employees with LOP"] = {
	"filters": [
        {
            "fieldname": "employee",
            "label": __("Employee"),
            "fieldtype": "Link",
            "options": "Employee",
            "reqd": 0
        }
    ]
};

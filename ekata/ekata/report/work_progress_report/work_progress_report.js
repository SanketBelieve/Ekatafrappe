// Copyright (c) 2025, kiran.c@indictrans.in and contributors
// For license information, please see license.txt

frappe.query_reports["Work Progress Report"] = {
    // 1. Define your filters here
    filters: [
        {
            fieldname: "employee",
            label: __("Employee"),
            fieldtype: "Link",
            options: "Employee"
        },
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            default: frappe.datetime.get_today()
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            default: frappe.datetime.get_today()
        }
    ],

    // 2. Refresh on change
    on_change: function() {
        this.refresh();
    }
};

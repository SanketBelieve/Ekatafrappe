frappe.query_reports["Buying Report"] = {
    "filters": [
        {
            "fieldname": "from_date",
            "label": __("From Date"),
            "fieldtype": "Date",
            "reqd": 1,
        },
        {
            "fieldname": "to_date",
            "label": __("To Date"),
            "fieldtype": "Date",
            "reqd": 1,
        },
        {
            "fieldname": "buying_category",
            "label": __("Buying Category"),
            "fieldtype": "Select",
            "options": "\nDirect Buying\nIndirect Buying\nAll",
            "default": "All"
        },
        {
            "fieldname": "show_detail",
            "label": __("Show Detail"),
            "fieldtype": "Check",
            "default": 0
        }
    ]
};
